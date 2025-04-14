# P2P File Sharing Project

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

**Note:** This is an educational project demonstrating P2P file-sharing concepts.