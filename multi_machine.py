#!/usr/bin/env python3
"""
Multi-Machine Demo Setup Script for P2P File Sharing Project
This script prepares the configuration files for running the P2P demo across multiple machines.
"""

import os
import sys
import socket
import argparse
import json
import shutil

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Create a socket to determine the outgoing IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google DNS
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Error determining local IP: {e}")
        return "localhost"

def create_common_config(file_path, file_size=20971520, piece_size=32768):
    """Create the Common.cfg file"""
    config = {
        "NumberOfPreferredNeighbors": 2,
        "UnchokingInterval": 5,
        "OptimisticUnchokingInterval": 15,
        "FileName": "TheFile.dat",
        "FileSize": file_size,
        "PieceSize": piece_size
    }
    
    with open(file_path, 'w') as f:
        for key, value in config.items():
            f.write(f"{key} {value}\n")
    
    print(f"Created Common.cfg at {file_path}")

def create_peer_info(file_path, machine_config, this_machine=None):
    """
    Create the PeerInfo.cfg file
    
    machine_config should be a list of dictionaries like:
    [
        {
            "machine_name": "Machine A",
            "host": "192.168.1.101",
            "peers": [
                {"id": "1001", "port": "6008", "has_file": "1"}
            ]
        },
        {
            "machine_name": "Machine B",
            "host": "192.168.1.102", 
            "peers": [
                {"id": "1002", "port": "6008", "has_file": "0"},
                {"id": "1003", "port": "6009", "has_file": "0"}
            ]
        }
    ]
    """
    with open(file_path, 'w') as f:
        for machine in machine_config:
            for peer in machine["peers"]:
                f.write(f"{peer['id']} {machine['host']} {peer['port']} {peer['has_file']}\n")
    
    print(f"Created PeerInfo.cfg at {file_path}")
    
    # If this_machine is specified, create a file listing which peers to run on this machine
    if this_machine is not None:
        for machine in machine_config:
            if machine["machine_name"] == this_machine:
                peers_to_run = [peer["id"] for peer in machine["peers"]]
                with open("peers_to_run.txt", 'w') as f:
                    for peer_id in peers_to_run:
                        f.write(f"{peer_id}\n")
                print(f"Created peers_to_run.txt with peers: {', '.join(peers_to_run)}")
                break

