# import random
# import socket
# import threading
# import time
# import math
# import os
# from logger import Logger
# from config import Config

# BUFFER_SIZE = 1024
# NUM_PIECES = 306  # This will be calculated based on file size and piece size

# # Decodes an integer into message type
# MESSAGE_TYPE_DECODE = {
#     "0": "choke",
#     "1": "unchoke",
#     "2": "interested",
#     "3": "not interested",
#     "4": "have",
#     "5": "bitfield",
#     "6": "request",
#     "7": "piece",
# }

# MESSAGE_TYPE_ENCODE = {
#     "choke": "0",
#     "unchoke": "1",
#     "interested": "2",
#     "not interested": "3",
#     "have": "4",
#     "bitfield": "5",
#     "request": "6",
#     "piece": "7",
# }

# # 1. Improved Message class to handle binary data
# class Message:
#     def __init__(self, message_type, message_payload=b""):
#         # Handle binary payload differently
#         if isinstance(message_payload, bytes):
#             self.is_binary = True
#             self.message_length = len(message_payload) + 1  # +1 for message type
#             self.decoded_message_type = message_type
#             self.encoded_message_type = MESSAGE_TYPE_ENCODE[message_type].encode('utf-8')
#             self.message_payload = message_payload
#         else:
#             self.is_binary = False
#             self.message_length = len(message_payload) + 1  # +1 for message type
#             self.decoded_message_type = message_type
#             self.encoded_message_type = MESSAGE_TYPE_ENCODE[message_type]
#             self.message_payload = message_payload

#         # Ensure message_length is 4 bytes by padding with zeros
#         self.message_length_bytes = str(self.message_length).zfill(4).encode('utf-8')

#     def get_message(self):
#         if self.is_binary:
#             # For binary data, return bytes directly
#             return self.message_length_bytes + self.encoded_message_type + self.message_payload
#         else:
#             # For text data, encode as before
#             message_length_str = str(self.message_length).zfill(4)
#             return (message_length_str + self.encoded_message_type + self.message_payload).encode('utf-8')


# class Peer:
#     # Will be used to store information on peers
#     def __init__(self, socket_number, ID):
#         self.socket = socket_number
#         self.ID = ID
#         self.bitfield = "0" * NUM_PIECES
#         self.complete = False
#         self.interested = False
#         self.choked = True
#         self.last_download_rate = 0  # For preferred neighbor selection
#         self.pieces_downloaded = 0  # Track how many pieces downloaded from this peer

# class Client:
#     def __init__(self, config_filepath, host, port, ID="1001"):
#         # Initialize with empty bitfield and peer list
#         self.host = host
#         self.port = int(port)
#         self.peers = []
#         self.unchoked_peers = []
#         self.optimistically_unchoked_peer = None
#         self.ID = ID
#         self.logger = Logger(ID)
#         self.config = Config(config_filepath)
#         self.other_peers = []  # Will be used for establishing connections
        
#         # Calculate the number of pieces based on file size and piece size
#         global NUM_PIECES
#         NUM_PIECES = math.ceil(self.config.file_size / self.config.piece_size)
        
#         self.bitfield = "0" * NUM_PIECES
        
#         # Create peer directory if it doesn't exist
#         self.peer_directory = f"peer_{self.ID}"
#         if not os.path.exists(self.peer_directory):
#             os.makedirs(self.peer_directory)
            
#         # Initialize file pieces as empty
#         self.file_pieces = [None] * NUM_PIECES
#         self.pieces_requested = [False] * NUM_PIECES
        
#         # For selecting preferred neighbors
#         self.download_rates = {}
#         self.interested_peers = []
        
#         # For thread synchronization
#         self.peers_lock = threading.Lock()
#         self.bitfield_lock = threading.Lock()
#         self.file_pieces_lock = threading.Lock()
        
#         # For threading control
#         self.running = True
        
#         # Debug info
#         print(f"Client initialized with:")
#         print(f"  - ID: {ID}")
#         print(f"  - Host: {host}")
#         print(f"  - Port: {port}")
#         print(f"  - Config: {config_filepath}")
#         print(f"  - Pieces: {NUM_PIECES}")
#         print(f"  - Peer directory: {self.peer_directory}")
        
#     def has_file(self):
#         """If this peer has the file, update its bitfield and read file into memory"""
#         # Check for file in various possible locations
#         file_paths = [
#             os.path.join(self.peer_directory, self.config.file_name),
#             os.path.join("project_config_file_small/project_config_file_small", self.ID, self.config.file_name),
#             os.path.join("project_config_file_small", self.ID, self.config.file_name),
#             self.config.file_name
#         ]
        
#         file_found = False
#         for path in file_paths:
#             if os.path.exists(path):
#                 print(f"Found file at: {path}")
#                 file_found = True
#                 # Read file into memory in pieces
#                 with open(path, 'rb') as f:
#                     for i in range(NUM_PIECES):
#                         try:
#                             f.seek(i * self.config.piece_size)
#                             piece_data = f.read(self.config.piece_size)
#                             if piece_data:
#                                 self.file_pieces[i] = piece_data
#                         except Exception as e:
#                             print(f"Error reading piece {i}: {e}")
                
#                 # Copy file to peer directory if it's not already there
#                 if path != os.path.join(self.peer_directory, self.config.file_name):
#                     os.makedirs(self.peer_directory, exist_ok=True)
#                     import shutil
#                     shutil.copy2(path, os.path.join(self.peer_directory, self.config.file_name))
#                     print(f"Copied file to peer directory: {self.peer_directory}")
                
#                 # Update bitfield
#                 self.bitfield = "1" * NUM_PIECES
#                 break
        
#         if not file_found:
#             print(f"Warning: File {self.config.file_name} not found in any expected locations!")
#             self.bitfield = "0" * NUM_PIECES
            
#     def setup(self, other_peers):
#         """Initialize server socket and connect to existing peers"""
#         # Start preferred neighbors selection thread
#         threading.Thread(target=self.select_preferred_neighbors, daemon=True).start()
        
#         # Start optimistically unchoked neighbor selection thread
#         threading.Thread(target=self.select_optimistically_unchoked_neighbor, daemon=True).start()
        
#         # Start server socket to listen for incoming connections
#         threading.Thread(target=self.listen_for_connections, daemon=True).start()
        
#         # Connect to existing peers
#         self.initiate_connections(other_peers)
        
#     def listen_for_connections(self):
#         """Set up listening socket and accept incoming connections"""
#         self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         try:
#             # Always listen on localhost regardless of configured host
#             listen_host = "127.0.0.1" if self.host not in ["localhost", "127.0.0.1"] else self.host
#             self.s.bind((listen_host, self.port))
#             self.s.listen(10)
#             print(f"Listening on {listen_host}:{self.port} (configured host was {self.host})")
            
#             while self.running:
#                 try:
#                     # Wait for connections and set them up
#                     peer_socket, peer_address = self.s.accept()
#                     print(f"Accepted connection from {peer_address}")
#                     threading.Thread(target=self.setup_connection_from_listening,
#                                     args=(peer_socket, peer_address), daemon=True).start()
#                 except socket.error as e:
#                     if not self.running:
#                         break
#                     print(f"Socket accept error: {e}")
#         except socket.error as e:
#             print(f"Socket binding error: {e}")
#             print("Trying alternative port...")
#             # Try an alternative port
#             try:
#                 alt_port = self.port + 1000  # Try a port 1000 higher
#                 self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#                 self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#                 self.s.bind((listen_host, alt_port))
#                 self.s.listen(10)
#                 self.port = alt_port  # Update the port
#                 print(f"Listening on {listen_host}:{alt_port} (alternative port)")
                
#                 while self.running:
#                     try:
#                         # Wait for connections and set them up
#                         peer_socket, peer_address = self.s.accept()
#                         print(f"Accepted connection from {peer_address}")
#                         threading.Thread(target=self.setup_connection_from_listening,
#                                         args=(peer_socket, peer_address), daemon=True).start()
#                     except socket.error as e:
#                         if not self.running:
#                             break
#                         print(f"Socket accept error: {e}")
#             except socket.error as e:
#                 print(f"Alternative port also failed: {e}")
#         finally:
#             if self.s:
#                 self.s.close()
                
#     def initiate_connections(self, other_peers):
#         """Reach out to other peers"""
#         for peer in other_peers:
#             try:
#                 peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#                 peer_socket.settimeout(3)
                
#                 # Always use localhost for testing
#                 host = "127.0.0.1" if peer[0] not in ["localhost", "127.0.0.1"] else peer[0]
#                 port = int(peer[1])
                
#                 print(f"Attempting to connect to {host}:{port}")
#                 peer_socket.connect((host, port))
                
#                 threading.Thread(target=self.setup_connection_from_initiating,
#                                 args=(peer_socket, host), daemon=True).start()
#             except (socket.error, ConnectionRefusedError) as e:
#                 print(f"Could not connect to peer at {peer[0]}:{peer[1]} - {e}")
#                 print("The peer may not be started yet, will retry later")
                
#                 # Schedule a retry after a delay
#                 def retry_connect(peer_info, delay):
#                     time.sleep(delay)
#                     if not self.running:
#                         return
#                     try:
#                         host = "127.0.0.1" if peer_info[0] not in ["localhost", "127.0.0.1"] else peer_info[0]
#                         port = int(peer_info[1])
#                         print(f"Retrying connection to {host}:{port}")
                        
#                         peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#                         peer_socket.settimeout(3)
#                         peer_socket.connect((host, port))
                        
#                         threading.Thread(target=self.setup_connection_from_initiating,
#                                         args=(peer_socket, host), daemon=True).start()
#                     except (socket.error, ConnectionRefusedError) as e:
#                         print(f"Retry failed: {e}")
                
#                 # Retry after 5 seconds
#                 threading.Thread(target=retry_connect, args=(peer, 5), daemon=True).start()
                
#     def setup_connection_from_listening(self, peer_socket, peer_address):
#         """Handle incoming connections from other peers"""
#         try:
#             # When a peer connects, they send the first handshake
#             peer_socket.settimeout(5)  # Set timeout for receiving handshake
#             handshake_message = peer_socket.recv(32).decode('utf-8')
            
#             if not handshake_message:
#                 print("Empty handshake received, closing connection")
#                 peer_socket.close()
#                 return
                
#             print(f"Received handshake: {handshake_message}")
                
#             # Validate handshake
#             if not self.check_handshake(handshake_message):
#                 print(f"Handshake is invalid: {handshake_message}")
#                 peer_socket.close()
#                 return
                
#             # Extract peer ID from handshake
#             peer_id = handshake_message[-4:]
            
#             # Reciprocal handshake is then sent
#             reciprocal_handshake = self.create_handshake()
#             peer_socket.sendall(reciprocal_handshake.encode('utf-8'))
#             print(f"Sent reciprocal handshake to peer {peer_id}")
            
#             # Add new connection to list of peers
#             peer = Peer(peer_socket, peer_id)
#             with self.peers_lock:
#                 self.peers.append(peer)
            
#             # Log connection
#             self.logger.log_tcp_connection(peer.ID, False)
            
#             # Send bitfield to peer if we have any pieces
#             if self.bitfield != "0" * NUM_PIECES:
#                 bitfield_message = self.make_bitfield_message(self.bitfield)
#                 encoded_message = bitfield_message.get_message().encode('utf-8')
#                 peer_socket.sendall(encoded_message)
#                 print(f"Sent bitfield to peer {peer_id}")
            
#             # Start receiving messages from this peer
#             peer_socket.settimeout(None)  # Remove timeout for normal operation
#             self.receive_from_peer(peer)
            
#         except Exception as e:
#             print(f"Error in setup_connection_from_listening: {e}")
#             peer_socket.close()
            
#     def setup_connection_from_initiating(self, peer_socket, peer_address):
#         """Handle outgoing connections to other peers"""
#         try:
#             # Send the handshake after connecting to a peer
#             initiating_handshake = self.create_handshake()
#             peer_socket.sendall(initiating_handshake.encode('utf-8'))
#             print(f"Sent initiating handshake to {peer_address}")
            
#             # Receive the peer's reciprocal handshake
#             peer_socket.settimeout(5)  # Set timeout for receiving handshake
#             handshake_message = peer_socket.recv(32).decode('utf-8')
            
#             if not handshake_message:
#                 print("Empty handshake received, closing connection")
#                 peer_socket.close()
#                 return
                
#             print(f"Received handshake: {handshake_message}")
                
#             # Validate handshake
#             if not self.check_handshake(handshake_message):
#                 print(f"Handshake is invalid: {handshake_message}")
#                 peer_socket.close()
#                 return
                
#             # Extract peer ID from handshake
#             peer_id = handshake_message[-4:]
            
#             # Add new connection to list of peers
#             peer = Peer(peer_socket, peer_id)
#             with self.peers_lock:
#                 self.peers.append(peer)
            
#             # Log the connection
#             self.logger.log_tcp_connection(peer.ID, True)
            
#             # Send bitfield to peer if we have any pieces
#             if self.bitfield != "0" * NUM_PIECES:
#                 bitfield_message = self.make_bitfield_message(self.bitfield)
#                 encoded_message = bitfield_message.get_message().encode('utf-8')
#                 peer_socket.sendall(encoded_message)
#                 print(f"Sent bitfield to peer {peer_id}")
            
