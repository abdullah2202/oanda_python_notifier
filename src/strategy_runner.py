class StrategyRunner:
    """
    Orchestrates the checking of all registered strategies.
    """
    def __init__(self, connector, notifier, strategies):
        self.connector = connector
        self.notifier = notifier
        self.strategies = strategies
        print(f"StrategyRunner initialized with {len(strategies)} strategies.")
        self.notifier.send_notification({"Initialised" : "bot started"})

    def run_checks(self):
        """
        Iterates through each strategy, fetches its required data,
        and runs its check method.
        """
        print("--- Running checks... ---")
        for strategy in self.strategies:
            try:
                candles = self.connector.get_candles(
                    strategy.instrument,
                    strategy.timeframe,
                    strategy.required_candles
                )

                if candles:
                    if strategy.check(candles):
                        # Condition met, send webhook
                        payload = {
                            "strategy": strategy.__class__.__name__,
                            "instrument": strategy.instrument,
                            "timeframe": strategy.timeframe,
                            "candle_time": candles[-1]['time'],
                            "message": f"Strategy condition met for {strategy.instrument}."
                        }
                        self.notifier.send_notification(payload)
                else:
                    print(f"Could not fetch candles for {strategy.instrument}")
            
            except Exception as e:
                print(f"Error checking strategy {strategy.__class__.__name__}: {e}")