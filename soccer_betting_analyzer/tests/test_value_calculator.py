import unittest
import sys
import os

# Add src directory to Python path to allow direct import of modules
# This assumes tests are run from the project root or that PYTHONPATH is set up.
# For robust testing, consider using a test runner that handles paths, or packaging the app.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

from analysis import value_calculator # Now this import should work

class TestValueCalculator(unittest.TestCase):

    def test_calculate_implied_probability(self):
        self.assertAlmostEqual(value_calculator.calculate_implied_probability(2.00), 0.5)
        self.assertAlmostEqual(value_calculator.calculate_implied_probability(1.50), 1 / 1.50)
        self.assertAlmostEqual(value_calculator.calculate_implied_probability(4.00), 0.25)
        self.assertEqual(value_calculator.calculate_implied_probability(1.00), 1.0)
        # Test invalid odds
        self.assertEqual(value_calculator.calculate_implied_probability(0.5), 0.0)
        self.assertEqual(value_calculator.calculate_implied_probability(-1.0), 0.0)

    def test_calculate_expected_value(self):
        # Positive EV
        self.assertAlmostEqual(value_calculator.calculate_expected_value(decimal_odds=2.00, true_probability=0.55), 0.10) 
        # Negative EV
        self.assertAlmostEqual(value_calculator.calculate_expected_value(decimal_odds=2.00, true_probability=0.45), -0.10)
        # Zero EV
        self.assertAlmostEqual(value_calculator.calculate_expected_value(decimal_odds=2.00, true_probability=0.50), 0.0)
        # Edge cases for probability
        self.assertAlmostEqual(value_calculator.calculate_expected_value(decimal_odds=2.00, true_probability=1.0), 1.0) # If prob is 100%, EV = odds - 1
        self.assertAlmostEqual(value_calculator.calculate_expected_value(decimal_odds=2.00, true_probability=0.0), -1.0) # If prob is 0%, EV is -1
        # Invalid odds
        self.assertAlmostEqual(value_calculator.calculate_expected_value(decimal_odds=0.5, true_probability=0.5), -1.0) 

    def test_simple_market_average_probability(self):
        example_bookmaker_odds = [
            {"key": "bookieA", "title": "Bookie A", "markets": [{"key": "h2h", "outcomes": [{"name": "Team X", "price": 2.0}]}]}, # Implied: 0.5
            {"key": "bookieB", "title": "Bookie B", "markets": [{"key": "h2h", "outcomes": [{"name": "Team X", "price": 2.5}]}]}, # Implied: 0.4
            {"key": "bookieC", "title": "Bookie C", "markets": [{"key": "h2h", "outcomes": [{"name": "Team X", "price": 2.2}]}]}  # Implied: 1/2.2 = 0.4545...
        ]
        # Expected: (0.5 + 0.4 + 1/2.2) / 3
        expected_avg_prob = (0.5 + 0.4 + (1/2.2)) / 3
        self.assertAlmostEqual(value_calculator.simple_market_average_probability(example_bookmaker_odds, "Team X"), expected_avg_prob)
        
        # Test with no odds for the outcome
        self.assertEqual(value_calculator.simple_market_average_probability(example_bookmaker_odds, "Team Y"), 0.0)
        
        # Test with empty bookmaker list
        self.assertEqual(value_calculator.simple_market_average_probability([], "Team X"), 0.0)
        
        # Test with invalid price data
        example_invalid_odds = [
            {"key": "bookieD", "title": "Bookie D", "markets": [{"key": "h2h", "outcomes": [{"name": "Team X", "price": 0.8}]}]} # Invalid price
        ]
        self.assertEqual(value_calculator.simple_market_average_probability(example_invalid_odds, "Team X"), 0.0)


    def test_find_value_bets_for_event(self):
        example_event = {
           "id": "testevent001",
           "home_team": "Arsenal",
           "away_team": "Chelsea",
           "bookmakers": [
               {"key": "unibet", "title": "Unibet", "markets": [{"key": "h2h", "outcomes": [
                   {"name": "Arsenal", "price": 2.5}, {"name": "Chelsea", "price": 3.0}, {"name": "Draw", "price": 3.2}
               ]}]}, # Arsenal EV with 0.42 prob: (2.5*0.42)-1 = 0.05
               {"key": "williamhill", "title": "William Hill", "markets": [{"key": "h2h", "outcomes": [
                   {"name": "Arsenal", "price": 2.6}, {"name": "Chelsea", "price": 2.9}, {"name": "Draw", "price": 3.1}
               ]}]}  # Arsenal EV with 0.42 prob: (2.6*0.42)-1 = 0.092
           ]
        }
        user_probs_for_event = {
           "Arsenal": 0.42, 
           "Chelsea": 0.30, 
           "Draw": 0.28    
        }

        # Test with EV threshold 0.0 (any positive EV)
        value_bets = value_calculator.find_value_bets_for_event(example_event, user_probs_for_event, value_threshold=0.0)
        self.assertEqual(len(value_bets), 2) # Both Arsenal bets should be value
        # Check details of the first value bet (Unibet)
        self.assertEqual(value_bets[0]['outcome_name'], "Arsenal")
        self.assertEqual(value_bets[0]['bookmaker'], "Unibet")
        self.assertAlmostEqual(value_bets[0]['decimal_odds'], 2.5)
        self.assertAlmostEqual(value_bets[0]['expected_value'], 0.05)

        # Test with higher EV threshold 0.06
        value_bets_strict = value_calculator.find_value_bets_for_event(example_event, user_probs_for_event, value_threshold=0.06)
        self.assertEqual(len(value_bets_strict), 1)
        self.assertEqual(value_bets_strict[0]['outcome_name'], "Arsenal")
        self.assertEqual(value_bets_strict[0]['bookmaker'], "William Hill") # Only William Hill bet (EV 0.092)
        self.assertAlmostEqual(value_bets_strict[0]['expected_value'], 0.092)

        # Test with no value bets expected
        user_probs_no_value = {"Arsenal": 0.35, "Chelsea": 0.30, "Draw": 0.35} # Lowered Arsenal prob
        value_bets_none = value_calculator.find_value_bets_for_event(example_event, user_probs_no_value, value_threshold=0.0)
        self.assertEqual(len(value_bets_none), 0)
        
        # Test with an outcome name mismatch (e.g. "Team A" vs "Arsenal")
        # The current find_value_bets_for_event is sensitive to exact name matches.
        # This test confirms that behavior.
        example_event_name_mismatch = {
           "id": "testevent002",
           "home_team": "Team Alpha", # Name used in event_data
           "away_team": "Team Beta",
           "bookmakers": [
               {"key": "unibet", "title": "Unibet", "markets": [{"key": "h2h", "outcomes": [
                   {"name": "Team Alpha", "price": 2.5} # Odds for "Team Alpha"
               ]}]}
           ]
        }
        user_probs_different_name = {
           "Arsenal": 0.50, # User prob for "Arsenal", not "Team Alpha"
        }
        value_bets_mismatch = value_calculator.find_value_bets_for_event(example_event_name_mismatch, user_probs_different_name, value_threshold=0.0)
        self.assertEqual(len(value_bets_mismatch), 0, "Should not find value if outcome names in event data and prob dict don't match")

    def test_get_implied_probabilities_for_market(self):
        market_outcomes = [
            {"name": "Team A", "price": 2.00}, # 0.5
            {"name": "Draw", "price": 3.20},   # 0.3125
            {"name": "Team B", "price": 4.50}    # 0.2222...
        ]
        expected_probs = {
            "Team A": 0.5,
            "Draw": 1/3.20,
            "Team B": 1/4.50
        }
        implied_probs = value_calculator.get_implied_probabilities_for_market(market_outcomes)
        self.assertAlmostEqual(implied_probs["Team A"], expected_probs["Team A"])
        self.assertAlmostEqual(implied_probs["Draw"], expected_probs["Draw"])
        self.assertAlmostEqual(implied_probs["Team B"], expected_probs["Team B"])

        # Test with empty input list
        self.assertEqual(value_calculator.get_implied_probabilities_for_market([]), {})

        # Test with outcomes missing 'name' or 'price', or with invalid prices
        market_invalid = [
            {"name": "Team A", "price": 2.00},
            {"name": "Team B"}, # Missing price
            {"price": 3.00}, # Missing name
            {"name": "Team C", "price": 0.8} # Invalid price
        ]
        implied_invalid = value_calculator.get_implied_probabilities_for_market(market_invalid)
        self.assertIn("Team A", implied_invalid)
        self.assertEqual(len(implied_invalid), 1, "Only one valid outcome should be processed.")

    def test_remove_vig(self):
        # Typical H2H market with vig
        market_probs_with_vig = {"Team A": 0.5, "Draw": 0.3125, "Team B": 0.22222222} # Sum = 1.03472222
        sum_with_vig = sum(market_probs_with_vig.values())
        
        de_vigged = value_calculator.remove_vig(market_probs_with_vig)
        self.assertAlmostEqual(sum(de_vigged.values()), 1.0)
        self.assertAlmostEqual(de_vigged["Team A"], market_probs_with_vig["Team A"] / sum_with_vig)
        self.assertAlmostEqual(de_vigged["Draw"], market_probs_with_vig["Draw"] / sum_with_vig)
        self.assertAlmostEqual(de_vigged["Team B"], market_probs_with_vig["Team B"] / sum_with_vig)

        # Test with empty input
        self.assertEqual(value_calculator.remove_vig({}), {})

        # Test with probabilities already summing to 1.0
        market_probs_no_vig = {"Team A": 0.5, "Draw": 0.3, "Team B": 0.2} # Sum = 1.0
        de_vigged_no_vig = value_calculator.remove_vig(market_probs_no_vig)
        self.assertAlmostEqual(sum(de_vigged_no_vig.values()), 1.0)
        self.assertAlmostEqual(de_vigged_no_vig["Team A"], 0.5) # Should be effectively unchanged

        # Test with probabilities summing to a non-positive number (should return original or empty)
        # Based on current implementation, it prints a warning and returns original.
        market_probs_neg_sum = {"Team A": -0.5, "Team B": -0.2}
        de_vigged_neg_sum = value_calculator.remove_vig(market_probs_neg_sum)
        self.assertEqual(de_vigged_neg_sum, market_probs_neg_sum) 

        market_probs_zero_sum = {"Team A": 0.0, "Team B": 0.0}
        de_vigged_zero_sum = value_calculator.remove_vig(market_probs_zero_sum)
        self.assertEqual(de_vigged_zero_sum, market_probs_zero_sum)


if __name__ == '__main__':
    # This allows running the tests directly from the command line
    # You might need to be in the `soccer_betting_analyzer` root directory and run as `python tests/test_value_calculator.py`
    # or ensure `src` is in PYTHONPATH. The sys.path manipulation at the top helps with direct execution.
    unittest.main()
