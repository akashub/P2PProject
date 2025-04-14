<!-- # P2P File Sharing System

This project implements a peer-to-peer file sharing system similar to BitTorrent. It includes mechanisms for choking/unchoking, preferred neighbor selection, and optimistic unchoking.

## Files in this Project

- `client.py`: Core BitTorrent-like protocol implementation
- `peerProcess.py`: Entry point for peer processes
- `config.py`: Configuration file parser
- `logger.py`: Logging functionality for peer operations
- `main.py`: Simple testing script for a single client
- `test_p2p.py`: Comprehensive test script to set up and run a multi-peer environment
- Configuration files in `project_config_file_small/`:
  - `Common.cfg`: Shared configuration parameters
  - `PeerInfo.cfg`: Information about each peer

## Getting Started

### Prerequisites

- Python 3.6 or higher

### Setting Up a Test Environment

The easiest way to set up a test environment is to use the `test_p2p.py` script:

```bash
python test_p2p.py [file_to_share]
```

This script will:
1. Create necessary configuration files
2. Set up peer directories
3. Copy the file to the first peer (or create a dummy test file if none is provided)
4. Optionally start all peer processes in separate terminals

### Manual Setup

1. Create the configuration directory and files:
   ```
   mkdir -p project_config_file_small
   ```

2. Create `Common.cfg` with parameters:
   ```
   NumberOfPreferredNeighbors 2
   UnchokingInterval 5
   OptimisticUnchokingInterval 15
   FileName test_file.dat
   FileSize 1048576
   PieceSize 16384
   ```

3. Create `PeerInfo.cfg` with peer information:
   ```
   1001 localhost 6001 1
   1002 localhost 6002 0
   1003 localhost 6003 0
   ```

4. Create peer directories:
   ```
   mkdir -p peer_1001 peer_1002 peer_1003
   ```

5. Place the file to be shared in the directory of the peer(s) that should have it initially:
   ```
   cp test_file.dat peer_1001/
   ```

## Running the Peer Processes

Start each peer process in a separate terminal:

```bash
python peerProcess.py 1001
python peerProcess.py 1002
python peerProcess.py 1003
```

The peers will connect to each other according to the protocol description. Peers that start later will connect to peers that started earlier.

## Monitoring Progress

Each peer creates a log file named `log_peer_[peerID].log` in the working directory. You can monitor these log files to see the progress of file sharing:

```bash
tail -f log_peer_1001.log
```

The log files include information about:
- TCP connections
- Changes in preferred neighbors
- Changes in optimistically unchoked neighbors
- Choking/unchoking events
- Piece downloads
- Download completion

## Implementation Details

### BitTorrent-like Protocol

The implementation follows a simplified BitTorrent protocol with the following message types:
- `choke` (0)
- `unchoke` (1)
- `interested` (2)
- `not interested` (3)
- `have` (4)
- `bitfield` (5)
- `request` (6)
- `piece` (7)

### Peer Selection

- Preferred neighbors are selected every `UnchokingInterval` seconds based on download rates
- An optimistically unchoked neighbor is selected every `OptimisticUnchokingInterval` seconds

### File Handling

- Files are divided into pieces of size specified in `Common.cfg`
- Pieces are requested randomly from peers that have them
- Once a piece is downloaded, a `have` message is sent to all connected peers

## Troubleshooting

### Connection Issues
- Ensure that the specified ports are available
- Make sure the hostnames or IP addresses in `PeerInfo.cfg` are correct
- Check firewall settings if peers are on different machines

### File Transfer Issues
- Verify that the file exists in the peer directory of peers that should have it initially
- Ensure the file size in `Common.cfg` matches the actual file size

### Process Termination
- If a peer process doesn't terminate properly after all peers have the complete file,
  you may need to terminate it manually (Ctrl+C) -->

  # P2P File Sharing System

A BitTorrent-like peer-to-peer file sharing application implemented in Python. This system allows multiple peers to share files by breaking them into pieces and distributing them across the network.

## Overview

This project implements a simplified version of the BitTorrent protocol with the following features:

