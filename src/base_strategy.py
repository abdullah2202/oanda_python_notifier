from abc import ABC, abstractmethod

# Value of 1 pip. Adjust for different instruments
PIP_SIZE = 0.01

class Strategy(ABC):
    """
    Abstract Base Class for all trading strategies.
    Defines common attributes and the required 'check' interface.
    """

    def __init__(self, instrument, timeframe):
        # These attributes are set during initialization and are inherited by subclasses.
        self.instrument = instrument
        self.timeframe = timeframe

        # These are default values, intended to be overwritten by the subclass 
        # constructors (e.g., EngulfingStrategy.__init__).
        self.required_candles = 4
        self.min_required_completed_candles = 4
    
    @abstractmethod
    def check(self, candles: list) -> tuple[bool, str]:
        """
        Runs the strategy check against the list of candles. Must be implemented 
        by all derived classes.
        
        Args:
            candles: A list of candle data dictionaries.
            
        Returns:
            A tuple (is_strategy_met: bool, notification_detail: str)
        """
        # Returns (is_strategy_met: bool, notification_detail: str)
        pass

# Removed all conflicting abstract property definitions (@property @abstractmethod)
# as the attributes are now set in __init__ and accessed directly by subclasses.