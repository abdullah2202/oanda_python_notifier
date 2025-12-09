from abc import ABC, abstractmethod

# Value of 1 pip. Adjust for different instruments
PIP_SIZE = 0.01

class Strategy(ABC):
    """
    Abstract Base Class for all trading strategies.
    """
    
    @abstractmethod
    def check(self, candles):
        # Returns (is_strategy_met: bool, notification_detail: str)
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
        # Total number of candles to request from API
        pass
        
    @property
    @abstractmethod
    def min_required_completed_candles(self):
        # Minimum completed candles needed for strategy logic
        pass