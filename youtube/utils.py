import json
import os

def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("config.json not found. Please create it based on the template.")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in config.json")
