import argparse
import json # For pretty printing example data

# Assuming your project structure allows these imports
# If soccer_betting_analyzer is the root and src is on PYTHONPATH:
from data_acquisition import the_odds_api
from analysis import value_calculator
from utils.config_loader import APP_CONFIG
from utils import data_storage 
from utils import probability_loader 

# --- Example Data (for analyze-bets command) ---
EXAMPLE_EVENT_DATA = {
    "id": "exampleevent001",
    "sport_key": "soccer_generic_league",
    "sport_title": "Generic Soccer League",
    "commence_time": "2024-01-01T12:00:00Z",
    "home_team": "Team Alpha",
    "away_team": "Team Beta",
    "bookmakers": [
        {
            "key": "bookieX", 
            "title": "Bookie X", 
            "last_update": "2024-01-01T11:55:00Z",
            "markets": [
                {
                    "key": "h2h", 
                    "last_update": "2024-01-01T11:50:00Z",
                    "outcomes": [
                        {"name": "Team Alpha", "price": 2.20}, 
                        {"name": "Team Beta", "price": 3.50}, 
                        {"name": "Draw", "price": 3.20}
                    ]
                },
                {
                    "key": "totals",
                    "last_update": "2024-01-01T11:52:00Z",
                    "outcomes": [
                      {"name": "Over 2.5", "price": 1.90},
                      {"name": "Under 2.5", "price": 1.95}
                    ]
                }
            ]
        },
        {
            "key": "bookieY", 
            "title": "Bookie Y", 
            "last_update": "2024-01-01T11:58:00Z",
            "markets": [
                {
                    "key": "h2h", 
                    "last_update": "2024-01-01T11:56:00Z",
                    "outcomes": [
                        {"name": "Team Alpha", "price": 2.25}, 
                        {"name": "Team Beta", "price": 3.40}, 
                        {"name": "Draw", "price": 3.30}
                    ]
                },
                {
                    "key": "totals",
                    "last_update": "2024-01-01T11:57:00Z",
                    "outcomes": [
                      {"name": "Over 2.5", "price": 1.85},
                      {"name": "Under 2.5", "price": 2.00}
                    ]
                }
            ]
        }
    ]
}

USER_ESTIMATED_PROBS_EXAMPLE = {
    "Team Alpha": 0.48,
    "Team Beta": 0.28,
    "Draw": 0.24,
    "Over 2.5": 0.55,
    "Under 2.5": 0.45
}

# --- Helper Functions for Formatting ---
def format_datetime_str(iso_str: str) -> str:
    """Basic formatting for ISO datetime string."""
    if iso_str and isinstance(iso_str, str):
        return iso_str.replace('T', ' ').replace('Z', ' UTC')
    return "N/A"

# --- Handler Functions ---
def handle_fetch_data(args):
    print(f"Attempting to fetch odds data for sport: {args.sport}")
    print("Important: Ensure your API key is correctly set in config/settings.yaml if fetching live data.")
    print("API usage may be subject to quotas and costs from The Odds API.\n")

    storage_config = APP_CONFIG.get('data_storage', {})
    cache_base_path = storage_config.get('base_path', 'data/api_cache/') 
    freshness_hours = storage_config.get('freshness_hours', 6) 
    
    cache_filepath = data_storage.get_cache_filepath(
        args.sport, args.regions, args.markets, cache_base_path
    )
    
    print(f"Checking for cached data at: {cache_filepath}")
    cached_data = data_storage.load_data(cache_filepath, freshness_hours)
    data_to_display = None

    if cached_data is not None: 
        print("Using fresh cached data.")
        data_to_display = cached_data
    else:
        print("No fresh cached data found. Fetching from API...")
        api_key = APP_CONFIG.get('the_odds_api', {}).get('api_key')
        if not api_key or api_key == 'YOUR_API_KEY_HERE': 
            print("\nError: API key is missing or is the placeholder 'YOUR_API_KEY_HERE'.")
            print("Please update 'api_key' in 'config/settings.yaml' with your actual The Odds API key.")
            print("Cannot fetch live data without a valid API key.")
            return

        print(f"\nFetching live data for sport: {args.sport}, regions: {args.regions}, markets: {args.markets}...")
        api_data = the_odds_api.get_odds(
            api_key=api_key, sport_key=args.sport, regions=args.regions, markets=args.markets
        )

        if api_data is not None: 
            print(f"Successfully fetched {len(api_data)} events from API.")
            data_storage.save_data(api_data, cache_filepath) 
            data_to_display = api_data
        else: 
            print("Failed to fetch data from API. Check error messages from the_odds_api module.")
            return # Exit if API fetch failed

    if data_to_display is None: # Should only happen if API fetch failed and no cache
         print("No data available to display.")
         return
    elif not data_to_display: # Empty list
        print("\nNo upcoming events found for the specified parameters (from cache or API).")
    else:
        print(f"\n--- Displaying up to 5 Events for {args.sport} ---")
        for i, event in enumerate(data_to_display[:5]):
            home = event.get('home_team', 'N/A')
            away = event.get('away_team', 'N/A')
            commence_time = format_datetime_str(event.get('commence_time'))
            sport_title = event.get('sport_title', args.sport) # Fallback to args.sport
            
            market_keys_str = "N/A"
            if event.get('bookmakers') and isinstance(event['bookmakers'], list) and event['bookmakers']:
                first_bookie_markets = event['bookmakers'][0].get('markets', [])
                market_keys = sorted([m.get('key', 'unknown') for m in first_bookie_markets]) # Sort for consistency
                if market_keys:
                    market_keys_str = ", ".join(market_keys)

            print(f"\nEvent: {home} vs {away}")
            print(f"  Start Time: {commence_time}")
            print(f"  Sport: {sport_title}")
            print(f"  Available Markets (from first bookmaker): {market_keys_str}")
            if i < 4 and i < len(data_to_display) -1 : 
                print("---------------------------------------------")
        if len(data_to_display) > 5:
            print(f"\n... and {len(data_to_display) - 5} more events not shown.")
        print("--- End of Event Display ---")

