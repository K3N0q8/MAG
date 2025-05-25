import requests
import json # Though requests handles json directly, good to have if manual parsing is ever needed.

# Assuming src is in PYTHONPATH or the script is run in a way that resolves this:
from utils.config_loader import APP_CONFIG

# Placeholder for the API base URL - check documentation for the correct v4 URL.
# Example: API_BASE_URL = "https://api.the-odds-api.com/v4" 
API_BASE_URL = "https://api.the-odds-api.com/v4/sports" # Adjusted based on typical API structures, confirm from docs

# API_KEY is now fetched from APP_CONFIG in the function
# API_KEY = 'YOUR_API_KEY' 

DEFAULT_API_KEY_PLACEHOLDER = 'YOUR_API_KEY_PLACEHOLDER' # Used if config is missing

def get_soccer_odds(api_key: str = None, regions: str = 'eu', markets: str = 'h2h', odds_format: str = 'decimal', date_format: str = 'iso'):
    """
    Fetches soccer odds from The Odds API.

    Args:
        api_key: The API key for The Odds API. If None, attempts to load from config.
        regions: Comma-separated list of regions (e.g., 'eu', 'us', 'uk', 'au'). Defaults to 'eu'.
        markets: Comma-separated list of markets (e.g., 'h2h', 'spreads', 'totals'). Defaults to 'h2h'.
        odds_format: The format for odds ('decimal' or 'american'). Defaults to 'decimal'.
        date_format: The format for dates ('iso' or 'unix'). Defaults to 'iso'.

    Returns:
        A dictionary containing the API response data, or None if an error occurs.
        Specifically, it should return the list of events data.
    """
    used_api_key = api_key
    if used_api_key is None:
        # Attempt to load API key from config if not provided directly
        used_api_key = APP_CONFIG.get('the_odds_api', {}).get('api_key', DEFAULT_API_KEY_PLACEHOLDER)

    if used_api_key == DEFAULT_API_KEY_PLACEHOLDER or not used_api_key:
        print(f"Warning: API key is set to placeholder '{DEFAULT_API_KEY_PLACEHOLDER}' or is missing. Please configure it in config/settings.yaml.")
        # Prevent actual API calls during development without a key.
        return []

    # Example: Fetching upcoming Premier League (soccer_epl) odds.
    # The actual sport key needs to be confirmed from The Odds API documentation.
    sport_key = 'soccer_epl' # Example, make this configurable or an argument later

    params = {
        'apiKey': api_key,
        'regions': regions,
        'markets': markets,
        'oddsFormat': odds_format,
        'dateFormat': date_format,
    }

    # Construct the URL for a specific sport, e.g., soccer_epl
    # The final URL structure needs to be verified from The Odds API documentation.
    # It might be something like /sports/{sport_key}/odds/ or similar.
    # For now, I'll assume a general odds endpoint and filter by sport if the API supports it,
    # or use a sport-specific endpoint if that's how it works.
    # Based on their site, it seems like {sport}/odds is a common pattern.
    
    # The URL should be: https://api.the-odds-api.com/v4/sports/{sport}/odds
    # Let's try with a generic soccer endpoint first if available, or a major league.
    # For this example, I'm using 'soccer_epl' as the sport_key.
    # Users will likely want to query various leagues.
    
    url = f"{API_BASE_URL}/{sport_key}/odds"

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        
        # Data is a list of events
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from The Odds API: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None

# Example usage (optional, for testing within the module)
if __name__ == '__main__':
    print("Attempting to fetch soccer odds (Premier League)...")
    # IMPORTANT: Replace 'YOUR_API_KEY' with a valid key to test.
    # For automated testing, this part should not run or should use a mock key/server.
    
    # Retrieve API_KEY for the test call from config
    test_api_key = APP_CONFIG.get('the_odds_api', {}).get('api_key', DEFAULT_API_KEY_PLACEHOLDER)

    if test_api_key != DEFAULT_API_KEY_PLACEHOLDER and test_api_key:
        print(f"Attempting to fetch soccer odds (Premier League) using API key from config...")
        # Pass the loaded key to the function for the test run
        odds_data = get_soccer_odds(api_key=test_api_key, regions='uk', markets='h2h')
        if odds_data is not None: # Check if None, not just falsy (empty list is valid if API returns no events)
            print(f"Successfully fetched {len(odds_data)} events.")
            # Print details of the first event if data exists
            if odds_data:
                print("Details of the first event:")
                print(json.dumps(odds_data[0], indent=2))
        else:
            print("Failed to fetch odds data or no data returned.")
    else:
            print("Please set your API_KEY in config/settings.yaml to test fetching odds.")
        # Example of what the data structure might look like (for development purposes)
        example_event = {
            "id": "abcdef1234567890",
            "sport_key": "soccer_epl",
            "sport_title": "English Premier League",
            "commence_time": "2023-08-15T18:00:00Z",
            "home_team": "Arsenal",
            "away_team": "Manchester City",
            "bookmakers": [
                {
                    "key": "unibet",
                    "title": "Unibet",
                    "last_update": "2023-08-15T17:55:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Arsenal", "price": 2.75},
                                {"name": "Manchester City", "price": 2.50},
                                {"name": "Draw", "price": 3.50}
                            ]
                        }
                    ]
                }
            ]
        }
        print("\nExample data structure for one event (if API_KEY was set):")
        print(json.dumps(example_event, indent=2))