#             # Start receiving messages from this peer
#             peer_socket.settimeout(None)  # Remove timeout for normal operation
#             self.receive_from_peer(peer)
            
#         except Exception as e:
#             print(f"Error in setup_connection_from_initiating: {e}")
#             peer_socket.close()
            
#     def receive_from_peer(self, peer):
#         """Process messages from a peer"""
#         while self.running:
#             try:
#                 # First receive the message length (4 bytes)
#                 mlength_bytes = peer.socket.recv(4)
#                 if not mlength_bytes:
#                     print(f"Connection with peer {peer.ID} closed")
#                     break
                    
#                 mlength = mlength_bytes.decode('utf-8')
#                 if not mlength.isdigit():
#                     print(f"Invalid message length: {mlength}")
#                     continue
                    
#                 mlength = int(mlength)
                
#                 # Then receive message type (1 byte)
#                 mtype_bytes = peer.socket.recv(1)
#                 if not mtype_bytes:
#                     break
                    
#                 mtype = mtype_bytes.decode('utf-8')
#                 print(f"Received message type {mtype} from peer {peer.ID}")
                
#                 # Process message based on type
#                 if mtype == "0":
#                     # Choked by peer
#                     self.logger.log_choked(peer.ID)
#                     peer.choked = True
#                     print(f"Choked by peer {peer.ID}")
                    
#                 elif mtype == "1":
#                     # Unchoked by peer
#                     self.logger.log_unchoked(peer.ID)
#                     peer.choked = False
#                     print(f"Unchoked by peer {peer.ID}")
                    
#                     # Request a piece if we're interested
#                     if peer.interested:
#                         self.request_piece(peer)
                        
#                 elif mtype == "2":
#                     # Peer is interested in pieces
#                     self.logger.log_interested_message(peer.ID)
#                     peer.interested = True
#                     print(f"Peer {peer.ID} is interested in our pieces")
                    
#                     # Add to interested peers list
#                     if peer not in self.interested_peers:
#                         self.interested_peers.append(peer)
                        
#                 elif mtype == "3":
#                     # Peer is not interested in any pieces
#                     self.logger.log_not_interested_message(peer.ID)
#                     peer.interested = False
#                     print(f"Peer {peer.ID} is not interested in our pieces")
                    
#                     # Remove from interested peers list
#                     if peer in self.interested_peers:
#                         self.interested_peers.remove(peer)
                        
#                 elif mtype == "4":
#                     # Peer has certain piece
#                     if mlength > 1:  # Must have payload
#                         piece_id_bytes = peer.socket.recv(mlength - 1)
#                         if not piece_id_bytes:
#                             break
                            
#                         piece_id = int(piece_id_bytes.decode('utf-8'))
#                         print(f"Peer {peer.ID} has piece {piece_id}")
                        
#                         # Update log and stored bitfield for that peer
#                         self.logger.log_have_message(peer.ID, str(piece_id))
                        
#                         # Update peer's bitfield
#                         temp_bitfield = list(peer.bitfield)
#                         if piece_id < len(temp_bitfield):
#                             temp_bitfield[piece_id] = '1'
#                             peer.bitfield = ''.join(temp_bitfield)
                        
#                         # Check if we need this piece
#                         with self.bitfield_lock:
#                             if piece_id < len(self.bitfield) and self.bitfield[piece_id] == '0':
#                                 # Send interested message if we need this piece
#                                 interested_message = self.make_interested_message()
#                                 peer.socket.sendall(interested_message.get_message().encode('utf-8'))
#                                 peer.interested = True
#                                 print(f"Sent interested message to peer {peer.ID} for piece {piece_id}")
                                
#                 elif mtype == "5":
#                     # Receiving bitfield of peer
#                     if mlength > 1:  # Must have payload
#                         bitfield_bytes = peer.socket.recv(mlength - 1)
#                         if not bitfield_bytes:
#                             break
                            
#                         peer.bitfield = bitfield_bytes.decode('utf-8')
#                         print(f"Received bitfield from peer {peer.ID}: {peer.bitfield}")
                        
#                         # Check if they have any pieces we need
#                         needs_pieces = False
#                         with self.bitfield_lock:
#                             for i in range(min(len(self.bitfield), len(peer.bitfield))):
#                                 if self.bitfield[i] == '0' and peer.bitfield[i] == '1':
#                                     needs_pieces = True
#                                     break
                                    
#                         if needs_pieces:
#                             # Send interested message
#                             interested_message = self.make_interested_message()
#                             peer.socket.sendall(interested_message.get_message().encode('utf-8'))
#                             peer.interested = True
#                             print(f"Sent interested message to peer {peer.ID}")
#                         else:
#                             # Send not interested message
#                             not_interested_message = self.make_not_interested_message()
#                             peer.socket.sendall(not_interested_message.get_message().encode('utf-8'))
#                             peer.interested = False
#                             print(f"Sent not interested message to peer {peer.ID}")
                            
#                 # elif mtype == "6":
#                 #     # A piece has been requested
#                 #     if mlength > 1:  # Must have payload
#                 #         piece_id_bytes = peer.socket.recv(mlength - 1)
#                 #         if not piece_id_bytes:
#                 #             break
                            
#                 #         piece_id = int(piece_id_bytes.decode('utf-8'))
#                 #         print(f"Peer {peer.ID} requested piece {piece_id}")
                        
#                 #         # Only send if peer is unchoked and we have the piece
#                 # # Only send if peer is unchoked and we have the piece
#                 # if ((peer in self.unchoked_peers or peer == self.optimistically_unchoked_peer) 
#                 #     and piece_id < len(self.bitfield) and self.bitfield[piece_id] == '1'):
                    
#                 #     with self.file_pieces_lock:
#                 #         piece_content = self.file_pieces[piece_id]
#                 #         if piece_content:
#                 #             try:
#                 #                 # Convert piece ID to string, but keep content as binary
#                 #                 piece_message = self.make_piece_message(str(piece_id), piece_content)
#                 #                 # Send as binary data
#                 #                 message = piece_message.get_message()
#                 #                 peer.socket.sendall(message.encode('latin1'))
#                 #                 print(f"Sent piece {piece_id} to peer {peer.ID}")
#                 #             except Exception as e:
#                 #                 print(f"Error sending piece {piece_id} to peer {peer.ID}: {e}")
#                 #         else:
#                 #             print(f"Cannot send piece {piece_id} to peer {peer.ID} (unchoked: {peer in self.unchoked_peers or peer == self.optimistically_unchoked_peer}, have piece: {piece_id < len(self.bitfield) and self.bitfield[piece_id] == '1'})")
#                 elif mtype == "6":
#                     # A piece has been requested
#                     if mlength > 1:  # Must have payload
#                         piece_id_bytes = peer.socket.recv(mlength - 1)
#                         if not piece_id_bytes:
#                             break
                            
#                         try:
#                             piece_id = int(piece_id_bytes.decode('utf-8'))
#                             print(f"Peer {peer.ID} requested piece {piece_id}")
                            
#                             # Only send if peer is unchoked and we have the piece
#                             if ((peer in self.unchoked_peers or peer == self.optimistically_unchoked_peer) 
#                                 and piece_id < len(self.bitfield) and self.bitfield[piece_id] == '1'):
                                
#                                 with self.file_pieces_lock:
#                                     piece_content = self.file_pieces[piece_id]
#                                     if piece_content:
#                                         try:
#                                             # Create a true binary piece message
#                                             # Format: [length:4][type:1][piece_id:string][space:1][binary_content]
#                                             piece_id_str = str(piece_id).encode('utf-8')
#                                             message_payload = piece_id_str + b' ' + piece_content
                                            
#                                             # Calculate message length (add 1 for type byte)
#                                             message_length = len(message_payload) + 1
#                                             message_length_str = str(message_length).zfill(4).encode('utf-8')
                                            
#                                             # Construct and send full binary message
#                                             full_message = message_length_str + b"7" + message_payload
#                                             peer.socket.sendall(full_message)
#                                             print(f"Sent piece {piece_id} to peer {peer.ID} ({len(piece_content)} bytes)")
#                                         except Exception as e:
#                                             print(f"Error sending piece {piece_id} to peer {peer.ID}: {e}")
#                                             import traceback
#                                             traceback.print_exc()
#                             else:
#                                 print(f"Cannot send piece {piece_id} - not authorized or don't have piece")
#                         except ValueError as e:
#                             print(f"Invalid piece ID received: {e}")
#                 # # When receiving a piece
#                 # elif mtype == "7":
#                 #     # Receiving a piece from a peer
#                 #     if mlength > 1:  # Must have payload
#                 #         try:
#                 #             # First read the piece ID
#                 #             piece_id_bytes = peer.socket.recv(mlength - 1)
#                 #             if not piece_id_bytes:
#                 #                 break
                                
#                 #             piece_id = int(piece_id_bytes.decode('utf-8'))
#                 #             print(f"Receiving piece {piece_id} from peer {peer.ID}")
                            
#                 #             # Now read the binary piece content directly
#                 #             piece_content = peer.socket.recv(self.config.piece_size)
                            
#                 #             print(f"Received piece {piece_id} ({len(piece_content)} bytes)")
                            
#                 #             # Update our bitfield
#                 #             with self.bitfield_lock:
#                 #                 if piece_id < len(self.bitfield):
#                 #                     temp_bitfield = list(self.bitfield)
#                 #                     temp_bitfield[piece_id] = '1'
#                 #                     self.bitfield = ''.join(temp_bitfield)
                                    
#                 #                     # Store the piece
#                 #                     with self.file_pieces_lock:
#                 #                         self.file_pieces[piece_id] = piece_content
#                 #                         self.pieces_requested[piece_id] = False
                                        
#                 #                         # Make sure directory exists
#                 #                         os.makedirs(self.peer_directory, exist_ok=True)
                                        
#                 #                         # Ensure file exists
#                 #                         file_path = os.path.join(self.peer_directory, self.config.file_name)
#                 #                         if not os.path.exists(file_path):
#                 #                             with open(file_path, 'wb') as f:
#                 #                                 f.seek(self.config.file_size - 1)
#                 #                                 f.write(b'\0')
                                        
#                 #                         # Write piece to file
#                 #                         with open(file_path, 'r+b') as f:
#                 #                             f.seek(piece_id * self.config.piece_size)
#                 #                             f.write(piece_content)
                                    
#                 #                     # Update stats
#                 #                     peer.pieces_downloaded += 1
#                 #                     num_pieces = self.bitfield.count('1')
#                 #                     self.logger.log_downloading_piece(peer.ID, str(piece_id), num_pieces)
                                    
#                 #                     # Request another piece
#                 #                     if not peer.choked:
#                 #                         self.request_piece(peer)
#                 #                 else:
#                 #                     print(f"Warning: Received piece {piece_id} but bitfield length is only {len(self.bitfield)}")
                                    
#                 #         except Exception as e:
#                 #             print(f"Error processing piece message: {e}")
#                 #             import traceback
#                 #             traceback.print_exc()
#                 elif mtype == "7":
#                     # Since we're ignoring the message format for piece data, this block is now empty
#                     # All actual piece data is received directly after sending a request
#                     pass  # No need to handle piece reception as part of the protocol
#                         #     # Update our bitfield
#                         #     with self.bitfield_lock:
#                         #         if piece_id < len(self.bitfield):
#                         #             temp_bitfield = list(self.bitfield)
#                         #             temp_bitfield[piece_id] = '1'
#                         #             self.bitfield = ''.join(temp_bitfield)
                                
#                         #     # Store the piece
#                         #     with self.file_pieces_lock:
#                         #         if piece_id < len(self.file_pieces):
#                         #             self.file_pieces[piece_id] = piece_content_bytes
#                         #             self.pieces_requested[piece_id] = False  # Reset request flag
                                    
#                         #             # Write the piece to file
#                         #             with open(os.path.join(self.peer_directory, self.config.file_name), 'r+b') as f:
#                         #                 f.seek(piece_id * self.config.piece_size)
#                         #                 f.write(piece_content_bytes)
                                        
#                         #     # Update download rate for this peer (for preferred neighbor selection)
#                         #     peer.pieces_downloaded += 1
                            
#                         #     # Count how many pieces we have
#                         #     num_pieces = self.bitfield.count('1')
                            
#                         #     # Log the piece download
#                         #     self.logger.log_downloading_piece(peer.ID, str(piece_id), num_pieces)
                            
#                         #     # Send have message to all peers
#                         #     have_message = self.make_have_message(str(piece_id))
#                         #     encoded_message = have_message.get_message().encode('utf-8')
                            
#                         #     with self.peers_lock:
#                         #         for other_peer in self.peers:
#                         #             if other_peer.ID != peer.ID:  # Don't send to the peer we got it from
#                         #                 try:
#                         #                     other_peer.socket.sendall(encoded_message)
#                         #                     print(f"Sent have message for piece {piece_id} to peer {other_peer.ID}")
#                         #                 except:
#                         #                     print(f"Failed to send have message to peer {other_peer.ID}")
                                            
