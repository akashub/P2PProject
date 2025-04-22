#!/usr/bin/env python3
"""
Demo Setup Script for P2P File Sharing Project
This script automates the setup of the demo environment for the P2P file sharing project.
It creates necessary directories, configuration files, and test files.
"""

import os
import sys
import shutil
import time
import subprocess
import signal
import random
import argparse

# Default configuration values
DEFAULT_CONFIG = {
    "NumberOfPreferredNeighbors": 2,
    "UnchokingInterval": 5,
    "OptimisticUnchokingInterval": 15,
    "FileName": "TheFile.dat",
    "FileSize": 10485760,  # 10MB
    "PieceSize": 32768     # 32KB
}

# Default peer information
DEFAULT_PEERS = [
    {"id": "1001", "host": "localhost", "port": "6008", "has_file": "1"},
    {"id": "1002", "host": "localhost", "port": "6009", "has_file": "0"},
    {"id": "1003", "host": "localhost", "port": "6010", "has_file": "0"},
    {"id": "1004", "host": "localhost", "port": "6011", "has_file": "0"},
    {"id": "1005", "host": "localhost", "port": "6012", "has_file": "0"}
]

def create_dummy_file(file_path, size):
    """Create a dummy file with random data"""
    print(f"Creating dummy file: {file_path}")
    print(f"File size: {size} bytes")
    
    # Create parent directory if it doesn't exist
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # Generate random data in chunks to avoid memory issues
    with open(file_path, 'wb') as f:
        chunk_size = 1024 * 1024  # 1MB at a time
        remaining = size
        
        while remaining > 0:
            this_chunk = min(chunk_size, remaining)
            f.write(os.urandom(this_chunk))
            remaining -= this_chunk
            if size > 10 * 1024 * 1024:  # If file is larger than 10MB, show progress
                progress = (size - remaining) / size * 100
                print(f"Progress: {progress:.1f}%", end='\r')
    
    print(f"\nCreated file: {file_path} ({size} bytes)")

def create_config_file(config_file, config):
    """Create the Common.cfg file with specified configuration"""
    print(f"Creating configuration file: {config_file}")
    with open(config_file, 'w') as f:
        for key, value in config.items():
            f.write(f"{key} {value}\n")
    print(f"Configuration file created: {config_file}")

def create_peer_info_file(peer_info_file, peers):
    """Create the PeerInfo.cfg file with specified peer information"""
    print(f"Creating peer information file: {peer_info_file}")
    with open(peer_info_file, 'w') as f:
        for peer in peers:
            f.write(f"{peer['id']} {peer['host']} {peer['port']} {peer['has_file']}\n")
    print(f"Peer information file created: {peer_info_file}")

def create_peer_directories(peers, file_name, file_size):
    """Create peer directories and copy the file to peers that should have it"""
    for peer in peers:
        # Create peer directory
        peer_dir = f"peer_{peer['id']}"
        if not os.path.exists(peer_dir):
            os.makedirs(peer_dir)
            print(f"Created peer directory: {peer_dir}")
        
        # If peer has the file, create it in the peer directory
        if peer['has_file'] == "1":
            file_path = os.path.join(peer_dir, file_name)
            create_dummy_file(file_path, file_size)

def start_peers(peers, stagger_time=2):
    """Start peer processes with staggered timing"""
    processes = []
    for peer in peers:
        peer_id = peer['id']
        print(f"Starting peer {peer_id}...")
        
        # Start the peer process
        process = subprocess.Popen(["python3", "peerProcess.py", peer_id], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  text=True,
                                  bufsize=1)
        
        processes.append({"id": peer_id, "process": process})
        print(f"Peer {peer_id} started")
        
        # Wait for a bit before starting the next peer
        if stagger_time > 0:
            print(f"Waiting {stagger_time} seconds before starting next peer...")
            time.sleep(stagger_time)
    
    return processes

