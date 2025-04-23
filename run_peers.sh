#!/bin/bash
echo "Starting peers on this machine..."

# Start peer 1001
echo "Starting peer 1001"
python3 peerProcess.py 1001 --file "hey.txt" > peer1001.out 2>&1 &
sleep 2

# Start peer 1002
echo "Starting peer 1002"
python3 peerProcess.py 1002 --file "hey.txt" > peer1002.out 2>&1 &
sleep 2

# Start peer 1003
echo "Starting peer 1003"
python3 peerProcess.py 1003 --file "hey.txt" > peer1003.out 2>&1 &
sleep 2

# Start peer 1004
echo "Starting peer 1004"
python3 peerProcess.py 1004 --file "hey.txt" > peer1004.out 2>&1 &
sleep 2

# Start peer 1005
echo "Starting peer 1005"
python3 peerProcess.py 1005 --file "hey.txt" > peer1005.out 2>&1 &
sleep 2

echo "All peers started."
echo "To monitor output, use: tail -f peer*.out"
