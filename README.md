# BitTorrent-Style P2P File Sharing System

## Project Overview

This project implements a robust peer-to-peer file sharing system based on the BitTorrent protocol. The system allows multiple peers to exchange pieces of a file until all peers have the complete file, enabling distributed file transfer across a network.

## Key Features

- **BitTorrent-style Protocol**: Implementation of handshake, choking/unchoking, and piece transfer mechanisms
- **Flexible File Sharing**: Support for sharing any file type, not just predefined ones
- **Peer Management**: Automatic peer discovery and connection establishment
- **Multi-Machine Support**: Run peers across multiple physical machines
- **Comprehensive Logging**: Detailed event tracking for all protocol operations
- **Automated Setup Scripts**: Easy setup for both single-machine and multi-machine environments

## Team Members

- **Aakash**: Protocol implementation, environment and multi_machine setup
- **Aelly**: Logging system, connection robustness, piece message handling
- **Helen**: File handling, choking/unchoking mechanism

## Quick Start Guide

### Single Machine Testing

1. **Set up the environment with a custom file**:
   ```bash
   python setup_demo.py --custom-file your_file.jpg --local-test
   ```

2. **Run all peers**:
   ```bash
   ./run_peers.sh
   ```

3. **Monitor output**:
   ```bash
   tail -f peer*.out
   ```

### Multi-Machine Deployment

1. **Generate a configuration template**:
   ```bash
   python multi_machine.py
   ```

2. **Edit the generated `sample_config.json` file** with the correct IP addresses for each machine.

3. **Run the setup script on each machine**:
   ```bash
   # On Machine A (with custom file)
   python multi_machine.py --config sample_config.json --machine "Machine A" --custom-file your_file.jpg
   
   # On other machines
   python multi_machine.py --config sample_config.json --machine "Machine B"
   ```

4. **Start the peers on each machine**:
   ```bash
   ./run_peers.sh
   ```

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
├── Common.cfg            # Global configuration
├── PeerInfo.cfg          # Peer information
└── peer_[peerID]/        # Peer-specific directories
    └── [FileName]        # Complete or partial file
```

## Protocol Implementation

The system implements the BitTorrent protocol with the following message types:

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

## Detailed Usage Instructions

### peerProcess.py Options

```
usage: peerProcess.py [-h] [--file FILE] [--config CONFIG] [--peer-info PEER_INFO] peer_id

positional arguments:
  peer_id               Peer ID to use

optional arguments:
  -h, --help            show this help message and exit
  --file FILE           Custom file to share instead of the default specified in Common.cfg
  --config CONFIG       Path to Common.cfg (default: project_config_file_small/project_config_file_small/Common.cfg)
  --peer-info PEER_INFO Path to PeerInfo.cfg (default: project_config_file_small/project_config_file_small/PeerInfo.cfg)
```

### setup_demo.py Options

```
usage: setup_demo.py [-h] [--file-size FILE_SIZE] [--piece-size PIECE_SIZE] [--num-peers NUM_PEERS]
                     [--stagger-time STAGGER_TIME] [--monitor-time MONITOR_TIME] [--setup-only]
                     [--local-test] [--custom-file CUSTOM_FILE]

optional arguments:
  -h, --help            show this help message and exit
  --file-size FILE_SIZE Size of the test file in bytes
  --piece-size PIECE_SIZE Size of each file piece in bytes
  --num-peers NUM_PEERS Number of peers to create
  --stagger-time STAGGER_TIME Time in seconds between starting each peer
  --monitor-time MONITOR_TIME Time in seconds to monitor logs
  --setup-only          Only set up configuration and files, don't start peers
  --local-test          Configure for testing on a single local machine
  --custom-file CUSTOM_FILE Path to a custom file to use
```

### multi_machine.py Options

```
usage: multi_machine.py [-h] [--machine MACHINE] [--config CONFIG] [--file-size FILE_SIZE]
                       [--piece-size PIECE_SIZE] [--local-test] [--windows] [--custom-file CUSTOM_FILE]

optional arguments:
  -h, --help            show this help message and exit
  --machine MACHINE     Name of this machine (e.g., 'Machine A')
  --config CONFIG       Path to a JSON configuration file
  --file-size FILE_SIZE Size of the test file in bytes
  --piece-size PIECE_SIZE Size of each piece in bytes
  --local-test          Create a configuration for local testing
  --windows             Create Windows batch files instead of bash scripts
  --custom-file CUSTOM_FILE Path to a custom file to use
```

## Peer Behavior

1. **Initialization**:
   - Reads configuration files
   - Sets up its bitfield based on file presence
   - Creates necessary directories

2. **Connection Establishment**:
   - Connects to all previously started peers
   - Listens for connections from later peers
   - Exchanges handshake messages

3. **Piece Exchange**:
   - Exchanges bitfield messages
   - Expresses interest in available pieces
   - Requests and downloads pieces based on choking/unchoking
   - Sends "have" messages for received pieces

4. **Choking Mechanism**:
   - Periodically selects preferred neighbors based on download rates
   - Optimistically unchokes a random peer
   - Uploads pieces only to unchoked peers

5. **Termination**:
   - Terminates when all peers have the complete file

## Logging System

Each peer writes extensive logs to `log_peer_[peerID].log` including:

- TCP connection events
- Changes in preferred neighbors
- Changes in optimistically unchoked neighbors
- Choking and unchoking events
- Receipt of protocol messages
- Piece downloads and completion

## Custom File Support

The system now supports sharing any file type, not just the default:

1. **Direct usage with peerProcess**:
   ```bash
   python peerProcess.py 1001 --file your_image.jpg
   ```

2. **With setup scripts**:
   ```bash
   python setup_demo.py --custom-file your_video.mp4
   python multi_machine.py --custom-file your_document.pdf
   ```

The system automatically:
- Detects the file size
- Updates the configuration
- Distributes the file information to all peers

## Troubleshooting

### Connection Issues

- **Port conflicts**: Use different ports for each peer on the same machine
- **Hostname resolution**: Try using IP addresses directly if hostname resolution fails
- **Firewall issues**: Ensure ports are open on all machines

### File Transfer Issues

- **File access**: Verify read/write permissions for all peer directories
- **Disk space**: Ensure sufficient space (at least 2x the file size per peer)
- **Timeout errors**: Increase socket timeout values for large files

### Process Termination

- If processes don't terminate automatically, use `Ctrl+C`
- Check logs for any error messages
- Verify all peers can communicate with each other

## Development Notes

- Increase the `--piece-size` for better performance with large files
- For multimedia files, ensure they can be reconstructed properly
- When testing across machines, ensure all machines have compatible Python versions

## Cleanup Script
To prevent orphaned processes and free up ports after testing, we've included a cleanup script. This script terminates all peer processes and releases any ports they were using.

### Usage
```
bash# Make the script executable (first time only)
chmod +x cleanup.sh

# Run the cleanup script
./cleanup.sh

# For processes that might require elevated privileges
sudo ./cleanup.sh
```
### What it does

- Terminates all peerProcess.py instances
- Checks and releases ports in the range 6000-7100
- Verifies successful termination of all processes
- Reports any processes that couldn't be terminated

### When to use

- Before starting a new test to ensure clean environment
- After testing to free up system resources
- When log files show continued activity after termination
- If you encounter "Address already in use" errors

## References

- BitTorrent Protocol Specification
- "Computer Networking: A Top-Down Approach" by Kurose and Ross