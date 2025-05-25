import requests
import json

# API_BASE_URL is a constant for this module
API_BASE_URL = "https://api.the-odds-api.com/v4/sports"

# Placeholder constant for comparison, actual key comes from config via function argument
# This helps identify if a placeholder is mistakenly used.
API_KEY_PLACEHOLDER_CONFIG = 'YOUR_API_KEY_HERE' # Matches the placeholder in settings.yaml
API_KEY_PLACEHOLDER_INTERNAL = 'YOUR_API_KEY_PLACEHOLDER' # Legacy internal placeholder, for safety

def get_odds(api_key: str, sport_key: str, regions: str = 'eu', markets: str = 'h2h', odds_format: str = 'decimal', date_format: str = 'iso'):
    """
    Fetches odds from The Odds API for a specified sport.

    Args:
        api_key: The API key for The Odds API. This is mandatory.
        sport_key: The key for the sport to fetch odds for (e.g., 'soccer_epl'). This is mandatory.
        regions: Comma-separated list of regions (e.g., 'eu', 'us', 'uk', 'au'). Defaults to 'eu'.
        markets: Comma-separated list of markets (e.g., 'h2h', 'spreads', 'totals'). Defaults to 'h2h'.
        odds_format: The format for odds ('decimal' or 'american'). Defaults to 'decimal'.
        date_format: The format for dates ('iso' or 'unix'). Defaults to 'iso'.

    Returns:
        A list of event data dictionaries from the API response, or None if a critical error occurs.
        Returns an empty list if the API call is successful but no events are found.
    """
    if not api_key or api_key == API_KEY_PLACEHOLDER_CONFIG or api_key == API_KEY_PLACEHOLDER_INTERNAL:
        print(f"Error: API key is missing or is a placeholder ('{api_key}'). Please configure it in config/settings.yaml.")
        return None # Critical error, cannot proceed

    if not sport_key:
        print("Error: Sport key is mandatory and was not provided.")
        return None # Critical error

    params = {
        'apiKey': api_key,
        'regions': regions,
        'markets': markets,
        'oddsFormat': odds_format,
        'dateFormat': date_format,
    }
    
    url = f"{API_BASE_URL}/{sport_key}/odds"
    response_obj = None # To store response for potential error logging outside try block for HTTPError

    try:
        response_obj = requests.get(url, params=params)
        
        # Check for specific client/server errors first
        if response_obj.status_code == 401:
            print(f"Error: Unauthorized (401). Check your API key. Message: {response_obj.text}")
            return None
        if response_obj.status_code == 404:
            print(f"Error: Data not found (404) for sport '{sport_key}'. Check sport key or API plan. Message: {response_obj.text}")
            return None # Could also be an empty list if preferred for "not found" type errors
        if response_obj.status_code == 429:
            print(f"Error: Too many requests (429). You may have exceeded your API quota. Message: {response_obj.text}")
            return None
            
        response_obj.raise_for_status()  # Raises an HTTPError for other bad responses (4XX or 5XX)
        
        data = response_obj.json()
        if not data: # API might return an empty list if no events match the query
            print(f"No upcoming events found for sport '{sport_key}' with regions '{regions}' and markets '{markets}'.")
            return [] # Successfully fetched, but no events
        return data
    except requests.exceptions.HTTPError as e:
        # This will catch errors from raise_for_status() for non-401/404/429 client/server errors
        err_msg = f"HTTP error fetching data from The Odds API for '{sport_key}': {e}"
        if response_obj is not None:
            err_msg += f"\nResponse status: {response_obj.status_code}. Response content: {response_obj.text}"
        else:
            err_msg += "\nNo response object available."
        print(err_msg)
        return None
    except requests.exceptions.RequestException as e: # Covers network errors, DNS failures, timeouts etc.
        print(f"Request error fetching data from The Odds API for '{sport_key}': {e}")
        return None
    except json.JSONDecodeError as e:
        # This means the server responded with success (2xx) but content was not valid JSON
        err_msg = f"Error decoding JSON response for '{sport_key}': {e}."
        if response_obj is not None and response_obj.text:
             err_msg += f"\nResponse content was: {response_obj.text[:500]}..." # Show partial content
        print(err_msg)
        return None

