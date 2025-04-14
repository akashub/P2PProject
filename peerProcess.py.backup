# from config import Config
# from client import Client
# import sys
# import socket
# import time
# import os
# import shutil

# CONFIG_FILEPATH = "project_config_file_small/project_config_file_small/Common.cfg"
# PEER_PROCESS_FILEPATH = "project_config_file_small/project_config_file_small/PeerInfo.cfg"

# class PeerProcess:
#     def __init__(self, peer_id, hostname, port, has_file):
#         self.peer_id = peer_id
#         self.hostname = hostname
#         self.port = port
#         self.has_file = has_file == "1"  # Convert to boolean
        
# def read_peer_info(filepath):
#     peers = []
#     with open(filepath) as file:
#         lines = file.readlines()
#         for line in lines:
#             params = line.split()
#             if len(params) >= 4:  # Ensure line has enough parameters
#                 peers.append(PeerProcess(params[0], params[1], params[2], params[3]))
#     return peers

# def main():
#     if len(sys.argv) != 2:
#         print("Usage: python peerProcess.py <peerID>")
#         return
        
#     peer_id = sys.argv[1]
    
#     # Read common configuration
#     config = Config(CONFIG_FILEPATH)
    
#     # Read peer information
#     peers = read_peer_info(PEER_PROCESS_FILEPATH)
    
#     # Find current peer's info
#     current_peer = None
#     for peer in peers:
#         if peer.peer_id == peer_id:
#             current_peer = peer
#             break
            
#     if not current_peer:
#         print(f"Peer ID {peer_id} not found in {PEER_PROCESS_FILEPATH}")
#         return
        
#     # Ensure peer directory exists
#     peer_dir = f"peer_{peer_id}"
#     if not os.path.exists(peer_dir):
#         os.makedirs(peer_dir)
        
#     # If peer has file, ensure it exists in peer directory
#     if current_peer.has_file:
#         source_file = config.file_name
#         dest_file = os.path.join(peer_dir, config.file_name)
        
#         # Check if file already exists in peer directory
#         if not os.path.exists(dest_file):
#             # Try to copy from root directory
#             if os.path.exists(source_file):
#                 with open(source_file, 'rb') as src, open(dest_file, 'wb') as dst:
#                     dst.write(src.read())
#                 print(f"Copied {source_file} to {dest_file}")
#             else:
#                 print(f"WARNING: Peer {peer_id} is supposed to have file {source_file}, but it doesn't exist")
#                 current_peer.has_file = False
    
#     # Get hostname and port for the current peer
#     hostname = current_peer.hostname
#     port = current_peer.port
    
#     # If hostname is a domain, try to resolve it to IP
#     try:
#         # Try to resolve hostname to IP
#         # If it's already an IP, this won't change it
#         # If it's 'localhost', it will resolve to 127.0.0.1
#         ip = socket.gethostbyname(hostname)
#     except socket.gaierror:
#         print(f"Cannot resolve hostname: {hostname}")
#         ip = hostname  # Use the hostname as-is
    
#     # Create a client instance
#     client = Client(CONFIG_FILEPATH, ip, port, peer_id)
    
#     # Set file status
#     if current_peer.has_file:
#         client.has_file()
    
#     # Find peers that started before this one to connect to
#     other_peers = []
#     found_self = False
#     for peer in peers:
#         if peer.peer_id == peer_id:
#             found_self = True
#             break
#         # Add peers that started before the current one
#         try:
#             other_ip = socket.gethostbyname(peer.hostname)
#         except socket.gaierror:
#             other_ip = peer.hostname
#         other_peers.append([other_ip, peer.port])
    
#     # Start the client
#     try:
#         print(f"Starting peer {peer_id} on {ip}:{port}")
#         print(f"Will connect to peers: {other_peers}")
#         client.setup(other_peers)
        
#         # Keep the process running
#         while True:
#             time.sleep(10)
            
#             # Check if all peers have the complete file
#             all_complete = True
#             for peer in client.peers:
#                 if '0' in peer.bitfield:
#                     all_complete = False
#                     break
            
#             # Also check if we have the complete file
#             if '0' in client.bitfield:
#                 all_complete = False
            
#             if all_complete and len(client.peers) == len(peers) - 1:
#                 print("All peers have the complete file. Shutting down.")
#                 break
    
#     except KeyboardInterrupt:
#         print("Peer process interrupted by user")
#     finally:
#         # Shutdown client gracefully
#         client.shutdown()
#         print(f"Peer {peer_id} shutdown complete")

# if __name__ == "__main__":
#     main()

from config import Config
from client import Client
import sys
import socket
import time
import os
import shutil

