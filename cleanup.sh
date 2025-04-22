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

# Final verification
remaining=$(ps aux | grep python | grep -E "peerProcess|setup_demo|multi_machine" | grep -v grep | wc -l)

if [ $remaining -eq 0 ]; then
    echo "Cleanup complete. All peer processes terminated."
else
    echo "Warning: $remaining processes may still be running."
    ps aux | grep python | grep -E "peerProcess|setup_demo|multi_machine" | grep -v grep
fi

echo "Cleanup script finished."