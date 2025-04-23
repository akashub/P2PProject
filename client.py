import random
import socket
import threading
import time
import math
import os
from logger import Logger
from config import Config

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

class Message:
    def __init__(self, message_type, message_payload=""):
        self.message_length = str(len(message_payload) + 1)  # +1 for the message type
        self.decoded_message_type = message_type
        self.encoded_message_type = MESSAGE_TYPE_ENCODE[message_type]
        self.message_payload = message_payload

        # Ensure message_length is 4 bytes by padding with zeros
        while len(self.message_length) < 4:
            self.message_length = "0" + self.message_length

    def get_message(self):
        length_bytes = int(self.message_length).to_bytes(4, byteorder='big')
        type_byte = int(self.encoded_message_type).to_bytes(1, byteorder='big')

        if isinstance(self.message_payload, str):
            payload_bytes = self.message_payload.encode('utf-8')
        else:
            payload_bytes = self.message_payload
        return length_bytes + type_byte + payload_bytes

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
        self.requested_piece = None

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
        self.requests_lock = threading.Lock()
        
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
                # Read file into memory in pieces
                with open(path, 'rb') as f:
                    for i in range(NUM_PIECES):
                        try:
                            start = i * self.config.piece_size
                            
                            f.seek(start)
                            if i == NUM_PIECES - 1:  # Last piece
                                remaining_size = self.config.file_size - start
                                piece_data = f.read(remaining_size)
                                print("final piece: ", remaining_size)
                            else:
                                piece_data = f.read(self.config.piece_size)

                            if piece_data:
                                self.file_pieces[i] = piece_data
                        except Exception as e:
                            print(f"Error reading piece {i}: {e}")
                
                # Copy file to peer directory if it's not already there
                if path != os.path.join(self.peer_directory, self.config.file_name):
                    os.makedirs(self.peer_directory, exist_ok=True)
                    import shutil
                    shutil.copy2(path, os.path.join(self.peer_directory, self.config.file_name))
                    print(f"Copied file to peer directory: {self.peer_directory}")
                
                # Update bitfield
                self.bitfield = "1" * NUM_PIECES
                break
        
        if not file_found:
            print(f"Warning: File {self.config.file_name} not found in any expected locations!")
            self.bitfield = "0" * NUM_PIECES
            
    def setup(self, other_peers):
        """Initialize server socket and connect to existing peers"""
        # Start preferred neighbors selection thread
        threading.Thread(target=self.select_preferred_neighbors, daemon=True).start()
        
        # Start optimistically unchoked neighbor selection thread
        threading.Thread(target=self.select_optimistically_unchoked_neighbor, daemon=True).start()
        
        # Start server socket to listen for incoming connections
        threading.Thread(target=self.listen_for_connections, daemon=True).start()
        
        # Connect to existing peers
        self.initiate_connections(other_peers)
        
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
                bitfield_message = self.make_bitfield_message(self.bitfield)
                encoded_message = bitfield_message.get_message()
                print(encoded_message)
                peer_socket.sendall(encoded_message)
                print(f"Sent bitfield to peer {peer_id}")
            
            # Start receiving messages from this peer
            peer_socket.settimeout(None)  # Remove timeout for normal operation
            self.receive_from_peer(peer)
            
        except Exception as e:
            print(f"Error in setup_connection_from_listening: {e}")
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
            print(peer_id)
            # Add new connection to list of peers
            peer = Peer(peer_socket, peer_id)
            with self.peers_lock:
                self.peers.append(peer)
            print(peer.ID)
            # Log the connection
            self.logger.log_tcp_connection(peer.ID, True)
            print(peer.ID)
            # Send bitfield to peer if we have any pieces
            if self.bitfield != "0" * NUM_PIECES:
                bitfield_message = self.make_bitfield_message(self.bitfield)
                encoded_message = bitfield_message.get_message()
                print(encoded_message)
                peer_socket.sendall(encoded_message)
                print(f"Sent bitfield to peer {peer_id}")
            else:
                print("skipping sending bitfield bc empty")
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
                mlength_bytes = peer.socket.recv(4)
                if not mlength_bytes:
                    print(f"Connection with peer {peer.ID} closed")
                    break

                mlength = int.from_bytes(mlength_bytes, byteorder='big')
        
                # Then receive message type (1 byte)
                mtype_bytes = peer.socket.recv(1)
                if not mtype_bytes:
                    break
                mtype = str(mtype_bytes[0])
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
                            self.request_piece(peer)
                        
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
                            
                        peer.bitfield = ''.join(f'{byte:08b}' for byte in bitfield_bytes)
                        print(f"Received bitfield from peer {peer.ID}: {peer.bitfield}")
                        
                        # Check if they have any pieces we need
                        needs_pieces = False
                        with self.bitfield_lock:
                            for i in range(min(len(self.bitfield), len(peer.bitfield))):
                                if self.bitfield[i] == '0' and peer.bitfield[i] == '1':
                                    needs_pieces = True
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
                            print(f"Sent not interested message to peer {peer.ID}")
                elif mtype == "6":
                    # A piece has been requested
                    if mlength > 1:  # Must have payload
                        piece_id_bytes = peer.socket.recv(mlength - 1)
                        if not piece_id_bytes:
                            print("not piece_id_bytes")
                            break
                            
                        try:
                            piece_id = int(piece_id_bytes.decode('utf-8'))
                            print("valid ID: ", piece_id)
                            print(len(self.file_pieces))
                            # Only send if peer is unchoked and we have the piece
                            with self.peers_lock:
                                if ((peer.ID in [p.ID for p in self.unchoked_peers] or (self.optimistically_unchoked_peer and peer.ID == self.optimistically_unchoked_peer.ID)) 
                                    and piece_id < len(self.bitfield) and self.bitfield[piece_id] == '1'):
                                    print("waiting for lock")
                                    with self.file_pieces_lock:
                                        print("entered lock")
                                        piece_content = self.file_pieces[piece_id]

                                        piece_id_bytes = piece_id.to_bytes(4, byteorder='big')
                                        payload = piece_id_bytes + piece_content
                                        if piece_content:
                                            piece_message = Message("piece", payload)
                                            try:
                                                peer.socket.sendall(piece_message.get_message())
                                                print(f"Sent piece {piece_id} to peer {peer.ID}")
                                            except Exception as e:
                                                print(f"Error sending piece {piece_id} to peer {peer.ID}: {e}")
                                else:
                                    print(f"Cannot send piece {piece_id} - not authorized")
                        except ValueError as e:
                            print(f"Invalid piece ID received: {e}")
                elif mtype == "7":
                    payload = peer.socket.recv(mlength)
                    
                    piece_id = int.from_bytes(payload[:4], byteorder='big')
                    piece_content = payload[4:]
                    print("payload length: ", mlength)

                    with self.requests_lock:
                        if peer.requested_piece and piece_id != peer.requested_piece:
                            print(f"Unexpected piece {piece_id} received, expected {peer.requested_piece}")
                            continue
                        else:
                            peer.requested_piece = None

                    self.process_piece(peer, piece_id, piece_content)
                    if not peer.choked:
                        self.request_piece(peer)
            except Exception as e:
                print(f"Error receiving from peer {peer.ID}: {e}")
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
                '''
                # Don't disturb optimistically unchoked peer
                if self.optimistically_unchoked_peer and self.optimistically_unchoked_peer not in new_unchoked:
                    new_unchoked.append(self.optimistically_unchoked_peer)
                    print(f"Added optimistically unchoked peer {self.optimistically_unchoked_peer.ID} to the unchoked list")
                 '''   
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
                    if peer not in self.unchoked_peers and peer != self.optimistically_unchoked_peer:
                        print(f"Unchoking peer {peer.ID}")
                        unchoke_message = self.make_unchoke_message()
                        try:
                            peer.socket.sendall(unchoke_message.get_message())
                            print(f"Sent unchoke message to peer {peer.ID}")
                        except Exception as e:
                            print(f"Failed to send unchoke message to peer {peer.ID}: {e}")
                            
                # Update unchoked peers list
                self.unchoked_peers = [p for p in new_unchoked]
                print([p.ID for p in self.unchoked_peers])
                
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
                    self.optimistically_unchoked_peer not in self.unchoked_peers and self.optimistically_unchoked_peer != selected_peer):
                    print(f"Choking previous optimistically unchoked peer {self.optimistically_unchoked_peer.ID}")
                    choke_message = self.make_choke_message()
                    try:
                        self.optimistically_unchoked_peer.socket.sendall(choke_message.get_message())
                        print(f"Sent choke message to peer {self.optimistically_unchoked_peer.ID}")
                    except Exception as e:
                        print(f"Failed to send choke message to peer {self.optimistically_unchoked_peer.ID}: {e}")
                        
                if self.optimistically_unchoked_peer and self.optimistically_unchoked_peer != selected_peer:
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
        padded_bitstring = bitfield.ljust(math.ceil(len(bitfield)/8)*8, '0')
        byte_array = bytearray()
        for i in range(0, len(padded_bitstring), 8):
            byte = padded_bitstring[i:i+8]
            byte_array.append(int(byte, 2))
        return Message("bitfield", byte_array)
        
    def make_request_message(self, piece_index):
        """Create a request message"""
        return Message("request", str(piece_index))
        
    def make_piece_message(self, piece_index, piece_content):
        """Create a piece message with binary content"""
        # For piece messages, handle binary content differently
        if isinstance(piece_content, bytes):
            # If piece_content is already bytes, just pass it as-is
            piece_index_bytes = piece_index.to_bytes(4, 'big')  # Ensure piece_index is in bytes format
            return Message("piece", piece_index_bytes + piece_content)
        else:
            # If it's a string, you may want to encode it properly (but usually, this should not happen)
            piece_index_bytes = piece_index.to_bytes(4, 'big')
            return Message("piece", piece_index_bytes + piece_content.encode('utf-8'))  # Convert string content to bytes
    def request_piece(self, peer):
        """Request a random piece from the peer and handle the response using the message protocol."""
        # Find pieces that peer has and we don't have
        desired_pieces = []
        with self.bitfield_lock:
            for i in range(min(len(self.bitfield), len(peer.bitfield))):
                if self.bitfield[i] == '0' and peer.bitfield[i] == '1' and not self.pieces_requested[i]:
                    desired_pieces.append(i)

        print(f"Pieces available from peer {peer.ID}: {len(desired_pieces)}")

        if desired_pieces:
            with self.requests_lock:
                if peer.requested_piece:
                    random_piece = peer.requested_piece
                else:
                    random_piece = random.choice(desired_pieces)
                    peer.requested_piece = random_piece

            print(f"Requesting piece {random_piece} from peer {peer.ID}")
            self.pieces_requested[random_piece] = True

            # Send request message
            request_message = self.make_request_message(random_piece)
            print(request_message)
            try:
                peer.socket.sendall(request_message.get_message())
                print(f"Sent request for piece {random_piece} to peer {peer.ID}")
            except Exception as e:
                print(f"Failed to send request to peer {peer.ID}: {e}")
                self.pieces_requested[random_piece] = False
                return
            with self.requests_lock:
                peer.requested_piece = random_piece

            self.receive_from_peer(peer)
            '''
            # Receive message loop � wait for the piece or a choke
            try:
                while not peer.choked:
                    print("about to peek")
                    mtype, mlength = self.peek_message_header(peer)

                    if mtype is None:
                        print(f"Connection closed by peer {peer.ID} while waiting for piece {random_piece}")
                        self.pieces_requested[random_piece] = False
                        break

                    elif 0<=mtype<=6:  # other message type
                        print(f"Peer {peer.ID} sent something else during piece request {random_piece}")
                        self.pieces_requested[random_piece] = False
                        self.receive_from_peer(peer)
                        continue

                    elif mtype == 7:  # Piece
                        # First 4 bytes = piece index
                        if mlength < 4:
                            print(f"Invalid piece message from peer {peer.ID}")
                            self.pieces_requested[random_piece] = False
                            return

                        full_message = peer.socket.recv(4+1+mlength)
                        payload = full_message[5:]

                        piece_id = int.from_bytes(payload[:4], byteorder='big')
                        piece_content = payload[4:]

                        if piece_id != random_piece:
                            print(f"Unexpected piece {piece_id} received, expected {random_piece}")
                            continue

                        self.process_piece(peer, piece_id, piece_content)
                        return

                    else:
                        print(f"Ignoring message type {mtype} from peer {peer.ID} while waiting for piece")

            except Exception as e:
                print(f"Error receiving message from peer {peer.ID}: {e}")
                self.pieces_requested[random_piece] = False
                '''
        elif peer.interested:
            print(f"No more pieces needed from peer {peer.ID}, sending not interested")
            try:
                not_interested_message = self.make_not_interested_message()
                peer.socket.sendall(not_interested_message.get_message())
                peer.interested = False
                print(f"Sent not interested message to peer {peer.ID}")
            except Exception as e:
                print(f"Failed to send not interested message to peer {peer.ID}: {e}")
        return


    def process_piece(self, peer, piece_id, piece_content):
        with self.bitfield_lock:
            temp_bitfield = list(self.bitfield)
            temp_bitfield[piece_id] = '1'
            self.bitfield = ''.join(temp_bitfield)

        with self.file_pieces_lock:
            self.file_pieces[piece_id] = piece_content
            self.pieces_requested[piece_id] = False

            file_path = os.path.join(self.peer_directory, self.config.file_name)
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as f:
                    f.seek(self.config.file_size - 1)
                    f.write(b'\0')

            with open(file_path, 'r+b') as f:
                f.seek(piece_id * self.config.piece_size)
                f.write(piece_content)

        peer.pieces_downloaded += 1
        num_pieces = self.bitfield.count('1')
        self.logger.log_downloading_piece(peer.ID, str(piece_id), num_pieces)

        have_msg = self.make_have_message(str(piece_id)).get_message()
        with self.peers_lock:
            for other_peer in self.peers:
                if other_peer.ID != peer.ID:
                    try:
                        other_peer.socket.sendall(have_msg)
                    except Exception:
                        pass

        if num_pieces == NUM_PIECES:
            self.logger.log_download_completion()
            print("Download complete! All pieces received.")
            self.reconstruct_file()



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
        print(f"Piece lengths: {[len(piece) for piece in self.file_pieces]}")
        try:
            output_file = os.path.join(self.peer_directory, self.config.file_name)
            print(f"Reconstructing file to: {output_file}")
            
            # Create a backup of any existing file
            if os.path.exists(output_file):
                backup_file = output_file + ".bak"
                try:
                    import shutil
                    shutil.copy2(output_file, backup_file)
                    print(f"Created backup of existing file: {backup_file}")
                except Exception as e:
                    print(f"Failed to create backup: {e}")
            
            # Open file for writing
            with open(output_file, 'wb') as f:
                pieces_written = 0
                bytes_written = 0
                
                for i in range(NUM_PIECES):
                    if self.file_pieces[i]:
                        f.write(self.file_pieces[i])
                        pieces_written += 1
                        bytes_written += len(self.file_pieces[i])
                        
                        # Progress indicator for large files
                        if NUM_PIECES > 50 and i % (NUM_PIECES // 10) == 0:
                            progress = 100 * i / NUM_PIECES
                            print(f"File reconstruction progress: {progress:.1f}%")
                    else:
                        print(f"Warning: Missing piece {i} during file reconstruction")
                        # Write empty bytes for missing pieces
                        if i < NUM_PIECES - 1:  # Not the last piece
                            f.write(b'\0' * self.config.piece_size)
                        else:  # Last piece might be smaller
                            last_piece_size = self.config.file_size % self.config.piece_size
                            print(last_piece_size)
                            if last_piece_size == 0:
                                last_piece_size = self.config.piece_size
                            f.write(b'\0' * last_piece_size)
                
                # Set file size to match original
                if bytes_written != self.config.file_size:
                    print(f"Warning: Bytes written ({bytes_written}) doesn't match expected file size ({self.config.file_size})")
                    print("Truncating file to expected size")
                    f.truncate(self.config.file_size)
            
            print(f"File reconstruction complete: {self.config.file_name}")
            print(f"Wrote {pieces_written} of {NUM_PIECES} pieces")
            
            # Verify file size
            actual_size = os.path.getsize(output_file)
            if actual_size == self.config.file_size:
                print(f"File size verification successful: {actual_size} bytes")
            else:
                print(f"File size verification failed: Expected {self.config.file_size} bytes, got {actual_size} bytes")
            
            return True
        except Exception as e:
            print(f"Error reconstructing file: {e}")
            import traceback
            traceback.print_exc()
            return False

        '''
    def peek_message_header(self, peer):
        try:
            # Peek at 5 bytes: 4-byte length + 1-byte message type
            header = peer.socket.recv(5, socket.MSG_PEEK)
            print("peeked at header")
            if len(header) < 5:
                return None, None  # Not enough data yet
            print("length long enough")
            message_length = int.from_bytes(header[:4], byteorder='big')
            message_type = header[4]
            return message_type, message_length
        except Exception as e:
            print(f"Failed to peek message type from peer {peer.ID}: {e}")
            return None
        '''