import os
from decimal import Decimal, ROUND_HALF_UP

# Assuming oanda_connector.py is in the same directory or accessible via PYTHONPATH
try:
    from oanda_connector import OANDAConnector
except ImportError:
    print("Error: Failed to import OANDAConnector. Ensure oanda_connector.py is accessible.")
    # Fallback for basic functionality if connector is missing, though order placement will fail.
    OANDAConnector = None 

import oandapyV20.endpoints.orders as orders_api
from oandapyV20.exceptions import V20Error

class OrderManager:
    """
    Manages the creation of market orders with stop-loss and take-profit levels.
    """
    def __init__(self, oanda_connector, default_units, default_sl_pips, default_tp_pips):
        """
        Initializes the OrderManager.

        Args:
            oanda_connector (OANDAConnector): An instance of OANDAConnector.
            default_units (int): Default number of units for orders.
            default_sl_pips (int): Default stop-loss distance in pips.
            default_tp_pips (int): Default take-profit distance in pips.
        """
        if not isinstance(oanda_connector, OANDAConnector):
            raise ValueError("oanda_connector must be an instance of OANDAConnector.")
        if not isinstance(default_units, int) or default_units <= 0:
            raise ValueError("default_units must be a positive integer.")
        if not isinstance(default_sl_pips, (int, float)) or default_sl_pips <= 0:
            raise ValueError("default_sl_pips must be a positive number.")
        if not isinstance(default_tp_pips, (int, float)) or default_tp_pips <= 0:
            raise ValueError("default_tp_pips must be a positive number.")

        self.oanda_connector = oanda_connector
        self.default_units = default_units
        self.default_sl_pips = Decimal(str(default_sl_pips))
        self.default_tp_pips = Decimal(str(default_tp_pips))

    def _get_pip_value(self, instrument):
        """
        Determines the pip value for an instrument based on a heuristic.
        Assumes JPY pairs have pip value 0.01, others 0.0001.
        """
        if "JPY" in instrument.upper():
            return Decimal("0.01")
        return Decimal("0.0001")

    def _get_price_precision(self, instrument):
        """
        Determines the price precision (decimal places) for an instrument.
        Assumes JPY pairs have 3 decimal places, others 5.
        """
        if "JPY" in instrument.upper():
            return 3
        return 5

    def _format_price(self, price_decimal, precision):
        """
        Formats a Decimal price to a string with the specified precision.
        """
        return str(price_decimal.quantize(Decimal('1e-' + str(precision)), rounding=ROUND_HALF_UP))

    def _calculate_price_details(self, instrument, signal):
        """
        Calculates entry price, stop-loss, and take-profit prices.

        Args:
            instrument (str): The trading instrument.
            signal (str): 'BUY' or 'SELL'.

        Returns:
            dict: Contains 'entry_price' (Decimal), 'stop_loss_price_str' (str),
                  'take_profit_price_str' (str). Returns None if calculation fails.
        """
        if not self.oanda_connector:
            print("Error: OANDAConnector not available in OrderManager._calculate_price_details.")
            return None
            
        current_prices_map = self.oanda_connector.get_current_price([instrument])
        if not current_prices_map or instrument not in current_prices_map:
            print(f"Error: Could not fetch current price for {instrument}.")
            return None

        price_data = current_prices_map[instrument]
        pip_value = self._get_pip_value(instrument)
        precision = self._get_price_precision(instrument)

        entry_price_decimal = Decimal(0)

        if signal == 'BUY':
            entry_price_decimal = Decimal(str(price_data['ask']))
            stop_loss_price = entry_price_decimal - (self.default_sl_pips * pip_value)
            take_profit_price = entry_price_decimal + (self.default_tp_pips * pip_value)
        elif signal == 'SELL':
            entry_price_decimal = Decimal(str(price_data['bid']))
            stop_loss_price = entry_price_decimal + (self.default_sl_pips * pip_value)
            take_profit_price = entry_price_decimal - (self.default_tp_pips * pip_value)
        else:
            print(f"Error: Invalid signal '{signal}' in _calculate_price_details.")
            return None
        
        return {
            'entry_price': entry_price_decimal, # Unformatted, for potential internal use
            'stop_loss_price_str': self._format_price(stop_loss_price, precision),
            'take_profit_price_str': self._format_price(take_profit_price, precision)
        }

    def create_market_order(self, instrument, signal):
        """
        Creates a market order with pre-defined stop-loss and take-profit.

        Args:
            instrument (str): The trading instrument (e.g., "EUR_USD").
            signal (str): The trading signal ('BUY' or 'SELL').

        Returns:
            dict: The API response from OANDA, or None if order placement fails or signal is invalid.
        """
        if signal not in ['BUY', 'SELL']:
            print(f"Info: Signal is '{signal}'. No order placed.")
            return None

        if not self.oanda_connector or not self.oanda_connector.client or not self.oanda_connector.account_id:
            print("Error: OANDAConnector not properly initialized or missing account_id.")
            return None

        price_details = self._calculate_price_details(instrument, signal)
        if not price_details:
            print(f"Error: Could not calculate price details for {instrument}. Order not placed.")
            return None

        units = self.default_units
        if signal == 'SELL':
            units = -self.default_units

        order_data = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(units),
                "timeInForce": "FOK", # Fill Or Kill for market orders
                "stopLossOnFill": {
                    "price": price_details['stop_loss_price_str'],
                    "timeInForce": "GTC" # Good Til Cancelled for SL
                },
                "takeProfitOnFill": {
                    "price": price_details['take_profit_price_str'],
                    "timeInForce": "GTC" # Good Til Cancelled for TP
                }
            }
        }
        
        print(f"\nAttempting to place {signal} order for {instrument} with data: {order_data}")

        r = orders_api.OrderCreate(accountID=self.oanda_connector.account_id, data=order_data)
        try:
            response = self.oanda_connector.client.request(r)
            print(f"Order Response for {instrument} ({signal}):")
            # Common responses: orderFillTransaction, orderCancelTransaction (if FOK fails), orderCreateTransaction
            if 'orderFillTransaction' in response:
                print(f"  Order filled successfully. Transaction ID: {response['orderFillTransaction']['id']}")
                print(f"  Price: {response['orderFillTransaction'].get('price', 'N/A')}, Units: {response['orderFillTransaction'].get('units', 'N/A')}")
            elif 'orderCreateTransaction' in response:
                 print(f"  Order created successfully. Transaction ID: {response['orderCreateTransaction']['id']}")
            elif 'orderCancelTransaction' in response:
                print(f"  Order CANCELED (e.g. FOK could not be filled, or other reason). Reason: {response['orderCancelTransaction'].get('reason')}")
            elif 'errorMessage' in response:
                print(f"  Order failed: {response['errorMessage']}")
            else:
                print(f"  Full response: {response}") # Print full response if structure is unexpected
            return response
        except V20Error as e:
            print(f"OANDA API Error while placing order for {instrument} ({signal}): {e}")
            if hasattr(e, 'msg') and e.msg: # V20Error often has a msg attribute with more details
                 print(f"Error details: {e.msg}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while placing order for {instrument} ({signal}): {e}")
            return None

