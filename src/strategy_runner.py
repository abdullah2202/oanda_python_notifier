import time
import schedule
from typing import List, Dict, Tuple
from collections import defaultdict
from src.oanda_connector import OandaConnector
from src.webhook_notifier import WebhookNotifier
from src.strategies import Strategy 

class StrategyRunner:
    """
    Orchestrates the checking of all registered strategies. It groups strategies
    by (instrument, timeframe) pair and runs checks only when a new completed 
    candle is detected for that pair, ensuring all strategies run on the same candle.
    """
    def __init__(self, connector: OandaConnector, notifier: WebhookNotifier, strategies: List[Strategy]):
        self.connector = connector
        self.notifier = notifier
        self.strategies = strategies
        # Cache stores the last checked candle time for each (instrument, timeframe) pair.
        self.last_run_time_cache: Dict[Tuple[str, str], str] = {}
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

    def _get_latest_completed_candle_time(self, instrument: str, timeframe: str) -> str | None:
        """
        Fetches the timestamp of the most recently completed candle.
        """
        try:
            # We only need 1 completed candle to determine the time, request 2 as the lastest one is always incomplete.
            candles = self.connector.get_candles(instrument, timeframe, count=2)
            
            # The latest completed candle is always at index -1
            if candles and len(candles) >= 1:
                return candles[-1]['time'] 
            
            return None

        except Exception as e:
            # Note: Minimal logging here to avoid excessive console output on minor failures.
            # print(f"Error fetching time for {instrument}/{timeframe}: {e}")
            return None

    def _group_strategies_by_pair(self) -> Dict[Tuple[str, str], List[Strategy]]:
        """Groups all strategies by their unique (instrument, timeframe) pair."""
        grouped_strategies = defaultdict(list)
        for strategy in self.strategies:
            pair = (strategy.instrument, strategy.timeframe)
            grouped_strategies[pair].append(strategy)
        return grouped_strategies

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

        # print(f"Candles: {candles}")

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
            # Only print failure details if the strategy returned a specific reason that is not a 'no-signal' message
            if details:
                if not any(phrase in details for phrase in ["No Engulfing Pattern", "No S/R Breakout", "No 3 bear candles", "Not enough candles"]):
                     print(f"Strategy fail: {details}")

    def _run_all_checks(self):
        """
        The wrapper function called by the scheduler. Iterates through unique
        instrument/timeframe pairs, runs all associated strategies if a new 
        candle is detected, and updates the cache only once per pair.
        """
        grouped_strategies = self._group_strategies_by_pair()

        for (instrument, timeframe), strategies_in_group in grouped_strategies.items():
            
            cache_key = (instrument, timeframe)
            latest_time = self._get_latest_completed_candle_time(instrument, timeframe)

            if not latest_time:
                continue

            # Check if this candle time is newer than the last time we ran the check for this pair
            if latest_time != self.last_run_time_cache.get(cache_key):
                print(f"\n[NEW CANDLE DETECTED] for {instrument} on {timeframe} at {latest_time}")
                
                # Determine the maximum number of candles required by ANY strategy in this group
                max_required_candles = max(s.required_candles for s in strategies_in_group)
                
                # 1. Fetch the full candle set required ONCE for the whole group
                try:
                    full_candles = self.connector.get_candles(
                        instrument,
                        timeframe,
                        max_required_candles
                    )
                except Exception as e:
                    print(f"Error fetching full candle data for {instrument}: {e}")
                    continue

                # 2. Run the actual strategy check for ALL strategies in the group
                check_successful = True
                for strategy in strategies_in_group:
                    try:
                        self._run_single_strategy_check(strategy, full_candles)
                    except Exception as e:
                        print(f"An unexpected error occurred during check for {strategy.__class__.__name__}: {e}")
                        check_successful = False

                # 3. FIX: Update the cache for the pair ONLY AFTER ALL strategies have run successfully
                if check_successful:
                    self.last_run_time_cache[cache_key] = latest_time
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