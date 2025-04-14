#!/usr/bin/env python3
"""
This script sets up a local test environment for the P2P file sharing system.
It creates configuration files and directories for multiple peers and distributes
a test file to the first peer.

Usage: python test_p2p.py [file_to_share]
If file_to_share is not provided, it will create a dummy test file.
"""

import os
import sys
import random
import shutil
import subprocess
import time

# Default configuration values
DEFAULT_FILE_SIZE = 1024 * 1024  # 1MB
DEFAULT_PIECE_SIZE = 16384  # 16KB
DEFAULT_NUM_PEERS = 3
DEFAULT_PORT_BASE = 6000
DEFAULT_PREFERRED_NEIGHBORS = 2
DEFAULT_UNCHOKING_INTERVAL = 5
DEFAULT_OPTIMISTIC_UNCHOKING_INTERVAL = 15

def create_dummy_file(filename, size):
    """Create a dummy file with random data"""
    print(f"Creating dummy file {filename} with size {size} bytes")
    with open(filename, 'wb') as f:
        # Create chunks of random data to avoid memory issues with large files
        chunk_size = 1024 * 1024  # 1MB chunks
        for i in range(0, size, chunk_size):
            chunk = os.urandom(min(chunk_size, size - i))
            f.write(chunk)

def create_config_files(file_to_share, file_size, piece_size, num_peers, port_base, 
                       preferred_neighbors, unchoking_interval, optimistic_unchoking_interval):
    """Create Common.cfg and PeerInfo.cfg files"""
    # Create config directory if it doesn't exist
    config_dir = "project_config_file_small"
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    # Create Common.cfg
    common_filepath = os.path.join(config_dir, "Common.cfg")
    with open(common_filepath, 'w') as f:
        f.write(f"NumberOfPreferredNeighbors {preferred_neighbors}\n")
        f.write(f"UnchokingInterval {unchoking_interval}\n")
        f.write(f"OptimisticUnchokingInterval {optimistic_unchoking_interval}\n")
        f.write(f"FileName {os.path.basename(file_to_share)}\n")
        f.write(f"FileSize {file_size}\n")
        f.write(f"PieceSize {piece_size}\n")
    
    # Create PeerInfo.cfg
    peer_filepath = os.path.join(config_dir, "PeerInfo.cfg")
    with open(peer_filepath, 'w') as f:
        for i in range(1, num_peers + 1):
            peer_id = f"{1000 + i}"
            port = port_base + i
            has_file = "1" if i == 1 else "0"  # Only first peer has the file
            f.write(f"{peer_id} localhost {port} {has_file}\n")
    
    return common_filepath, peer_filepath

def setup_peer_directories(num_peers, file_to_share):
    """Set up directories for each peer"""
    for i in range(1, num_peers + 1):
        peer_id = f"{1000 + i}"
        peer_dir = f"peer_{peer_id}"
        
        # Create peer directory if it doesn't exist
        if not os.path.exists(peer_dir):
            os.makedirs(peer_dir)
        
        # Copy file to first peer
        if i == 1:
            dest_path = os.path.join(peer_dir, os.path.basename(file_to_share))
            shutil.copy2(file_to_share, dest_path)
            print(f"Copied {file_to_share} to {dest_path}")

def run_test(num_peers, start_delay=2):
    """Run the peer processes in separate terminals or with subprocess"""
    processes = []
    
    try:
        for i in range(1, num_peers + 1):
            peer_id = f"{1000 + i}"
            
            # Different approaches for different platforms
            if sys.platform == 'darwin':  # macOS
                cmd = ['osascript', '-e', f'tell app "Terminal" to do script "cd {os.getcwd()} && python peerProcess.py {peer_id}"']
                subprocess.Popen(cmd)
            elif sys.platform == 'win32':  # Windows
                cmd = f'start cmd /k "cd {os.getcwd()} && python peerProcess.py {peer_id}"'
                subprocess.Popen(cmd, shell=True)
            else:  # Linux and others
                # Use gnome-terminal, xterm, or just run in background
                try:
                    cmd = ['gnome-terminal', '--', 'python', 'peerProcess.py', peer_id]
                    subprocess.Popen(cmd)
                except FileNotFoundError:
                    try:
                        cmd = ['xterm', '-e', f'python peerProcess.py {peer_id}']
                        subprocess.Popen(cmd)
                    except FileNotFoundError:
                        # Fallback to just running in background
                        cmd = ['python', 'peerProcess.py', peer_id]
                        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        processes.append(p)
            
            # Delay between starting peers
            time.sleep(start_delay)
            print(f"Started peer {peer_id}")
            
        # Wait for user to stop the test
        print("\n" + "="*80)
        print("All peers have been started.")
        print("Check the log files to monitor progress.")
        print("Press Ctrl+C to stop the test.")
        print("="*80 + "\n")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Stopping test...")
        # Kill processes if we started them directly
        for p in processes:
            p.terminate()

def main():
    # Parse command line arguments
    if len(sys.argv) > 1:
        file_to_share = sys.argv[1]
        if not os.path.exists(file_to_share):
            print(f"Error: File {file_to_share} not found")
            return
        file_size = os.path.getsize(file_to_share)
    else:
        file_to_share = "test_file.dat"
        file_size = DEFAULT_FILE_SIZE
        create_dummy_file(file_to_share, file_size)
    
    # Configuration parameters
    piece_size = DEFAULT_PIECE_SIZE
    num_peers = DEFAULT_NUM_PEERS
    port_base = DEFAULT_PORT_BASE
    preferred_neighbors = DEFAULT_PREFERRED_NEIGHBORS
    unchoking_interval = DEFAULT_UNCHOKING_INTERVAL
    optimistic_unchoking_interval = DEFAULT_OPTIMISTIC_UNCHOKING_INTERVAL
    
    # Create configuration files
    common_filepath, peer_filepath = create_config_files(
        file_to_share, file_size, piece_size, num_peers, port_base,
        preferred_neighbors, unchoking_interval, optimistic_unchoking_interval
    )
    
    print(f"Created configuration files: {common_filepath}, {peer_filepath}")
    
    # Set up peer directories
    setup_peer_directories(num_peers, file_to_share)
    
    # Ask user if they want to run the test
    response = input("Do you want to run the test now? (y/n): ").strip().lower()
    if response == 'y':
        run_test(num_peers)
    else:
        print("Test setup completed. Run manually using: python peerProcess.py <peerID>")

if __name__ == "__main__":
    main()