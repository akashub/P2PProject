from datetime import datetime
import os

class Logger:
    def __init__(self, peer_id):
        self.peer_id = peer_id
        self.log_filepath = f"log_peer_{peer_id}.log"
        
        # Create log file if it doesn't exist and clear it if it does
        with open(self.log_filepath, "w") as file:
            file.write(f"Log file for Peer {peer_id}\n")
            file.write(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            file.write("-" * 80 + "\n")
    
    def log_message(self, message):
        """Log a message with timestamp"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_filepath, "a") as file:
            file.write(f"{current_time}: {message}\n")
            
    def log_tcp_connection(self, other_peer_id="1002", self_initiated=False):
        """Log TCP connection establishment"""
        if self_initiated:
            message = f"Peer {self.peer_id} makes a connection to Peer {other_peer_id}."
        else:
            message = f"Peer {self.peer_id} is connected from Peer {other_peer_id}."
        self.log_message(message)
    
    def log_change_in_pref_neighbors(self, pref_list=None):
        """Log change in preferred neighbors"""
        if pref_list is None:
            pref_list = []
        formatted_pref_list = ", ".join(pref_list)
        message = f"Peer {self.peer_id} has the preferred neighbors {formatted_pref_list}."
        self.log_message(message)
    
    def log_optimistic_unchoke(self, other_peer_id="1002"):
        """Log change in optimistically unchoked neighbor"""
        message = f"Peer {self.peer_id} has the optimistically unchoked neighbor {other_peer_id}."
        self.log_message(message)
    
    def log_unchoked(self, other_peer_id="1002"):
        """Log when unchoked by another peer"""
        message = f"Peer {self.peer_id} is unchoked by {other_peer_id}."
        self.log_message(message)
    
    def log_choked(self, other_peer_id="1002"):
        """Log when choked by another peer"""
        message = f"Peer {self.peer_id} is choked by {other_peer_id}."
        self.log_message(message)
    
    def log_have_message(self, other_peer_id="1002", piece_index="1"):
        """Log reception of 'have' message"""
        message = f"Peer {self.peer_id} received the 'have' message from {other_peer_id} for the piece {piece_index}."
        self.log_message(message)
    
    def log_interested_message(self, other_peer_id="1002"):
        """Log reception of 'interested' message"""
        message = f"Peer {self.peer_id} received the 'interested' message from {other_peer_id}."
        self.log_message(message)
    
    def log_not_interested_message(self, other_peer_id="1002"):
        """Log reception of 'not interested' message"""
        message = f"Peer {self.peer_id} received the 'not interested' message from {other_peer_id}."
        self.log_message(message)
    
    def log_downloading_piece(self, other_peer_id="1002", piece_index="1", number_of_pieces=0):
        """Log completion of piece download"""
        message = (f"Peer {self.peer_id} has downloaded the piece {piece_index} from {other_peer_id}. "
                   f"Now the number of pieces it has is {number_of_pieces}.")
        self.log_message(message)
    
    def log_download_completion(self):
        """Log completion of file download"""
        message = f"Peer {self.peer_id} has downloaded the complete file."
        self.log_message(message)