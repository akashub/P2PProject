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
    {"id": "1001", "host": "localhost", "port": "6002", "has_file": "1"},
    {"id": "1002", "host": "localhost", "port": "6003", "has_file": "0"},
    {"id": "1003", "host": "localhost", "port": "6004", "has_file": "0"},
    {"id": "1004", "host": "localhost", "port": "6005", "has_file": "0"},
    {"id": "1005", "host": "localhost", "port": "6006", "has_file": "0"}
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

def create_peer_directories(peers, file_name, file_path=None, file_size=None):
    """Create peer directories and copy the file to peers that should have it
    
    Args:
        peers: List of peer dictionaries
        file_name: Name of the file to use
        file_path: Path to an existing file to copy (optional)
        file_size: Size of file to create if file_path is not provided
    """
    for peer in peers:
        # Create peer directory
        peer_dir = f"peer_{peer['id']}"
        if not os.path.exists(peer_dir):
            os.makedirs(peer_dir)
            print(f"Created peer directory: {peer_dir}")
        
        # If peer has the file, ensure it's in the peer directory
        if peer['has_file'] == "1":
            dest_file = os.path.join(peer_dir, file_name)
            
            # If a specific file was provided, copy it
            if file_path and os.path.exists(file_path):
                shutil.copy2(file_path, dest_file)
                print(f"Copied {file_path} to {dest_file}")
            # Otherwise create a dummy file if size is provided
            elif file_size:
                create_dummy_file(dest_file, file_size)
            else:
                print(f"Warning: No file provided for peer {peer['id']} and no size specified for dummy file")

def create_run_script(script_path, peers_to_run, custom_file=None):
    """Create a bash script to run the specified peers"""
    with open(script_path, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write('echo "Starting peers on this machine..."\n\n')
        
        for peer_id in peers_to_run:
            f.write(f'# Start peer {peer_id}\n')
            f.write(f'echo "Starting peer {peer_id}"\n')
            
            # Add custom file parameter if provided
            file_param = f' --file "{custom_file}"' if custom_file else ''
            
            f.write(f'python3 peerProcess.py {peer_id}{file_param} > peer{peer_id}.out 2>&1 &\n')
            f.write('sleep 2\n\n')
        
        f.write('echo "All peers started."\n')
        f.write('echo "To monitor output, use: tail -f peer*.out"\n')
    
    # Make the script executable
    os.chmod(script_path, 0o755)
    print(f"Created run script at {script_path}")

def start_peers(peers, custom_file=None, stagger_time=2):
    """Start peer processes with staggered timing"""
    processes = []
    for peer in peers:
        peer_id = peer['id']
        print(f"Starting peer {peer_id}...")
        
        # Build command with custom file if provided
        cmd = ["python3", "peerProcess.py", peer_id]
        if custom_file:
            cmd.extend(["--file", custom_file])
        
        # Start the peer process
        process = subprocess.Popen(cmd, 
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

def setup_demo(config=None, peers=None, custom_file=None, custom_file_path=None, stagger_time=2, monitor_time=0):
    """Set up the demo environment with specified configuration and peers
    
    Args:
        config: Dictionary of configuration values
        peers: List of peer dictionaries
        custom_file: Name of custom file to use instead of default
        custom_file_path: Path to an existing file to use
        stagger_time: Time to wait between starting peers (-1 to not start peers)
        monitor_time: Time to monitor logs for (0 to not monitor)
    """
    if config is None:
        config = DEFAULT_CONFIG.copy()
    
    if peers is None:
        peers = DEFAULT_PEERS.copy()
    
    # Update filename in config if custom file is provided
    if custom_file:
        config["FileName"] = custom_file
        print(f"Using custom file name: {custom_file}")
    
    # Create configuration files
    create_config_file("Common.cfg", config)
    create_peer_info_file("PeerInfo.cfg", peers)
    
    # Create peer directories and files
    create_peer_directories(peers, config["FileName"], custom_file_path, config["FileSize"])
    
    # Create run script
    create_run_script("run_peers.sh", [peer['id'] for peer in peers], custom_file)
    
    # Start peer processes if requested
    if stagger_time >= 0:
        peer_processes = start_peers(peers, custom_file, stagger_time)
        
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
    parser.add_argument("--local-test", action="store_true",
                        help="Configure for testing on a single local machine")
    parser.add_argument("--custom-file", type=str, default=None,
                        help="Path to a custom file to use instead of generating a random one")
    
    return parser.parse_args()

def create_peers_list(num_peers):
    """Create a list of peer configurations based on the number of peers"""
    peers = []
    
    for i in range(1, num_peers + 1):
        peer_id = f"{1000 + i}"
        port = 6000 + i + 1  # Start at 6002 to avoid common ports
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
    
    # Handle custom file
    custom_file_name = None
    custom_file_path = None
    
    if args.custom_file:
        if os.path.exists(args.custom_file):
            custom_file_path = args.custom_file
            custom_file_name = os.path.basename(args.custom_file)
            # Update file size in config to match the actual file
            config["FileSize"] = os.path.getsize(args.custom_file)
            print(f"Using custom file: {custom_file_path} (size: {config['FileSize']} bytes)")
        else:
            print(f"Warning: Custom file {args.custom_file} not found. Will create a random file instead.")
    
    try:
        # If --setup-only flag or --local-test is provided, adjust stagger_time
        if args.setup_only:
            stagger_time = -1  # Don't start peers
        else:
            stagger_time = args.stagger_time
            
        # Set up demo environment
        processes = setup_demo(
            config, 
            peers, 
            custom_file_name, 
            custom_file_path, 
            stagger_time, 
            args.monitor_time
        )
            
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