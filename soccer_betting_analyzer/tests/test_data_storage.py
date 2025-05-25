import unittest
import os
import sys
import json
import tempfile
import datetime # Keep for creating actual datetime objects for comparison
from unittest.mock import patch, MagicMock

# Add src to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

from utils import data_storage

class TestDataStorage(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for cache files
        self.test_dir_obj = tempfile.TemporaryDirectory() # Store the object
        self.mock_base_path = self.test_dir_obj.name
    
    def tearDown(self):
        # Clean up the temporary directory
        self.test_dir_obj.cleanup()

    def test_get_cache_filepath(self):
        sport_key = "soccer_epl"
        regions = "uk,eu"
        markets = "h2h,totals"
        
        filepath = data_storage.get_cache_filepath(sport_key, regions, markets, self.mock_base_path)
        
        self.assertTrue(filepath.startswith(self.mock_base_path))
        self.assertIn("soccer-epl_uk_eu_h2h_totals", filepath)
        self.assertIn(datetime.date.today().isoformat(), filepath)
        self.assertTrue(filepath.endswith(".json"))
        
        # Check directory creation
        self.assertTrue(os.path.exists(self.mock_base_path))
        
        # Test with a nested base_path that doesn't exist yet
        nested_base_path = os.path.join(self.mock_base_path, "level1", "level2")
        filepath_nested = data_storage.get_cache_filepath(sport_key, regions, markets, nested_base_path)
        self.assertTrue(os.path.exists(nested_base_path)) # Check if directory was created

    def test_save_and_load_data_success(self):
        filepath = os.path.join(self.mock_base_path, "test_data.json")
        test_data = {"key": "value", "numbers": [1, 2, 3]}
        
        data_storage.save_data(test_data, filepath)
        self.assertTrue(os.path.exists(filepath))
        
        loaded_data = data_storage.load_data(filepath)
        self.assertEqual(loaded_data, test_data)

    def test_load_non_existent_file(self):
        filepath = os.path.join(self.mock_base_path, "non_existent.json")
        loaded_data = data_storage.load_data(filepath)
        self.assertIsNone(loaded_data)

    def test_load_corrupted_json_file(self):
        filepath = os.path.join(self.mock_base_path, "corrupted.json")
        with open(filepath, 'w') as f:
            f.write("this is not json {")
        
        loaded_data = data_storage.load_data(filepath)
        self.assertIsNone(loaded_data) # Expect None due to parsing error

    @patch('utils.data_storage.os.path.getmtime')
    @patch('utils.data_storage.datetime') # Mocking datetime module used inside data_storage
    def test_load_data_freshness(self, mock_datetime_module, mock_getmtime):
        filepath = os.path.join(self.mock_base_path, "fresh_test.json")
        test_data = {"status": "fresh"}
        data_storage.save_data(test_data, filepath)

        # --- Test 1: Data is fresh ---
        # Simulate file modification time: 30 minutes ago
        # Simulate current time: now
        mock_now = datetime.datetime(2023, 1, 1, 12, 0, 0) # Fixed "now"
        mock_file_mod_time_timestamp = (mock_now - datetime.timedelta(minutes=30)).timestamp()
        
        mock_getmtime.return_value = mock_file_mod_time_timestamp
        mock_datetime_module.datetime.now.return_value = mock_now
        # When fromtimestamp is called, ensure it returns a datetime object
        mock_datetime_module.datetime.fromtimestamp = datetime.datetime.fromtimestamp 

        freshness_hours = 1 # 1 hour
        loaded_data = data_storage.load_data(filepath, freshness_hours=freshness_hours)
        self.assertEqual(loaded_data, test_data, "Should load fresh data.")

        # --- Test 2: Data is stale ---
        # Simulate file modification time: 2 hours ago
        mock_file_mod_time_stale_timestamp = (mock_now - datetime.timedelta(hours=2)).timestamp()
        mock_getmtime.return_value = mock_file_mod_time_stale_timestamp
        # mock_datetime_module.datetime.now is still mock_now

        loaded_data_stale = data_storage.load_data(filepath, freshness_hours=freshness_hours)
        self.assertIsNone(loaded_data_stale, "Should not load stale data, should return None.")

        # --- Test 3: Freshness not specified (should load) ---
        loaded_data_no_freshness = data_storage.load_data(filepath) # freshness_hours is None
        self.assertEqual(loaded_data_no_freshness, test_data, "Should load data if freshness is not specified.")

    @patch('utils.data_storage.os.path.getmtime', side_effect=Exception("Test getmtime error"))
    def test_load_data_getmtime_exception(self, mock_getmtime_exc):
        filepath = os.path.join(self.mock_base_path, "getmtime_exc.json")
        test_data = {"data": "some"}
        data_storage.save_data(test_data, filepath)

        # If freshness_hours is provided, and getmtime fails, it should be treated as stale/error
        loaded_data = data_storage.load_data(filepath, freshness_hours=1)
        self.assertIsNone(loaded_data, "Should return None if getmtime raises an exception and freshness is checked.")


if __name__ == '__main__':
    unittest.main()
