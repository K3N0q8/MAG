import os
# For users who prefer .env files for managing credentials:
# from dotenv import load_dotenv
import oandapyV20
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.instruments as instruments_api
import oandapyV20.endpoints.pricing as pricing_api
from oandapyV20.exceptions import V20Error
import pandas as pd

def load_credentials():
    """
    Loads OANDA API key and Account ID from environment variables.

    Raises:
        EnvironmentError: If OANDA_API_KEY or OANDA_ACCOUNT_ID are not found.

    Returns:
        tuple: (api_key, account_id)
    """
    # Uncomment the next line if you are using a .env file
    # load_dotenv()

    api_key = os.getenv("OANDA_API_KEY")
    account_id = os.getenv("OANDA_ACCOUNT_ID")

    if not api_key:
        raise EnvironmentError("OANDA_API_KEY not found in environment variables.")
    if not account_id:
        raise EnvironmentError("OANDA_ACCOUNT_ID not found in environment variables.")

    return api_key, account_id

class OANDAConnector:
    """
    A class to connect to OANDA's v20 API and fetch data.
    """
    def __init__(self):
        """
        Initializes the OANDAConnector.
        Loads credentials and sets up the API client.
        """
        try:
            self.api_key, self.account_id = load_credentials()
            # Ensure environment is set correctly, e.g., "practice" or "live"
            # For demo accounts, "practice" is typically used.
            self.client = oandapyV20.API(access_token=self.api_key, environment="practice") 
        except EnvironmentError as e:
            print(f"Error initializing OANDAConnector: {e}")
            # Propagate the error or handle it as needed, e.g., by setting client to None
            self.client = None 
            self.account_id = None
        except V20Error as e:
            print(f"OANDA API Error during initialization: {e}")
            self.client = None
            self.account_id = None
        except Exception as e:
            print(f"An unexpected error occurred during initialization: {e}")
            self.client = None
            self.account_id = None


    def test_connection(self):
        """
        Tests the API connection by fetching account summary.

        Returns:
            bool: True if connection is successful, False otherwise.
        """
        if not self.client or not self.account_id:
            print("OANDA client not initialized. Cannot test connection.")
            return False

        r = accounts.AccountSummary(accountID=self.account_id)
        try:
            response = self.client.request(r)
            if response and 'account' in response and 'id' in response['account']:
                if response['account']['id'] == self.account_id:
                    print(f"Successfully connected to OANDA. Account ID: {response['account']['id']}")
                    return True
                else:
                    print(f"Connected to OANDA, but account ID mismatch. Expected: {self.account_id}, Got: {response['account']['id']}")
                    return False
            else:
                print(f"Failed to connect or retrieve valid account summary. Response: {response}")
                return False
        except V20Error as e:
            print(f"OANDA API Error while testing connection: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred while testing connection: {e}")
            return False

    def get_account_summary(self):
        """
        Fetches and prints the detailed account summary.

        Returns:
            dict: The account summary data from OANDA, or None if an error occurs.
        """
        if not self.client or not self.account_id:
            print("OANDA client not initialized. Cannot get account summary.")
            return None

        r = accounts.AccountSummary(accountID=self.account_id)
        try:
            response = self.client.request(r)
            account_summary = response.get('account')

            if account_summary:
                print("\n--- Account Summary ---")
                print(f"Account ID: {account_summary.get('id')}")
                print(f"Currency: {account_summary.get('currency')}")
                print(f"Balance: {account_summary.get('balance')}")
                print(f"Unrealized P/L: {account_summary.get('unrealizedPL')}")
                print(f"Realized P/L: {account_summary.get('pl')}") # 'pl' is often realized P/L
                print(f"Margin Used: {account_summary.get('marginUsed')}")
                print(f"Margin Available: {account_summary.get('marginAvailable')}")
                print(f"Open Trade Count: {account_summary.get('openTradeCount')}")
                print(f"NAV (Net Asset Value): {account_summary.get('NAV')}")
                print("-----------------------\n")
                return account_summary
            else:
                print("Could not retrieve account summary from response.")
                return None
        except V20Error as e:
            print(f"OANDA API Error in get_account_summary: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred in get_account_summary: {e}")
            return None

    def get_historical_data(self, instrument, params):
        """
        Fetches historical price data for an instrument and returns it as a pandas DataFrame.

        Args:
            instrument (str): The trading instrument (e.g., "EUR_USD").
            params (dict): Parameters for the API request (e.g., 
                           {"count": 100, "granularity": "H1", "price": "M"}).
                           'price': 'M' (Midpoint), 'B' (Bid), 'A' (Ask).

        Returns:
            pandas.DataFrame: A DataFrame containing candle data (time, open, high, low, close, volume),
                              or None if an error occurs or no data is fetched.
        """
        if not self.client:
            print("OANDA client not initialized. Cannot get historical data.")
            return None

        r = instruments_api.InstrumentsCandles(instrument=instrument, params=params)
        try:
            response = self.client.request(r)
            candles_data = response.get('candles')

            if not candles_data:
                print(f"No candle data returned for {instrument} with params {params}.")
                return None

            # Determine which price point to use (mid, bid, or ask)
            price_type = params.get('price', 'M').upper() # Default to Midpoint
            if price_type == 'M':
                ohlc_key = 'mid'
            elif price_type == 'B':
                ohlc_key = 'bid'
            elif price_type == 'A':
                ohlc_key = 'ask'
            else:
                print(f"Warning: Invalid price type '{params.get('price')}' in params. Defaulting to Midpoint ('M').")
                ohlc_key = 'mid'


            processed_candles = []
            for candle in candles_data:
                if candle.get('complete', False) and ohlc_key in candle: # Process only complete candles with ohlc data
                    processed_candles.append({
                        'time': candle['time'],
                        'volume': candle['volume'],
                        'open': float(candle[ohlc_key]['o']),
                        'high': float(candle[ohlc_key]['h']),
                        'low': float(candle[ohlc_key]['l']),
                        'close': float(candle[ohlc_key]['c'])
                    })
            
            if not processed_candles:
                print(f"No processable candle data found for {instrument} (key: {ohlc_key}). Check 'price' param and API response.")
                return None

            df = pd.DataFrame(processed_candles)
            df['time'] = pd.to_datetime(df['time'])
            df = df[['time', 'open', 'high', 'low', 'close', 'volume']] # Ensure column order
            
            print(f"\n--- Historical Data for {instrument} ({params.get('granularity', 'N/A')}) ---")
            print(f"Successfully fetched {len(df)} candles.")
            print("-------------------------------------------\n")
            return df

        except V20Error as e:
            print(f"OANDA API Error in get_historical_data for {instrument}: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred in get_historical_data for {instrument}: {e}")
            return None

    def get_current_price(self, instruments_list):
        """
        Fetches the current bid and ask prices for a list of instruments.

        Args:
            instruments_list (list): A list of instrument names (e.g., ["EUR_USD", "USD_JPY"]).

        Returns:
            dict: A dictionary where keys are instrument names and values are
                  dictionaries containing their 'bid', 'ask', and 'time',
                  or None if an error occurs.
        """
        if not self.client or not self.account_id:
            print("OANDA client not initialized. Cannot get current prices.")
            return None

        if not instruments_list:
            print("Instruments list is empty. Cannot fetch current prices.")
            return {}

        instruments_str = ",".join(instruments_list)
        params = {"instruments": instruments_str}
        r = pricing_api.PricingInfo(accountID=self.account_id, params=params)

        try:
            response = self.client.request(r)
            prices_data = response.get('prices')

            if not prices_data:
                print(f"No price data returned for instruments {instruments_str}.")
                return None

            current_prices_map = {}
            for price_obj in prices_data:
                instrument_name = price_obj.get('instrument')
                time_val = price_obj.get('time')
                
                # Ensure bids and asks lists are present and not empty
                bids = price_obj.get('bids')
                asks = price_obj.get('asks')

                if bids and len(bids) > 0 and asks and len(asks) > 0:
                    bid_price = float(bids[0].get('price'))
                    ask_price = float(asks[0].get('price'))
                    current_prices_map[instrument_name] = {
                        'bid': bid_price,
                        'ask': ask_price,
                        'time': time_val
                    }
                else:
                    print(f"Warning: Incomplete bid/ask data for instrument {instrument_name}. Skipping.")
            
            print(f"\n--- Current Prices for {instruments_str} ---")
            for instrument, data in current_prices_map.items():
                print(f"  {instrument}: Bid={data['bid']}, Ask={data['ask']}, Time={data['time']}")
            print("------------------------------------------\n")
            return current_prices_map

        except V20Error as e:
            print(f"OANDA API Error in get_current_price for {instruments_str}: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred in get_current_price for {instruments_str}: {e}")
            return None