# Example usage (optional, for testing within the module)
if __name__ == '__main__':
    print("This script is intended to be used as a module.")
    print("To test 'get_odds', you would typically call it from another script (like main.py)")
    print("that handles API key configuration from 'config/settings.yaml'.")
    print("\nExample of how you might call it (requires manual API_KEY and SPORT_KEY):")
    print("# from utils.config_loader import APP_CONFIG # Assuming you have this for config")
    print("# configured_api_key = APP_CONFIG.get('the_odds_api', {}).get('api_key')")
    print("# if configured_api_key and configured_api_key != 'YOUR_API_KEY_HERE':")
    print("#     odds = get_odds(configured_api_key, sport_key='soccer_epl', regions='uk')")
    print("#     if odds is not None:")
    print("#         print(f'Fetched {len(odds)} events for soccer_epl')")
    print("# else:")
    print("#     print('API key not configured or is placeholder in settings.yaml')")

    # Minimal direct test if someone insists on running, but not recommended without care
    # api_key_manual = "YOUR_ACTUAL_KEY_FOR_TESTING_ONLY" # Replace if testing directly
    # sport_key_manual = "soccer_usa_mls"
    # if api_key_manual != "YOUR_ACTUAL_KEY_FOR_TESTING_ONLY" and api_key_manual != API_KEY_PLACEHOLDER_CONFIG :
    #     print(f"\nAttempting a direct test call with manually set key for sport '{sport_key_manual}'...")
    #     odds_data = get_odds(api_key_manual, sport_key_manual, regions='us', markets='h2h')
    #     if odds_data is not None:
    #         print(f"Successfully fetched {len(odds_data)} events for '{sport_key_manual}'.")
    #         if odds_data:
    #             print("Details of the first event:")
    #             print(json.dumps(odds_data[0], indent=2))
    #     else:
    #         print(f"Failed to fetch odds data for '{sport_key_manual}'.")
    # else:
    #     print("\nDirect test call skipped: API key not manually set in script for testing.")

def get_available_sports(api_key: str) -> Optional[List[Dict[str, Any]]]:
    """
    Fetches the list of available sports from The Odds API.

    Args:
        api_key: The API key for The Odds API. This is mandatory.

    Returns:
        A list of sport objects (dictionaries) from the API response, 
        or None if a critical error occurs.
    """
    if not api_key or api_key == API_KEY_PLACEHOLDER_CONFIG or api_key == API_KEY_PLACEHOLDER_INTERNAL:
        print(f"Error: API key is missing or is a placeholder ('{api_key}'). Please configure it in config/settings.yaml.")
        return None

    params = {'apiKey': api_key}
    url = f"{API_BASE_URL}" # The base URL itself is for /sports

    response_obj = None
    try:
        response_obj = requests.get(url, params=params)

        if response_obj.status_code == 401:
            print(f"Error: Unauthorized (401) when fetching sports list. Check your API key. Message: {response_obj.text}")
            return None
        if response_obj.status_code == 429:
            print(f"Error: Too many requests (429) when fetching sports list. You may have exceeded your API quota. Message: {response_obj.text}")
            return None
            
        response_obj.raise_for_status()  # For other 4XX or 5XX errors

        data = response_obj.json()
        if not data: # Should not happen for /sports endpoint if API is working
            print("No sports data returned from API, though request was successful.")
            return [] 
        return data
    except requests.exceptions.HTTPError as e:
        err_msg = f"HTTP error fetching available sports: {e}"
        if response_obj is not None:
            err_msg += f"\nResponse status: {response_obj.status_code}. Response content: {response_obj.text}"
        print(err_msg)
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error fetching available sports: {e}")
        return None
    except json.JSONDecodeError as e:
        err_msg = f"Error decoding JSON response for available sports: {e}."
        if response_obj is not None and response_obj.text:
             err_msg += f"\nResponse content was: {response_obj.text[:500]}..."
        print(err_msg)
        return None
