#!/bin/bash
# cleanup.sh - Script to terminate all peer processes and free up ports

echo "Cleaning up all peer processes..."

# Kill all Python processes related to peerProcess
echo "Killing peerProcess instances..."
pkill -f "python.*peerProcess"

# Check if any processes are still running
remaining=$(ps aux | grep python | grep -E "peerProcess|setup_demo|multi_machine" | grep -v grep | wc -l)

if [ $remaining -gt 0 ]; then
    echo "Some processes are still running. Trying with SIGKILL..."
    pkill -9 -f "python.*peerProcess"
fi

# Clean up ports in the range we commonly use
echo "Checking for processes on commonly used ports..."
for port in $(seq 6000 7100); do
    pid=$(lsof -t -i:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null
    fi
done

# Remove any socket connections that might be lingering in TIME_WAIT
echo "Checking for lingering socket connections..."
netstat -anpt 2>/dev/null | grep -E "6[0-9][0-9][0-9]|7[0-9][0-9][0-9]" | grep "TIME_WAIT"

# Final verification
remaining=$(ps aux | grep python | grep -E "peerProcess|setup_demo|multi_machine" | grep -v grep | wc -l)

if [ $remaining -eq 0 ]; then
    echo "Cleanup complete. All peer processes terminated."
else
    echo "Warning: $remaining processes may still be running."
    ps aux | grep python | grep -E "peerProcess|setup_demo|multi_machine" | grep -v grep
fi

# Optional: Clean up any partial files that might be corrupted
echo "Looking for partial downloads (optional cleanup)..."
for dir in peer_*; do
    if [ -d "$dir" ]; then
        for file in "$dir"/*; do
            if [[ "$file" != *".bak" && -f "$file" ]]; then
                size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
                echo "Found file: $file (Size: $size bytes)"
            fi
        done
    fi
done

echo "Cleanup script finished. Ready for a fresh test."