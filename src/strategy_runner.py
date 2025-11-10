import time
import schedule
from src.oanda_connector import OandaConnector
from src.webhook_notifier import WebhookNotifier
from src.strategies import Strategy

class StrategyRunner:
    """
    Orchestrates the checking of all registered strategies.
    """
    def __init__(self, connector: OandaConnector, notifier: WebhookNotifier, strategies: list):
        self.connector = connector
        self.notifier = notifier
        self.strategies = strategies

        print(f"StrategyRunner initialized with {len(strategies)} strategies.")
        self.notifier.send_notification({"strategy":"Bot initialised"})

    def _get_unique_timeframe(self):
        # Extracts unique timeframe for efficient scheduling
        return sorted(list(set(s.timeframe for s in self.strategies)))

    def _get_strategies_for_timeframe(self, timeframe):
        # Return strategies filtered by the given timeframe
        return [s for s in self.strategies if s.timeframe == timeframe]

    def run_checks(self, timeframe):

        strategies_to_check = self._get_strategies_for_timeframe(timeframe)

        for strategy in self.strategies_to_check:
            print(f"\n-> Checking {strategy.__class__.__name__} ({strategy.instrument}/{strategy.timeframe})...")

            try:
                candles = self.connector.get_candles(
                    strategy.instrument,
                    strategy.timeframe,
                    strategy.required_candles
                )

                # No candles received, failed
                if not candles:
                    print(f"Data fetch failed for {strategy.instrument}. Skipping check.")
                    continue
                
                # Number of candles not sufficient, failed
                if len(candles) < strategy.min_required_completed_candles:
                    print(
                        f"Strategy check failed for {strategy.instrument}: Received {len(candles)} candles, "
                        f"but requires at least {strategy.min_required_completed_candles} completed candles. "
                        f"Try increasing the required_candles property."
                    )
                    continue

                # Capture the tuple return (is_met, detail)
                is_met, details = strategy.check(candles)

                if is_met:
                    print(f"*** STRATEGY MET: {strategy.__class__.__name__} - {detail} ***")

                    # Prepare and send the notification payload
                    payload = {
                        "strategy": strategy.__class__.__name__,
                        "instrument": strategy.instrument,
                        "timeframe": strategy.timeframe,
                        "candle_time": candles[-1]['time'],
                        "message": detail # Use the detail string as the primary message
                    }
                    self.notifier.send_notification(payload)
                else:
                    print(f"Strategy fail: {detail}")
            
            except Exception as e:
                print(f"An unexpected error occurred during check for {strategy.__class__.__name__}: {e}")


    def start(self):
        # Sets up the scheduler and starts the main loop.
        if not self.strategies:
            print("No strategies registered. Exiting.")
            return

        print("\n--- Strategy Scanner Initialization ---")
        
        # Schedule the runner for every minute to cover all timeframes
        # This will call run_checks(timeframe) every minute.
        print("Scheduling checks to run every minute...")
        schedule.every(1).minute.do(self._run_all_checks)
        
        self.is_running = True
        print("Scheduler started. Press Ctrl+C to stop.")

        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
        

    def stop(self):
        # Stops the scheduler loop.
        self.is_running = False

    def _run_all_checks(self):
        # Wrapper to iterate and run checks for all unique timeframes.
        # For a simple scanner, we just run all strategies on every minute.
        # Strategies like M30 will check the same data every minute until a new M30 candle forms.
        # The internal 'last_checked_timestamp' handles the repeat prevention.
        
        for timeframe in self.timeframes:
             # Run checks for all strategies registered under this timeframe
             self.run_checks(timeframe)