#                         #     # Check if we've completed the download
#                         #     if num_pieces == NUM_PIECES:
#                         #         self.logger.log_download_completion()
#                         #         print(f"Download complete! All {NUM_PIECES} pieces received.")
                                
#                         #         # Reconstruct the complete file
#                         #         self.reconstruct_file()
                                
#                         #     # Request another piece if the peer has more we need
#                         #     if not peer.choked:
#                         #         self.request_piece(peer)
#                         # except Exception as e:
#                         #     print(f"Error processing piece message from peer {peer.ID}: {e}")
#                 else:
#                     print(f"Unknown message type {mtype} from peer {peer.ID}")
#                     # Skip the payload
#                     if mlength > 1:
#                         peer.socket.recv(mlength - 1)
                            
#             except Exception as e:
#                 print(f"Error receiving from peer {peer.ID}: {e}")
#                 break
                
#         # Connection ended, clean up
#         self.remove_peer(peer)

#     def select_preferred_neighbors(self):
#         """Periodically select preferred neighbors"""
#         while self.running:
#             # Sleep for unchoking interval
#             print(f"Sleeping for {self.config.unchoking_interval} seconds before selecting preferred neighbors")
#             time.sleep(self.config.unchoking_interval)
            
#             with self.peers_lock:
#                 if not self.peers:
#                     print("No peers connected, skipping preferred neighbor selection")
#                     continue
                
#                 print(f"Selecting preferred neighbors from {len(self.peers)} connected peers")
                    
#                 # Calculate download rates for each peer
#                 for peer in self.peers:
#                     peer.last_download_rate = peer.pieces_downloaded
#                     print(f"Peer {peer.ID} download rate: {peer.last_download_rate} pieces")
#                     peer.pieces_downloaded = 0  # Reset for next interval
                    
#                 # Get interested peers
#                 candidates = [p for p in self.peers if p.interested]
#                 print(f"Found {len(candidates)} interested peers")
                
#                 if not candidates:
#                     print("No interested peers, skipping preferred neighbor selection")
#                     continue
                    
#                 # If we have the complete file, select randomly
#                 if self.bitfield.count('1') == NUM_PIECES:
#                     print("We have complete file, selecting neighbors randomly")
#                     # Random selection from interested peers
#                     selected_peers = random.sample(candidates, 
#                                                 min(self.config.num_of_pref_neighbords, len(candidates)))
#                 else:
#                     print("Selecting neighbors based on download rates")
#                     # Select based on download rates
#                     sorted_peers = sorted(candidates, key=lambda p: p.last_download_rate, reverse=True)
#                     selected_peers = sorted_peers[:min(self.config.num_of_pref_neighbords, len(sorted_peers))]
                
#                 print(f"Selected {len(selected_peers)} preferred neighbors")
                    
#                 # Unchoke selected peers
#                 new_unchoked = selected_peers.copy()
                
#                 # Don't disturb optimistically unchoked peer
#                 if self.optimistically_unchoked_peer and self.optimistically_unchoked_peer not in new_unchoked:
#                     new_unchoked.append(self.optimistically_unchoked_peer)
#                     print(f"Added optimistically unchoked peer {self.optimistically_unchoked_peer.ID} to the unchoked list")
                    
#                 # Handle peers that need to be choked
#                 for peer in self.unchoked_peers:
#                     if peer not in new_unchoked and peer != self.optimistically_unchoked_peer:
#                         print(f"Choking peer {peer.ID}")
#                         choke_message = self.make_choke_message()
#                         try:
#                             peer.socket.sendall(choke_message.get_message().encode('utf-8'))
#                             print(f"Sent choke message to peer {peer.ID}")
#                         except Exception as e:
#                             print(f"Failed to send choke message to peer {peer.ID}: {e}")
                            
#                 # Handle peers that need to be unchoked
#                 for peer in new_unchoked:
#                     if peer not in self.unchoked_peers:
#                         print(f"Unchoking peer {peer.ID}")
#                         unchoke_message = self.make_unchoke_message()
#                         try:
#                             peer.socket.sendall(unchoke_message.get_message().encode('utf-8'))
#                             print(f"Sent unchoke message to peer {peer.ID}")
#                         except Exception as e:
#                             print(f"Failed to send unchoke message to peer {peer.ID}: {e}")
                            
#                 # Update unchoked peers list
#                 self.unchoked_peers = [p for p in new_unchoked if p != self.optimistically_unchoked_peer]
                
#                 # Log preferred neighbors change
#                 pref_ids = [peer.ID for peer in self.unchoked_peers]
#                 print(f"New preferred neighbors: {pref_ids}")
#                 self.logger.log_change_in_pref_neighbors(pref_ids)

#     def select_optimistically_unchoked_neighbor(self):
#         """Periodically select an optimistically unchoked neighbor"""
#         while self.running:
#             # Sleep for optimistic unchoking interval
#             print(f"Sleeping for {self.config.optimistic_unchoking_interval} seconds before selecting optimistically unchoked neighbor")
#             time.sleep(self.config.optimistic_unchoking_interval)
            
#             with self.peers_lock:
#                 # Get choked but interested peers
#                 candidates = [p for p in self.peers if p.interested and p not in self.unchoked_peers]
#                 print(f"Found {len(candidates)} candidates for optimistic unchoking")
                
#                 if not candidates:
#                     print("No candidates for optimistic unchoking, skipping")
#                     continue
                    
#                 # Select a random peer
#                 selected_peer = random.choice(candidates)
#                 print(f"Selected peer {selected_peer.ID} as optimistically unchoked neighbor")
                
#                 # Unchoke the previously optimistically unchoked peer if not in preferred neighbors
#                 if (self.optimistically_unchoked_peer and 
#                     self.optimistically_unchoked_peer not in self.unchoked_peers):
#                     print(f"Choking previous optimistically unchoked peer {self.optimistically_unchoked_peer.ID}")
#                     choke_message = self.make_choke_message()
#                     try:
#                         self.optimistically_unchoked_peer.socket.sendall(choke_message.get_message().encode('utf-8'))
#                         print(f"Sent choke message to peer {self.optimistically_unchoked_peer.ID}")
#                     except Exception as e:
#                         print(f"Failed to send choke message to peer {self.optimistically_unchoked_peer.ID}: {e}")
                        
#                 # Set new optimistically unchoked peer
#                 self.optimistically_unchoked_peer = selected_peer
                
#                 # Send unchoke message to the selected peer
#                 unchoke_message = self.make_unchoke_message()
#                 try:
#                     selected_peer.socket.sendall(unchoke_message.get_message().encode('utf-8'))
#                     print(f"Sent unchoke message to peer {selected_peer.ID}")
#                 except Exception as e:
#                     print(f"Failed to send unchoke message to peer {selected_peer.ID}: {e}")
                    
#                 # Log optimistically unchoked neighbor change
#                 self.logger.log_optimistic_unchoke(selected_peer.ID)

#     def shutdown(self):
#         """Gracefully shut down the client"""
#         print("Shutting down client...")
#         self.running = False
        
#         # Close all peer connections
#         with self.peers_lock:
#             for peer in self.peers:
#                 try:
#                     print(f"Closing connection to peer {peer.ID}")
#                     peer.socket.close()
#                 except Exception as e:
#                     print(f"Error closing peer socket: {e}")
                    
#         # Close server socket
#         try:
#             if hasattr(self, 's') and self.s:
#                 self.s.close()
#                 print("Closed server socket")
#         except Exception as e:
#             print(f"Error closing server socket: {e}")
            
#         print("Client shutdown complete")


#     def create_handshake(self):
#         """Create a handshake message"""
#         zero_bytes = '0' * 10
#         handshake_message = "P2PFILESHARINGPROJ" + zero_bytes + self.ID
#         return handshake_message
        
#     def check_handshake(self, handshake_message):
#         """Check the handshake message for valid header"""
#         if len(handshake_message) != 32:
#             print(f"Handshake length mismatch: {len(handshake_message)} != 32")
#             return False
            
#         header = handshake_message[:18]
#         if header != "P2PFILESHARINGPROJ":
#             print(f"Handshake header mismatch: '{header}' != 'P2PFILESHARINGPROJ'")
#             return False
            
#         return True
        
#     def make_choke_message(self):
#         """Create a choke message"""
#         return Message("choke")
        
#     def make_unchoke_message(self):
#         """Create an unchoke message"""
#         return Message("unchoke")
        
#     def make_interested_message(self):
#         """Create an interested message"""
#         return Message("interested")
        
#     def make_not_interested_message(self):
#         """Create a not interested message"""
#         return Message("not interested")
        
#     def make_have_message(self, piece_index):
#         """Create a have message"""
#         return Message("have", piece_index)
        
#     def make_bitfield_message(self, bitfield):
#         """Create a bitfield message"""
#         return Message("bitfield", bitfield)
        
#     def make_request_message(self, piece_index):
#         """Create a request message"""
#         return Message("request", piece_index)
        
#     def make_piece_message(self, piece_index, piece_content):
#         """Create a piece message with binary content"""
#         # Convert piece index to bytes
#         piece_index_bytes = str(piece_index).encode('utf-8')
        
#         # Combine piece index and content with a space separator
#         if isinstance(piece_content, bytes):
#             # If piece_content is already bytes, keep it as is
#             payload = piece_index_bytes + b' ' + piece_content
#         else:
#             # If it's a string, encode it
#             payload = piece_index_bytes + b' ' + piece_content.encode('utf-8')
            
#         # Create a binary message
#         message = Message("piece", payload)
#         return message
    
#     # def request_piece(self, peer):
#     #     """Request a random piece that we need from the peer"""
#     #     # Find pieces that peer has and we don't have
#     #     desired_pieces = []
#     #     with self.bitfield_lock:
#     #         for i in range(min(len(self.bitfield), len(peer.bitfield))):
#     #             if self.bitfield[i] == '0' and peer.bitfield[i] == '1' and not self.pieces_requested[i]:
#     #                 desired_pieces.append(i)
        
#     #     print(f"Pieces available from peer {peer.ID}: {len(desired_pieces)}")
                    
#     #     if desired_pieces:
#     #         # Choose a random piece
#     #         random_piece = random.choice(desired_pieces)
#     #         print(f"Requesting piece {random_piece} from peer {peer.ID}")
            
#     #         # Mark as requested
#     #         self.pieces_requested[random_piece] = True
            
#     #         # Create request message and send
#     #         request_message = self.make_request_message(str(random_piece))
#     #         try:
#     #             peer.socket.sendall(request_message.get_message().encode('utf-8'))
#     #             print(f"Sent request for piece {random_piece} to peer {peer.ID}")
                
#     #             # Immediately receive the piece data (raw bytes)
#     #             try:
#     #                 piece_content = b''
#     #                 remaining = self.config.piece_size
#     #                 while remaining > 0:
#     #                     chunk = peer.socket.recv(min(BUFFER_SIZE, remaining))
#     #                     if not chunk:
#     #                         break
#     #                     piece_content += chunk
#     #                     remaining -= len(chunk)
                    
#     #                 # Process the received piece
#     #                 if piece_content:
#     #                     print(f"Received piece {random_piece} ({len(piece_content)} bytes)")
                        
#     #                     # Update bitfield
#     #                     with self.bitfield_lock:
#     #                         temp_bitfield = list(self.bitfield)
#     #                         temp_bitfield[random_piece] = '1'
#     #                         self.bitfield = ''.join(temp_bitfield)
                        
#     #                     # Store piece
#     #                     with self.file_pieces_lock:
#     #                         self.file_pieces[random_piece] = piece_content
                            
#     #                         # Write to file
#     #                         file_path = os.path.join(self.peer_directory, self.config.file_name)
#     #                         if not os.path.exists(file_path):
#     #                             with open(file_path, 'wb') as f:
#     #                                 f.seek(self.config.file_size - 1)
#     #                                 f.write(b'\0')
                            
#     #                         with open(file_path, 'r+b') as f:
#     #                             f.seek(random_piece * self.config.piece_size)
#     #                             f.write(piece_content)
                        
#     #                     # Log download
#     #                     peer.pieces_downloaded += 1
#     #                     num_pieces = self.bitfield.count('1')
#     #                     self.logger.log_downloading_piece(peer.ID, str(random_piece), num_pieces)
                        
#     #                     # Check if we're done
#     #                     if num_pieces == NUM_PIECES:
#     #                         self.logger.log_download_completion()
#     #                         print("Download complete!")
                        
#     #                     # Request another piece
#     #                     if not peer.choked:
#     #                         self.request_piece(peer)
#     #             except Exception as e:
#     #                 print(f"Error receiving piece data: {e}")
#     #                 self.pieces_requested[random_piece] = False  # Reset request flag
#     #         except Exception as e:
#     #             print(f"Failed to send request message to peer {peer.ID}: {e}")
#     #             self.pieces_requested[random_piece] = False  # Reset request flag
#     #     elif peer.interested:
#     #         # No more pieces needed from this peer, send not interested
#     #         print(f"No more pieces needed from peer {peer.ID}, sending not interested")
#     #         not_interested_message = self.make_not_interested_message()
#     #         try:
#     #             peer.socket.sendall(not_interested_message.get_message().encode('utf-8'))
#     #             peer.interested = False
#     #             print(f"Sent not interested message to peer {peer.ID}")
#     #         except Exception as e:
#     #             print(f"Failed to send not interested message to peer {peer.ID}: {e}")
#     # def request_piece(self, peer):
#     #     """Request a random piece that we need from the peer"""
#     #     # Find pieces that peer has and we don't have
#     #     desired_pieces = []
#     #     with self.bitfield_lock:
#     #         for i in range(min(len(self.bitfield), len(peer.bitfield))):
#     #             if self.bitfield[i] == '0' and peer.bitfield[i] == '1' and not self.pieces_requested[i]:
#     #                 desired_pieces.append(i)
        
