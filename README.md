<!-- # P2P File Sharing Project

## Overview

This is a Peer-to-Peer (P2P) file-sharing application that implements a BitTorrent-like protocol for distributed file transfer. The project enables multiple peers to collaboratively download and share files across a network.

## Features

- Distributed file downloading
- Piece-wise file transfer
- Optimistic unchoking mechanism
- Peer connection and management
- Robust error handling and logging

## Project Structure

### Core Components

- `client.py`: Main client implementation
- `config.py`: Configuration management
- `logger.py`: Logging functionality

### Key Protocols

- Handshake mechanism
- Message types:
  - Choke
  - Unchoke
  - Interested
  - Not Interested
  - Have
  - Bitfield
  - Request
  - Piece

## Project Details

### Technical Implementation

The project is designed with a modular approach, breaking down the complex P2P file-sharing process into distinct technical challenges:

#### Network Communication
- Robust socket-based communication
- Multithreaded peer connection handling
- Sophisticated message parsing and protocol implementation
- Dynamic peer discovery and connection management

#### File Management
- Intelligent file fragmentation strategy
- Piece-wise file transfer and reconstruction
- Bitfield tracking for download progress
- File integrity verification mechanisms

#### Download Optimization
- Adaptive neighbor selection algorithms
- Optimistic unchoking mechanism
- Performance-driven peer prioritization
- Download efficiency tracking and logging

### Peer Interaction Workflow
1. Establish initial connections
2. Exchange handshake and bitfield information
3. Determine piece availability
4. Request and transfer file pieces
5. Reconstruct complete file
6. Continuously optimize peer connections

## Technical Details

### Piece Management
- Dynamic piece size calculation
- Bitfield tracking for downloaded pieces
- Random piece selection strategy

### Connection Handling
- Multithreaded peer connections
- Periodic neighbor selection
- Optimistic unchoking interval management

## Installation

1. Clone the repository
2. Ensure Python 3.7+ is installed
3. Install required dependencies
   ```bash
   pip install -r requirements.txt
   ```

## Usage

```bash
python client.py <config_file> <host> <port>
```

## Configuration

The `config.py` file allows customization of:
- Piece size
- File to be shared
- Unchoking intervals
- Number of preferred neighbors

## Logging

Comprehensive logging tracks:
- TCP connections
- Piece downloads
- Neighbor selections
- File transfer progress

## Potential Improvements

- Implement advanced piece selection algorithms
- Add encryption for file transfers
- Create a more sophisticated choking mechanism
- Implement bandwidth throttling

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

[Specify your license here - e.g., MIT License]

## Acknowledgments

- Inspired by BitTorrent protocol
- Developed as a distributed systems learning project

---

**Note:** This is an educational project demonstrating P2P file-sharing concepts. -->

# P2P File Sharing System - BitTorrent Protocol Implementation

## Project Overview

This project implements a peer-to-peer file sharing system based on the BitTorrent protocol. It allows multiple peers to collaborate in distributing a file by exchanging pieces until all peers have the complete file. Key features include:

- TCP-based communication between peers
- BitTorrent-style handshake and bitfield exchange
- Choking/unchoking mechanism for fair bandwidth allocation
- Piece-wise file transfer with random piece selection
- Comprehensive logging system for tracking all protocol events
- Support for multi-machine deployment

## Team Members

- **Aakash**: Core protocol implementation, piece message handling, demo environment setup
- **Aelly**: Logging system, connection robustness
- **Helen**: File handling, choking/unchoking mechanism

## File Structure

```
project/
├── client.py             # Main client implementation
├── config.py             # Configuration parser
├── logger.py             # Logging functionality
├── peerProcess.py        # Entry point script
├── setup_demo.py         # Setup script for quick testing
├── multi_machine.py      # Multi-machine deployment script
├── create_dummy_file.py  # Test file generator
├── README.md             # This file
├── Common.cfg            # Global configuration (created by setup scripts)
├── PeerInfo.cfg          # Peer information (created by setup scripts)
└── peer_[peerID]/        # Peer-specific directories
    └── TheFile.dat       # Complete or partial file
```

