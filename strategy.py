import pandas as pd
# import numpy as np # Not strictly necessary for this basic SMA strategy

class Strategy:
    """
    Implements a simple Moving Average Crossover (SMA) trading strategy.
    """
    def __init__(self, short_window, long_window):
        """
        Initializes the Strategy with short and long SMA window periods.

        Args:
            short_window (int): The period for the short-term Simple Moving Average.
            long_window (int): The period for the long-term Simple Moving Average.
        """
        if not isinstance(short_window, int) or short_window <= 0:
            raise ValueError("short_window must be a positive integer.")
        if not isinstance(long_window, int) or long_window <= 0:
            raise ValueError("long_window must be a positive integer.")
        if short_window >= long_window:
            raise ValueError("short_window must be less than long_window.")
            
        self.short_window = short_window
        self.long_window = long_window

    def generate_signal(self, historical_data_df):
        """
        Generates a trading signal based on SMA crossover.

        Args:
            historical_data_df (pd.DataFrame): A DataFrame containing historical price data,
                                              must include a 'close' column.

        Returns:
            str: The trading signal ('BUY', 'SELL', 'HOLD').
        """
        if not isinstance(historical_data_df, pd.DataFrame):
            print("Warning: historical_data_df must be a pandas DataFrame.")
            return 'HOLD'
            
        if 'close' not in historical_data_df.columns:
            print("Warning: 'close' column not found in historical_data_df.")
            return 'HOLD'

        if len(historical_data_df) < self.long_window:
            print(f"Warning: Insufficient data for long SMA calculation. "
                  f"Need at least {self.long_window} data points, got {len(historical_data_df)}.")
            return 'HOLD'

        # Calculate SMAs
        try:
            short_sma = historical_data_df['close'].rolling(window=self.short_window, min_periods=self.short_window).mean()
            long_sma = historical_data_df['close'].rolling(window=self.long_window, min_periods=self.long_window).mean()
        except Exception as e:
            print(f"Error calculating SMAs: {e}")
            return 'HOLD'

        # Check if we have enough data points for iloc[-2] after rolling mean calculation
        # The SMAs will have NaNs at the beginning. We need at least two valid SMA values.
        if len(short_sma.dropna()) < 2 or len(long_sma.dropna()) < 2:
            # This condition implies we don't have enough data for historical_data_df.iloc[-2]
            # for both SMAs after dropping NaNs, which means we can't check the previous crossover state.
            # This is often covered by the initial len(historical_data_df) < self.long_window check,
            # but it's a good safeguard if min_periods were different or for edge cases.
            print("Warning: Not enough SMA values to determine a crossover (need at least 2 for current and previous).")
            return 'HOLD'
            
        signal = 'HOLD' # Default signal

        # Current and previous SMA values
        # Ensure we use .iloc on the series, not the DataFrame, to avoid issues if index isn't standard integer index
        current_short_sma = short_sma.iloc[-1]
        previous_short_sma = short_sma.iloc[-2]
        current_long_sma = long_sma.iloc[-1]
        previous_long_sma = long_sma.iloc[-2]

        # Check for NaN in the specific values we need (iloc[-1], iloc[-2])
        # This can happen if the overall dataframe is long enough, but the last few 'close' values are NaN
        if pd.isna(current_short_sma) or pd.isna(previous_short_sma) or \
           pd.isna(current_long_sma) or pd.isna(previous_long_sma):
            print("Warning: NaN values in SMAs at crossover check points. Holding.")
            return 'HOLD'

        # BUY signal: Short SMA crosses above Long SMA
        if current_short_sma > current_long_sma and previous_short_sma <= previous_long_sma:
            signal = 'BUY'
        # SELL signal: Short SMA crosses below Long SMA
        elif current_short_sma < current_long_sma and previous_short_sma >= previous_long_sma:
            signal = 'SELL'
            
        return signal

if __name__ == "__main__":
    print("--- Strategy Module Example ---")

    # Example 1: Buy signal
    print("\nExample 1: Testing BUY Signal")
    data_buy = {
        'time': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05', 
                                '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10',
                                '2023-01-11', '2023-01-12']), # 12 data points
        'close': [10, 11, 10, 9, 8, 7, 8, 9, 10, 11, 13, 14] # Short SMA should cross above Long SMA at the end
    }
    df_buy = pd.DataFrame(data_buy)
    
    # Strategy with short_window=3, long_window=6 (needs at least 6 data points)
    strategy_buy = Strategy(short_window=3, long_window=6)
    signal_buy = strategy_buy.generate_signal(df_buy)
    print(f"Generated Signal for Buy Example: {signal_buy}") # Expected: BUY

    # Example 2: Sell signal
    print("\nExample 2: Testing SELL Signal")
    data_sell = {
        'time': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05',
                                '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10',
                                '2023-01-11', '2023-01-12']),
        'close': [10, 11, 12, 13, 14, 15, 14, 13, 10, 9, 8, 7] # Short SMA should cross below Long SMA
    }
    df_sell = pd.DataFrame(data_sell)
    strategy_sell = Strategy(short_window=3, long_window=6)
    signal_sell = strategy_sell.generate_signal(df_sell)
    print(f"Generated Signal for Sell Example: {signal_sell}") # Expected: SELL

    # Example 3: Hold signal (no crossover)
    print("\nExample 3: Testing HOLD Signal (No Crossover)")
    data_hold = {
        'time': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05',
                                '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10',
                                '2023-01-11', '2023-01-12']),
        'close': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21] # Consistently rising
    }
    df_hold = pd.DataFrame(data_hold)
    strategy_hold = Strategy(short_window=3, long_window=6)
    signal_hold = strategy_hold.generate_signal(df_hold)
    print(f"Generated Signal for Hold Example: {signal_hold}") # Expected: HOLD (or BUY if initial condition is met)

    # Example 4: Hold signal (short SMA already above long SMA, no recent crossover)
    print("\nExample 4: Testing HOLD Signal (Short SMA already above, no crossover)")
    data_hold_above = { # Short SMA starts above long SMA and stays above
        'time': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05',
                                '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10',
                                '2023-01-11', '2023-01-12']),
        'close': [10,10,10,10,15,16,17,18,19,20,21,22] 
    } # short_sma = [NaN,NaN,10,10,11.6,13.6,16,17,18,19,20,21]
      # long_sma = [NaN,NaN,NaN,NaN,NaN,11.8,13,14.3,15.8,17.1,18.5,19.8]
      # At iloc[-1]: short 21 > long 19.8. At iloc[-2]: short 20 > long 18.5. So HOLD.
    df_hold_above = pd.DataFrame(data_hold_above)
    strategy_hold_above = Strategy(short_window=3, long_window=6)
    signal_hold_above = strategy_hold_above.generate_signal(df_hold_above)
    print(f"Generated Signal for Hold (Above) Example: {signal_hold_above}") # Expected: HOLD

    # Example 5: Insufficient data
    print("\nExample 5: Testing Insufficient Data")
    data_insufficient = {
        'time': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']), # Only 3 data points
        'close': [10, 11, 12]
    }
    df_insufficient = pd.DataFrame(data_insufficient)
    strategy_insufficient = Strategy(short_window=3, long_window=6) # Needs 6
    signal_insufficient = strategy_insufficient.generate_signal(df_insufficient)
    print(f"Generated Signal for Insufficient Data Example: {signal_insufficient}") # Expected: HOLD
    
    print("\n--- Strategy Module Example End ---")
```
