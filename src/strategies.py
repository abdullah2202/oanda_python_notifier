from abc import ABC, abstractmethod
import math

# Value of 1 pip. Adjust for different instruments
PIP_SIZE = 0.01

class Strategy(ABC):
    """
    Abstract Base Class for all trading strategies.
    """
    @abstractmethod
    def check(self, candles):
        """Returns (is_strategy_met: bool, notification_detail: str)"""
        pass

    @property
    @abstractmethod
    def instrument(self):
        pass

    @property
    @abstractmethod
    def timeframe(self):
        pass

    @property
    @abstractmethod
    def required_candles(self):
        pass

    @property
    @abstractmethod
    def min_required_completed_candles(self):
        """Minimum *completed* candles needed for strategy logic (e.g., 4 for Candle 1-4)."""
        pass


class EngulfingStrategy(Strategy):
    """
    Checks for the engulfing pattern:
    - Candles 2, 3, 4 are the same direction.
    - Candle 1 is the opposite direction.
    - Candle 1's body > Candle 2's body.
    """
    def __init__(self):
        self._instrument = "XAU_USD"
        self._timeframe = "M30"
        # Check candles 1, 2, 3, and 4
        self._required_candles = 6  # Request 5 to be safe
        # We need candles 1, 2, 3, 4, so the minimum is 4 completed candles.
        self._min_required_completed_candles = 4
        self.last_checked_timestamp = None
        print(f"EngulfingStrategy initialized for {self.instrument} ({self.timeframe})")

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
            print("Not enough candle data to check strategy.")
            return False
        
        # Candle Indexing
        # OANDA returns candles in chronological order.
        # candles[-1] is the most recent *completed* candle ("Candle 1")
        # candles[-2] is the one before that ("Candle 2")
        
        candle_1 = candles[-1]
        candle_2 = candles[-2]
        candle_3 = candles[-3]
        candle_4 = candles[-4]

        # State Check
        # This is crucial: it prevents the script from sending 30 alerts
        # for the same M30 candle. It only checks *new* candles.
        current_timestamp = candle_1['time']
        if current_timestamp == self.last_checked_timestamp:
            return False
        
        # This is a new candle, so we check it and update the state.
        self.last_checked_timestamp = current_timestamp
        print(f"\nChecking new candle: {current_timestamp}")

        # Strategy Logic
        # 1. Candles 2-4 same direction
        dir_2 = self._get_candle_direction(candle_2)
        dir_3 = self._get_candle_direction(candle_3)
        dir_4 = self._get_candle_direction(candle_4)

        if dir_2 == 'doji' or dir_3 == 'doji' or dir_4 == 'doji':
            print("Strategy fail: Doji found in candles 2-4.")
            return False, "No Engulfing Pattern"

        if not (dir_2 == dir_3 == dir_4):
            print(f"Strategy fail: Candles 2-4 not same direction ({dir_4}, {dir_3}, {dir_2})")
            return False, "No Engulfing Pattern"
        
        # 2. Candle 1 is opposite direction
        dir_1 = self._get_candle_direction(candle_1)
        
        if dir_1 == 'doji':
            print("Strategy fail: Candle 1 is a doji.")
            return False, "No Engulfing Pattern"

        if dir_1 == dir_2:
            print(f"Strategy fail: Candle 1 ({dir_1}) same direction as Candle 2 ({dir_2})")
            return False, "No Engulfing Pattern"
        
        # 3. Candle 1's body > Candle 2's body
        body_1 = self._get_body_size(candle_1)
        body_2 = self._get_body_size(candle_2)

        if body_1 <= body_2:
            print(f"Strategy fail: Candle 1 body ({body_1}) not > Candle 2 body ({body_2})")
            return False, "No Engulfing Pattern"
        
        # All conditions are met
        print(f"*** STRATEGY MET: EngulfingPattern on {self.instrument} ***")
        return True, "Engulfing Pattern Found"

class SRBreakout(Strategy):
    """
    Detects Support/Resistance (S/R) levels based on pin-bar structure 
    and checks if the latest candle closes across the established S/R.
    """
    def __init__(self):
        self._instrument = "XAU_USD"
        self._timeframe = "M30"
        # 51 completed candles for a robust check (50 for S/R + 1 for breakout)
        self._min_required_completed_candles = 51 
        # Request 52
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
        
        historical_candles = candles[:-1]
        
        support_levels = []
        resistance_levels = []
        
        # S/R Detection Loop
        # Iterate over pairs (c_prev, c_curr) to detect levels
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

        # Level Consolidation (5-pip rule implemented by finding the extreme level)
        
        # Find the single lowest support level (most extreme support)
        best_support = min(support_levels) if support_levels else None
        
        # Find the single highest resistance level (most extreme resistance)
        best_resistance = max(resistance_levels) if resistance_levels else None

        # Breakout Check
        
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