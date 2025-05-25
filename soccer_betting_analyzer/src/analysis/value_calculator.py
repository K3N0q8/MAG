from typing import List, Dict, Any

def calculate_implied_probability(decimal_odds: float) -> float:
    """
    Calculates the implied probability from decimal odds.
    Accounts for the bookmaker's margin by not normalizing probabilities here.
    Normalization should be handled if comparing multiple outcomes of the same event.

    Args:
        decimal_odds: The decimal odds offered by the bookmaker.

    Returns:
        The implied probability (e.g., 0.5 for odds of 2.00).
        Returns 0 if odds are invalid (less than 1.0).
    """
    if decimal_odds < 1.0:
        return 0.0  # Odds cannot be less than 1.0
    return 1 / decimal_odds

def calculate_expected_value(decimal_odds: float, true_probability: float) -> float:
    """
    Calculates the Expected Value (EV) of a bet.

    Args:
        decimal_odds: The decimal odds offered by the bookmaker.
        true_probability: The estimated true probability of the outcome occurring (0.0 to 1.0).

    Returns:
        The Expected Value. For example, an EV of 0.05 means a 5% expected return on investment.
    """
    if decimal_odds < 1.0 or not (0.0 <= true_probability <= 1.0):
        # Invalid input, though true_probability could be 0 if an outcome is deemed impossible.
        # Odds < 1.0 is definitively invalid.
        return -1.0 # Or raise an error, returning -1 indicates a bad bet / input error

    return (decimal_odds * true_probability) - 1

def simple_market_average_probability(bookmaker_odds_list: List[Dict[str, Any]], outcome_name: str) -> float:
    """
    Estimates 'true' probability by averaging implied probabilities from multiple bookmakers for a specific outcome.
    This is a simplistic model and doesn't remove bookmaker margins explicitly,
    but averaging can sometimes get closer to true odds if some bookies are sharper than others
    or if it helps dilute individual vigs. A more advanced model would remove the overround.

    Args:
        bookmaker_odds_list: A list of bookmaker data dictionaries. Each dictionary
                            should have a 'markets' key, which is a list of markets.
                            Each market should have an 'outcomes' key, which is a list
                            of outcome dictionaries, each with 'name' and 'price'.
                            Assumes 'h2h' (Head-to-Head) market for now.
        outcome_name: The name of the outcome to calculate average probability for (e.g., "Arsenal", "Draw").

    Returns:
        The average implied probability for the given outcome, or 0.0 if not found or no odds available.
    """
    probabilities = []
    for bookmaker_data in bookmaker_odds_list:
        for market in bookmaker_data.get('markets', []):
            # Assuming we are interested in the 'h2h' market for soccer (Home Win, Away Win, Draw)
            if market.get('key') == 'h2h':
                for outcome in market.get('outcomes', []):
                    if outcome.get('name') == outcome_name:
                        price = outcome.get('price')
                        if isinstance(price, (int, float)) and price >= 1.0:
                            probabilities.append(calculate_implied_probability(float(price)))
    
    if not probabilities:
        return 0.0
    return sum(probabilities) / len(probabilities)

# Example of how this might be used with data from the_odds_api.py
# This function would typically be called from a higher-level analysis script.
def find_value_bets_for_event(event_data: Dict[str, Any], user_estimated_probabilities: Dict[str, float], value_threshold: float = 0.0) -> List[Dict[str, Any]]:
    """
    Identifies value bets for a single event by comparing bookmaker odds against user-estimated true probabilities.

    Args:
        event_data: A dictionary representing a single sporting event, including bookmaker odds.
                    Expected structure similar to The Odds API response for an event.
                    Example: {
                        "home_team": "Team A", "away_team": "Team B",
                        "bookmakers": [{"key": "bookie1", "markets": [...]}, ...]
                    }
        user_estimated_probabilities: A dictionary where keys are outcome names (e.g., event_data['home_team'], 
                                        event_data['away_team'], "Draw") and values are their estimated true probabilities.
        value_threshold: The minimum EV to consider a bet as a "value bet". Defaults to 0.0 (any positive EV).

    Returns:
        A list of dictionaries, where each dictionary represents a value bet and includes
        details like team, outcome, odds, estimated probability, and EV.
    """
    value_bets = []
    home_team = event_data.get('home_team')
    away_team = event_data.get('away_team')

    # Define outcomes we are interested in for H2H soccer
    possible_outcomes = [home_team, away_team, "Draw"]

    for bookmaker in event_data.get('bookmakers', []):
        for market in bookmaker.get('markets', []):
            if market.get('key') == 'h2h': # Focus on H2H market
                for outcome_details in market.get('outcomes', []):
                    outcome_name = outcome_details.get('name')
                    decimal_odds = outcome_details.get('price')

                    if not (outcome_name and isinstance(decimal_odds, (int, float)) and decimal_odds >= 1.0):
                        continue

                    # Check if this outcome is one we have a probability for
                    # (e.g. home_team name, away_team name, or "Draw")
                    # This mapping might need to be more robust if team names vary slightly
                    true_probability_key = None
                    if outcome_name == home_team:
                        true_probability_key = home_team
                    elif outcome_name == away_team:
                        true_probability_key = away_team
                    elif outcome_name == "Draw": # Assuming "Draw" is the standard name
                        true_probability_key = "Draw"
                    
                    if true_probability_key and true_probability_key in user_estimated_probabilities:
                        true_prob = user_estimated_probabilities[true_probability_key]
                        ev = calculate_expected_value(float(decimal_odds), true_prob)

                        if ev > value_threshold:
                            value_bets.append({
                                "event_id": event_data.get('id'),
                                "home_team": home_team,
                                "away_team": away_team,
                                "bookmaker": bookmaker.get('title'),
                                "market_key": market.get('key'),
                                "outcome_name": outcome_name,
                                "decimal_odds": float(decimal_odds),
                                "estimated_true_probability": true_prob,
                                "expected_value": ev
                            })
    return value_bets

