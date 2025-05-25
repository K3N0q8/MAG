import unittest
import os
import sys
import json
import tempfile

# Add src to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

from utils import probability_loader

class TestProbabilityLoader(unittest.TestCase):

    def setUp(self):
        # Create a temporary file for dummy probability data
        # self.temp_file will be an object, use self.temp_file.name for the path
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_filepath = self.temp_file.name

    def tearDown(self):
        # Ensure the file is closed before attempting to delete
        self.temp_file.close() 
        if os.path.exists(self.temp_filepath):
            os.remove(self.temp_filepath)

    def write_json_to_temp_file(self, data):
        # Helper to write data to the temp file and re-open for reading by loader
        self.temp_file.seek(0) # Go to beginning
        self.temp_file.truncate() # Clear existing content
        json.dump(data, self.temp_file)
        self.temp_file.flush() # Ensure data is written to disk
        # The file needs to be closed for probability_loader to open it on some OS,
        # but NamedTemporaryFile handles this if delete=False.
        # If issues, may need to close and use self.temp_filepath directly.

    def test_load_valid_probabilities(self):
        valid_data = [
            {
                "event_id": "event1", 
                "home_team": "Team A", "away_team": "Team B",
                "probabilities": {"Team A": 0.5, "Draw": 0.3, "Team B": 0.2}
            },
            {
                "event_id": "event2", 
                "home_team": "Team C", "away_team": "Team D",
                "probabilities": {"Team C": 0.4, "Draw": 0.25, "Team D": 0.35}
            }
        ]
        self.write_json_to_temp_file(valid_data)
        
        loaded_map = probability_loader.load_probabilities_from_file(self.temp_filepath)
        
        self.assertIsNotNone(loaded_map)
        self.assertEqual(len(loaded_map), 2)
        self.assertIn("event1", loaded_map)
        self.assertEqual(loaded_map["event1"]["Team A"], 0.5)
        self.assertIn("event2", loaded_map)
        self.assertEqual(loaded_map["event2"]["Team D"], 0.35)

    def test_file_not_found(self):
        non_existent_filepath = os.path.join(os.path.dirname(self.temp_filepath), "does_not_exist.json")
        loaded_map = probability_loader.load_probabilities_from_file(non_existent_filepath)
        self.assertIsNone(loaded_map)

    def test_invalid_json_format(self):
        with open(self.temp_filepath, 'w') as f: # Open directly to write invalid JSON
            f.write("this is not json {")
        
        loaded_map = probability_loader.load_probabilities_from_file(self.temp_filepath)
        self.assertIsNone(loaded_map)

    def test_incorrect_data_structure_not_a_list(self):
        self.write_json_to_temp_file({"event_id": "event1", "probabilities": {}}) # Dict instead of list
        loaded_map = probability_loader.load_probabilities_from_file(self.temp_filepath)
        self.assertIsNone(loaded_map) # Expect None as per function's error handling

    def test_incorrect_data_structure_item_not_dict(self):
        self.write_json_to_temp_file(["string_instead_of_dict"])
        loaded_map = probability_loader.load_probabilities_from_file(self.temp_filepath)
        self.assertIsNone(loaded_map) # Should skip the invalid item and return None if no valid items

    def test_missing_event_id(self):
        data = [{"probabilities": {"Team A": 0.5}}] # Missing event_id
        self.write_json_to_temp_file(data)
        loaded_map = probability_loader.load_probabilities_from_file(self.temp_filepath)
        self.assertIsNone(loaded_map) # Or empty dict {} if that's the chosen behavior for no valid items

    def test_missing_probabilities_field(self):
        data = [{"event_id": "event1"}] # Missing probabilities field
        self.write_json_to_temp_file(data)
        loaded_map = probability_loader.load_probabilities_from_file(self.temp_filepath)
        self.assertIsNone(loaded_map)

    def test_invalid_probability_values(self):
        data = [{
            "event_id": "event1",
            "probabilities": {"Team A": 1.5, "Draw": 0.2, "Team B": -0.1} # Invalid values
        }]
        self.write_json_to_temp_file(data)
        loaded_map = probability_loader.load_probabilities_from_file(self.temp_filepath)
        # The function prints warnings and skips invalid outcomes.
        # If all outcomes for an event are invalid, the event itself might be skipped.
        # If an event has some valid and some invalid, it might load the valid ones.
        # Based on current implementation, invalid values are skipped, if no valid outcomes left, event is skipped.
        self.assertIsNone(loaded_map, "Should be None as all outcomes for event1 are invalid, so event1 is skipped")

        data_mixed = [{ # event_valid has one valid outcome
            "event_id": "event_valid", "probabilities": {"Team A": 0.5, "Team B": 1.2}
        },{ # event_all_invalid has all invalid
            "event_id": "event_all_invalid", "probabilities": {"Team C": -0.1, "Team D": "bad"}
        }]
        self.write_json_to_temp_file(data_mixed)
        loaded_map_mixed = probability_loader.load_probabilities_from_file(self.temp_filepath)
        self.assertIsNotNone(loaded_map_mixed)
        self.assertIn("event_valid", loaded_map_mixed)
        self.assertNotIn("Team B", loaded_map_mixed["event_valid"]) # Invalid outcome skipped
        self.assertEqual(loaded_map_mixed["event_valid"]["Team A"], 0.5)
        self.assertNotIn("event_all_invalid", loaded_map_mixed)


    def test_probabilities_not_summing_to_one(self):
        # The function currently prints a warning but loads the data.
        data = [{
            "event_id": "event_sum_low",
            "probabilities": {"Team A": 0.3, "Draw": 0.3, "Team B": 0.3} # Sums to 0.9
        }]
        self.write_json_to_temp_file(data)
        loaded_map = probability_loader.load_probabilities_from_file(self.temp_filepath)
        self.assertIsNotNone(loaded_map)
        self.assertIn("event_sum_low", loaded_map)
        self.assertEqual(loaded_map["event_sum_low"]["Team A"], 0.3) # Data should be loaded

    def test_empty_file(self):
        self.write_json_to_temp_file([]) # Empty list
        loaded_map = probability_loader.load_probabilities_from_file(self.temp_filepath)
        self.assertIsNone(loaded_map) # No valid probability entries

    def test_file_with_no_valid_entries(self):
        data = [
            {"event_id": None, "probabilities": {"A": 0.5}}, # Invalid event_id
            {"event_id": "ev2", "probabilities": "not_a_dict"} # Invalid probabilities structure
        ]
        self.write_json_to_temp_file(data)
        loaded_map = probability_loader.load_probabilities_from_file(self.temp_filepath)
        self.assertIsNone(loaded_map)

if __name__ == '__main__':
    unittest.main()
