from .base_strategy import Strategy, PIP_SIZE

class SRBreakout(Strategy):
    """
    Detects Support/Resistance (S/R) levels based on pin-bar structure 
    and checks if the latest candle closes across the established S/R.
    """
    # CRITICAL FIX: Accept instrument and timeframe, and pass them to the base class.
    def __init__(self, instrument, timeframe):
        # 1. Call the base class constructor
        super().__init__(instrument, timeframe)
        
        # 2. Override the base class defaults with strategy-specific values
        # We need 51 completed candles for a robust check (50 for S/R + 1 for breakout)
        self.min_required_completed_candles = 51 
        # Request 52 to ensure we get 51 completed candles (accounting for 1 incomplete)
        self.required_candles = self.min_required_completed_candles + 1 
        
        print(f"SRBreakout initialized for {self.instrument} ({self.timeframe})")

    def check(self, candles):
        """
        Scans for support (bear-bull close) and resistance (bull-bear close) 
        and checks for a breakout on the latest completed candle.
        """
        # FIX: Corrected typo from min_required_completed_completed_candles
        if len(candles) < self.min_required_completed_candles: 
            return False, f"Not enough candles ({len(candles)}) for check."
            
        # The latest candle in the list, candles[-1], is the one whose close we are evaluating for breakout.
        breakout_candle = candles[-1]
        last_close = float(breakout_candle['mid']['c'])
        
        # historical_candles includes all candles *before* the breakout candle
        historical_candles = candles[:-1]
        
        support_levels = []
        resistance_levels = []

        # 1. S/R Detection Loop
        for i in range(len(historical_candles) - 1):
            c_prev = historical_candles[i]
            c_curr = historical_candles[i+1]
            
            # Extract prices for the previous candle
            c_prev_close = float(c_prev['mid']['c'])
            c_prev_open = float(c_prev['mid']['o'])
            
            # Extract prices for the current candle
            c_curr_close = float(c_curr['mid']['c'])
            c_curr_open = float(c_curr['mid']['o'])
            
            # Check for Support Pattern: c_prev is Bear (close < open) and c_curr is Bull (close > open)
            is_support_pattern = (c_prev_close < c_prev_open) and (c_curr_close > c_curr_open)
            if is_support_pattern:
                # Support is the Close price of the bear candle (c_prev)
                support_levels.append(c_prev_close)
            
            # Check for Resistance Pattern: c_prev is Bull (close > open) and c_curr is Bear (close < open)
            is_resistance_pattern = (c_prev_close > c_prev_open) and (c_curr_close < c_curr_open)
            if is_resistance_pattern:
                # Resistance is the Close price of the bull candle (c_prev)
                resistance_levels.append(c_prev_close)

        # 2. Level Consolidation (Find the most extreme levels)
        best_support = min(support_levels) if support_levels else None

        # Change: Changed to min() to select the closest resistance.
        best_resistance = min(resistance_levels) if resistance_levels else None
        # best_resistance = max(resistance_levels) if resistance_levels else None

        print(f"Support: {best_support} Resistance: {best_resistance}")

        # 3. Breakout Check (using the close of the breakout_candle)
        
        # Check for Breakout UP (Close is above the highest resistance)
        if best_resistance is not None and last_close > best_resistance:
            # Add a 1 pip buffer to confirm the breakout is significant
            if last_close > (best_resistance + PIP_SIZE):
                return True, f"RESISTANCE Breakout detected at R={best_resistance:.5f} (Close={last_close:.5f})."
            
        # Check for Breakout DOWN (Close is below the lowest support)
        if best_support is not None and last_close < best_support:
            # Add a 1 pip buffer to confirm the breakout is significant
            if last_close < (best_support - PIP_SIZE):
                return True, f"SUPPORT Breakout detected at S={best_support:.5f} (Close={last_close:.5f})."

        return False, "No S/R Breakout found."