## Protocol Implementation

The implemented protocol follows the specified BitTorrent-style message exchange:

### Message Types

| Message Type   | Value | Description                               |
|----------------|-------|-------------------------------------------|
| choke          | 0     | Indicates no pieces will be sent          |
| unchoke        | 1     | Indicates pieces can be requested         |
| interested     | 2     | Expresses interest in peer's pieces       |
| not interested | 3     | Expresses no interest in peer's pieces    |
| have           | 4     | Announces possession of a piece           |
| bitfield       | 5     | Indicates all pieces a peer has           |
| request        | 6     | Requests a specific piece                 |
| piece          | 7     | Contains the actual piece data            |

### Peer Workflow

1. **Initialization**:
   - Read configuration files (`Common.cfg` and `PeerInfo.cfg`)
   - Set up peer-specific directory
   - Initialize bitfield based on file presence

2. **Connection Establishment**:
   - Connect to all previously started peers
   - Listen for connections from peers starting later
   - Exchange handshake messages to verify peer identity

3. **Piece Exchange**:
   - Exchange bitfield messages to establish piece availability
   - Express interest in pieces from other peers
   - Request and download pieces based on choking/unchoking mechanism
   - Send "have" messages when pieces are received

4. **Choking Mechanism**:
   - Every `UnchokingInterval` seconds:
     - Select `k` preferred neighbors based on download rates
     - If peer has complete file, select preferred neighbors randomly
   - Every `OptimisticUnchokingInterval` seconds:
     - Select one optimistically unchoked neighbor randomly

5. **Termination**:
   - Monitor all peers' completion status
   - Terminate when all peers have the complete file

## Configuration

### Common.cfg Format

```
NumberOfPreferredNeighbors 2
UnchokingInterval 5
OptimisticUnchokingInterval 15
FileName TheFile.dat
FileSize 10000232
PieceSize 32768
```

### PeerInfo.cfg Format

```
1001 hostname1 6008 1
1002 hostname2 6008 0
1003 hostname3 6008 0
```

Format: `[peer ID] [hostname] [port] [has file (1) or not (0)]`

## Running the System

### Single Machine Setup

For development and initial testing, you can run the entire system on a single machine:

1. **Set up the environment**:
   ```bash
   python setup_demo.py --file-size 20971520 --piece-size 16384 --local-test
   ```

2. **Run all peers** (either manually or using the generated script):
   ```bash
   # Run the generated script
   ./run_peers.sh
   
   # Or start peers manually
   python peerProcess.py 1001
   python peerProcess.py 1002
   # ... and so on
   ```

### Multi-Machine Setup

For the demo and final testing, you should run the system across multiple physical machines:

1. **Generate a configuration template** (on any machine):
   ```bash
   python multi_machine.py
   ```
   This creates a sample configuration file (`sample_config.json`) that you'll need to edit.

2. **Edit `sample_config.json`** to specify the machines and their hostnames/IPs:
   ```json
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
   ```

3. **Copy the project files and modified configuration** to all machines.

4. **Run the setup script on each machine** (specify the machine name):
   ```bash
   # On Machine A
   python multi_machine.py --config sample_config.json --machine "Machine A" --file-size 20971520 --piece-size 16384
   
   # On Machine B
   python multi_machine.py --config sample_config.json --machine "Machine B"
   ```

5. **Start the peers in the correct order** (based on `PeerInfo.cfg`):
   ```bash
   # First start peers on Machine A
   ./run_peers.sh
   
   # Then start peers on Machine B
   ./run_peers.sh
   
   # ... and so on for other machines
   ```

### Understanding multi_machine.py

