import random
import socket
import threading
import time
import os
from logger import Logger
from config import Config
from shutil import copy2
from math import ceil



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
        return self.message_length + self.encoded_message_type + self.message_payload

class Peer:
    # Will be used to store information on peers
    def __init__(self, socket_number, ID, num_pieces):
        self.socket = socket_number
        self.ID = ID
        self.bitfield = "0" * num_pieces
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
        self.num_pieces = ceil(self.config.file_size / self.config.piece_size)
        
        self.bitfield = "0" * self.num_pieces
        
        # Create peer directory if it doesn't exist
        self.peer_directory = f"peer_{self.ID}"
        if not os.path.exists(self.peer_directory):
            os.makedirs(self.peer_directory)
            
        # Initialize file pieces as empty
        self.file_pieces = [None] * self.num_pieces
        self.pieces_requested = [False] * self.num_pieces
        
        # For selecting preferred neighbors
        self.download_rates = {}
        self.interested_peers = []
        
        # For thread synchronization
        self.peers_lock = threading.Lock()
        self.bitfield_lock = threading.Lock()
        self.file_pieces_lock = threading.Lock()
        
        # For threading control
        self.running = True
        self.s = None
        
        # Debug info
        print(f"Client initialized with:")
        print(f"  - ID: {ID}")
        print(f"  - Host: {host}")
        print(f"  - Port: {port}")
        print(f"  - Config: {config_filepath}")
        print(f"  - Pieces: {self.num_pieces}")
        print(f"  - Peer directory: {self.peer_directory}")
        
    def has_file(self):
        """If this peer has the file, update its bitfield and read file into memory"""
        # Check for file in various possible locations
        file_paths = [
            os.path.join(self.peer_directory, self.config.file_name),
            os.path.join("project_config_file_small/project_config_file_small", self.ID, self.config.file_name),
            os.path.join("project_config_file_small", self.ID, self.config.file_name),
            # self.config.file_name
        ]
        
        file_found = False
        for path in file_paths:
            if os.path.exists(path):
                print(f"Found file at: {path}")
                file_found = True
                # Read file into memory in pieces
                with open(path, 'rb') as f:
                    for i in range(self.num_pieces):
                        try:
                            f.seek(i * self.config.piece_size)
                            piece_data = f.read(self.config.piece_size)
                            print(f"PIECE {i}: {piece_data[:20]}")
                            if piece_data:
                                self.file_pieces[i] = piece_data
                        except Exception as e:
                            print(f"Error reading piece {i}: {e}")
                
                # Copy file to peer directory if it's not already there
                if path != os.path.join(self.peer_directory, self.config.file_name):
                    os.makedirs(self.peer_directory, exist_ok=True)
                    copy2(path, os.path.join(self.peer_directory, self.config.file_name))
                    print(f"Copied file to peer directory: {self.peer_directory}")
                
                # Update bitfield
                self.bitfield = "1" * self.num_pieces
                break
        
        if not file_found:
            print(f"Warning: File {self.config.file_name} not found in any expected locations!")
            self.bitfield = "0" * self.num_pieces
            
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

        listen_host = "127.0.0.1" if self.host not in ["localhost", "127.0.0.1"] else self.host

        while True:
            try:
                self.s.bind((listen_host, self.port))
                break
            except socket.error:
                self.port += 1

        # Always listen on localhost regardless of configured host
        self.s.listen(10)
        print(f"Listening on {listen_host}:{self.port} (configured host was {self.host})")

        while self.running:
                # Wait for connections and set them up
                peer_socket, peer_address = self.s.accept()
                print(f"Accepted connection from {peer_address}")
                threading.Thread(target=self.setup_connection_from_listening,
                                args=(peer_socket,), daemon=True).start()

        if self.s:
            self.s.close()

    def try_connect(self, peer_info, delay):
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
            threading.Thread(target=self.try_connect, args=(peer_info, delay), daemon=True).start()
            print(f"try failed: {e}")
                
    def initiate_connections(self, other_peers):
        """Reach out to other peers"""
        for peer in other_peers:
            self.try_connect(peer, 5)


    def setup_connection_from_listening(self, peer_socket):
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

            if peer_id in [p.ID for p in self.peers] or peer_id == self.ID:
                print(f"Peer {peer_id} is already connected, closing connection")
                peer_socket.close()
                return
            
            # Reciprocal handshake is then sent
            reciprocal_handshake = self.create_handshake()
            peer_socket.sendall(reciprocal_handshake.encode('utf-8'))
            print(f"Sent reciprocal handshake to peer {peer_id}")
            
            # Add new connection to list of peers
            peer = Peer(peer_socket, peer_id, self.num_pieces)
            with self.peers_lock:
                self.peers.append(peer)
                print(peer.ID, "IS CONNECTED")
            
            # Log connection
            self.logger.log_tcp_connection(peer.ID, False)
            
            # Send bitfield to peer if we have any pieces
            if self.bitfield != "0" * self.num_pieces:
                bitfield_message = self.make_bitfield_message(self.bitfield)
                encoded_message = bitfield_message.get_message().encode('utf-8')
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
            
            # Add new connection to list of peers
            peer = Peer(peer_socket, peer_id, self.num_pieces)
            with self.peers_lock:
                self.peers.append(peer)
            
            # Log the connection
            self.logger.log_tcp_connection(peer.ID, True)
            
            # Send bitfield to peer if we have any pieces
            if self.bitfield != "0" * self.num_pieces:
                bitfield_message = self.make_bitfield_message(self.bitfield)
                encoded_message = bitfield_message.get_message().encode('utf-8')
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
                                peer.socket.sendall(interested_message.get_message().encode('utf-8'))
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
                                    break
                                    
                        if needs_pieces:
                            # Send interested message
                            interested_message = self.make_interested_message()
                            peer.socket.sendall(interested_message.get_message().encode('utf-8'))
                            peer.interested = True
                            print(f"Sent interested message to peer {peer.ID}")
                        else:
                            # Send not interested message
                            not_interested_message = self.make_not_interested_message()
                            peer.socket.sendall(not_interested_message.get_message().encode('utf-8'))
                            peer.interested = False
                            print(f"Sent not interested message to peer {peer.ID}")

                elif mtype == "6":
                    # A piece has been requested
                    if mlength > 1:  # Must have payload
                        piece_id_bytes = peer.socket.recv(mlength - 1)
                        if not piece_id_bytes:
                            break
                            
                        piece_id = int(piece_id_bytes.decode('utf-8'))
                        print(f"Peer {peer.ID} requested piece {piece_id}")
                        if piece_id > self.num_pieces - 1:
                            print(f"Invalid piece ID received: {piece_id}")
                            continue

                        # Only send if peer is unchoked and we have the piece
                        if ((peer in self.unchoked_peers or peer == self.optimistically_unchoked_peer)
                            and piece_id < len(self.bitfield) and self.bitfield[piece_id] == '1'):

                            with self.file_pieces_lock:
                                piece_content = self.file_pieces[piece_id]
                                if piece_content:
                                    try:
                                        peer.socket.sendall(piece_content)
                                        print(f"PIECE {piece_id} SENT: {piece_content[:10]}")
                                        print(f"Sent piece {piece_id} to peer {peer.ID}")
                                    except Exception as e:
                                        print(f"Error sending piece {piece_id} to peer {peer.ID}: {e}")
                        else:
                            print(f"Cannot send piece {piece_id} - not authorized")


                elif mtype == "7":
                    # Since we're ignoring the message format for piece data, this block is now empty
                    # All actual piece data is received directly after sending a request
                    pass
                else:
                    print(f"Unknown message type {mtype} from peer {peer.ID}")
                    # Skip the payload
                    if mlength > 1:
                        peer.socket.recv(mlength - 1)
                            
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
                    print(f"Peer {peer.ID} download rate: {peer.last_download_rate} pieces and is intereseted?: {peer.interested}")
                    peer.pieces_downloaded = 0  # Reset for next interval
                    
                # Get interested peers
                candidates = [p for p in self.peers if p.interested]
                print(f"Found {len(candidates)} interested peers")
                
                if not candidates:
                    print("No interested peers, skipping preferred neighbor selection")
                    continue
                    
                # If we have the complete file, select randomly
                if self.bitfield.count('1') == self.num_pieces:
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
                        peer.choked = True
                        try:
                            peer.socket.sendall(choke_message.get_message().encode('utf-8'))
                            print(f"Sent choke message to peer {peer.ID}")
                        except Exception as e:
                            print(f"Failed to send choke message to peer {peer.ID}: {e}")
                            
                # Handle peers that need to be unchoked
                for peer in new_unchoked:
                    if peer not in self.unchoked_peers:
                        print(f"Unchoking peer {peer.ID}")
                        unchoke_message = self.make_unchoke_message()
                        try:
                            peer.socket.sendall(unchoke_message.get_message().encode('utf-8'))
                            peer.choked = False
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
                        self.optimistically_unchoked_peer.socket.sendall(choke_message.get_message().encode('utf-8'))
                        print(f"Sent choke message to peer {self.optimistically_unchoked_peer.ID}")
                    except Exception as e:
                        print(f"Failed to send choke message to peer {self.optimistically_unchoked_peer.ID}: {e}")
                        
                # Set new optimistically unchoked peer
                self.optimistically_unchoked_peer = selected_peer
                
                # Send unchoke message to the selected peer
                unchoke_message = self.make_unchoke_message()
                try:
                    selected_peer.socket.sendall(unchoke_message.get_message().encode('utf-8'))
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
        print(self.ID, "HAS SEND A BITFIELD MESSAGE")
        """Create a bitfield message"""
        return Message("bitfield", bitfield)
        
    def make_request_message(self, piece_index):
        """Create a request message"""
        return Message("request", piece_index)
        
    def make_piece_message(self, piece_index, piece_content):
        """Create a piece message with binary content"""
        # For piece messages, handle binary content differently
        if isinstance(piece_content, bytes):
            # If piece_content is already bytes, convert to latin1 string
            piece_content_str = piece_content.decode('latin1')
            return Message("piece", piece_index + piece_content_str)
        else:
            # If it's already a string
            return Message("piece", piece_index + piece_content)

    def request_piece(self, peer):
        """Request a random piece that we need from the peer"""
        # Find pieces that peer has and we don't have
        desired_pieces = []
        with self.bitfield_lock:
            for i in range(len(peer.bitfield)):
                if self.bitfield[i] == '0' and peer.bitfield[i] == '1' and not self.pieces_requested[i]:
                    desired_pieces.append(i)
        
        print(f"Pieces available from peer {peer.ID}: {len(desired_pieces)}")
                    
        if desired_pieces:
            # Choose a random piece
            random_piece = random.choice(desired_pieces)
            print(f"Requesting piece {random_piece} from peer {peer.ID}")
            
            # Mark as requested
            self.pieces_requested[random_piece] = True
            
            # Create request message and send
            request_message = self.make_request_message(str(random_piece))
            try:
                peer.socket.sendall(request_message.get_message().encode('utf-8'))
                print(f"Sent request for piece {random_piece} to peer {peer.ID}")
                
                # Immediately receive the piece data after sending request
                start_time = time.time()
                try:
                    piece_content = b''
                    remaining = self.config.piece_size
                    
                    # Set a timeout for piece reception
                    peer.socket.settimeout(10.0)  # 10 second timeout
                    
                    while remaining > 0:
                        chunk = peer.socket.recv(min(self.config.piece_size, remaining))
                        if not chunk:
                            print(f"Connection closed while receiving piece {random_piece}")
                            break
                        piece_content += chunk
                        remaining -= len(chunk)
                        
                        # Progress indicator for large pieces
                        if self.config.piece_size > 100000:  # Over 100KB
                            progress = 100 * (self.config.piece_size - remaining) / self.config.piece_size
                            if progress % 20 == 0:  # Show progress at 0%, 20%, 40%, etc.
                                print(f"Download progress for piece {random_piece}: {progress:.1f}%")
                    
                    # Reset socket timeout to default
                    peer.socket.settimeout(None)
                    
                    # Process the received piece
                    if piece_content:
                        download_time = time.time() - start_time
                        download_rate = len(piece_content) / download_time if download_time > 0 else 0
                        print(f"Received piece {random_piece} ({len(piece_content)} bytes) at {download_rate:.2f} B/s")

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
                            if not os.path.exists(file_path):
                                # Create an empty file of the right size
                                with open(file_path, 'wb') as f:
                                    f.seek(self.config.file_size - 1)
                                    f.write(b'\0')
                            
                            # Write the piece to the correct position in the file
                            with open(file_path, 'r+b') as f:
                                f.seek(random_piece * self.config.piece_size)
                                f.write(piece_content)
                        
                        # Log download and update statistics
                        peer.pieces_downloaded += 1
                        cur_num_pieces = self.bitfield.count('1')
                        self.logger.log_downloading_piece(peer.ID, str(random_piece), cur_num_pieces)
                        
                        # Send have messages to all peers
                        have_message = self.make_have_message(str(random_piece))
                        have_encoded = have_message.get_message().encode('utf-8')
                        
                        with self.peers_lock:
                            for other_peer in self.peers:
                                if other_peer.ID != peer.ID:  # Don't send to the peer we got the piece from
                                    try:
                                        other_peer.socket.sendall(have_encoded)
                                        print(f"Sent have message for piece {random_piece} to peer {other_peer.ID}")
                                    except Exception as e:
                                        print(f"Error sending have message to peer {other_peer.ID}: {e}")
                        
                        # Check if download is complete
                        if cur_num_pieces == self.num_pieces:
                            self.logger.log_download_completion()
                            print(f"Download complete! All {self.num_pieces} pieces received.")
                            self.reconstruct_file()
                            
                            # Tell all peers that they can terminate if everyone has the file
                            # This would require additional protocol extension
                        
                        # Request another piece if not choked
                        if not peer.choked:
                            self.request_piece(peer)
                    else:
                        print(f"Received empty piece data for piece {random_piece}")
                        self.pieces_requested[random_piece] = False  # Reset request flag
                except socket.timeout:
                    print(f"Timeout while receiving piece {random_piece} from peer {peer.ID}")
                    self.pieces_requested[random_piece] = False  # Reset request flag
                except Exception as e:
                    print(f"Error receiving piece data: {e}")
                    self.pieces_requested[random_piece] = False  # Reset request flag
            except Exception as e:
                print(f"Failed to send request message to peer {peer.ID}: {e}")
                self.pieces_requested[random_piece] = False  # Reset request flag
        elif peer.interested:
            # No more pieces needed from this peer, send not interested
            print(f"No more pieces needed from peer {peer.ID}, sending not interested")
            not_interested_message = self.make_not_interested_message()
            try:
                peer.socket.sendall(not_interested_message.get_message().encode('utf-8'))
                # peer.interested = False
                print(f"Sent not interested message to peer {peer.ID}")
            except Exception as e:
                print(f"Failed to send not interested message to peer {peer.ID}: {e}")


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
                
                for i in range(self.num_pieces):
                    print(f"PIECE {i}: {self.file_pieces[i][:20]}")
                    if self.file_pieces[i]:
                        f.write(self.file_pieces[i])
                        pieces_written += 1
                        bytes_written += len(self.file_pieces[i])
                        
                        # Progress indicator for large files
                        if self.num_pieces > 50 and i % (self.num_pieces // 10) == 0:
                            progress = 100 * i / self.num_pieces
                            print(f"File reconstruction progress: {progress:.1f}%")
                    else:
                        print(f"Warning: Missing piece {i} during file reconstruction")
                        # Write empty bytes for missing pieces
                        if i < self.num_pieces - 1:  # Not the last piece
                            f.write(b'\0' * self.config.piece_size)
                        else:  # Last piece might be smaller
                            last_piece_size = self.config.file_size % self.config.piece_size
                            if last_piece_size == 0:
                                last_piece_size = self.config.piece_size
                            f.write(b'\0' * last_piece_size)
                
                # Set file size to match original
                if bytes_written != self.config.file_size:
                    print(f"Warning: Bytes written ({bytes_written}) doesn't match expected file size ({self.config.file_size})")
                    print("Truncating file to expected size")
                    f.truncate(self.config.file_size)
            
            print(f"File reconstruction complete: {self.config.file_name}")
            print(f"Wrote {pieces_written} of {self.num_pieces} pieces")
            
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