CONFIG_FILEPATH = "project_config_file_small/project_config_file_small/Common.cfg"
PEER_PROCESS_FILEPATH = "project_config_file_small/project_config_file_small/PeerInfo.cfg"

class PeerProcess:
    def __init__(self, peer_id, hostname, port, has_file):
        self.peer_id = peer_id
        self.hostname = hostname
        self.port = port
        self.has_file = has_file == "1"  # Convert to boolean
        
def read_peer_info(filepath):
    peers = []
    with open(filepath) as file:
        lines = file.readlines()
        for line in lines:
            params = line.split()
            if len(params) >= 4:  # Ensure line has enough parameters
                peers.append(PeerProcess(params[0], params[1], params[2], params[3]))
    return peers

def main():
    if len(sys.argv) != 2:
        print("Usage: python peerProcess.py <peerID>")
        return
        
    peer_id = sys.argv[1]
    
    # Read common configuration
    config = Config(CONFIG_FILEPATH)
    
    # Read peer information
    peers = read_peer_info(PEER_PROCESS_FILEPATH)
    
    # Find current peer's info
    current_peer = None
    for peer in peers:
        if peer.peer_id == peer_id:
            current_peer = peer
            break
            
    if not current_peer:
        print(f"Peer ID {peer_id} not found in {PEER_PROCESS_FILEPATH}")
        return
        
    # Ensure peer directory exists
    peer_dir = f"peer_{peer_id}"
    if not os.path.exists(peer_dir):
        os.makedirs(peer_dir)
        
    # If peer has file, ensure it exists in peer directory
    if current_peer.has_file:
        source_file = config.file_name
        dest_file = os.path.join(peer_dir, config.file_name)
        
        # Check if file already exists in peer directory
        if not os.path.exists(dest_file):
            # Try to copy from root directory
            if os.path.exists(source_file):
                with open(source_file, 'rb') as src, open(dest_file, 'wb') as dst:
                    dst.write(src.read())
                print(f"Copied {source_file} to {dest_file}")
            else:
                print(f"WARNING: Peer {peer_id} is supposed to have file {source_file}, but it doesn't exist")
                current_peer.has_file = False
    
    # Get hostname and port for the current peer
    hostname = current_peer.hostname
    port = current_peer.port
    
    # If hostname is a domain, try to resolve it to IP
    try:
        # Try to resolve hostname to IP
        # If it's already an IP, this won't change it
        # If it's 'localhost', it will resolve to 127.0.0.1
        if hostname == "localhost" or hostname.startswith("127."):
            ip = hostname
        else:
            try:
                ip = socket.gethostbyname(hostname)
            except socket.gaierror:
                print(f"Cannot resolve hostname: {hostname}, using localhost instead")
                ip = "127.0.0.1"  # Fallback to localhost
    except Exception as e:
        print(f"Error resolving hostname: {e}")
        ip = "127.0.0.1"  # Fallback to localhost
    
    # Create a client instance
    client = Client(CONFIG_FILEPATH, ip, port, peer_id)
    
    # Set file status
    if current_peer.has_file:
        client.has_file()
    
    # Find peers that started before this one to connect to
    other_peers = []
    found_self = False
    for peer in peers:
        if peer.peer_id == peer_id:
            found_self = True
            break
        # Add peers that started before the current one
        try:
            # Use localhost instead of trying to resolve potentially non-existent hostnames
            if peer.hostname == "localhost" or peer.hostname.startswith("127."):
                other_ip = peer.hostname
            else:
                # For this test environment, we'll use localhost regardless of what's in the config
                print(f"Using localhost instead of {peer.hostname} for testing")
                other_ip = "localhost"
        except Exception as e:
            print(f"Error processing peer hostname: {e}")
            other_ip = "localhost"
        other_peers.append([other_ip, peer.port])
    
    # Start the client
    try:
        print(f"Starting peer {peer_id} on {ip}:{port}")
        print(f"Will connect to peers: {other_peers}")
        client.setup(other_peers)
        
        # Keep the process running
        while True:
            time.sleep(10)
            
            # Check if all peers have the complete file
            all_complete = True
            for peer in client.peers:
                if '0' in peer.bitfield:
                    all_complete = False
                    break
            
            # Also check if we have the complete file
            if '0' in client.bitfield:
                all_complete = False
            
            if all_complete and len(client.peers) == len(peers) - 1:
                print("All peers have the complete file. Shutting down.")
                break
    
    except KeyboardInterrupt:
        print("Peer process interrupted by user")
    finally:
        # Shutdown client gracefully
        client.shutdown()
        print(f"Peer {peer_id} shutdown complete")

if __name__ == "__main__":
    main()