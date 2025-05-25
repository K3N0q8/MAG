import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add src to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

from data_acquisition import the_odds_api

class TestTheOddsApi(unittest.TestCase):

    VALID_API_KEY = "test_api_key_valid"
    PLACEHOLDER_API_KEY = "YOUR_API_KEY_HERE" # As in settings.yaml
    SPORT_KEY_VALID = "soccer_epl"
    REGIONS_VALID = "uk"
    MARKETS_VALID = "h2h"

    def create_mock_response(self, status_code, json_data=None, text_data=None, raise_for_status_effect=None):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        if json_data is not None:
            mock_resp.json.return_value = json_data
        mock_resp.text = text_data if text_data is not None else json.dumps(json_data) if json_data else ""
        
        if raise_for_status_effect:
            mock_resp.raise_for_status.side_effect = raise_for_status_effect
        else:
            if status_code >= 400: # Simulate raise_for_status for error codes if not specifically handled
                 mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(f"Mock HTTP Error {status_code}")
            else:
                mock_resp.raise_for_status.return_value = None
        return mock_resp

    # --- Tests for get_odds ---
    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_odds_success(self, mock_requests_get):
        mock_response_data = [{"id": "event1"}, {"id": "event2"}]
        mock_requests_get.return_value = self.create_mock_response(200, json_data=mock_response_data)
        
        result = the_odds_api.get_odds(self.VALID_API_KEY, self.SPORT_KEY_VALID, self.REGIONS_VALID, self.MARKETS_VALID)
        self.assertEqual(result, mock_response_data)
        mock_requests_get.assert_called_once()

    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_odds_empty_list(self, mock_requests_get):
        mock_requests_get.return_value = self.create_mock_response(200, json_data=[])
        result = the_odds_api.get_odds(self.VALID_API_KEY, self.SPORT_KEY_VALID)
        self.assertEqual(result, [])

    def test_get_odds_missing_api_key(self):
        result = the_odds_api.get_odds(None, self.SPORT_KEY_VALID)
        self.assertIsNone(result)
        result_placeholder = the_odds_api.get_odds(self.PLACEHOLDER_API_KEY, self.SPORT_KEY_VALID)
        self.assertIsNone(result_placeholder)

    def test_get_odds_missing_sport_key(self):
        result = the_odds_api.get_odds(self.VALID_API_KEY, None)
        self.assertIsNone(result)
        result_empty_sport = the_odds_api.get_odds(self.VALID_API_KEY, "")
        self.assertIsNone(result_empty_sport)

    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_odds_http_401_unauthorized(self, mock_requests_get):
        mock_requests_get.return_value = self.create_mock_response(401, text_data="Unauthorized")
        result = the_odds_api.get_odds(self.VALID_API_KEY, self.SPORT_KEY_VALID)
        self.assertIsNone(result)

    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_odds_http_404_not_found(self, mock_requests_get):
        mock_requests_get.return_value = self.create_mock_response(404, text_data="Not Found")
        result = the_odds_api.get_odds(self.VALID_API_KEY, "invalid_sport_key")
        self.assertIsNone(result)

    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_odds_http_429_too_many_requests(self, mock_requests_get):
        mock_requests_get.return_value = self.create_mock_response(429, text_data="Too Many Requests")
        result = the_odds_api.get_odds(self.VALID_API_KEY, self.SPORT_KEY_VALID)
        self.assertIsNone(result)

    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_odds_other_http_error(self, mock_requests_get):
        # Test a generic HTTP error not specifically handled by 401/404/429 checks
        mock_requests_get.return_value = self.create_mock_response(500, text_data="Server Error", raise_for_status_effect=requests.exceptions.HTTPError("Server Error"))
        result = the_odds_api.get_odds(self.VALID_API_KEY, self.SPORT_KEY_VALID)
        self.assertIsNone(result)

    @patch('data_acquisition.the_odds_api.requests.get', side_effect=requests.exceptions.RequestException("Network Error"))
    def test_get_odds_request_exception(self, mock_requests_get):
        result = the_odds_api.get_odds(self.VALID_API_KEY, self.SPORT_KEY_VALID)
        self.assertIsNone(result)

    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_odds_json_decode_error(self, mock_requests_get):
        mock_requests_get.return_value = self.create_mock_response(200, text_data="invalid json")
        # Make json.loads raise JSONDecodeError
        mock_requests_get.return_value.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        result = the_odds_api.get_odds(self.VALID_API_KEY, self.SPORT_KEY_VALID)
        self.assertIsNone(result)

    # --- Tests for get_available_sports ---
    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_available_sports_success(self, mock_requests_get):
        mock_response_data = [{"key": "soccer_epl", "title": "English Premier League"}]
        mock_requests_get.return_value = self.create_mock_response(200, json_data=mock_response_data)
        
        result = the_odds_api.get_available_sports(self.VALID_API_KEY)
        self.assertEqual(result, mock_response_data)
        mock_requests_get.assert_called_once()

    def test_get_available_sports_missing_api_key(self):
        result = the_odds_api.get_available_sports(None)
        self.assertIsNone(result)
        result_placeholder = the_odds_api.get_available_sports(self.PLACEHOLDER_API_KEY)
        self.assertIsNone(result_placeholder)

    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_available_sports_http_401(self, mock_requests_get):
        mock_requests_get.return_value = self.create_mock_response(401, text_data="Unauthorized")
        result = the_odds_api.get_available_sports(self.VALID_API_KEY)
        self.assertIsNone(result)

    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_available_sports_http_429(self, mock_requests_get):
        mock_requests_get.return_value = self.create_mock_response(429, text_data="Too Many Requests")
        result = the_odds_api.get_available_sports(self.VALID_API_KEY)
        self.assertIsNone(result)

    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_available_sports_other_http_error(self, mock_requests_get):
        mock_requests_get.return_value = self.create_mock_response(503, text_data="Service Unavailable", raise_for_status_effect=requests.exceptions.HTTPError("Service Unavailable"))
        result = the_odds_api.get_available_sports(self.VALID_API_KEY)
        self.assertIsNone(result)

    @patch('data_acquisition.the_odds_api.requests.get', side_effect=requests.exceptions.Timeout("Timeout Error"))
    def test_get_available_sports_request_exception(self, mock_requests_get):
        result = the_odds_api.get_available_sports(self.VALID_API_KEY)
        self.assertIsNone(result)

    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_available_sports_json_decode_error(self, mock_requests_get):
        mock_requests_get.return_value = self.create_mock_response(200, text_data="not valid json")
        mock_requests_get.return_value.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        result = the_odds_api.get_available_sports(self.VALID_API_KEY)
        self.assertIsNone(result)

    @patch('data_acquisition.the_odds_api.requests.get')
    def test_get_available_sports_empty_list_from_api(self, mock_requests_get):
        mock_requests_get.return_value = self.create_mock_response(200, json_data=[])
        result = the_odds_api.get_available_sports(self.VALID_API_KEY)
        self.assertEqual(result, [])


if __name__ == '__main__':
    # Need to import requests here if create_mock_response uses requests.exceptions.HTTPError
    import requests 
    unittest.main()
