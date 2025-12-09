from .base_strategy import Strategy, PIP_SIZE

class SRBreakout(Strategy):
    """
    Detects Support/Resistance (S/R) levels based on pin-bar structure 
    and checks if the latest candle closes across the established S/R.
    """
    def __init__(self):
        self._instrument = "XAU_USD"
        self._timeframe = "M30"
        # We need 51 completed candles for a robust check (50 for S/R + 1 for breakout)
        self._min_required_completed_candles = 51 
        # Request 52 to ensure we get 51 completed candles (accounting for 1 incomplete)
        self._required_candles = self._min_required_completed_candles + 1 
        self.last_checked_timestamp = None
        print(f"SRBreakout initialized for {self.instrument} ({self.timeframe})")

    @property
    def instrument(self):
        return self._instrument

    @property
    def timeframe(self):
        return self._timeframe

    @property
    def required_candles(self):
        return self._required_candles

    @property
    def min_required_completed_candles(self):
        return self._min_required_completed_candles

    def check(self, candles):
        """
        Scans for support (bear-bull close) and resistance (bull-bear close) 
        and checks for a breakout on the latest completed candle.
        """
        current_timestamp = candles[-1]['time']
        if current_timestamp == self.last_checked_timestamp:
            return False, "Already checked"

        self.last_checked_timestamp = current_timestamp
        
        # We only use historical candles for S/R detection (up to the second-to-last candle)
        historical_candles = candles[:-1]
        
        support_levels = []
        resistance_levels = []
        
        # 1. S/R Detection Loop
        # Iterate over pairs (c_prev, c_curr)
        for i in range(len(historical_candles) - 1):
            c_prev = historical_candles[i]
            c_curr = historical_candles[i+1]
            
            c_prev_close = float(c_prev['mid']['c'])
            c_prev_open = float(c_prev['mid']['o'])
            
            c_curr_close = float(c_curr['mid']['c'])
            c_curr_open = float(c_curr['mid']['o'])
            
            # Check if c_prev is Bear and c_curr is Bull
            is_support_pattern = (c_prev_close < c_prev_open) and (c_curr_close > c_curr_open)
            if is_support_pattern:
                # Support is the Close price of the bear candle (c_prev)
                support_levels.append(c_prev_close)
            
            # Check if c_prev is Bull and c_curr is Bear
            is_resistance_pattern = (c_prev_close > c_prev_open) and (c_curr_close < c_curr_open)
            if is_resistance_pattern:
                # Resistance is the Close price of the bull candle (c_prev)
                resistance_levels.append(c_prev_close)

        # 2. Level Consolidation (5-pip rule implemented by finding the extreme level)
        
        # Find the single lowest support level (most extreme support)
        best_support = min(support_levels) if support_levels else None
        
        # Find the single highest resistance level (most extreme resistance)
        best_resistance = max(resistance_levels) if resistance_levels else None

        # 3. Breakout Check
        
        # The latest completed candle
        breakout_candle = candles[-1]
        last_close = float(breakout_candle['mid']['c'])

        # Check for Breakout UP (Close is above the highest resistance)
        if best_resistance and last_close > best_resistance:
            # Add a 1 pip buffer to confirm the breakout is significant
            if last_close > (best_resistance + PIP_SIZE):
                return True, f"RESISTANCE Breakout detected at {best_resistance:.2f}."
            
        # Check for Breakout DOWN (Close is below the lowest support)
        if best_support and last_close < best_support:
            # Add a 1 pip buffer to confirm the breakout is significant
            if last_close < (best_support - PIP_SIZE):
                return True, f"SUPPORT Breakout detected at {best_support:.2f}."

        return False, "No S/R Breakout found."