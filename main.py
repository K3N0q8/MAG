import time
import logging
import os # For checking environment variables

# Import custom modules
try:
    from oanda_connector import OANDAConnector
    from strategy import Strategy
    from order_manager import OrderManager
except ImportError as e:
    print(f"Error: Failed to import one or more custom modules: {e}")
    print("Please ensure oanda_connector.py, strategy.py, and order_manager.py are in the Python path.")
    exit()


# --- Configuration Section ---
INSTRUMENT = "EUR_USD"  # Default instrument
CANDLE_GRANULARITY = "M1" # 1-minute candles
# For M1 candles, SMA_LONG_WINDOW should be reasonable, e.g., 10-60 for a 10-60 minute SMA.
# If CANDLE_GRANULARITY is H1, then windows are in hours.
SMA_SHORT_WINDOW = 5      # e.g., 5-minute SMA if CANDLE_GRANULARITY is M1
SMA_LONG_WINDOW = 15      # e.g., 15-minute SMA if CANDLE_GRANULARITY is M1
HISTORICAL_DATA_COUNT = SMA_LONG_WINDOW + 10 # Fetch enough data for longest SMA + buffer

ORDER_UNITS = 100
STOP_LOSS_PIPS = 20
TAKE_PROFIT_PIPS = 40
LOOP_SLEEP_SECONDS = 60   # For M1 candles, check every 60 seconds.

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler() # Output to console
        # You can add logging.FileHandler("trading_bot.log") here if you want to log to a file
    ]
)

def run_bot():
    """
    Main function to run the trading bot.
    """
    logging.info("--- Trading Bot Starting ---")
    logging.info(f"Instrument: {INSTRUMENT}, Granularity: {CANDLE_GRANULARITY}")
    logging.info(f"SMA Windows: Short={SMA_SHORT_WINDOW}, Long={SMA_LONG_WINDOW}")
    logging.info(f"Order Config: Units={ORDER_UNITS}, SL Pips={STOP_LOSS_PIPS}, TP Pips={TAKE_PROFIT_PIPS}")
    logging.info(f"Loop Sleep: {LOOP_SLEEP_SECONDS} seconds")

    # Check for OANDA credentials before initializing connector
    if not os.getenv("OANDA_API_KEY") or not os.getenv("OANDA_ACCOUNT_ID"):
        logging.error("CRITICAL: OANDA_API_KEY or OANDA_ACCOUNT_ID not found in environment variables.")
        logging.error("Please set them up before running the bot.")
        return

    # --- Initialization ---
    try:
        logging.info("Initializing OANDAConnector...")
        connector = OANDAConnector()
        if not connector.client:
            logging.error("Failed to initialize OANDAConnector client (e.g. credentials missing or invalid). Exiting.")
            return
        
        logging.info("Testing OANDA API connection...")
        if not connector.test_connection():
            logging.error("OANDA API connection test failed. Please check credentials and network. Exiting.")
            return
        logging.info("OANDA API connection successful.")

        logging.info("Initializing Strategy...")
        strategy = Strategy(short_window=SMA_SHORT_WINDOW, long_window=SMA_LONG_WINDOW)

        logging.info("Initializing OrderManager...")
        order_manager = OrderManager(
            oanda_connector=connector,
            default_units=ORDER_UNITS,
            default_sl_pips=STOP_LOSS_PIPS,
            default_tp_pips=TAKE_PROFIT_PIPS
        )
        logging.info("All components initialized successfully.")

    except ValueError as ve:
        logging.error(f"Configuration Error during initialization: {ve}")
        return
    except Exception as e:
        logging.error(f"An unexpected error occurred during initialization: {e}")
        return

    # --- Main Loop ---
    try:
        while True:
            logging.info(f"--- New Iteration for {INSTRUMENT} ---")

            # 1. Fetch Historical Data
            logging.info(f"Fetching historical data for {INSTRUMENT} ({CANDLE_GRANULARITY}, count={HISTORICAL_DATA_COUNT})...")
            # Parameters for historical data
            hist_params = {
                "count": HISTORICAL_DATA_COUNT,
                "granularity": CANDLE_GRANULARITY,
                "price": "M"  # Midpoint prices for strategy calculation
            }
            historical_df = connector.get_historical_data(INSTRUMENT, params=hist_params)

            if historical_df is None or historical_df.empty:
                logging.warning(f"Could not fetch historical data for {INSTRUMENT}. Skipping this iteration.")
                logging.info(f"Sleeping for {LOOP_SLEEP_SECONDS} seconds...")
                time.sleep(LOOP_SLEEP_SECONDS)
                continue # Skip to next iteration

            # 2. Generate Trading Signal
            logging.info("Generating trading signal...")
            signal = strategy.generate_signal(historical_df)
            logging.info(f"Generated signal for {INSTRUMENT}: {signal}")

            # 3. Act on Signal
            if signal in ['BUY', 'SELL']:
                logging.info(f"Attempting to place {signal} order for {INSTRUMENT}.")
                order_response = order_manager.create_market_order(INSTRUMENT, signal)
                if order_response:
                    # OrderManager already prints details, we can log a summary here
                    if 'orderFillTransaction' in order_response:
                        logging.info(f"Order for {INSTRUMENT} ({signal}) filled. TxID: {order_response['orderFillTransaction']['id']}")
                    elif 'orderCreateTransaction' in order_response:
                         logging.info(f"Order for {INSTRUMENT} ({signal}) created. TxID: {order_response['orderCreateTransaction']['id']}")
                    elif 'orderCancelTransaction' in order_response:
                        logging.warning(f"Order for {INSTRUMENT} ({signal}) CANCELED. Reason: {order_response['orderCancelTransaction'].get('reason')}")
                    else:
                        logging.warning(f"Order for {INSTRUMENT} ({signal}) response received but structure not fully recognized for fill/create details.")
                else:
                    logging.error(f"Failed to place {signal} order for {INSTRUMENT} or no response.")
            elif signal == 'HOLD':
                logging.info(f"Signal is HOLD for {INSTRUMENT}. No action taken.")
            else:
                logging.warning(f"Unknown signal '{signal}' received for {INSTRUMENT}. No action taken.")

            # 4. Display Account Summary (Optional)
            # This can be verbose, so enable if needed or make it more concise in OANDAConnector
            # logging.info("Fetching account summary...")
            # connector.get_account_summary() # This method in oanda_connector prints details

            logging.info(f"Iteration complete. Sleeping for {LOOP_SLEEP_SECONDS} seconds...")
            time.sleep(LOOP_SLEEP_SECONDS)

    except KeyboardInterrupt:
        logging.info("Trading bot stopped manually (Ctrl+C). Shutting down...")
    except Exception as e:
        logging.error(f"An critical error occurred in the main loop: {e}", exc_info=True) # Log full traceback
    finally:
        logging.info("--- Trading Bot Shutdown ---")


if __name__ == "__main__":
    run_bot()
```
