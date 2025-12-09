import time
import schedule
import json # needed for clean error logging
from src.oanda_connector import OandaConnector
from src.webhook_notifier import WebhookNotifier
from src.strategies import Strategy # Import Base Strategy

class StrategyRunner:
    """
    Orchestrates the checking of all registered strategies, optimizing checks
    to run only when a new completed candle is detected for a given instrument/timeframe.
    """
    def __init__(self, connector: OandaConnector, notifier: WebhookNotifier, strategies: list):
        self.connector = connector
        self.notifier = notifier
        self.strategies = strategies
        self.last_run_time_cache = {} 
        self.is_running = False

        print(f"StrategyRunner initialized with {len(strategies)} strategies.")
        # Initial notification
        self.notifier.send_notification({"strategy": "Bot initialised"})

    def _get_latest_completed_candle_time(self, strategy: Strategy):
        try:
            # We only need 2 candles to get the time of the latest completed one
            candles = self.connector.get_candles(
                strategy.instrument,
                strategy.timeframe,
                2
            )
            
            if candles and len(candles) >= 2:
                return candles[-2]['time'] 
            
            return None

        except Exception as e:
            print(f"Error fetching time for {strategy.instrument}/{strategy.timeframe}: {e}")
            return None

    def _run_single_strategy_check(self, strategy: Strategy, candles):
        """Runs the core logic for a single strategy instance."""
        
        print(f"\n-> Checking {strategy.__class__.__name__} ({strategy.instrument}/{strategy.timeframe})...")

        # Number of candles not sufficient, failed
        if len(candles) < strategy.min_required_completed_candles:
            print(
                f"Strategy check failed for {strategy.instrument}: Received {len(candles)} candles, "
                f"but requires at least {strategy.min_required_completed_candles} completed candles. "
                f"Try increasing the required_candles property in {strategy.__class__.__name__}."
            )
            return

        # Capture the tuple return (is_met, detail)
        # Note: 'details' variable name fixed from 'detail' to match unpacking
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
            if details not in ["Already checked", "No S/R Breakout found."]:
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
                # print(f"Skipping check for {strategy.instrument}/{strategy.timeframe}: Failed to retrieve candle time.")
                print(f"Skipping check")
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
                    print("Running check for strategy.")
                    self._run_single_strategy_check(strategy, full_candles)
                    
                    # 3. Update the cache ONLY if the check ran successfully
                    self.last_run_time_cache[cache_key] = latest_time

                except Exception as e:
                    print(f"An unexpected error occurred during check for {strategy.__class__.__name__}: {e}")
            
    def start(self):
        # Sets up the scheduler and starts the main loop.
        if not self.strategies:
            print("No strategies registered. Exiting.")
            return

        print("\n--- Strategy Scanner Initialization ---")
        
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