#!/usr/bin/env python3
"""
Creates a dummy file for testing the P2P file sharing system.
This is useful if you don't have the original file but need to proceed with testing.
"""

import os
import sys
import random

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

def main():
    if len(sys.argv) < 2:
        print("Usage: python create_dummy_file.py <file_path> [size_in_bytes]")
        print("Default size is 1MB if not specified.")
        return
    
    file_path = sys.argv[1]
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 1024 * 1024  # Default 1MB
    
    create_dummy_file(file_path, size)

if __name__ == "__main__":
    main()