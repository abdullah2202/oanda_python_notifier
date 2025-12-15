import time
import schedule
import json 
from typing import List, Tuple
from src.oanda_connector import OandaConnector
from src.webhook_notifier import WebhookNotifier
from src.strategies import Strategy # Import Base Strategy

class StrategyRunner:
    """
    Orchestrates the checking of all registered strategies, optimizing checks
    to run only when a new completed candle is detected for a given instrument/timeframe.
    """
    def __init__(self, connector: OandaConnector, notifier: WebhookNotifier, strategies: List[Strategy]):
        self.connector = connector
        self.notifier = notifier
        self.strategies = strategies
        self.last_run_time_cache = {} 
        self.is_running = False

        print(f"StrategyRunner initialized with {len(strategies)} strategies.")
        
        # Initial notification
        initial_message = {
            "strategy": "Bot initialised",
            "instrument": "N/A",
            "timeframe": "N/A",
            "candle_time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "message": f"Strategy Scanner starting with {len(strategies)} registered strategies."
        }
        self.notifier.send_notification(initial_message)

    def _get_latest_completed_candle_time(self, strategy: Strategy) -> str | None:
        """
        Fetches a small count of candles to quickly determine the timestamp of 
        the most recently completed candle for a given instrument/timeframe.
        """
        try:
            # We only need 1 completed candle to get the time of the latest completed one.
            candles = self.connector.get_candles(
                strategy.instrument,
                strategy.timeframe,
                count=1 
            )
            
            # FIX: If we receive any completed candle, its time is at index -1.
            if candles and len(candles) >= 1:
                return candles[-1]['time'] 
            
            return None

        except Exception as e:
            # Note: We skip printing this error inside the main loop for cleanliness,
            # but it's kept here in case of deep failure.
            # print(f"Error fetching time for {strategy.instrument}/{strategy.timeframe}: {e}")
            return None

    def _run_single_strategy_check(self, strategy: Strategy, candles: list):
        """Runs the core logic for a single strategy instance."""
        
        print(f"\n-> Checking {strategy.__class__.__name__} ({strategy.instrument}/{strategy.timeframe})...")

        # Check if the number of candles is sufficient
        if len(candles) < strategy.min_required_completed_candles:
            print(
                f"Strategy check failed for {strategy.instrument}: Received {len(candles)} candles, "
                f"but requires at least {strategy.min_required_completed_candles} completed candles."
            )
            return

        # Run the strategy check
        is_met, details = strategy.check(candles) 

        if is_met:
            print(f"*** STRATEGY MET: {strategy.__class__.__name__} - {details} ***")

            # Prepare and send the notification payload
            payload = {
                "strategy": strategy.__class__.__name__,
                "instrument": strategy.instrument,
                "timeframe": strategy.timeframe,
                "candle_time": candles[-1]['time'],
                "message": details # Use the details string as the primary message
            }
            self.notifier.send_notification(payload)
        else:
            # Only print failure details if the strategy returned a specific reason
            if details:
                # Filter out messages that indicate "no signal" rather than an error
                if not any(phrase in details for phrase in ["No Engulfing Pattern", "No S/R Breakout", "No 3 bear candles"]):
                     print(f"Strategy fail: {details}")

    def _run_all_checks(self):
        """
        The wrapper function called by the scheduler. Iterates through all strategies
        and runs the check only if a new candle time is detected.
        """
        for strategy in self.strategies:
            
            cache_key = (strategy.instrument, strategy.timeframe)
            latest_time = self._get_latest_completed_candle_time(strategy)
            
            if not latest_time:
                # If we fail to get the time, we skip this strategy for this run.
                continue

            # Check if this candle time is newer than the last time we ran the check for this pair
            if latest_time != self.last_run_time_cache.get(cache_key):
                print(f"\n[NEW CANDLE DETECTED] for {strategy.instrument} on {strategy.timeframe} at {latest_time}")
                
                # 1. Fetch the full candle set required by the strategy
                try:
                    full_candles = self.connector.get_candles(
                        strategy.instrument,
                        strategy.timeframe,
                        strategy.required_candles
                    )
                except Exception as e:
                    print(f"Error fetching full candle data for {strategy.instrument}: {e}")
                    continue

                # 2. Run the actual strategy check
                try:
                    self._run_single_strategy_check(strategy, full_candles)
                    
                    # 3. Update the cache ONLY if the check ran successfully (to prevent re-running on failure)
                    self.last_run_time_cache[cache_key] = latest_time

                except Exception as e:
                    print(f"An unexpected error occurred during check for {strategy.__class__.__name__}: {e}")
            else:
                pass # Candle already checked, skipping.
    
    def start(self):
        # Sets up the scheduler and starts the main loop.
        if not self.strategies:
            print("No strategies registered. Exiting.")
            return

        print("\n--- Strategy Scanner Initialization (Live Mode) ---")
        
        # Schedule the runner for every minute
        print("Scheduling checks to run every minute (Optimized for new candles)...")
        schedule.every(1).minute.do(self._run_all_checks)
        
        self.is_running = True
        print("Scheduler started. Press Ctrl+C to stop.")

        # Run one immediate check to populate the cache and check current conditions
        self._run_all_checks()

        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
            
    def stop(self):
        # Stops the scheduler loop.
        self.is_running = False