def create_run_script(script_path, is_windows=False):
    """Create a script to run all peers on this machine"""
    if is_windows:
        # Create a batch file for Windows
        with open(script_path, 'w') as f:
            f.write('@echo off\n')
            f.write('echo Starting peers on this machine...\n')
            f.write('for /f "tokens=*" %%a in (peers_to_run.txt) do (\n')
            f.write('    echo Starting peer %%a\n')
            f.write('    start cmd /k python peerProcess.py %%a\n')
            f.write(')\n')
            f.write('echo All peers started.\n')
    else:
        # Create a bash script for Unix-like systems
        with open(script_path, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('echo "Starting peers on this machine..."\n')
            f.write('while read peer_id; do\n')
            f.write('    echo "Starting peer $peer_id"\n')
            f.write('    gnome-terminal -- python peerProcess.py $peer_id &\n')
            f.write('    # Alternatively, use xterm if gnome-terminal is not available:\n')
            f.write('    # xterm -e "python peerProcess.py $peer_id" &\n')
            f.write('    sleep 1\n')
            f.write('done < peers_to_run.txt\n')
            f.write('echo "All peers started."\n')
        
        # Make the script executable
        os.chmod(script_path, 0o755)
    
    print(f"Created run script at {script_path}")

def create_local_test_config():
    """Create a configuration for testing on a single machine with localhost"""
    machine_config = [
        {
            "machine_name": "Local Machine",
            "host": "localhost",
            "peers": [
                {"id": "1001", "port": "6008", "has_file": "1"},
                {"id": "1002", "port": "6009", "has_file": "0"},
                {"id": "1003", "port": "6010", "has_file": "0"},
                {"id": "1004", "port": "6011", "has_file": "0"},
                {"id": "1005", "port": "6012", "has_file": "0"}
            ]
        }
    ]
    return machine_config

def create_peer_directories(peer_ids, file_name, file_size=None):
    """Create directories for each peer and copy the file if needed"""
    for peer_id in peer_ids:
        peer_dir = f"peer_{peer_id}"
        
        # Create peer directory if it doesn't exist
        if not os.path.exists(peer_dir):
            os.makedirs(peer_dir)
            print(f"Created directory: {peer_dir}")
        
        # For the first peer, create the file if it doesn't exist
        if peer_id == "1001" and file_size is not None:
            file_path = os.path.join(peer_dir, file_name)
            if not os.path.exists(file_path):
                print(f"Creating test file: {file_path}")
                # Check if we have the create_dummy_file.py script
                if os.path.exists("create_dummy_file.py"):
                    import subprocess
                    subprocess.run([sys.executable, "create_dummy_file.py", file_path, str(file_size)])
                else:
                    # Create a basic file of the specified size
                    with open(file_path, 'wb') as f:
                        f.seek(file_size - 1)
                        f.write(b'\0')
                    print(f"Created empty file of size {file_size} bytes")

def main():
    parser = argparse.ArgumentParser(description="Multi-Machine Demo Setup for P2P File Sharing")
    
    parser.add_argument("--machine", type=str, default=None,
                        help="Name of this machine (e.g., 'Machine A')")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to a JSON configuration file")
    parser.add_argument("--file-size", type=int, default=20971520,
                        help="Size of the test file in bytes (default: 20MB)")
    parser.add_argument("--piece-size", type=int, default=32768,
                        help="Size of each piece in bytes (default: 32KB)")
    parser.add_argument("--local-test", action="store_true",
                        help="Create a configuration for testing on a single machine with localhost")
    parser.add_argument("--windows", action="store_true",
                        help="Create Windows batch files instead of bash scripts")
    
    args = parser.parse_args()
    
    # Create Common.cfg
    create_common_config("Common.cfg", args.file_size, args.piece_size)
    
    # Determine the machine configuration
    if args.local_test:
        machine_config = create_local_test_config()
        create_peer_info("PeerInfo.cfg", machine_config, "Local Machine")
        create_run_script("run_peers.bat" if args.windows else "run_peers.sh", args.windows)
        
        # Create peer directories for the local test
        peer_ids = ["1001", "1002", "1003", "1004", "1005"]
        create_peer_directories(peer_ids, "TheFile.dat", args.file_size)
    elif args.config:
        # Load configuration from JSON file
        try:
            with open(args.config, 'r') as f:
                machine_config = json.load(f)
            
            create_peer_info("PeerInfo.cfg", machine_config, args.machine)
            
            if args.machine:
                create_run_script("run_peers.bat" if args.windows else "run_peers.sh", args.windows)
                
                # Create peer directories for this machine
                peer_ids = []
                for machine in machine_config:
                    if machine["machine_name"] == args.machine:
                        peer_ids = [peer["id"] for peer in machine["peers"]]
                
                create_peer_directories(peer_ids, "TheFile.dat", args.file_size)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)
    else:
        # Create a sample configuration file
        sample_config = [
            {
                "machine_name": "Machine A",
                "host": get_local_ip(),
                "peers": [
                    {"id": "1001", "port": "6008", "has_file": "1"}
                ]
            },
            {
                "machine_name": "Machine B",
                "host": "<MACHINE_B_IP>",
                "peers": [
                    {"id": "1002", "port": "6008", "has_file": "0"},
                    {"id": "1003", "port": "6009", "has_file": "0"}
                ]
            },
            {
                "machine_name": "Machine C",
                "host": "<MACHINE_C_IP>",
                "peers": [
                    {"id": "1004", "port": "6008", "has_file": "0"},
                    {"id": "1005", "port": "6009", "has_file": "0"}
                ]
            }
        ]
        
        # Save the sample configuration
        with open("sample_config.json", 'w') as f:
            json.dump(sample_config, f, indent=4)
        
        print("Created sample configuration file: sample_config.json")
        print("Edit this file with the correct IP addresses for each machine.")
        print("Then run this script again with:")
        print(f"    python {sys.argv[0]} --config sample_config.json --machine \"Machine A\"")
        print("on Machine A, and similar commands on the other machines.")

if __name__ == "__main__":
    main()