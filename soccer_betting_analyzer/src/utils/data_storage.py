import json
import os
import datetime
from typing import Optional, Dict, Any

# Assuming APP_CONFIG is loaded and available from utils.config_loader
# This might require adjusting imports if APP_CONFIG is not directly accessible
# or passing config values as arguments. For this subtask, assume direct import works.
# If not, the calling function (in main.py) will need to pass config values.
# Let's make it more robust by having functions accept config parameters.

def get_cache_filepath(sport_key: str, regions: str, markets: str, base_path: str) -> str:
    """Generates a filepath for caching data based on query parameters."""
    today = datetime.date.today().isoformat()
    # Sanitize inputs for filename (simple replacement)
    sport_s = sport_key.replace('_', '-')
    regions_s = regions.replace(',', '_').replace(' ', '')
    markets_s = markets.replace(',', '_').replace(' ', '')
    
    filename = f"{sport_s}_{regions_s}_{markets_s}_{today}.json"
    
    # Ensure base_path exists
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)
    return os.path.join(base_path, filename)

def save_data(data: Any, filepath: str):
    """Saves data to a JSON file."""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Data successfully saved to {filepath}")
    except IOError as e:
        print(f"Error saving data to {filepath}: {e}")

def load_data(filepath: str, freshness_hours: Optional[int] = None) -> Optional[Any]:
    """Loads data from a JSON file if it exists and is fresh."""
    if not os.path.exists(filepath):
        return None

    if freshness_hours is not None:
        try:
            file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
            if datetime.datetime.now() - file_mod_time > datetime.timedelta(hours=freshness_hours):
                print(f"Cache file {filepath} is stale (older than {freshness_hours} hours).")
                return None
        except Exception as e:
            print(f"Could not determine file age for {filepath}: {e}")
            return None # Treat as stale if age check fails

    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        print(f"Data successfully loaded from {filepath}")
        return data
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading or parsing data from {filepath}: {e}")
        return None

if __name__ == '__main__':
    # Example Usage (requires config values)
    mock_config = {
        'data_storage': {
            'base_path': 'data/api_cache_test/',
            'freshness_hours': 1
        }
    }
    test_base_path = mock_config['data_storage']['base_path']
    test_freshness = mock_config['data_storage']['freshness_hours']

    # Ensure test cache directory exists
    if not os.path.exists(test_base_path):
        os.makedirs(test_base_path, exist_ok=True)

    fp = get_cache_filepath("soccer_epl", "uk", "h2h", test_base_path)
    print(f"Generated cache filepath: {fp}")

    # Test save
    test_data = {"event_count": 2, "events": [{"id": "1", "name": "Test Event"}]}
    save_data(test_data, fp)

    # Test load (should be fresh)
    loaded_data = load_data(fp, test_freshness)
    if loaded_data:
        print(f"Loaded fresh data: {loaded_data}")
    
    # Simulate time passing for staleness (by setting freshness to 0 hours)
    stale_data = load_data(fp, freshness_hours=0)
    if stale_data is None:
        print("Stale data correctly not loaded (or treated as stale).")

    # Clean up test file/dir if necessary
    # os.remove(fp)
    # if not os.listdir(test_base_path):
    #    os.rmdir(test_base_path)
