class Config:
    def __init__(self, filepath, custom_filename=None):
        self.config_filepath = filepath
        self.num_of_pref_neighbords = None
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
                        self.num_of_pref_neighbords = int(param_value)
                    elif param_name == "UnchokingInterval":
                        self.unchoking_interval = int(param_value)
                    elif param_name == "OptimisticUnchokingInterval":
                        self.optimistic_unchoking_interval = int(param_value)
                    elif param_name == "FileName":
                        # Allow overriding the filename from config if custom_filename is provided
                        self.file_name = custom_filename if custom_filename else param_value
                    elif param_name == "FileSize":
                        self.file_size = int(param_value)
                    elif param_name == "PieceSize":
                        self.piece_size = int(param_value)
                    else:
                        print(f"Unknown parameter: {param_name} with value: {param_value}")
        
        # If custom filename was provided, log it
        if custom_filename:
            print(f"Using custom file: {custom_filename} instead of {param_value}")
                        
    def print_config(self):
        """Print all configuration parameters for debugging"""
        print("Configuration Parameters:")
        print("NumberOfPreferredNeighbors:", self.num_of_pref_neighbords)
        print("UnchokingInterval:", self.unchoking_interval)
        print("OptimisticUnchokingInterval:", self.optimistic_unchoking_interval)
        print("FileName:", self.file_name)
        print("FileSize:", self.file_size)
        print("PieceSize:", self.piece_size)
        print("PeersFile:", self.peers_file)