def handle_analyze_bets(args):
    ev_threshold_to_use = args.ev_threshold
    print(f"Analyzing bets with EV threshold: {ev_threshold_to_use:.2f}")

    current_event_id = EXAMPLE_EVENT_DATA['id'] 
    probabilities_for_current_event = None
    source_of_probabilities = "Unknown"

    if args.prob_file:
        source_of_probabilities = f"file ({args.prob_file})"
        print(f"Loading user-defined probabilities from: {args.prob_file}")
        user_event_probabilities_map = probability_loader.load_probabilities_from_file(args.prob_file)
        
        if user_event_probabilities_map is None:
            print(f"\nError: Failed to load probabilities from {args.prob_file}. Cannot proceed.")
            return
        
        if current_event_id in user_event_probabilities_map:
            probabilities_for_current_event = user_event_probabilities_map[current_event_id]
            print(f"Using probabilities from file for event ID: {current_event_id}")
        else:
            print(f"\nError: Probabilities for example event ID '{current_event_id}' not found in '{args.prob_file}'.")
            print("Cannot analyze this event using the provided file. Ensure the event_id matches.")
            return
            
    elif args.use_vig_removal:
        source_of_probabilities = "vig removal model (from example event data's first bookmaker)"
        print("\nAttempting to use vig removal model for probabilities...")
        combined_de_vigged_probs = {}
        try:
            if not EXAMPLE_EVENT_DATA.get('bookmakers'):
                raise ValueError("Example event data is missing 'bookmakers' list.")
            first_bookmaker_all_markets = EXAMPLE_EVENT_DATA['bookmakers'][0].get('markets', [])
            if not first_bookmaker_all_markets:
                print("Error: No markets found for the first bookmaker in example data.")
                raise ValueError("No markets for vig removal.") 

            for market_data in first_bookmaker_all_markets:
                market_key = market_data.get('key', 'unknown_market')
                market_outcomes = market_data.get('outcomes')
                if not market_outcomes: 
                    print(f"Warning: No outcomes found for market '{market_key}' during vig removal. Skipping this market.")
                    continue
                
                raw_implied = value_calculator.get_implied_probabilities_for_market(market_outcomes)
                if not raw_implied: 
                    print(f"Warning: Could not calculate raw implied probabilities for market '{market_key}'. Skipping this market.")
                    continue
                
                de_vigged = value_calculator.remove_vig(raw_implied)
                if not de_vigged: 
                    print(f"Warning: Failed to remove vig for market '{market_key}'. Skipping this market.")
                    continue
                
                print(f"  De-vigged probabilities for market '{market_key}': {de_vigged}")
                combined_de_vigged_probs.update(de_vigged)
            
            if not combined_de_vigged_probs:
                print("Error: Vig removal process yielded no valid probabilities across all markets.")
                probabilities_for_current_event = None 
            else:
                probabilities_for_current_event = combined_de_vigged_probs

        except (IndexError, ValueError) as e: 
            print(f"Error processing example event data for vig removal: {e}")
            probabilities_for_current_event = None 
        except Exception as e: 
            print(f"An unexpected error occurred during vig removal: {e}")
            probabilities_for_current_event = None 

        if probabilities_for_current_event:
             print(f"Successfully estimated probabilities using vig removal (combined): {probabilities_for_current_event}")
        else: 
            print("\nFalling back to predefined example probabilities due to issues with vig removal.")
            probabilities_for_current_event = USER_ESTIMATED_PROBS_EXAMPLE 
            source_of_probabilities = "example (fallback after vig removal failure)"
            
    else: 
        source_of_probabilities = "predefined example"
        print("\nNo specific probability source selected. Using predefined example probabilities.")
        probabilities_for_current_event = USER_ESTIMATED_PROBS_EXAMPLE 

    if not probabilities_for_current_event:
        print(f"\nError: No probabilities available for event '{current_event_id}' from source '{source_of_probabilities}'. Cannot analyze.")
        return

    print(f"\nAnalyzing event: {EXAMPLE_EVENT_DATA.get('home_team')} vs {EXAMPLE_EVENT_DATA.get('away_team')} (ID: {current_event_id})")
    print(f"Using probabilities from: {source_of_probabilities}")
    print(f"Probabilities used: {probabilities_for_current_event}")

    value_bets = value_calculator.find_value_bets_for_event(
        event_data=EXAMPLE_EVENT_DATA, 
        user_estimated_probabilities=probabilities_for_current_event,
        value_threshold=ev_threshold_to_use
    )

    if value_bets:
        print(f"\nFound {len(value_bets)} value bet(s):")
        for bet in value_bets:
            print("--------------------------------------------------")
            print("  VALUE BET FOUND:")
            print(f"    Event: {bet['home_team']} vs {bet['away_team']} (ID: {bet['event_id']})")
            print(f"    Bookmaker: {bet['bookmaker']}")
            print(f"    Market: {bet['market_key']}")
            print(f"    Outcome: {bet['outcome_name']}")
            print(f"    Odds: {bet['decimal_odds']:.2f}")
            print(f"    Estimated True Probability: {bet['estimated_true_probability']:.2%}")
            print(f"    Calculated Expected Value (EV): {bet['expected_value']:.3f}")
        print("--------------------------------------------------")
    else:
        print("\nNo value bets found matching the criteria with the example data.")

