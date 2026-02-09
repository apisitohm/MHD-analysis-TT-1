# src/utils/config_manager.py
import json
import os
import threading

class ConfigManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_path = os.path.join(self.base_path, 'config.json')
        self.params_path = os.path.join(self.base_path, 'params.json')
        
        self.config = {}
        self.params = {}
        
        self.load_config()
        self.load_params()
        
    def load_config(self):
        """Loads config.json"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error loading config.json: {e}")
                self.config = {}
        else:
            print(f"config.json not found at {self.config_path}")
            
    def load_params(self):
        """Loads params.json"""
        if os.path.exists(self.params_path):
            try:
                with open(self.params_path, 'r') as f:
                    self.params = json.load(f)
            except Exception as e:
                print(f"Error loading params.json: {e}")
                self.params = {}
        else:
            print(f"params.json not found at {self.params_path}")

    def get_config(self, path=None, default=None):
        """
        Retrieves a value from config.json using a dot-notation path.
        Example: get_config("analysis.cal_duration.threshold")
        """
        if path is None:
            return self.config
            
        keys = path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def get_params(self):
        """Returns the loaded parameters."""
        return self.params
        
# Global instance for easy access
config_manager = ConfigManager()
