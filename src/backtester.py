import datetime
from src.strategies import Strategy # Import the abstract base class

class Backtester:
    """
    Simulates strategy execution over historical OANDA candle data.
    The simulation runs instantly by iterating through the historical dataset.
    """
    def __init__(self, connector, strategies: list, instrument: str, timeframe: str, start_date: str, end_date: str):
        self.connector = connector
        # Filter strategies for the specific instrument and timeframe being backtested
        self.strategies = [s for s in strategies if s.instrument == instrument and s.timeframe == timeframe]
        self.instrument = instrument
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.backtest_results = {s.__class__.__name__: 0 for s in self.strategies}
        self.candle_cache = {} # Not strictly used in this fast simulation, but kept for context

    def _fetch_historical_data(self):
        """
        Fetches all necessary historical data from OANDA for the defined range,
        prioritizing 'from_date' and 'to_date'.
        
        NOTE: OANDA API limits historical candle requests (e.g., to 5000 candles).
        For a real-world scenario, you would need to implement pagination here.
        """
        print(f"Fetching historical data for {self.instrument} on {self.timeframe} from {self.start_date} to {self.end_date}...")
        
        try:
            # FIX: We rely solely on the 'from_date' and 'to_date' parameters 
            # for defining the range, as requested.
            candles = self.connector.get_candles(
                instrument=self.instrument,
                timeframe=self.timeframe,
                # count=5000 is removed to ensure the date range is used exclusively for time span
                from_date=self.start_date,
                to_date=self.end_date
            )
            
            if not candles:
                print("Error: No historical candles returned for the specified range.")
                return None
            
            print(f"Successfully loaded {len(candles)} candles.")
            return candles
            
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return None

    def run_backtest(self):
        """
        Main backtesting loop. It rapidly iterates through the entire dataset 
        (one candle = one check).
        """
        all_candles = self._fetch_historical_data()
        
        if not all_candles:
            return self.backtest_results

        print("-" * 50)
        print(f"Starting rapid backtest simulation over {len(all_candles)} candles.")
        
        # Determine the maximum lookback period needed by any strategy
        max_lookback = max(s.required_candles for s in self.strategies)
        
        # We start the loop *after* we have enough data to satisfy the max lookback,
        # ensuring all strategies can run their first check.
        for i in range(max_lookback, len(all_candles)):
            
            # The current candle time being evaluated (the one that just "completed")
            current_candle_data = all_candles[i]
            
            for strategy in self.strategies:
                
                # Calculate the exact slice of candles this strategy needs
                lookback_start_index = i - strategy.required_candles + 1
                
                # The slice represents the historical candles *leading up to and including* the current one.
                # This simulates the 'candles' list passed during a live check.
                candle_slice = all_candles[lookback_start_index : i + 1]

                # Ensure we have the minimum completed candles required for the strategy's logic
                if len(candle_slice) < strategy.min_required_completed_candles:
                    continue

                # Run the strategy check
                is_met, details = strategy.check(candle_slice)
                
                if is_met:
                    strategy_name = strategy.__class__.__name__
                    # In a real backtest, you would track profit/loss here. 
                    # For simplicity, we just count the signal occurrences.
                    self.backtest_results[strategy_name] += 1
                    
                    # Log the successful trade setup
                    print(
                        f"[{current_candle_data['time']}][{strategy_name}] "
                        f"SIGNAL: {details} (Candle #{i})"
                    )

        self._print_results()
        return self.backtest_results

    def _print_results(self):
        """Prints the final backtesting report."""
        print("-" * 50)
        print(f"Backtesting Results for {self.instrument} ({self.timeframe}):")
        total_signals = sum(self.backtest_results.values())
        
        if total_signals == 0:
            print("No signals were generated during the backtesting period.")
            return

        for strategy_name, count in self.backtest_results.items():
            print(f"- {strategy_name}: {count} signals generated.")
        print("-" * 50)