def handle_list_sports(args):
    print("Fetching available sports from The Odds API...")
    print("Important: Ensure your API key is correctly set in config/settings.yaml.")
    print("API usage may be subject to quotas and costs from The Odds API.\n")

    api_key = APP_CONFIG.get('the_odds_api', {}).get('api_key')
    
    if not api_key or api_key == 'YOUR_API_KEY_HERE': 
        print("Error: API key is missing or is the placeholder 'YOUR_API_KEY_HERE'.")
        print("Please update 'api_key' in 'config/settings.yaml' with your actual The Odds API key.")
        return

    sports_data = the_odds_api.get_available_sports(api_key)

    if sports_data is None:
        print("Failed to fetch available sports. Check error messages above and API key/plan.")
    elif not sports_data:
        print("Successfully connected to API, but no sports were returned (this is unusual).")
    else:
        print("--- Available Sports from The Odds API ---")
        header = f"{'Sport Key':<40} | {'Title':<45} | {'Group':<25}"
        print(header)
        print(f"{'-'*40}-|-{'-'*45}-|-{'-'*25}")
        for sport in sports_data:
            key = sport.get('key', 'N/A')
            title = sport.get('title', 'N/A')
            group = sport.get('group', 'N/A')
            print(f"{key:<40} | {title:<45} | {group:<25}")
        print(f"\nFetched {len(sports_data)} sports.")
        print("--- End of Sports List ---")

# --- Main CLI Logic ---
def main():
    parser = argparse.ArgumentParser(
        description="Sports Betting Analysis CLI. \n\nNote: Live data fetching requires a valid API key in config/settings.yaml and may be subject to API provider's usage limits and costs.",
        formatter_class=argparse.RawTextHelpFormatter # For better display of multiline description
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    # Subparser for the fetch-data command
    parser_fetch = subparsers.add_parser('fetch-data', 
                                         help='Fetches live sports odds data using The Odds API (with caching).')
    parser_fetch.add_argument('--sport', 
                              type=str, 
                              required=True, 
                              help='Sport key to fetch (e.g., soccer_epl). Use "list-sports" to see available keys.')
    parser_fetch.add_argument('--regions', 
                              type=str, 
                              default='eu', 
                              help="Comma-separated list of regions (e.g., 'eu','us','uk','au'). Default: 'eu'.")
    parser_fetch.add_argument('--markets', 
                              type=str, 
                              default='h2h', 
                              help="Comma-separated list of markets (e.g., 'h2h','spreads','totals'). Default: 'h2h'.")
    parser_fetch.set_defaults(func=handle_fetch_data)

    # Subparser for the list-sports command
    parser_list_sports = subparsers.add_parser('list-sports', help='Lists available sports from The Odds API.')
    parser_list_sports.set_defaults(func=handle_list_sports)

    # Subparser for the analyze-bets command
    parser_analyze = subparsers.add_parser('analyze-bets', 
                                           help='Analyzes bets to find value. Uses example event data.')
    
    default_ev_from_config = APP_CONFIG.get('analysis', {}).get('default_ev_threshold', 0.05)
    
    parser_analyze.add_argument(
        '--ev-threshold', 
        type=float, 
        default=default_ev_from_config, 
        help=f'Minimum Expected Value (EV) to consider a bet valuable (default from config: {default_ev_from_config:.2f}).'
    )
    parser_analyze.add_argument(
        '--prob-file', 
        type=str, 
        default=None, 
        help='Path to a JSON file containing user-defined probabilities for the example event.'
    )
    parser_analyze.add_argument(
        '--use-vig-removal', 
        action='store_true', 
        help='Estimate probabilities for the example event using vig removal from its first bookmaker. Ignored if --prob-file is used.'
    )
    parser_analyze.set_defaults(func=handle_analyze_bets)

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
