class Config:
    def __init__(self, filepath):
        self.config_filepath = filepath
        self.num_of_pref_neighbors = None
        self.unchoking_interval = None
        self.optimistic_unchoking_interval = None
        self.file_name = None
        self.file_size = None
        self.piece_size = None
        self.peers_file = "project_config_file_small/project_config_file_small/PeerInfo.cfg"  # Default value
        
        with open(filepath, "r") as file:
            lines = file.readlines()
            for line in lines:
                params = line.split()
                if len(params) >= 2:
                    param_name = params[0]
                    param_value = params[1]
                    
                    if param_name == "NumberOfPreferredNeighbors":
                        self.num_of_pref_neighbors = int(param_value)
                    elif param_name == "UnchokingInterval":
                        self.unchoking_interval = int(param_value)
                    elif param_name == "OptimisticUnchokingInterval":
                        self.optimistic_unchoking_interval = int(param_value)
                    elif param_name == "FileName":
                        self.file_name = param_value
                    elif param_name == "FileSize":
                        self.file_size = int(param_value)
                    elif param_name == "PieceSize":
                        self.piece_size = int(param_value)
                    else:
                        print(f"Unknown parameter: {param_name} with value: {param_value}")
                        
    def print_config(self):
        """Print all configuration parameters for debugging"""
        print("Configuration Parameters:")
        print("NumberOfPreferredNeighbors:", self.num_of_pref_neighbors)
        print("UnchokingInterval:", self.unchoking_interval)
        print("OptimisticUnchokingInterval:", self.optimistic_unchoking_interval)
        print("FileName:", self.file_name)
        print("FileSize:", self.file_size)
        print("PieceSize:", self.piece_size)
        print("PeersFile:", self.peers_file)