#     #     print(f"Pieces available from peer {peer.ID}: {len(desired_pieces)}")
                    
#     #     if desired_pieces:
#     #         # Choose a random piece
#     #         random_piece = random.choice(desired_pieces)
#     #         print(f"Requesting piece {random_piece} from peer {peer.ID}")
            
#     #         # Mark as requested
#     #         self.pieces_requested[random_piece] = True
            
#     #         # Create request message and send
#     #         request_message = self.make_request_message(str(random_piece))
#     #         try:
#     #             peer.socket.sendall(request_message.get_message().encode('utf-8'))
#     #             print(f"Sent request for piece {random_piece} to peer {peer.ID}")
                
#     #             # Immediately receive the piece data after sending request
#     #             start_time = time.time()
#     #             try:
#     #                 piece_content = b''
#     #                 remaining = self.config.piece_size
                    
#     #                 # Set a timeout for piece reception
#     #                 peer.socket.settimeout(10.0)  # 10 second timeout
                    
#     #                 while remaining > 0:
#     #                     chunk = peer.socket.recv(min(BUFFER_SIZE, remaining))
#     #                     if not chunk:
#     #                         print(f"Connection closed while receiving piece {random_piece}")
#     #                         break
#     #                     piece_content += chunk
#     #                     remaining -= len(chunk)
                        
#     #                     # Progress indicator for large pieces
#     #                     if self.config.piece_size > 100000:  # Over 100KB
#     #                         progress = 100 * (self.config.piece_size - remaining) / self.config.piece_size
#     #                         if progress % 20 == 0:  # Show progress at 0%, 20%, 40%, etc.
#     #                             print(f"Download progress for piece {random_piece}: {progress:.1f}%")
                    
#     #                 # Reset socket timeout to default
#     #                 peer.socket.settimeout(None)
                    
#     #                 # Process the received piece
#     #                 if piece_content:
#     #                     download_time = time.time() - start_time
#     #                     download_rate = len(piece_content) / download_time if download_time > 0 else 0
#     #                     print(f"Received piece {random_piece} ({len(piece_content)} bytes) at {download_rate:.2f} B/s")
                        
#     #                     # Update bitfield
#     #                     with self.bitfield_lock:
#     #                         temp_bitfield = list(self.bitfield)
#     #                         temp_bitfield[random_piece] = '1'
#     #                         self.bitfield = ''.join(temp_bitfield)
                        
#     #                     # Store piece
#     #                     with self.file_pieces_lock:
#     #                         self.file_pieces[random_piece] = piece_content
                            
#     #                         # Write to file
#     #                         file_path = os.path.join(self.peer_directory, self.config.file_name)
#     #                         if not os.path.exists(file_path):
#     #                             # Create an empty file of the right size
#     #                             with open(file_path, 'wb') as f:
#     #                                 f.seek(self.config.file_size - 1)
#     #                                 f.write(b'\0')
                            
#     #                         # Write the piece to the correct position in the file
#     #                         with open(file_path, 'r+b') as f:
#     #                             f.seek(random_piece * self.config.piece_size)
#     #                             f.write(piece_content)
                        
#     #                     # Log download and update statistics
#     #                     peer.pieces_downloaded += 1
#     #                     num_pieces = self.bitfield.count('1')
#     #                     self.logger.log_downloading_piece(peer.ID, str(random_piece), num_pieces)
                        
#     #                     # Send have messages to all peers
#     #                     have_message = self.make_have_message(str(random_piece))
#     #                     have_encoded = have_message.get_message().encode('utf-8')
                        
#     #                     with self.peers_lock:
#     #                         for other_peer in self.peers:
#     #                             if other_peer.ID != peer.ID:  # Don't send to the peer we got the piece from
#     #                                 try:
#     #                                     other_peer.socket.sendall(have_encoded)
#     #                                     print(f"Sent have message for piece {random_piece} to peer {other_peer.ID}")
#     #                                 except Exception as e:
#     #                                     print(f"Error sending have message to peer {other_peer.ID}: {e}")
                        
#     #                     # Check if download is complete
#     #                     if num_pieces == NUM_PIECES:
#     #                         self.logger.log_download_completion()
#     #                         print(f"Download complete! All {NUM_PIECES} pieces received.")
#     #                         self.reconstruct_file()
                            
#     #                         # Tell all peers that they can terminate if everyone has the file
#     #                         # This would require additional protocol extension
                        
#     #                     # Request another piece if not choked
#     #                     if not peer.choked:
#     #                         self.request_piece(peer)
#     #                 else:
#     #                     print(f"Received empty piece data for piece {random_piece}")
#     #                     self.pieces_requested[random_piece] = False  # Reset request flag
#     #             except socket.timeout:
#     #                 print(f"Timeout while receiving piece {random_piece} from peer {peer.ID}")
#     #                 self.pieces_requested[random_piece] = False  # Reset request flag
#     #             except Exception as e:
#     #                 print(f"Error receiving piece data: {e}")
#     #                 self.pieces_requested[random_piece] = False  # Reset request flag
#     #         except Exception as e:
#     #             print(f"Failed to send request message to peer {peer.ID}: {e}")
#     #             self.pieces_requested[random_piece] = False  # Reset request flag
#     #     elif peer.interested:
#     #         # No more pieces needed from this peer, send not interested
#     #         print(f"No more pieces needed from peer {peer.ID}, sending not interested")
#     #         not_interested_message = self.make_not_interested_message()
#     #         try:
#     #             peer.socket.sendall(not_interested_message.get_message().encode('utf-8'))
#     #             peer.interested = False
#     #             print(f"Sent not interested message to peer {peer.ID}")
#     #         except Exception as e:
#     #             print(f"Failed to send not interested message to peer {peer.ID}: {e}")
#     def request_piece(self, peer):
#         """Request a random piece that we need from the peer"""
#         # Find pieces that peer has and we don't have
#         desired_pieces = []
#         with self.bitfield_lock:
#             for i in range(min(len(self.bitfield), len(peer.bitfield))):
#                 if self.bitfield[i] == '0' and peer.bitfield[i] == '1' and not self.pieces_requested[i]:
#                     desired_pieces.append(i)
        
#         print(f"Pieces available from peer {peer.ID}: {len(desired_pieces)}")
                    
#         if desired_pieces:
#             # Choose a random piece
#             random_piece = random.choice(desired_pieces)
#             print(f"Requesting piece {random_piece} from peer {peer.ID}")
            
#             # Mark as requested
#             self.pieces_requested[random_piece] = True
            
#             # Create request message and send
#             request_message = self.make_request_message(str(random_piece))
#             try:
#                 # Send request message
#                 if isinstance(request_message.get_message(), bytes):
#                     peer.socket.sendall(request_message.get_message())
#                 else:
#                     peer.socket.sendall(request_message.get_message().encode('utf-8'))
                    
#                 print(f"Sent request for piece {random_piece} to peer {peer.ID}")
                
#                 # Receive the piece data
#                 start_time = time.time()
#                 try:
#                     # Set a longer timeout for large files
#                     peer.socket.settimeout(30.0)  # 30 second timeout
                    
#                     # First, receive the message header (4 bytes for length + 1 byte for type)
#                     header = peer.socket.recv(5)
#                     if len(header) != 5:
#                         raise Exception(f"Incomplete header received: {len(header)} bytes")
                    
#                     # Parse the header
#                     msg_length = int(header[:4].decode('utf-8'))
#                     msg_type = header[4:5].decode('utf-8')
                    
#                     if msg_type != "7":  # Piece message
#                         raise Exception(f"Expected piece message (7), got type {msg_type}")
                    
#                     # Next, receive the piece index (as a string until space)
#                     piece_id_bytes = b""
#                     while True:
#                         b = peer.socket.recv(1)
#                         if not b or b == b' ':
#                             break
#                         piece_id_bytes += b
                    
#                     piece_id = int(piece_id_bytes.decode('utf-8'))
#                     if piece_id != random_piece:
#                         raise Exception(f"Expected piece {random_piece}, got {piece_id}")
                    
#                     # Finally, receive the actual piece data
#                     piece_content = b''
#                     remaining = msg_length - 1 - len(piece_id_bytes) - 1  # Subtract message type, piece ID, and space
                    
#                     while remaining > 0:
#                         chunk = peer.socket.recv(min(BUFFER_SIZE, remaining))
#                         if not chunk:
#                             raise Exception("Connection closed during piece transfer")
#                         piece_content += chunk
#                         remaining -= len(chunk)
                        
#                         # Progress indicator for large pieces
#                         if remaining > 100000:
#                             progress = 100 * (msg_length - 1 - len(piece_id_bytes) - 1 - remaining) / (msg_length - 1 - len(piece_id_bytes) - 1)
#                             if int(progress) % 10 == 0:
#                                 print(f"Download progress for piece {random_piece}: {progress:.1f}%")
                    
#                     # Reset socket timeout to default
#                     peer.socket.settimeout(None)
                    
#                     # Process the received piece
#                     if piece_content:
#                         download_time = time.time() - start_time
#                         download_rate = len(piece_content) / download_time if download_time > 0 else 0
#                         print(f"Received piece {random_piece} ({len(piece_content)} bytes) at {download_rate:.2f} B/s")
                        
#                         # Update bitfield
#                         with self.bitfield_lock:
#                             temp_bitfield = list(self.bitfield)
#                             temp_bitfield[random_piece] = '1'
#                             self.bitfield = ''.join(temp_bitfield)
                        
#                         # Store piece
#                         with self.file_pieces_lock:
#                             self.file_pieces[random_piece] = piece_content
                            
#                             # Write to file
#                             file_path = os.path.join(self.peer_directory, self.config.file_name)
#                             if not os.path.exists(file_path):
#                                 # Create an empty file of the right size
#                                 with open(file_path, 'wb') as f:
#                                     f.seek(self.config.file_size - 1)
#                                     f.write(b'\0')
                            
#                             # Write the piece to the correct position in the file
#                             with open(file_path, 'r+b') as f:
#                                 f.seek(random_piece * self.config.piece_size)
#                                 f.write(piece_content)
                        
#                         # Log download and update statistics
#                         peer.pieces_downloaded += 1
#                         num_pieces = self.bitfield.count('1')
#                         self.logger.log_downloading_piece(peer.ID, str(random_piece), num_pieces)
                        
#                         # Send have messages to all peers
#                         have_message = self.make_have_message(str(random_piece))
#                         have_encoded = have_message.get_message()
                        
#                         with self.peers_lock:
#                             for other_peer in self.peers:
#                                 if other_peer.ID != peer.ID:  # Don't send to the peer we got the piece from
#                                     try:
#                                         other_peer.socket.sendall(have_encoded)
#                                         print(f"Sent have message for piece {random_piece} to peer {other_peer.ID}")
#                                     except Exception as e:
#                                         print(f"Error sending have message to peer {other_peer.ID}: {e}")
                        
#                         # Check if download is complete
#                         if num_pieces == NUM_PIECES:
#                             self.logger.log_download_completion()
#                             print(f"Download complete! All {NUM_PIECES} pieces received.")
#                             self.reconstruct_file()
                        
#                         # Request another piece if not choked
#                         if not peer.choked:
#                             self.request_piece(peer)
#                     else:
#                         print(f"Received empty piece data for piece {random_piece}")
#                         self.pieces_requested[random_piece] = False  # Reset request flag
#                 except socket.timeout:
#                     print(f"Timeout while receiving piece {random_piece} from peer {peer.ID}")
#                     self.pieces_requested[random_piece] = False  # Reset request flag
#                 except Exception as e:
#                     print(f"Error receiving piece data: {e}")
#                     import traceback
#                     traceback.print_exc()
#                     self.pieces_requested[random_piece] = False  # Reset request flag
#             except Exception as e:
#                 print(f"Failed to send request message to peer {peer.ID}: {e}")
#                 self.pieces_requested[random_piece] = False  # Reset request flag
#         elif peer.interested:
#             # No more pieces needed from this peer, send not interested
#             print(f"No more pieces needed from peer {peer.ID}, sending not interested")
#             not_interested_message = self.make_not_interested_message()
#             try:
#                 peer.socket.sendall(not_interested_message.get_message())
#                 peer.interested = False
#                 print(f"Sent not interested message to peer {peer.ID}")
#             except Exception as e:
#                 print(f"Failed to send not interested message to peer {peer.ID}: {e}")



#     def remove_peer(self, peer):
#         """Remove peer from all collections and close socket"""
#         try:
#             print(f"Removing peer {peer.ID} from connections")
            
#             # Close socket
#             if peer.socket:
#                 peer.socket.close()
                
#             # Remove from collections
#             with self.peers_lock:
#                 if peer in self.peers:
#                     self.peers.remove(peer)
#                     print(f"Removed peer {peer.ID} from peers list")
                    