if __name__ == "__main__":
    print("--- OrderManager Module Example ---")

    # IMPORTANT: This example will try to place a REAL ORDER on your OANDA account.
    # Ensure your OANDA_API_KEY and OANDA_ACCOUNT_ID environment variables are set
    # for a DEMO/PRACTICE account. Do NOT run against a live account without full awareness.

    # Check if OANDAConnector is available and credentials are set
    if OANDAConnector and os.getenv("OANDA_API_KEY") and os.getenv("OANDA_ACCOUNT_ID"):
        try:
            connector = OANDAConnector() # Assumes credentials are in env variables
            
            if connector.client and connector.test_connection(): # Test connection first
                print("OANDA connection successful.")
                order_manager = OrderManager(
                    oanda_connector=connector,
                    default_units=100,      # Example: 100 units
                    default_sl_pips=20,     # Example: 20 pips SL
                    default_tp_pips=40      # Example: 40 pips TP
                )

                # Example 1: Place a BUY order for EUR_USD
                print("\nExample 1: Attempting BUY order for EUR_USD...")
                # WARNING: THIS WILL PLACE AN ORDER IF CONNECTION AND CREDENTIALS ARE VALID
                buy_response = order_manager.create_market_order("EUR_USD", "BUY")
                # if buy_response:
                # print(f"BUY order response for EUR_USD: {buy_response}")


                # Example 2: Attempt a SELL order for USD_JPY
                # print("\nExample 2: Attempting SELL order for USD_JPY...")
                # WARNING: THIS WILL PLACE AN ORDER
                # sell_response_jpy = order_manager.create_market_order("USD_JPY", "SELL")
                # if sell_response_jpy:
                # print(f"SELL order response for USD_JPY: {sell_response_jpy}")

                # Example 3: HOLD signal (should do nothing)
                print("\nExample 3: Attempting HOLD order for EUR_USD (should do nothing)...")
                hold_response = order_manager.create_market_order("EUR_USD", "HOLD")
                if hold_response is None:
                    print("HOLD signal handled correctly (no order placed).")

            else:
                print("Failed to connect to OANDA. Check credentials and network.")
        except EnvironmentError as e:
            print(f"Environment Error: {e}. Please ensure OANDA_API_KEY and OANDA_ACCOUNT_ID are set.")
        except Exception as e:
            print(f"An error occurred during OANDAConnector setup or OrderManager example: {e}")
    else:
        print("\nSkipping OrderManager live example because OANDAConnector is not available or "
              "OANDA_API_KEY/OANDA_ACCOUNT_ID are not set in environment variables.")
        print("To run the live example, ensure oanda_connector.py is present and credentials are set.")

    print("\n--- OrderManager Module Example End ---")
```