The `multi_machine.py` script facilitates running the P2P system across multiple physical machines:

- **Purpose**: Coordinates configuration across all machines in the P2P network
- **Configuration file**: Uses a JSON file to specify which peers run on which machines
- **Per-machine setup**: Creates machine-specific configurations and startup scripts
- **IP detection**: Automatically detects the local machine's IP address
- **Test file generation**: Creates the test file on the machine with the first peer

Key parameters:
- `--machine`: Specifies which machine configuration to use from the JSON file
- `--config`: Path to the JSON configuration file
- `--file-size`: Size of the test file (default: 20MB)
- `--piece-size`: Size of each piece (default: 32KB)
- `--windows`: Creates Windows batch files instead of bash scripts

## Logging System

The logging system records all significant events in files named `log_peer_[peerID].log`. Events logged include:

- TCP connection establishment
- Changes in preferred neighbors
- Changes in optimistically unchoked neighbors
- Choking and unchoking events
- Receipt of have/interested/not interested messages
- Piece downloads
- Download completion

Example log entries:
```
2025-03-15 14:30:22: Peer 1001 makes a connection to Peer 1002.
2025-03-15 14:30:25: Peer 1001 has the preferred neighbors 1002, 1003.
2025-03-15 14:30:35: Peer 1001 has the optimistically unchoked neighbor 1004.
2025-03-15 14:31:02: Peer 1001 has downloaded the piece 5 from 1002. Now the number of pieces it has is 10.
```

## Key Implementation Details

### Client Class

The `Client` class is the core component that implements peer functionality:

- **Connection Management**: Handles TCP connections with other peers
- **Message Processing**: Encodes/decodes protocol messages
- **Piece Management**: Tracks, requests, and stores file pieces
- **Choking Algorithm**: Implements preferred neighbor selection logic
- **File Handling**: Handles file reading/writing and reconstruction

### Peer Selection Algorithm

- **Preferred Neighbors**: Selected based on download rates during the previous unchoking interval
- **Optimistically Unchoked Neighbor**: Randomly selected from choked but interested peers
- **Random Selection**: Used for peers with the complete file

### Piece Transfer Logic

- **Piece Selection**: Random selection from available pieces
- **Piece Storage**: Pieces stored in memory and written to disk
- **File Reconstruction**: Pieces combined to reconstruct the complete file
- **Progress Tracking**: Bitfield used to track which pieces each peer has

## Troubleshooting

### Connection Issues

- **Port conflicts**: Ensure each peer on the same machine uses a different port
- **Firewall issues**: Check that firewalls allow the specified ports
- **Hostname resolution**: Use IP addresses if hostname resolution fails
- **Connection timing**: Start peers in the order specified in `PeerInfo.cfg`

### File Transfer Issues

- **File access**: Ensure all peers have read/write permissions to their directories
- **Disk space**: Verify sufficient disk space (at least 5x the file size)
- **Piece size**: Confirm piece size is consistent across all configuration files

### Process Termination

- **Stuck processes**: If a process doesn't terminate automatically, use Ctrl+C
- **Zombie processes**: Check for and kill any zombie processes after testing
- **Log verification**: Check logs to see if all peers received the complete file

## Demo Preparation

For the video demo:

1. **Setup multiple machines**: At least 3 different physical machines
2. **Create a large test file**: At least 20MB with 16KB piece size
3. **Configure the network**: Ensure all machines can communicate
4. **Start in sequence**: Start peers in the order listed in `PeerInfo.cfg`
5. **Monitor logs**: Show log entries demonstrating key protocol features
6. **Verify completion**: Confirm all peers have identical copies of the file

## Future Improvements

Potential enhancements to consider:

- Implementing the "rarest first" piece selection strategy
- Adding NAT traversal for peers behind firewalls
- Implementing bandwidth throttling
- Adding data verification through checksums
- Creating a graphical user interface
- Supporting multiple simultaneous file downloads