#                 if peer in self.unchoked_peers:
#                     self.unchoked_peers.remove(peer)
#                     print(f"Removed peer {peer.ID} from unchoked peers list")
                    
#                 if peer in self.interested_peers:
#                     self.interested_peers.remove(peer)
#                     print(f"Removed peer {peer.ID} from interested peers list")
                    
#                 if peer == self.optimistically_unchoked_peer:
#                     self.optimistically_unchoked_peer = None
#                     print(f"Removed peer {peer.ID} as optimistically unchoked peer")
                    
#         except Exception as e:
#             print(f"Error removing peer {peer.ID}: {e}")

#     # def reconstruct_file(self):
#     #     """Reconstruct the complete file from pieces"""
#     #     try:
#     #         output_file = os.path.join(self.peer_directory, self.config.file_name)
#     #         print(f"Reconstructing file to: {output_file}")
            
#     #         with open(output_file, 'wb') as f:
#     #             pieces_written = 0
#     #             for i in range(NUM_PIECES):
#     #                 if self.file_pieces[i]:
#     #                     f.write(self.file_pieces[i])
#     #                     pieces_written += 1
#     #                 else:
#     #                     print(f"Warning: Missing piece {i} during file reconstruction")
#     #                     # Write empty bytes for missing pieces
#     #                     if i < NUM_PIECES - 1:  # Not the last piece
#     #                         f.write(b'\0' * self.config.piece_size)
#     #                     else:  # Last piece might be smaller
#     #                         last_piece_size = self.config.file_size % self.config.piece_size
#     #                         if last_piece_size == 0:
#     #                             last_piece_size = self.config.piece_size
#     #                         f.write(b'\0' * last_piece_size)
                
#     #         # Set file size to match original
#     #         os.truncate(output_file, self.config.file_size)
#     #         print(f"File reconstruction complete: {self.config.file_name}")
#     #         print(f"Wrote {pieces_written} of {NUM_PIECES} pieces")
            
#     #     except Exception as e:
#     #         print(f"Error reconstructing file: {e}")
#     def reconstruct_file(self):
#         """Reconstruct the complete file from pieces with validation"""
#         try:
#             output_file = os.path.join(self.peer_directory, self.config.file_name)
#             print(f"Reconstructing file to: {output_file}")
            
#             # Create a backup of any existing file
#             if os.path.exists(output_file):
#                 backup_file = output_file + ".bak"
#                 try:
#                     import shutil
#                     shutil.copy2(output_file, backup_file)
#                     print(f"Created backup of existing file: {backup_file}")
#                 except Exception as e:
#                     print(f"Failed to create backup: {e}")
            
#             # First check if we have all the pieces
#             missing_pieces = []
#             for i in range(NUM_PIECES):
#                 if not self.file_pieces[i]:
#                     missing_pieces.append(i)
                    
#             if missing_pieces:
#                 print(f"Warning: Missing {len(missing_pieces)} pieces during reconstruction: {missing_pieces[:10]}...")
#                 print("Reconstruction might be incomplete")
            
#             # Open file for writing
#             with open(output_file, 'wb') as f:
#                 pieces_written = 0
#                 bytes_written = 0
                
#                 for i in range(NUM_PIECES):
#                     if self.file_pieces[i]:
#                         # Validate piece content
#                         if not isinstance(self.file_pieces[i], bytes):
#                             print(f"Warning: Piece {i} is not binary data. Type: {type(self.file_pieces[i])}")
#                             continue
                            
#                         f.write(self.file_pieces[i])
#                         pieces_written += 1
#                         bytes_written += len(self.file_pieces[i])
                        
#                         # Progress indicator for large files
#                         if NUM_PIECES > 50 and i % (NUM_PIECES // 10) == 0:
#                             progress = 100 * i / NUM_PIECES
#                             print(f"File reconstruction progress: {progress:.1f}%")
#                     else:
#                         print(f"Skipping missing piece {i}")
                
#                 # Ensure proper file size at the end
#                 current_size = f.tell()
#                 if current_size != self.config.file_size:
#                     print(f"Warning: File size mismatch. Written {current_size} bytes, expected {self.config.file_size}")
#                     # Only truncate if the file is larger than expected, not if it's smaller
#                     if current_size > self.config.file_size:
#                         print("Truncating file to expected size")
#                         f.truncate(self.config.file_size)
            
#             print(f"File reconstruction complete: {self.config.file_name}")
#             print(f"Wrote {pieces_written} of {NUM_PIECES} pieces ({bytes_written} bytes)")
            
#             # Verify file size
#             actual_size = os.path.getsize(output_file)
#             if actual_size == self.config.file_size:
#                 print(f"File size verification successful: {actual_size} bytes")
#             else:
#                 print(f"File size verification failed: Expected {self.config.file_size} bytes, got {actual_size} bytes")
            
#             return True
#         except Exception as e:
#             print(f"Error reconstructing file: {e}")
#             import traceback
#             traceback.print_exc()
#             return False


import random
import socket
import threading
import time
import math
import os
from logger import Logger
from config import Config
import traceback
import sys

BUFFER_SIZE = 1024
NUM_PIECES = 306  # This will be calculated based on file size and piece size

# Decodes an integer into message type
MESSAGE_TYPE_DECODE = {
    "0": "choke",
    "1": "unchoke",
    "2": "interested",
    "3": "not interested",
    "4": "have",
    "5": "bitfield",
    "6": "request",
    "7": "piece",
}

MESSAGE_TYPE_ENCODE = {
    "choke": "0",
    "unchoke": "1",
    "interested": "2",
    "not interested": "3",
    "have": "4",
    "bitfield": "5",
    "request": "6",
    "piece": "7",
}

# class Message:
#     def __init__(self, message_type, message_payload=b""):
#         # Handle binary payload differently
#         if isinstance(message_payload, bytes):
#             self.is_binary = True
#             self.message_length = len(message_payload) + 1  # +1 for message type
#             self.decoded_message_type = message_type
#             self.encoded_message_type = MESSAGE_TYPE_ENCODE[message_type].encode('utf-8')
#             self.message_payload = message_payload
#         else:
#             self.is_binary = False
#             self.message_length = len(message_payload) + 1  # +1 for message type
#             self.decoded_message_type = message_type
#             self.encoded_message_type = MESSAGE_TYPE_ENCODE[message_type]
#             self.message_payload = message_payload

#         # Ensure message_length is 4 bytes by padding with zeros
#         self.message_length_bytes = str(self.message_length).zfill(4).encode('utf-8')

#     def get_message(self):
#         if self.is_binary:
#             # For binary data, return bytes directly
#             return self.message_length_bytes + self.encoded_message_type + self.message_payload
#         else:
#             # For text data, encode as before
#             message_length_str = str(self.message_length).zfill(4)
#             return (message_length_str + self.encoded_message_type + self.message_payload).encode('utf-8')
class Message:
    def __init__(self, message_type, message_payload=b""):
        # Handle binary payload consistently
        if isinstance(message_payload, str):
            message_payload = message_payload.encode('utf-8')
            
        # Now message_payload is guaranteed to be bytes
        self.message_length = len(message_payload) + 1  # +1 for message type
        self.message_type = message_type
        self.encoded_message_type = MESSAGE_TYPE_ENCODE[message_type].encode('utf-8')
        self.message_payload = message_payload
        
        # Ensure message_length is 4 bytes by padding with zeros
        self.message_length_bytes = str(self.message_length).zfill(4).encode('utf-8')

    def get_message(self):
        """Get the full message as bytes"""
        return self.message_length_bytes + self.encoded_message_type + self.message_payload

class Peer:
    # Will be used to store information on peers
    def __init__(self, socket_number, ID):
        self.socket = socket_number
        self.ID = ID
        self.bitfield = "0" * NUM_PIECES
        self.complete = False
        self.interested = False
        self.choked = True
        self.last_download_rate = 0  # For preferred neighbor selection
        self.pieces_downloaded = 0  # Track how many pieces downloaded from this peer

