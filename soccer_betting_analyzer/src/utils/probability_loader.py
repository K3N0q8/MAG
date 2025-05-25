import json
import os # Added for os.remove in __main__
from typing import Dict, List, Optional, Any

def load_probabilities_from_file(filepath: str) -> Optional[Dict[str, Dict[str, float]]]:
    """
    Loads user-defined probabilities from a JSON file.

    The file should contain a list of objects, each with "event_id" and "probabilities"
    (a dict of outcome_name: probability).

    Args:
        filepath: Path to the JSON file.

    Returns:
        A dictionary mapping event_id to its probabilities object, 
        or None if loading/parsing fails or format is incorrect.
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Probability file not found at {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from probability file {filepath}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while reading {filepath}: {e}")
        return None

    if not isinstance(data, list):
        print(f"Error: Probability file content should be a list of events. Found: {type(data)}")
        return None

    probabilities_map = {}
    for item in data:
        if not isinstance(item, dict):
            print(f"Warning: Skipping item, expected a dictionary, got {type(item)}: {item}")
            continue
        
        event_id = item.get('event_id')
        event_probs = item.get('probabilities')
        home_team = item.get('home_team', 'N/A') # Optional for error message

        if not event_id or not isinstance(event_id, str):
            print(f"Warning: Skipping item due to missing or invalid 'event_id': {item}")
            continue
        
        if not isinstance(event_probs, dict):
            print(f"Warning: Skipping event '{event_id}' ({home_team}) due to missing or invalid 'probabilities' field.")
            continue

        # Validate probabilities
        valid_probs_for_event = {}
        prob_sum = 0.0
        for outcome, prob in event_probs.items():
            if not isinstance(prob, (float, int)) or not (0.0 <= prob <= 1.0):
                print(f"Warning: Invalid probability value for outcome '{outcome}' in event '{event_id}'. Skipping outcome.")
                continue
            valid_probs_for_event[outcome] = float(prob)
            prob_sum += float(prob)
        
        # Optional: Check if probabilities for an event sum to ~1.0
        # This is a soft check; user is responsible for coherent probabilities.
        if not (0.98 < prob_sum < 1.02): # Allowing for slight float inaccuracies
             print(f"Warning: Probabilities for event '{event_id}' ({home_team}) sum to {prob_sum:.3f}, not close to 1.0. Using as is.")

        if not valid_probs_for_event:
            print(f"Warning: No valid probabilities found for event '{event_id}' ({home_team}). Skipping event.")
            continue
            
        probabilities_map[event_id] = valid_probs_for_event
    
    if not probabilities_map:
        print("No valid probability data loaded from file.")
        return None # Or return {} if preferred for "empty but valid" result

    return probabilities_map

if __name__ == '__main__':
    # Create a dummy user_probabilities.json for testing
    dummy_filepath = 'dummy_user_probabilities.json'
    dummy_data = [
        {
            "event_id": "event123",
            "home_team": "Team A",
            "away_team": "Team B",
            "probabilities": {"Team A": 0.5, "Draw": 0.3, "Team B": 0.2}
        },
        {
            "event_id": "event456",
            "home_team": "Team C",
            "away_team": "Team D",
            "probabilities": {"Team C": 0.4, "Draw": 0.25, "Team D": 0.35}
        },
        { # Item with an invalid probability value
            "event_id": "event789",
            "home_team": "Team E",
            "away_team": "Team F",
            "probabilities": {"Team E": 1.5, "Draw": 0.2, "Team F": -0.1} # Invalid
        },
        { # Item with probabilities not summing to 1
            "event_id": "event101",
            "home_team": "Team G",
            "away_team": "Team H",
            "probabilities": {"Team G": 0.3, "Draw": 0.3, "Team H": 0.3} # Sums to 0.9
        },
        { # Item missing event_id
             "home_team": "Team I", "away_team": "Team J",
             "probabilities": {"Team I": 0.6, "Draw": 0.2, "Team J": 0.2}
        }
    ]
    with open(dummy_filepath, 'w') as f:
        json.dump(dummy_data, f, indent=2)

    print(f"Attempting to load probabilities from {dummy_filepath}...")
    loaded_map = load_probabilities_from_file(dummy_filepath)

    if loaded_map:
        print("\nSuccessfully loaded probabilities map:")
        for event_id, probs in loaded_map.items():
            print(f"  Event ID: {event_id}, Probabilities: {probs}")
    else:
        print("\nFailed to load probabilities map or file contained no valid data.")
    
    # Clean up dummy file
    os.remove(dummy_filepath)
