from config import Config
from client import Client
import socket
import time
import os
import shutil
import argparse

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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="P2P File Sharing Peer Process")
    parser.add_argument("peer_id", help="Peer ID to use")
    parser.add_argument("--file", help="Custom file to share instead of the default specified in Common.cfg")
    parser.add_argument("--config", help="Path to Common.cfg (default: project_config_file_small/project_config_file_small/Common.cfg)")
    parser.add_argument("--peer-info", help="Path to PeerInfo.cfg (default: project_config_file_small/project_config_file_small/PeerInfo.cfg)")
    
    args = parser.parse_args()
    peer_id = args.peer_id
    custom_file = args.file
    
    # Use provided config paths if specified
    config_filepath = args.config if args.config else CONFIG_FILEPATH
    peer_process_filepath = args.peer_info if args.peer_info else PEER_PROCESS_FILEPATH
    
    # Read common configuration with custom filename if provided
    config = Config(config_filepath, custom_file)
    
    # Read peer information
    peers = read_peer_info(peer_process_filepath)
    
    # Find current peer's info
    current_peer = None
    for peer in peers:
        if peer.peer_id == peer_id:
            current_peer = peer
            break
            
    if not current_peer:
        print(f"Peer ID {peer_id} not found in {peer_process_filepath}")
        return
        
    # Ensure peer directory exists
    peer_dir = f"peer_{peer_id}"
    if not os.path.exists(peer_dir):
        os.makedirs(peer_dir)
        
    # If peer has file, ensure it exists in peer directory
    if current_peer.has_file:
        # Try to find the file in various locations
        file_paths = [
            config.file_name,  # Root directory
            os.path.join(peer_dir, config.file_name),  # Peer directory
            os.path.join("project_config_file_small", peer_id, config.file_name),  # Project config directory
            os.path.join("project_config_file_small/project_config_file_small", peer_id, config.file_name)  # Nested project config directory
        ]
        
        file_found = False
        source_path = None
        
        # Check each potential location
        for path in file_paths:
            if os.path.exists(path):
                source_path = path
                file_found = True
                print(f"Found source file at: {path}")
                break
                
        if file_found:
            # Ensure file is in peer directory
            dest_file = os.path.join(peer_dir, config.file_name)
            if source_path != dest_file:
                shutil.copy2(source_path, dest_file)
                print(f"Copied {source_path} to {dest_file}")
        else:
            print(f"WARNING: Peer {peer_id} is supposed to have file {config.file_name}, but it doesn't exist in any expected location")
            print(f"Looked in: {file_paths}")
            current_peer.has_file = False
    
    # Get hostname and port for the current peer
    hostname = current_peer.hostname
    port = current_peer.port
    
    # If hostname is a domain, try to resolve it to IP
    try:
        # Try to resolve hostname to IP
        # If it's already an IP, this won't change it
        # If it's 'localhost', it will resolve to 127.0.0.1
        if hostname == "localhost" or hostname[-1].isdigit():
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
    client = Client(config_filepath, ip, port, peer_id)
    
    # Set file status and update with custom filename if provided
    if current_peer.has_file:
        if custom_file:
            # If using a custom file, make sure the client knows about it
            client.config.file_name = custom_file
        client.has_file()
    
    # Find peers that started before this one to connect to
    other_peers = []
    found_self = False
    for peer in peers:
        if peer.peer_id == peer_id:
            found_self = True
            continue
        # Add peers that started before the current one
        other_ip = peer.hostname
        other_peers.append([other_ip, peer.port])
    
    # Start the client
    try:
        print(f"Starting peer {peer_id} on {ip}:{port} with file {config.file_name}")
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
    try:
        main()
    except Exception as e:
        import traceback
        print(f"Error running peer process: {e}")
        traceback.print_exc()