class Client:
    def __init__(self, config_filepath, host, port, ID="1001"):
        # Initialize with empty bitfield and peer list
        self.host = host
        self.port = int(port)
        self.peers = []
        self.unchoked_peers = []
        self.optimistically_unchoked_peer = None
        self.ID = ID
        self.logger = Logger(ID)
        self.config = Config(config_filepath)
        self.other_peers = []  # Will be used for establishing connections
        
        # Calculate the number of pieces based on file size and piece size
        global NUM_PIECES
        NUM_PIECES = math.ceil(self.config.file_size / self.config.piece_size)
        
        self.bitfield = "0" * NUM_PIECES
        
        # Create peer directory if it doesn't exist
        self.peer_directory = f"peer_{self.ID}"
        if not os.path.exists(self.peer_directory):
            os.makedirs(self.peer_directory)
            
        # Initialize file pieces as empty
        self.file_pieces = [None] * NUM_PIECES
        self.pieces_requested = [False] * NUM_PIECES
        
        # For selecting preferred neighbors
        self.download_rates = {}
        self.interested_peers = []
        
        # For thread synchronization
        self.peers_lock = threading.Lock()
        self.bitfield_lock = threading.Lock()
        self.file_pieces_lock = threading.Lock()
        
        # For threading control
        self.running = True
        
        # Debug info
        print(f"Client initialized with:")
        print(f"  - ID: {ID}")
        print(f"  - Host: {host}")
        print(f"  - Port: {port}")
        print(f"  - Config: {config_filepath}")
        print(f"  - Pieces: {NUM_PIECES}")
        print(f"  - Peer directory: {self.peer_directory}")
        
    def has_file(self):
        """If this peer has the file, update its bitfield and read file into memory"""
        # Check for file in various possible locations
        file_paths = [
            os.path.join(self.peer_directory, self.config.file_name),
            os.path.join("project_config_file_small/project_config_file_small", self.ID, self.config.file_name),
            os.path.join("project_config_file_small", self.ID, self.config.file_name),
            self.config.file_name
        ]
        
        file_found = False
        for path in file_paths:
            if os.path.exists(path):
                print(f"Found file at: {path}")
                file_found = True
                
                # Get actual file size
                actual_size = os.path.getsize(path)
                print(f"Actual file size: {actual_size} bytes, expected: {self.config.file_size} bytes")
                
                # Ensure correct number of pieces
                global NUM_PIECES
                NUM_PIECES = math.ceil(self.config.file_size / self.config.piece_size)
                print(f"File will be divided into {NUM_PIECES} pieces of {self.config.piece_size} bytes each")
                
                # Reinitialize file pieces array with correct size
                self.file_pieces = [None] * NUM_PIECES
                self.pieces_requested = [False] * NUM_PIECES
                
                # Read file into memory in pieces
                with open(path, 'rb') as f:
                    for i in range(NUM_PIECES):
                        try:
                            f.seek(i * self.config.piece_size)
                            piece_data = f.read(self.config.piece_size)
                            if piece_data:
                                self.file_pieces[i] = piece_data
                                print(f"Read piece {i}: {len(piece_data)} bytes")
                        except Exception as e:
                            print(f"Error reading piece {i}: {e}")
                
                # Update bitfield
                self.bitfield = "1" * NUM_PIECES
                print(f"Updated bitfield: {self.bitfield}")
                
                # Copy file to peer directory if it's not already there
                target_path = os.path.join(self.peer_directory, self.config.file_name)
                if path != target_path:
                    os.makedirs(self.peer_directory, exist_ok=True)
                    import shutil
                    shutil.copy2(path, target_path)
                    print(f"Copied file to peer directory: {self.peer_directory}")
                
                break
        
        if not file_found:
            print(f"Warning: File {self.config.file_name} not found in any expected locations!")
            self.bitfield = "0" * NUM_PIECES
            
    def setup(self, other_peers):
        """Initialize server socket and connect to existing peers"""
        # Start debug state printer
        threading.Thread(target=self.debug_peer_state, daemon=True).start()
        
        # Start preferred neighbors selection thread
        threading.Thread(target=self.select_preferred_neighbors, daemon=True).start()
        
        # Start optimistically unchoked neighbor selection thread
        threading.Thread(target=self.select_optimistically_unchoked_neighbor, daemon=True).start()
        
        # Start server socket to listen for incoming connections
        threading.Thread(target=self.listen_for_connections, daemon=True).start()
        
        # Connect to existing peers
        self.initiate_connections(other_peers)
        
        # Debug log - schedule a test connection to all peers after 10 seconds
        def test_all_connections():
            print("Testing connections to all peers...")
            with self.peers_lock:
                for peer in self.peers:
                    self.test_connection(peer.ID)
        
        threading.Timer(10.0, test_all_connections).start()

        # Add diagnostic scheduling
        def run_diagnostics():
            print("Running connection diagnostics...")
            self.diagnose_connections()
            
            # Schedule forced piece requests to all peers
            if len(self.peers) > 0:
                print("Scheduling forced piece requests...")
                for i, peer in enumerate(self.peers):
                    # Stagger requests by 2 seconds each
                    threading.Timer(10 + i*2, lambda p=peer.ID: self.force_piece_request(p)).start()
            
            # Schedule next diagnostic run
            if self.running:
                threading.Timer(30.0, run_diagnostics).start()

        threading.Timer(5.0, run_diagnostics).start()

        # Debug message formats
        print("\nDEBUG MESSAGE FORMATS:")
        self.print_message_debug("bitfield", "10101")
        self.print_message_debug("interested")
        self.print_message_debug("request", "5")
        self.print_message_debug("have", "2")
        
    def listen_for_connections(self):
        """Set up listening socket and accept incoming connections"""
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            # Always listen on localhost regardless of configured host
            listen_host = "127.0.0.1" if self.host not in ["localhost", "127.0.0.1"] else self.host
            self.s.bind((listen_host, self.port))
            self.s.listen(10)
            print(f"Listening on {listen_host}:{self.port} (configured host was {self.host})")
            
            while self.running:
                try:
                    # Wait for connections and set them up
                    peer_socket, peer_address = self.s.accept()
                    print(f"Accepted connection from {peer_address}")
                    threading.Thread(target=self.setup_connection_from_listening,
                                    args=(peer_socket, peer_address), daemon=True).start()
                except socket.error as e:
                    if not self.running:
                        break
                    print(f"Socket accept error: {e}")
        except socket.error as e:
            print(f"Socket binding error: {e}")
            print("Trying alternative port...")
            # Try an alternative port
            try:
                alt_port = self.port + 1000  # Try a port 1000 higher
                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.s.bind((listen_host, alt_port))
                self.s.listen(10)
                self.port = alt_port  # Update the port
                print(f"Listening on {listen_host}:{alt_port} (alternative port)")
                
                while self.running:
                    try:
                        # Wait for connections and set them up
                        peer_socket, peer_address = self.s.accept()
                        print(f"Accepted connection from {peer_address}")
                        threading.Thread(target=self.setup_connection_from_listening,
                                        args=(peer_socket, peer_address), daemon=True).start()
                    except socket.error as e:
                        if not self.running:
                            break
                        print(f"Socket accept error: {e}")
            except socket.error as e:
                print(f"Alternative port also failed: {e}")
        finally:
            if self.s:
                self.s.close()
                
    def initiate_connections(self, other_peers):
        """Reach out to other peers"""
        for peer in other_peers:
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.settimeout(3)
                
                # Always use localhost for testing
                host = "127.0.0.1" if peer[0] not in ["localhost", "127.0.0.1"] else peer[0]
                port = int(peer[1])
                
                print(f"Attempting to connect to {host}:{port}")
                peer_socket.connect((host, port))
                
                threading.Thread(target=self.setup_connection_from_initiating,
                                args=(peer_socket, host), daemon=True).start()
            except (socket.error, ConnectionRefusedError) as e:
                print(f"Could not connect to peer at {peer[0]}:{peer[1]} - {e}")
                print("The peer may not be started yet, will retry later")
                
                # Schedule a retry after a delay
                def retry_connect(peer_info, delay):
                    time.sleep(delay)
                    if not self.running:
                        return
                    try:
                        host = "127.0.0.1" if peer_info[0] not in ["localhost", "127.0.0.1"] else peer_info[0]
                        port = int(peer_info[1])
                        print(f"Retrying connection to {host}:{port}")
                        
                        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        peer_socket.settimeout(3)
                        peer_socket.connect((host, port))
                        
                        threading.Thread(target=self.setup_connection_from_initiating,
                                        args=(peer_socket, host), daemon=True).start()
                    except (socket.error, ConnectionRefusedError) as e:
                        print(f"Retry failed: {e}")
                
                # Retry after 5 seconds
                threading.Thread(target=retry_connect, args=(peer, 5), daemon=True).start()
                
    def setup_connection_from_listening(self, peer_socket, peer_address):
        """Handle incoming connections from other peers"""
        try:
            # When a peer connects, they send the first handshake
            peer_socket.settimeout(5)  # Set timeout for receiving handshake
            handshake_message = peer_socket.recv(32).decode('utf-8')
            
            if not handshake_message:
                print("Empty handshake received, closing connection")
                peer_socket.close()
                return
                    
            print(f"Received handshake: {handshake_message}")
                    
            # Validate handshake
            if not self.check_handshake(handshake_message):
                print(f"Handshake is invalid: {handshake_message}")
                peer_socket.close()
                return
                    
            # Extract peer ID from handshake
            peer_id = handshake_message[-4:]
            
            # Reciprocal handshake is then sent
            reciprocal_handshake = self.create_handshake()
            peer_socket.sendall(reciprocal_handshake.encode('utf-8'))
            print(f"Sent reciprocal handshake to peer {peer_id}")
            
            # Add new connection to list of peers
            peer = Peer(peer_socket, peer_id)
            with self.peers_lock:
                self.peers.append(peer)
            
            # Log connection
            self.logger.log_tcp_connection(peer.ID, False)
            
            # Send bitfield to peer if we have any pieces
            if self.bitfield != "0" * NUM_PIECES:
                print(f"Sending bitfield to peer {peer_id}: {self.bitfield}")
                bitfield_message = self.make_bitfield_message(self.bitfield)
                encoded_message = bitfield_message.get_message()
                peer_socket.sendall(encoded_message)
                print(f"Sent bitfield to peer {peer_id}")
            
            # Start receiving messages from this peer
            peer_socket.settimeout(None)  # Remove timeout for normal operation
            self.receive_from_peer(peer)
            
        except Exception as e:
            print(f"Error in setup_connection_from_listening: {e}")
            traceback.print_exc()
            peer_socket.close()
            
    def setup_connection_from_initiating(self, peer_socket, peer_address):
        """Handle outgoing connections to other peers"""
        try:
            # Send the handshake after connecting to a peer
            initiating_handshake = self.create_handshake()
            peer_socket.sendall(initiating_handshake.encode('utf-8'))
            print(f"Sent initiating handshake to {peer_address}")
            
            # Receive the peer's reciprocal handshake
            peer_socket.settimeout(5)  # Set timeout for receiving handshake
            handshake_message = peer_socket.recv(32).decode('utf-8')
            
            if not handshake_message:
                print("Empty handshake received, closing connection")
                peer_socket.close()
                return
                
            print(f"Received handshake: {handshake_message}")
                
            # Validate handshake
            if not self.check_handshake(handshake_message):
                print(f"Handshake is invalid: {handshake_message}")
                peer_socket.close()
                return
                
            # Extract peer ID from handshake
            peer_id = handshake_message[-4:]
            
            # Add new connection to list of peers
            peer = Peer(peer_socket, peer_id)
            with self.peers_lock:
                self.peers.append(peer)
            
            # Log the connection
            self.logger.log_tcp_connection(peer.ID, True)
            
            # Send bitfield to peer if we have any pieces
            if self.bitfield != "0" * NUM_PIECES:
                bitfield_message = self.make_bitfield_message(self.bitfield)
                encoded_message = bitfield_message.get_message()
                peer_socket.sendall(encoded_message)
                print(f"Sent bitfield to peer {peer_id}")
            
            # Start receiving messages from this peer
            peer_socket.settimeout(None)  # Remove timeout for normal operation
            self.receive_from_peer(peer)
            
        except Exception as e:
            print(f"Error in setup_connection_from_initiating: {e}")
            peer_socket.close()
            
    def receive_from_peer(self, peer):
        """Process messages from a peer"""
        while self.running:
            try:
                # First receive the message length (4 bytes)
                mlength_bytes = peer.socket.recv(4)
                if not mlength_bytes:
                    print(f"Connection with peer {peer.ID} closed")
                    break
                    
                mlength = mlength_bytes.decode('utf-8')
                if not mlength.isdigit():
                    print(f"Invalid message length: {mlength}")
                    continue
                    
                mlength = int(mlength)
                
                # Then receive message type (1 byte)
                mtype_bytes = peer.socket.recv(1)
                if not mtype_bytes:
                    break
                    
                mtype = mtype_bytes.decode('utf-8')
                print(f"Received message type {mtype} from peer {peer.ID}")
                
                # Process message based on type
                if mtype == "0":
                    # Choked by peer
                    self.logger.log_choked(peer.ID)
                    peer.choked = True
                    print(f"Choked by peer {peer.ID}")
                    
                elif mtype == "1":
                    # Unchoked by peer
                    self.logger.log_unchoked(peer.ID)
                    peer.choked = False
                    print(f"Unchoked by peer {peer.ID}")
                    
                    # Request a piece if we're interested
                    if peer.interested:
                        print(f"We are interested in peer {peer.ID}'s pieces, sending request")
                        self.request_piece(peer)
                    else:
                        print(f"Not requesting piece from peer {peer.ID} - not interested in their pieces")
                        
                elif mtype == "2":
                    # Peer is interested in pieces
                    self.logger.log_interested_message(peer.ID)
                    peer.interested = True
                    print(f"Peer {peer.ID} is interested in our pieces")
                    
                    # Add to interested peers list
                    if peer not in self.interested_peers:
                        self.interested_peers.append(peer)
                        
                elif mtype == "3":
                    # Peer is not interested in any pieces
                    self.logger.log_not_interested_message(peer.ID)
                    peer.interested = False
                    print(f"Peer {peer.ID} is not interested in our pieces")
                    
                    # Remove from interested peers list
                    if peer in self.interested_peers:
                        self.interested_peers.remove(peer)
                        
                elif mtype == "4":
                    # Peer has certain piece
                    if mlength > 1:  # Must have payload
                        piece_id_bytes = peer.socket.recv(mlength - 1)
                        if not piece_id_bytes:
                            break
                            
                        piece_id = int(piece_id_bytes.decode('utf-8'))
                        print(f"Peer {peer.ID} has piece {piece_id}")
                        
                        # Update log and stored bitfield for that peer
                        self.logger.log_have_message(peer.ID, str(piece_id))
                        
                        # Update peer's bitfield
                        temp_bitfield = list(peer.bitfield)
                        if piece_id < len(temp_bitfield):
                            temp_bitfield[piece_id] = '1'
                            peer.bitfield = ''.join(temp_bitfield)
                        
                        # Check if we need this piece
                        with self.bitfield_lock:
                            if piece_id < len(self.bitfield) and self.bitfield[piece_id] == '0':
                                # Send interested message if we need this piece
                                interested_message = self.make_interested_message()
                                peer.socket.sendall(interested_message.get_message())
                                peer.interested = True
                                print(f"Sent interested message to peer {peer.ID} for piece {piece_id}")
                                
                elif mtype == "5":
                    # Receiving bitfield of peer
                    if mlength > 1:  # Must have payload
                        bitfield_bytes = peer.socket.recv(mlength - 1)
                        if not bitfield_bytes:
                            break
                            
                        peer.bitfield = bitfield_bytes.decode('utf-8')
                        print(f"Received bitfield from peer {peer.ID}: {peer.bitfield}")
                        
                        # Check if they have any pieces we need
                        needs_pieces = False
                        with self.bitfield_lock:
                            for i in range(min(len(self.bitfield), len(peer.bitfield))):
                                if self.bitfield[i] == '0' and peer.bitfield[i] == '1':
                                    needs_pieces = True
                                    print(f"Need piece {i} from peer {peer.ID}")
                                    break
                            
                        if needs_pieces:
                            # Send interested message
                            interested_message = self.make_interested_message()
                            peer.socket.sendall(interested_message.get_message())
                            peer.interested = True
                            print(f"Sent interested message to peer {peer.ID}")
                        else:
                            # Send not interested message
                            not_interested_message = self.make_not_interested_message()
                            peer.socket.sendall(not_interested_message.get_message())
                            peer.interested = False
                            print(f"Sent not interested message to peer {peer.ID} - we don't need any of their pieces")
                            
                elif mtype == "6":
                    # A piece has been requested
                    if mlength > 1:  # Must have payload
                        piece_id_bytes = peer.socket.recv(mlength - 1)
                        if not piece_id_bytes:
                            break
                            
                        try:
                            piece_id = int(piece_id_bytes.decode('utf-8'))
                            print(f"[DEBUG] Peer {peer.ID} requested piece {piece_id}")
                            
                            # Only send if peer is unchoked and we have the piece
                            if ((peer in self.unchoked_peers or peer == self.optimistically_unchoked_peer) 
                                and piece_id < len(self.bitfield) and self.bitfield[piece_id] == '1'):
                                
                                with self.file_pieces_lock:
                                    piece_content = self.file_pieces[piece_id]
                                    if piece_content:
                                        try:
                                            print(f"[DEBUG] Sending piece {piece_id} to peer {peer.ID}, size: {len(piece_content)} bytes")
                                            
                                            # For troubleshooting, just send the raw piece data
                                            # No message headers, no formatting, just the binary data
                                            peer.socket.sendall(piece_content)
                                            print(f"[DEBUG] Sent raw piece {piece_id} to peer {peer.ID} ({len(piece_content)} bytes)")
                                        except Exception as e:
                                            print(f"[DEBUG] Error sending piece {piece_id} to peer {peer.ID}: {e}")
                                            traceback.print_exc()
                            else:
                                if peer not in self.unchoked_peers and peer != self.optimistically_unchoked_peer:
                                    print(f"[DEBUG] Cannot send piece {piece_id} - peer {peer.ID} is choked")
                                elif piece_id >= len(self.bitfield) or self.bitfield[piece_id] != '1':
                                    print(f"[DEBUG] Cannot send piece {piece_id} - don't have this piece")
                                else:
                                    print(f"[DEBUG] Cannot send piece {piece_id} - unknown reason")
                        except ValueError as e:
                            print(f"[DEBUG] Invalid piece ID received: {e}")
                            traceback.print_exc()

                elif mtype == "7":
                    # Since piece data is handled in the request_piece method, this is mainly for logging
                    print(f"Received piece message from peer {peer.ID}")
                    # Skip the payload since it's handled elsewhere
                    if mlength > 1:
                        peer.socket.recv(mlength - 1)
                else:
                    print(f"Unknown message type {mtype} from peer {peer.ID}")
                    # Skip the payload
                    if mlength > 1:
                        peer.socket.recv(mlength - 1)
                            
            except Exception as e:
                print(f"Error receiving from peer {peer.ID}: {e}")
                traceback.print_exc()
                break
                
        # Connection ended, clean up
        self.remove_peer(peer)

    def select_preferred_neighbors(self):
        """Periodically select preferred neighbors"""
        while self.running:
            # Sleep for unchoking interval
            print(f"Sleeping for {self.config.unchoking_interval} seconds before selecting preferred neighbors")
            time.sleep(self.config.unchoking_interval)
            
            with self.peers_lock:
                if not self.peers:
                    print("No peers connected, skipping preferred neighbor selection")
                    continue
                
                print(f"Selecting preferred neighbors from {len(self.peers)} connected peers")
                    
                # Calculate download rates for each peer
                for peer in self.peers:
                    peer.last_download_rate = peer.pieces_downloaded
                    print(f"Peer {peer.ID} download rate: {peer.last_download_rate} pieces")
                    peer.pieces_downloaded = 0  # Reset for next interval
                    
                # Get interested peers
                candidates = [p for p in self.peers if p.interested]
                print(f"Found {len(candidates)} interested peers")
                
                if not candidates:
                    print("No interested peers, skipping preferred neighbor selection")
                    continue
                    
                # If we have the complete file, select randomly
                if self.bitfield.count('1') == NUM_PIECES:
                    print("We have complete file, selecting neighbors randomly")
                    # Random selection from interested peers
                    selected_peers = random.sample(candidates, 
                                                min(self.config.num_of_pref_neighbords, len(candidates)))
                else:
                    print("Selecting neighbors based on download rates")
                    # Select based on download rates
                    sorted_peers = sorted(candidates, key=lambda p: p.last_download_rate, reverse=True)
                    selected_peers = sorted_peers[:min(self.config.num_of_pref_neighbords, len(sorted_peers))]
                
                print(f"Selected {len(selected_peers)} preferred neighbors")
                    
                # Unchoke selected peers
                new_unchoked = selected_peers.copy()
                
                # Don't disturb optimistically unchoked peer
                if self.optimistically_unchoked_peer and self.optimistically_unchoked_peer not in new_unchoked:
                    new_unchoked.append(self.optimistically_unchoked_peer)
                    print(f"Added optimistically unchoked peer {self.optimistically_unchoked_peer.ID} to the unchoked list")
                    
                # Handle peers that need to be choked
                for peer in self.unchoked_peers:
                    if peer not in new_unchoked and peer != self.optimistically_unchoked_peer:
                        print(f"Choking peer {peer.ID}")
                        choke_message = self.make_choke_message()
                        try:
                            peer.socket.sendall(choke_message.get_message())
                            print(f"Sent choke message to peer {peer.ID}")
                        except Exception as e:
                            print(f"Failed to send choke message to peer {peer.ID}: {e}")
                            
                # Handle peers that need to be unchoked
                for peer in new_unchoked:
                    if peer not in self.unchoked_peers:
                        print(f"Unchoking peer {peer.ID}")
                        unchoke_message = self.make_unchoke_message()
                        try:
                            peer.socket.sendall(unchoke_message.get_message())
                            print(f"Sent unchoke message to peer {peer.ID}")
                        except Exception as e:
                            print(f"Failed to send unchoke message to peer {peer.ID}: {e}")
                            
                # Update unchoked peers list
                self.unchoked_peers = [p for p in new_unchoked if p != self.optimistically_unchoked_peer]
                
                # Log preferred neighbors change
                pref_ids = [peer.ID for peer in self.unchoked_peers]
                print(f"New preferred neighbors: {pref_ids}")
                self.logger.log_change_in_pref_neighbors(pref_ids)

    def select_optimistically_unchoked_neighbor(self):
        """Periodically select an optimistically unchoked neighbor"""
        while self.running:
            # Sleep for optimistic unchoking interval
            print(f"Sleeping for {self.config.optimistic_unchoking_interval} seconds before selecting optimistically unchoked neighbor")
            time.sleep(self.config.optimistic_unchoking_interval)
            
            with self.peers_lock:
                # Get choked but interested peers
                candidates = [p for p in self.peers if p.interested and p not in self.unchoked_peers]
                print(f"Found {len(candidates)} candidates for optimistic unchoking")
                
                if not candidates:
                    print("No candidates for optimistic unchoking, skipping")
                    continue
                    
                # Select a random peer
                selected_peer = random.choice(candidates)
                print(f"Selected peer {selected_peer.ID} as optimistically unchoked neighbor")
                
                # Unchoke the previously optimistically unchoked peer if not in preferred neighbors
                if (self.optimistically_unchoked_peer and 
                    self.optimistically_unchoked_peer not in self.unchoked_peers):
                    print(f"Choking previous optimistically unchoked peer {self.optimistically_unchoked_peer.ID}")
                    choke_message = self.make_choke_message()
                    try:
                        self.optimistically_unchoked_peer.socket.sendall(choke_message.get_message())
                        print(f"Sent choke message to peer {self.optimistically_unchoked_peer.ID}")
                    except Exception as e:
                        print(f"Failed to send choke message to peer {self.optimistically_unchoked_peer.ID}: {e}")
                        
                # Set new optimistically unchoked peer
                self.optimistically_unchoked_peer = selected_peer
                
                # Send unchoke message to the selected peer
                unchoke_message = self.make_unchoke_message()
                try:
                    selected_peer.socket.sendall(unchoke_message.get_message())
                    print(f"Sent unchoke message to peer {selected_peer.ID}")
                except Exception as e:
                    print(f"Failed to send unchoke message to peer {selected_peer.ID}: {e}")
                    
                # Log optimistically unchoked neighbor change
                self.logger.log_optimistic_unchoke(selected_peer.ID)

    def shutdown(self):
        """Gracefully shut down the client"""
        print("Shutting down client...")
        self.running = False
        
        # Close all peer connections
        with self.peers_lock:
            for peer in self.peers:
                try:
                    print(f"Closing connection to peer {peer.ID}")
                    peer.socket.close()
                except Exception as e:
                    print(f"Error closing peer socket: {e}")
                    
        # Close server socket
        try:
            if hasattr(self, 's') and self.s:
                self.s.close()
                print("Closed server socket")
        except Exception as e:
            print(f"Error closing server socket: {e}")
            
        print("Client shutdown complete")


    def create_handshake(self):
        """Create a handshake message"""
        zero_bytes = '0' * 10
        handshake_message = "P2PFILESHARINGPROJ" + zero_bytes + self.ID
        return handshake_message
        
    def check_handshake(self, handshake_message):
        """Check the handshake message for valid header"""
        if len(handshake_message) != 32:
            print(f"Handshake length mismatch: {len(handshake_message)} != 32")
            return False
            
        header = handshake_message[:18]
        if header != "P2PFILESHARINGPROJ":
            print(f"Handshake header mismatch: '{header}' != 'P2PFILESHARINGPROJ'")
            return False
            
        return True
        
    def make_choke_message(self):
        """Create a choke message"""
        return Message("choke")
        
    def make_unchoke_message(self):
        """Create an unchoke message"""
        return Message("unchoke")
        
    def make_interested_message(self):
        """Create an interested message"""
        return Message("interested")
        
    def make_not_interested_message(self):
        """Create a not interested message"""
        return Message("not interested")
        
    def make_have_message(self, piece_index):
        """Create a have message"""
        return Message("have", piece_index)
        
    def make_bitfield_message(self, bitfield):
        """Create a bitfield message"""
        # Ensure the bitfield is properly formatted
        if isinstance(bitfield, str):
            # Convert string bitfield (e.g. "10101") to bytes
            # First pad to multiple of 8 bits
            padded_length = (len(bitfield) + 7) // 8 * 8
            padded_bitfield = bitfield.ljust(padded_length, '0')
            
            # Convert to bytes
            bytes_array = bytearray()
            for i in range(0, len(padded_bitfield), 8):
                byte = 0
                for j in range(8):
                    if i + j < len(padded_bitfield) and padded_bitfield[i + j] == '1':
                        byte |= (1 << (7 - j))
                bytes_array.append(byte)
                
            return Message("bitfield", bytes(bytes_array))
        else:
            # If already bytes, use as is
            return Message("bitfield", bitfield)
        
    def make_request_message(self, piece_index):
        """Create a request message"""
        return Message("request", piece_index)
        
    def make_piece_message(self, piece_index, piece_content):
        """Create a piece message with binary content"""
        # Ensure piece_content is bytes
        if not isinstance(piece_content, bytes):
            piece_content = piece_content.encode('utf-8')
            
        # Create a binary message
        return Message("piece", piece_content)
    
    # Modify the request_piece method with enhanced debugging
    def request_piece(self, peer):
        """Request a random piece that we need from the peer"""
        # Find pieces that peer has and we don't have
        desired_pieces = []
        with self.bitfield_lock:
            for i in range(min(len(self.bitfield), len(peer.bitfield))):
                if self.bitfield[i] == '0' and peer.bitfield[i] == '1' and not self.pieces_requested[i]:
                    desired_pieces.append(i)
        
        print(f"[DEBUG] Pieces available from peer {peer.ID}: {len(desired_pieces)}")
                    
        if desired_pieces:
            # Choose a random piece
            random_piece = random.choice(desired_pieces)
            print(f"[DEBUG] Requesting piece {random_piece} from peer {peer.ID}")
            
            # Mark as requested
            self.pieces_requested[random_piece] = True
            
            # Create request message and send
            request_message = self.make_request_message(str(random_piece))
            try:
                # Send request message
                peer.socket.sendall(request_message.get_message())
                print(f"[DEBUG] Sent request for piece {random_piece} to peer {peer.ID}")
                
                # Set a reasonable timeout for large files
                peer.socket.settimeout(120.0)  # 2 minute timeout
                
                # Receive piece length and type
                length_bytes = peer.socket.recv(4)
                if not length_bytes:
                    print(f"[DEBUG] Connection closed while receiving length")
                    self.pieces_requested[random_piece] = False
                    return
                    
                type_byte = peer.socket.recv(1)
                if not type_byte or type_byte.decode('utf-8') != "7":  # Must be a piece message
                    print(f"[DEBUG] Received wrong message type: {type_byte}")
                    self.pieces_requested[random_piece] = False
                    return
                    
                # Get piece length from the message
                piece_length = int(length_bytes.decode('utf-8')) - 1  # -1 for message type
                
                # Receive the piece index
                index_buffer = b""
                while len(index_buffer) < 4:  # Assume piece index is 4 bytes
                    chunk = peer.socket.recv(4 - len(index_buffer))
                    if not chunk:
                        break
                    index_buffer += chunk
                
                # Extract the actual piece data (skip the piece index)
                piece_content = b""
                bytes_left = piece_length - 4  # Subtract the piece index size
                
                while bytes_left > 0:
                    chunk_size = min(BUFFER_SIZE, bytes_left)
                    chunk = peer.socket.recv(chunk_size)
                    if not chunk:
                        print(f"[DEBUG] Connection closed during transfer after {len(piece_content)} bytes")
                        break
                        
                    piece_content += chunk
                    bytes_left -= len(chunk)
                    
                    if len(piece_content) % (BUFFER_SIZE*10) == 0:
                        print(f"[DEBUG] Received {len(piece_content)} of {piece_length - 4} bytes...")
                
                # Reset socket timeout to default
                peer.socket.settimeout(None)
                
                print(f"[DEBUG] Total received: {len(piece_content)} bytes for piece {random_piece}")
                
                # Process the received piece
                if piece_content and len(piece_content) == self.config.piece_size or (
                    random_piece == NUM_PIECES - 1 and len(piece_content) <= self.config.piece_size
                ):
                    print(f"[DEBUG] Processing received piece {random_piece} (size: {len(piece_content)})")
                    
                    # Update bitfield
                    with self.bitfield_lock:
                        temp_bitfield = list(self.bitfield)
                        temp_bitfield[random_piece] = '1'
                        self.bitfield = ''.join(temp_bitfield)
                    
                    # Store piece
                    with self.file_pieces_lock:
                        self.file_pieces[random_piece] = piece_content
                        
                        # Write to file
                        file_path = os.path.join(self.peer_directory, self.config.file_name)
                        
                        # Create file if it doesn't exist but don't initialize with zeros
                        if not os.path.exists(file_path):
                            open(file_path, 'wb').close()  # Create empty file
                        
                        # Write the piece directly to the correct position
                        with open(file_path, 'r+b') as f:
                            offset = random_piece * self.config.piece_size
                            f.seek(offset)
                            bytes_written = f.write(piece_content)
                            print(f"[DEBUG] Wrote {bytes_written} bytes to file at position {offset}")
                            
                    # Log download and update statistics
                    peer.pieces_downloaded += 1
                    num_pieces = self.bitfield.count('1')
                    self.logger.log_downloading_piece(peer.ID, str(random_piece), num_pieces)
                    
                    # Send have messages to all peers
                    have_message = self.make_have_message(str(random_piece))
                    have_encoded = have_message.get_message()
                    
                    with self.peers_lock:
                        for other_peer in self.peers:
                            if other_peer.ID != peer.ID:
                                try:
                                    other_peer.socket.sendall(have_encoded)
                                    print(f"[DEBUG] Sent have message for piece {random_piece} to peer {other_peer.ID}")
                                except Exception as e:
                                    print(f"[DEBUG] Error sending have message to peer {other_peer.ID}: {e}")
                    
                    # Check if download is complete
                    if num_pieces == NUM_PIECES:
                        self.logger.log_download_completion()
                        print(f"[DEBUG] Download complete! All {NUM_PIECES} pieces received.")
                        self.reconstruct_file()
                    
                    # Request another piece if not choked
                    if not peer.choked:
                        print(f"[DEBUG] Requesting another piece from peer {peer.ID}")
                        self.request_piece(peer)
                    else:
                        print(f"[DEBUG] Not requesting another piece because peer {peer.ID} has choked us")
                else:
                    print(f"[DEBUG] Received incomplete or invalid piece data: got {len(piece_content)} bytes")
                    self.pieces_requested[random_piece] = False  # Reset request flag
                    
            except socket.timeout:
                print(f"[DEBUG] Timeout while receiving piece {random_piece} from peer {peer.ID}")
                self.pieces_requested[random_piece] = False  # Reset request flag
            except Exception as e:
                print(f"[DEBUG] Error receiving piece: {e}")
                traceback.print_exc()
                self.pieces_requested[random_piece] = False  # Reset request flag
        elif peer.interested:
            # No more pieces needed from this peer, send not interested
            print(f"[DEBUG] No more pieces needed from peer {peer.ID}, sending not interested")
            not_interested_message = self.make_not_interested_message()
            try:
                peer.socket.sendall(not_interested_message.get_message())
                peer.interested = False
                print(f"[DEBUG] Sent not interested message to peer {peer.ID}")
            except Exception as e:
                print(f"[DEBUG] Failed to send not interested message to peer {peer.ID}: {e}")

    def remove_peer(self, peer):
        """Remove peer from all collections and close socket"""
        try:
            print(f"Removing peer {peer.ID} from connections")
            
            # Close socket
            if peer.socket:
                peer.socket.close()
                
            # Remove from collections
            with self.peers_lock:
                if peer in self.peers:
                    self.peers.remove(peer)
                    print(f"Removed peer {peer.ID} from peers list")
                    
                if peer in self.unchoked_peers:
                    self.unchoked_peers.remove(peer)
                    print(f"Removed peer {peer.ID} from unchoked peers list")
                    
                if peer in self.interested_peers:
                    self.interested_peers.remove(peer)
                    print(f"Removed peer {peer.ID} from interested peers list")
                    
                if peer == self.optimistically_unchoked_peer:
                    self.optimistically_unchoked_peer = None
                    print(f"Removed peer {peer.ID} as optimistically unchoked peer")
                    
        except Exception as e:
            print(f"Error removing peer {peer.ID}: {e}")

    def reconstruct_file(self):
        """Reconstruct the complete file from pieces with validation"""
        try:
            output_file = os.path.join(self.peer_directory, self.config.file_name)
            print(f"Reconstructing file to: {output_file}")
            
            # First check if we have all the pieces
            missing_pieces = []
            for i in range(NUM_PIECES):
                if not self.file_pieces[i]:
                    missing_pieces.append(i)
                    
            if missing_pieces:
                print(f"Warning: Missing {len(missing_pieces)} pieces during reconstruction: {missing_pieces[:10]}...")
                print("Reconstruction might be incomplete")
                return False
            
            # Open file for writing in binary mode
            with open(output_file, 'wb') as f:
                for i in range(NUM_PIECES):
                    if self.file_pieces[i]:
                        # Validate piece content
                        if not isinstance(self.file_pieces[i], bytes):
                            print(f"Warning: Piece {i} is not binary data. Type: {type(self.file_pieces[i])}")
                            continue
                            
                        f.write(self.file_pieces[i])
                        
                        # Progress indicator for large files
                        if NUM_PIECES > 50 and i % (NUM_PIECES // 10) == 0:
                            progress = 100 * i / NUM_PIECES
                            print(f"File reconstruction progress: {progress:.1f}%")
                    else:
                        print(f"Error: Missing piece {i} during reconstruction")
                        return False
            
            # Verify file size
            actual_size = os.path.getsize(output_file)
            if actual_size == self.config.file_size:
                print(f"File size verification successful: {actual_size} bytes")
            else:
                print(f"File size verification failed: Expected {self.config.file_size} bytes, got {actual_size} bytes")
                # Try to fix the file size
                with open(output_file, 'r+b') as f:
                    f.truncate(self.config.file_size)
                
                print(f"Truncated file to expected size: {self.config.file_size} bytes")
            
            return True
        except Exception as e:
            print(f"Error reconstructing file: {e}")
            import traceback
            traceback.print_exc()
            return False
    def validate_file(self, file_path):
        """Validate that the file at the given path is properly formed"""
        try:
            # Check file exists
            if not os.path.exists(file_path):
                print(f"File does not exist: {file_path}")
                return False
                
            # Check file size
            actual_size = os.path.getsize(file_path)
            if actual_size != self.config.file_size:
                print(f"File size mismatch: Expected {self.config.file_size} bytes, got {actual_size} bytes")
                return False
                
            # For image files, try to validate the header
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                with open(file_path, 'rb') as f:
                    header = f.read(8)  # Read first 8 bytes
                    
                    # Check for common image headers
                    if file_path.lower().endswith(('.jpg', '.jpeg')):
                        if header[:2] != b'\xFF\xD8':  # JPEG signature
                            print(f"Invalid JPEG header: {header[:2].hex()}")
                            return False
                    elif file_path.lower().endswith('.png'):
                        if header[:8] != b'\x89PNG\r\n\x1a\n':  # PNG signature
                            print(f"Invalid PNG header: {header.hex()}")
                            return False
            
            return True
        except Exception as e:
            print(f"Error validating file: {e}")
            return False
    
    def debug_peer_state(self):
        """Print debug information about all peers and their state"""
        print("===== DEBUG: PEER STATE =====")
        print(f"My ID: {self.ID}")
        print(f"My bitfield: {self.bitfield}")
        print(f"My file pieces: {[i for i, p in enumerate(self.file_pieces) if p is not None]}")
        print(f"Connected peers: {len(self.peers)}")
        
        with self.peers_lock:
            for peer in self.peers:
                print(f"Peer {peer.ID}:")
                print(f"  - Bitfield: {peer.bitfield}")
                print(f"  - Interested: {peer.interested}")
                print(f"  - Choked: {peer.choked}")
                print(f"  - Complete: {peer.complete}")
                print(f"  - Download rate: {peer.last_download_rate}")
                print(f"  - Pieces downloaded: {peer.pieces_downloaded}")
        
        print(f"Unchoked peers: {[p.ID for p in self.unchoked_peers]}")
        print(f"Optimistically unchoked peer: {self.optimistically_unchoked_peer.ID if self.optimistically_unchoked_peer else 'None'}")
        print("==============================")
        
        # Schedule next debug print
        if self.running:
            threading.Timer(10.0, self.debug_peer_state).start()

    def test_connection(self, peer_id):
        """Test connection to a specific peer"""
        with self.peers_lock:
            for peer in self.peers:
                if peer.ID == peer_id:
                    try:
                        # Send a simple have message for piece 0
                        have_message = self.make_have_message("0")
                        peer.socket.sendall(have_message.get_message())
                        print(f"Sent test have message to peer {peer_id}")
                        return True
                    except Exception as e:
                        print(f"Connection test to peer {peer_id} failed: {e}")
                        return False
        
        print(f"Peer {peer_id} not found in connected peers")
        return False
    
    def diagnose_connections(self):
        """Diagnostic method to check all connections"""
        print("============ CONNECTION DIAGNOSIS ============")
        print(f"My ID: {self.ID}")
        print(f"My bitfield: {self.bitfield}")
        print(f"Connected peers: {len(self.peers)}")
        
        with self.peers_lock:
            for peer in self.peers:
                print(f"Peer {peer.ID}:")
                print(f"  - Socket: {peer.socket}")
                print(f"  - Bitfield: {peer.bitfield}")
                print(f"  - Interested: {peer.interested}")
                print(f"  - Choked: {peer.choked}")
                
                # Try to send a test message
                try:
                    test_message = Message("have", "0")
                    peer.socket.sendall(test_message.get_message())
                    print(f"  - Test message sent successfully")
                except Exception as e:
                    print(f"  - Test message failed: {e}")
                    traceback.print_exc()
        
        print("==============================================")

    def force_piece_request(self, peer_id):
        """Force a piece request to a specific peer for testing"""
        print(f"Forcing piece request to peer {peer_id}")
        target_peer = None
        
        with self.peers_lock:
            for peer in self.peers:
                if peer.ID == peer_id:
                    target_peer = peer
                    break
        
        if not target_peer:
            print(f"Peer {peer_id} not found")
            return False
        
        # Make sure we're interested in this peer
        if not target_peer.interested:
            interested_message = self.make_interested_message()
            try:
                target_peer.socket.sendall(interested_message.get_message())
                target_peer.interested = True
                print(f"Sent forced interested message to peer {peer_id}")
            except Exception as e:
                print(f"Failed to send interested message: {e}")
                return False
        
        # Force a piece request regardless of choke state
        desired_pieces = []
        with self.bitfield_lock:
            for i in range(min(len(self.bitfield), len(target_peer.bitfield))):
                if self.bitfield[i] == '0' and target_peer.bitfield[i] == '1':
                    desired_pieces.append(i)
        
        if not desired_pieces:
            print(f"No desired pieces from peer {peer_id}")
            return False
        
        # Choose a random piece
        random_piece = random.choice(desired_pieces)
        print(f"Forcing request for piece {random_piece} from peer {peer_id}")
        
        # Create and send request message
        request_message = self.make_request_message(str(random_piece))
        try:
            target_peer.socket.sendall(request_message.get_message())
            print(f"Sent forced request for piece {random_piece} to peer {peer_id}")
            return True
        except Exception as e:
            print(f"Failed to send request message: {e}")
            traceback.print_exc()
            return False

    def print_message_debug(self, message_type, message_payload=b""):
        """Debug print message format"""
        message = Message(message_type, message_payload)
        encoded = message.get_message()
        print(f"DEBUG - {message_type} message format:")
        print(f"  Length: {len(encoded)} bytes")
        print(f"  Hex: {encoded.hex()}")
        print(f"  Raw: {encoded}")

    def debug_parse_message(self, message_bytes):
        """Attempt to parse a raw message and print debug info"""
        try:
            if len(message_bytes) < 5:
                print(f"Message too short: {len(message_bytes)} bytes")
                return None
                
            length_str = message_bytes[:4].decode('utf-8')
            if not length_str.isdigit():
                print(f"Invalid length format: '{length_str}'")
                return None
                
            length = int(length_str)
            if length < 1:
                print(f"Invalid length value: {length}")
                return None
                
            message_type = message_bytes[4:5].decode('utf-8')
            if message_type not in MESSAGE_TYPE_DECODE:
                print(f"Unknown message type: '{message_type}'")
                return None
                
            decoded_type = MESSAGE_TYPE_DECODE[message_type]
            print(f"Parsed message: Type={decoded_type}, Length={length}")
            
            if length > 1:
                payload = message_bytes[5:5+length-1]
                print(f"Payload: {payload}")
                if decoded_type == "piece":
                    # Try to parse piece index
                    try:
                        index_end = payload.find(b' ')
                        if index_end > 0:
                            piece_index = int(payload[:index_end].decode('utf-8'))
                            print(f"Piece index: {piece_index}")
                            print(f"Data length: {len(payload) - index_end - 1}")
                    except Exception as e:
                        print(f"Failed to parse piece index: {e}")
            
            return {
                "type": decoded_type,
                "length": length,
                "payload": message_bytes[5:5+length-1] if length > 1 else b""
            }
        except Exception as e:
            print(f"Error parsing message: {e}")
            traceback.print_exc()
            return None

    def send_direct_test_message(self, peer_id, message_type, message_payload=b""):
        """Send a test message directly to a specific peer"""
        with self.peers_lock:
            for peer in self.peers:
                if peer.ID == peer_id:
                    try:
                        message = Message(message_type, message_payload)
                        peer.socket.sendall(message.get_message())
                        print(f"Direct {message_type} test message sent to peer {peer_id}")
                        return True
                    except Exception as e:
                        print(f"Failed to send test message: {e}")
                        traceback.print_exc()
                        return False
        
        print(f"Peer {peer_id} not found")
        return False