- Choking/unchoking mechanism for peer selection
- Preferred neighbor selection based on download rates
- Optimistic unchoking for discovering better connections
- File piece exchange via TCP connections
- Logging of all protocol events

## Files in the Project

- `client.py`: Core implementation of the P2P protocol
- `peerProcess.py`: Entry point for starting peer processes
- `config.py`: Configuration file parser
- `logger.py`: Logging functionality for peer operations
- `project_config_file_small/`: Configuration files directory

## Requirements

- Python 3.6 or higher
- Standard Python libraries (socket, threading, os, etc.)

## Configuration Files

The system uses two configuration files:

1. **Common.cfg**: Contains shared parameters for all peers.
   ```
   NumberOfPreferredNeighbors 3
   UnchokingInterval 5
   OptimisticUnchokingInterval 10
   FileName thefile
   FileSize 2167705
   PieceSize 16384
   ```

2. **PeerInfo.cfg**: Contains information about each peer in the network.
   ```
   1001 localhost 6002 1 
   1002 localhost 6003 0
   1003 localhost 6004 0
   ```
   Each line represents a peer with:
   - Peer ID
   - Hostname/IP
   - Port
   - File status (1 = has complete file, 0 = doesn't have file)

## Directory Structure

Each peer has its own directory named `peer_[peerID]` to store its files. For example:
- `peer_1001/` - Directory for peer 1001
- `peer_1002/` - Directory for peer 1002

## Running the Application

1. **Prepare the configuration files** in `project_config_file_small/` directory.

2. **Ensure that peers who should have the complete file** have it in their directories.
   For example, if peer 1001 should have the complete file:
   - Place the file in `peer_1001/` directory
   - Ensure the file has the name specified in Common.cfg

3. **Start each peer process** in a separate terminal:
   ```bash
   python peerProcess.py 1001
   python peerProcess.py 1002
   python peerProcess.py 1003
   ```

## Protocol Description

The protocol consists of a handshake followed by a series of messages:

1. **Handshake**: 32-byte message with format: header(18) + zero_bits(10) + peer_id(4)

2. **Message Types**:
   - Choke (0): Informs a peer they are choked
   - Unchoke (1): Informs a peer they are unchoked
   - Interested (2): Expresses interest in peer's pieces
   - Not Interested (3): Expresses lack of interest in peer's pieces
   - Have (4): Informs peers about a newly acquired piece
   - Bitfield (5): Shares which pieces a peer has
   - Request (6): Requests a specific piece
   - Piece (7): Delivers the requested piece

3. **Neighbor Selection**:
   - Preferred neighbors are selected based on download rates
   - One optimistically unchoked neighbor is selected randomly

## Logging

Each peer creates a log file (`log_peer_[peerID].log`) that records events such as:
- TCP connections
- Choking/unchoking events
- Changes in preferred neighbors
- Changes in optimistically unchoked neighbor
- Piece downloads
- Download completion

## Implementation Details

- Peers use TCP connections for reliable transmission
- File data is transferred as raw binary to avoid encoding issues
- Thread synchronization is used to handle concurrent connections
- Pieces are requested in random order for better distribution

## Troubleshooting

- **Connection Issues**: Check if ports are already in use
- **File Transfer Issues**: Verify file exists and permissions are correct
- **Peer Discovery**: Ensure PeerInfo.cfg has correct hostnames/IPs
- **Bitfield Errors**: Verify the file size and piece size in Common.cfg

## Limitations

- Does not implement rarest-first piece selection
- Does not implement pipelining of requests
- Does not implement end-game mode
- Uses localhost for testing (modify for distributed testing)

## Team Breakdown

- **Helen Radomski**: File Management and Piece Distribution

    - Developed and optimize the handshake mechanism and message parsing
    - Implemented robust socket communication methods
    - Handle peer connection management and error handling

- **Aakash Singh**: Network Communication and Protocol Implementation

    - Design the file fragmentation and reconstruction strategy
    - Implement piece request and download tracking mechanisms
    - Create logging and file integrity verification systems

- **Aelly Alwardi**: Peer Selection and Download Optimization

    - Develop algorithms for preferred neighbor selection
    - Implement optimistic unchoking mechanism
    - Create performance metrics and download efficiency tracking