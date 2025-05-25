import yaml
import os

# Determine the base directory of the project (soccer_betting_analyzer)
# This assumes utils/config_loader.py is two levels down from the project root.
# Adjust if your execution context is different.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config', 'settings.yaml')

def load_config(config_path: str = None) -> dict:
    """
    Loads the YAML configuration file.

    Args:
        config_path: Path to the configuration file. 
                     Defaults to 'config/settings.yaml' relative to project root.

    Returns:
        A dictionary containing the configuration, or an empty dict if loading fails.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    
    if not os.path.exists(config_path):
        print(f"Warning: Configuration file not found at {config_path}. Using default or empty config.")
        return {}

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config if config else {}
    except yaml.YAMLError as e:
        print(f"Error parsing YAML configuration file {config_path}: {e}")
        return {}
    except Exception as e:
        print(f"Error loading configuration file {config_path}: {e}")
        return {}

# Load configuration once and make it available
# This approach makes the config a bit like a singleton accessible after first load.
# Alternatively, functions could call load_config() every time they need it.
APP_CONFIG = load_config()

if __name__ == '__main__':
    # Example of how to use and access the config
    print(f"Loading configuration from: {DEFAULT_CONFIG_PATH}")
    retrieved_config = load_config() # Can also use APP_CONFIG directly if module is imported
    
    if retrieved_config:
        print("Configuration loaded successfully:")
        print(f"  API Key (The Odds API): {retrieved_config.get('the_odds_api', {}).get('api_key')}")
        print(f"  Default EV Threshold: {retrieved_config.get('analysis', {}).get('default_ev_threshold')}")
    else:
        print("Failed to load or empty configuration.")
    
    # Showing direct use of APP_CONFIG
    print("\nUsing pre-loaded APP_CONFIG:")
    if APP_CONFIG:
         print(f"  API Key (from APP_CONFIG): {APP_CONFIG.get('the_odds_api', {}).get('api_key')}")
    else:
        print("  APP_CONFIG is empty.")