def monitor_logs(num_seconds=30, interval=5):
    """Monitor peer log files for a specified period"""
    end_time = time.time() + num_seconds
    log_files = [f for f in os.listdir('.') if f.startswith('log_peer_') and f.endswith('.log')]
    
    while time.time() < end_time:
        print("\n--- Log Summary ---")
        for log_file in log_files:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    num_lines = len(lines)
                    print(f"{log_file}: {num_lines} log entries")
                    
                    # Print last 3 log entries
                    if num_lines > 0:
                        print("Latest entries:")
                        for line in lines[-min(3, num_lines):]:
                            print(f"  {line.strip()}")
        
        # Wait for next check
        time.sleep(interval)

def setup_demo(config=None, peers=None, stagger_time=2, monitor_time=0):
    """Set up the demo environment with specified configuration and peers"""
    if config is None:
        config = DEFAULT_CONFIG
    
    if peers is None:
        peers = DEFAULT_PEERS
    
    # Create configuration files
    create_config_file("Common.cfg", config)
    create_peer_info_file("PeerInfo.cfg", peers)
    
    # Create peer directories and files
    create_peer_directories(peers, config["FileName"], config["FileSize"])
    
    # Start peer processes if requested
    if stagger_time >= 0:
        peer_processes = start_peers(peers, stagger_time)
        
        # Monitor logs if requested
        if monitor_time > 0:
            try:
                monitor_logs(monitor_time)
            except KeyboardInterrupt:
                print("Log monitoring interrupted")
        
        # Return the list of processes for later termination
        return peer_processes
    
    return None

def terminate_processes(processes):
    """Terminate running peer processes"""
    if not processes:
        return
        
    print("\nTerminating peer processes...")
    for proc_info in processes:
        try:
            print(f"Terminating peer {proc_info['id']}...")
            proc_info['process'].terminate()
            proc_info['process'].wait(timeout=5)
            print(f"Peer {proc_info['id']} terminated")
        except subprocess.TimeoutExpired:
            print(f"Peer {proc_info['id']} did not terminate within timeout, killing...")
            proc_info['process'].kill()
        except Exception as e:
            print(f"Error terminating peer {proc_info['id']}: {e}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Demo setup script for P2P file sharing project")
    
    parser.add_argument("--file-size", type=int, default=DEFAULT_CONFIG["FileSize"],
                        help="Size of the test file in bytes")
    parser.add_argument("--piece-size", type=int, default=DEFAULT_CONFIG["PieceSize"],
                        help="Size of each file piece in bytes")
    parser.add_argument("--num-peers", type=int, default=len(DEFAULT_PEERS),
                        help="Number of peers to create")
    parser.add_argument("--stagger-time", type=float, default=2,
                        help="Time in seconds between starting each peer (-1 to not start peers)")
    parser.add_argument("--monitor-time", type=int, default=0,
                        help="Time in seconds to monitor logs (0 to not monitor)")
    parser.add_argument("--setup-only", action="store_true",
                        help="Only set up configuration and files, don't start peers")
    
    return parser.parse_args()

def create_peers_list(num_peers):
    """Create a list of peer configurations based on the number of peers"""
    peers = []
    
    for i in range(1, num_peers + 1):
        peer_id = f"{1000 + i}"
        port = 6000 + i
        has_file = "1" if i == 1 else "0"  # First peer has the file
        
        peers.append({
            "id": peer_id,
            "host": "localhost",
            "port": str(port),
            "has_file": has_file
        })
    
    return peers

def main():
    """Main function to set up the demo environment"""
    args = parse_arguments()
    
    # Update configuration based on arguments
    config = DEFAULT_CONFIG.copy()
    config["FileSize"] = args.file_size
    config["PieceSize"] = args.piece_size
    
    # Create peers list based on number of peers
    peers = create_peers_list(args.num_peers)
    
    try:
        # Set up demo environment
        if args.setup_only:
            setup_demo(config, peers, -1, 0)
            print("Demo environment set up successfully. Peers not started.")
        else:
            processes = setup_demo(config, peers, args.stagger_time, args.monitor_time)
            
            # Keep running until interrupted if we started processes
            if processes:
                try:
                    print("\nDemo is running. Press Ctrl+C to terminate.")
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nDemo interrupted.")
                finally:
                    terminate_processes(processes)
    except Exception as e:
        print(f"Error setting up demo environment: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())