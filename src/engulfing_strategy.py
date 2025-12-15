from .base_strategy import Strategy

class EngulfingStrategy(Strategy):

    # CRITICAL FIX: Accept instrument and timeframe, and pass them to the base class.
    # The base class now handles instrument, timeframe, required_candles, and min_required_completed_candles 
    # as standard attributes, so the @property decorators are removed.
    def __init__(self, instrument, timeframe):
        # 1. Call the base class constructor
        super().__init__(instrument, timeframe)
        
        # 2. Override the base class defaults with strategy-specific values
        self.required_candles = 6 
        self.min_required_completed_candles = 4
        
        # NOTE: The last_checked_timestamp logic has been moved to the StrategyRunner
        # for efficient polling, so it is removed here to prevent redundancy.
        
        print(f"EngulfingStrategy initialized for {self.instrument} ({self.timeframe})")

    # Removed: @property decorators for instrument, timeframe, required_candles, etc. 
    # These are now standard attributes inherited from the base class.
    
    def _get_candle_direction(self, candle):
        o = float(candle['mid']['o'])
        c = float(candle['mid']['c'])
        if c > o:
            return 'bull'
        elif c < o:
            return 'bear'
        else:
            return 'doji'

    def _get_body_size(self, candle):
        o = float(candle['mid']['o'])
        c = float(candle['mid']['c'])
        return abs(c - o)

    def check(self, candles):
        # Ensure enough data
        if len(candles) < self.min_required_completed_candles:
            # We return False, but the StrategyRunner will print the specific error.
            return False, f"Not enough completed candles ({len(candles)}) for check."
        
        # Note: The StrategyRunner ensures this method is ONLY called when a new candle has completed.
        # The logic for 'last_checked_timestamp' is therefore removed from here.

        # Candle Indexing
        # candles[-1] is the most recent completed candle ("Candle 1")
        # candles[-2] is the one before that ("Candle 2")
        candle_1 = candles[-1]
        candle_2 = candles[-2]
        candle_3 = candles[-3]
        candle_4 = candles[-4]

        current_timestamp = candle_1['time']
        print(f"\nChecking new candle: {current_timestamp}")

        # Strategy Logic
        # 1. Candles 2-4 same direction
        dir_2 = self._get_candle_direction(candle_2)
        dir_3 = self._get_candle_direction(candle_3)
        dir_4 = self._get_candle_direction(candle_4)

        if dir_2 == 'doji' or dir_3 == 'doji' or dir_4 == 'doji':
            print("Strategy fail: Doji found in candles 2-4.")
            return False, "No Engulfing Pattern (Doji in 2-4)"

        if not (dir_2 == dir_3 == dir_4):
            print(f"Strategy fail: Candles 2-4 not same direction ({dir_4}, {dir_3}, {dir_2})")
            return False, "No Engulfing Pattern (Candles 2-4 direction mismatch)"
        
        # 2. Candle 1 is opposite direction
        dir_1 = self._get_candle_direction(candle_1)
        
        if dir_1 == 'doji':
            print("Strategy fail: Candle 1 is a doji.")
            return False, "No Engulfing Pattern (Candle 1 Doji)"

        if dir_1 == dir_2:
            print(f"Strategy fail: Candle 1 ({dir_1}) same direction as Candle 2 ({dir_2})")
            return False, "No Engulfing Pattern (Candle 1 same direction as Candle 2)"
        
        # 3. Candle 1's body > Candle 2's body
        body_1 = self._get_body_size(candle_1)
        body_2 = self._get_body_size(candle_2)

        if body_1 <= body_2:
            print(f"Strategy fail: Candle 1 body ({body_1}) not > Candle 2 body ({body_2})")
            return False, "No Engulfing Pattern (Candle 1 body not greater than Candle 2 body)"
        
        # All conditions are met
        print(f"*** STRATEGY MET: EngulfingPattern on {self.instrument} ***")
        return True, f"Engulfing Pattern Found ({dir_1.upper()} Signal)"