if __name__ == '__main__':
    # Example Usage
    print("Value Calculator Module Examples:")

    # 1. Implied Probability
    odds1 = 2.00
    imp_prob1 = calculate_implied_probability(odds1)
    print(f"Implied probability for odds {odds1}: {imp_prob1:.4f} (Bookmaker's probability)")

    odds2 = 1.50
    imp_prob2 = calculate_implied_probability(odds2)
    print(f"Implied probability for odds {odds2}: {imp_prob2:.4f} (Bookmaker's probability)")
    
    odds_invalid = 0.9
    imp_prob_invalid = calculate_implied_probability(odds_invalid)
    print(f"Implied probability for odds {odds_invalid}: {imp_prob_invalid} (Invalid odds)")

    # 2. Expected Value
    my_prob = 0.55  # My 'true' probability for the outcome with odds1 (2.00)
    ev = calculate_expected_value(odds1, my_prob)
    print(f"Expected Value for odds {odds1} if true probability is {my_prob}: {ev:.4f}")
    # If EV > 0, it's considered a value bet.

    my_prob_bad_bet = 0.45 # My 'true' probability for outcome with odds1 (2.00)
    ev_bad = calculate_expected_value(odds1, my_prob_bad_bet)
    print(f"Expected Value for odds {odds1} if true probability is {my_prob_bad_bet}: {ev_bad:.4f}")

    # 3. Simple Market Average Probability (Example Data)
    example_bookmaker_odds = [
        {"key": "bookieA", "title": "Bookie A", "markets": [{"key": "h2h", "outcomes": [{"name": "Team X", "price": 2.0}, {"name": "Team Y", "price": 3.0}, {"name": "Draw", "price": 3.2}]}]},
        {"key": "bookieB", "title": "Bookie B", "markets": [{"key": "h2h", "outcomes": [{"name": "Team X", "price": 2.1}, {"name": "Team Y", "price": 2.9}, {"name": "Draw", "price": 3.1}]}]},
        {"key": "bookieC", "title": "Bookie C", "markets": [{"key": "h2h", "outcomes": [{"name": "Team X", "price": 1.9}, {"name": "Team Y", "price": 3.1}, {"name": "Draw", "price": 3.3}]}]}
    ]
    avg_prob_team_x = simple_market_average_probability(example_bookmaker_odds, "Team X")
    print(f"Simple market average implied probability for Team X: {avg_prob_team_x:.4f}")
    
    # 4. Find Value Bets for an Event (Example Data)
    example_event = {
        "id": "testevent001",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "bookmakers": [
            {"key": "unibet", "title": "Unibet", "markets": [{"key": "h2h", "outcomes": [
                {"name": "Arsenal", "price": 2.5}, {"name": "Chelsea", "price": 3.0}, {"name": "Draw", "price": 3.2}
            ]}]},
            {"key": "williamhill", "title": "William Hill", "markets": [{"key": "h2h", "outcomes": [
                {"name": "Arsenal", "price": 2.6}, {"name": "Chelsea", "price": 2.9}, {"name": "Draw", "price": 3.1}
            ]}]}
        ]
    }
    # User's own estimated probabilities for the outcomes
    # These would ideally come from a more sophisticated model or research
    user_probs_for_event = {
        "Arsenal": 0.42,  # User believes Arsenal has a 42% chance of winning
        "Chelsea": 0.30,  # User believes Chelsea has a 30% chance of winning
        "Draw": 0.28     # User believes Draw has a 28% chance
    }
    # Check: sum of user_probs should be close to 1.0 (0.42 + 0.30 + 0.28 = 1.00)

    value_bets_found = find_value_bets_for_event(example_event, user_probs_for_event, value_threshold=0.05) # EV > 5%
    if value_bets_found:
        print(f"\nFound {len(value_bets_found)} value bets with EV > 0.05:")
        for bet in value_bets_found:
            print(f"  - Event: {bet['home_team']} vs {bet['away_team']}")
            print(f"    Outcome: {bet['outcome_name']} with {bet['bookmaker']} at odds {bet['decimal_odds']}")
            print(f"    Estimated True Probability: {bet['estimated_true_probability']:.2%}, EV: {bet['expected_value']:.3f}")
    else:
        print("\nNo value bets found with EV > 0.05 for the example event.")
