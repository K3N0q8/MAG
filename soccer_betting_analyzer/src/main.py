import argparse
import json # For pretty printing example data

# Assuming your project structure allows these imports
# If soccer_betting_analyzer is the root and src is on PYTHONPATH:
from data_acquisition import the_odds_api
from analysis import value_calculator
from utils.config_loader import APP_CONFIG # Import APP_CONFIG

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
            "markets": [{
                "key": "h2h", 
                "outcomes": [
                    {"name": "Team Alpha", "price": 2.20}, 
                    {"name": "Team Beta", "price": 3.50}, 
                    {"name": "Draw", "price": 3.20}
                ]
            }]
        },
        {
            "key": "bookieY", 
            "title": "Bookie Y", 
            "last_update": "2024-01-01T11:58:00Z",
            "markets": [{
                "key": "h2h", 
                "outcomes": [
                    {"name": "Team Alpha", "price": 2.25}, 
                    {"name": "Team Beta", "price": 3.40}, 
                    {"name": "Draw", "price": 3.30}
                ]
            }]
        }
    ]
}

USER_ESTIMATED_PROBS_EXAMPLE = {
    "Team Alpha": 0.48,  # User estimates Team Alpha has a 48% chance
    "Team Beta": 0.28,   # User estimates Team Beta has a 28% chance
    "Draw": 0.24         # User estimates Draw has a 24% chance
    # Sum: 0.48 + 0.28 + 0.24 = 1.00
}

# --- Handler Functions ---
def handle_fetch_data(args):
    print("Simulating data fetching...")
    print("(Note: Actual API call to The Odds API is not made without a valid API key and further configuration in the_odds_api.py module.)")
    print("\nThis command would eventually call functions from 'src.data_acquisition.the_odds_api'.")
    print("Example of data structure expected by the analysis module for one event:")
    print(json.dumps(EXAMPLE_EVENT_DATA, indent=2))
    print("\nTo fetch real data (once configured):")
    print("1. Ensure 'YOUR_API_KEY' in 'src/data_acquisition/the_odds_api.py' is replaced with your actual key.")
    print("2. The 'get_soccer_odds' function might need adjustments for specific sports/leagues.")


def handle_analyze_bets(args):
    # Use EV threshold from args if provided, otherwise from config, else fallback to a hardcoded default
    ev_threshold_to_use = args.ev_threshold 
    
    # Check if the ev_threshold from args is the argparse default.
    # We need to know what that default was. Let's assume it was 0.05 as per previous setup.
    # A more robust way is to store the default in parser_analyze.get_default('ev_threshold')
    # but that's slightly more complex to access here.
    # For now, we check if it's the known default and if APP_CONFIG has a value.
    
    # Get the default from config, with a fallback if not set in config.
    config_default_ev = APP_CONFIG.get('analysis', {}).get('default_ev_threshold', 0.05)

    # If the args.ev_threshold is still the argparse default (0.05 given in setup),
    # and config has a different value, prefer config.
    # This logic implies: CLI arg > config value > argparse default
    # The setup for parser_analyze.add_argument should ideally set its default from config directly.
    # Let's adjust that later. For now, this logic will be:
    # If user did not specify --ev-threshold, args.ev_threshold will be the default set in add_argument.
    # We want that default to be the one from config.
    # The current args.ev_threshold *is* the value to use, as argparse handles CLI override of default.
    
    print(f"Analyzing example bets with EV threshold: {ev_threshold_to_use:.2f}")
    print("Using predefined example event data and user-estimated probabilities.")
    
    # For this example, we use the predefined EXAMPLE_EVENT_DATA and USER_ESTIMATED_PROBS_EXAMPLE
    # In a real application, event_data might come from the fetch_data command or a local cache.
    # User_estimated_probabilities might be loaded from a file, a model, or user input.

    value_bets = value_calculator.find_value_bets_for_event(
        event_data=EXAMPLE_EVENT_DATA,
        user_estimated_probabilities=USER_ESTIMATED_PROBS_EXAMPLE,
        value_threshold=ev_threshold_to_use
    )

    if value_bets:
        print(f"\nFound {len(value_bets)} value bets:")
        for bet in value_bets:
            print("--------------------------------------------------")
            print(f"  Event: {bet['home_team']} vs {bet['away_team']} (ID: {bet['event_id']})")
            print(f"  Bookmaker: {bet['bookmaker']}")
            print(f"  Market: {bet['market_key']}")
            print(f"  Outcome: {bet['outcome_name']}")
            print(f"  Odds: {bet['decimal_odds']:.2f}")
            print(f"  Your Estimated True Probability: {bet['estimated_true_probability']:.2%}")
            print(f"  Calculated Expected Value (EV): {bet['expected_value']:.3f}")
        print("--------------------------------------------------")
    else:
        print("\nNo value bets found matching the criteria with the example data.")

# --- Main CLI Logic ---
def main():
    parser = argparse.ArgumentParser(description="Sports Betting Analysis CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    # Subparser for the fetch-data command
    parser_fetch = subparsers.add_parser('fetch-data', help='Simulates fetching sports odds data.')
    parser_fetch.set_defaults(func=handle_fetch_data)
    # Add arguments for fetch-data if needed in future, e.g.:
    # parser_fetch.add_argument('--sport', type=str, default='soccer_epl', help='Sport key to fetch (e.g., soccer_epl)')

    # Subparser for the analyze-bets command
    parser_analyze = subparsers.add_parser('analyze-bets', help='Analyzes example bets to find value.')
    
    # Get default EV threshold from config, with a fallback for add_argument
    default_ev_from_config = APP_CONFIG.get('analysis', {}).get('default_ev_threshold', 0.05)
    
    parser_analyze.add_argument(
        '--ev-threshold', 
        type=float, 
        default=default_ev_from_config, 
        help=f'Minimum Expected Value (EV) to consider a bet valuable (e.g., {default_ev_from_config:.2f} from config).'
    )
    parser_analyze.set_defaults(func=handle_analyze_bets)

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