if __name__ == "__main__":
    print("Attempting to initialize OANDAConnector and test connection...")
    connector = OANDAConnector()
    if connector.client: # Check if client was initialized successfully
        if connector.test_connection():
            print("\n--- Testing get_account_summary ---")
            summary = connector.get_account_summary()
            if summary:
                # The method already prints the details.
                # You can choose to print the raw summary dict here if needed:
                # import json
                # print(f"Raw Account Summary: {json.dumps(summary, indent=2)}")
                pass
            else:
                print("Failed to retrieve account summary in main block.")
            print("-----------------------------------\n")

            # Example call to get_historical_data
            print("--- Testing get_historical_data ---")
            hist_params = {"count": 5, "granularity": "H1", "price": "M"} # Midpoint prices
            historical_data_df = connector.get_historical_data("EUR_USD", params=hist_params)

            if historical_data_df is not None and not historical_data_df.empty:
                print(f"Fetched {len(historical_data_df)} candles for EUR_USD.")
                print("First candle:")
                print(historical_data_df.head(1))
                print("\nLast candle:")
                print(historical_data_df.tail(1))
            else:
                print("Failed to retrieve historical data or data was empty.")
            print("-----------------------------------\n")
            
            # Example call to get_current_price
            print("--- Testing get_current_price ---")
            instruments_to_fetch = ["EUR_USD", "USD_JPY", "GBP_USD"]
            current_prices = connector.get_current_price(instruments_to_fetch)

            if current_prices:
                # The method already prints the details.
                # You can add more processing here if needed.
                # For example, to access a specific price:
                # if "EUR_USD" in current_prices:
                # print(f"EUR_USD Ask: {current_prices['EUR_USD']['ask']}")
                pass
            else:
                print("Failed to retrieve current prices in main block.")
            print("-----------------------------------\n")

    else:
        print("OANDAConnector initialization failed. Check credentials and environment variables.")
