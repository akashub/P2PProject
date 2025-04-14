from client import Client

# Basic const params
MY_ID = "1001"
PEER_ID = "1002"
TCP_IP = "127.0.0.1"
TCP_PORT = 5005
BUFFER_SIZE = 1024
OTHER_PEERS = [["127.0.0.1", 6008]]
CONFIG_FILEPATH = "project_config_file_small/Common.cfg"

def main():
    client = Client(CONFIG_FILEPATH, TCP_IP, TCP_PORT, MY_ID)
    client.has_file()
    client.setup(OTHER_PEERS)
    
    try:
        # Keep the main thread running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down client...")
        client.shutdown()

if __name__ == "__main__":
    main()