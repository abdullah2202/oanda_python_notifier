# OANDA V20 Strategy Scanner Bot

This is a modular Python application designed to scan the OANDA V20 API for specific trading strategies. It runs on a one-minute schedule and sends a notification to a specified webhook when a strategy's conditions are met.

The entire application is packaged to run inside a Docker container.

## Features

* **Modular OOP Design:** New strategies can be added by creating new classes that inherit from the `Strategy` base class.
* **OANDA V20 API:** Uses the `oandapyV20` library for communication with the OANDA API.
* **Webhook Alerts:** Sends a JSON payload to any webhook URL when a trading setup is identified.
* **Scheduled Scans:** Uses the `schedule` library to run checks every minute.
* **Docker Ready:** Includes a `Dockerfile` for containerized deployment.
* **State-Aware:** Strategies include logic to prevent sending duplicate alerts for the same candle.

## Setup and Installation

### 1. Clone the Repository

```bash
git clone <this-repos-url>
cd project-directory
```

### 2. Create the .env File
In the root oanda-scanner/ directory, create a file named .env. This file holds all the secret keys and configuration.

3. Build the Docker Image
From the project's root directory, run:
```bash
docker build -t oanda-scanner .
```

4. Run the Docker Container
Run the image in detached mode, securely passing in the .env file:
```bash
docker run --env-file .env -d --name my-oanda-bot oanda-scanner
```

The bot is now running in the background.

## Managing the Bot
### Viewing Logs
To see the real-time output of the bot, including print statements and strategy checks:
```bash
docker logs -f my-oanda-bot
```

### Stopping the Bot
To stop and remove the container:
```bash
# Stop the running container
docker stop my-oanda-bot

# Remove the container
docker rm my-oanda-bot
```

## How to Add a New Strategy
This project is designed to be easily extendable. Follow these two steps:

### Step 1: Create the Strategy Class
Open ```src/strategies.py``` and add a new class that inherits from ```Strategy```. You must implement all the abstract methods.

Example Template:

```python
from src.strategies import Strategy # Import the base class

class MyNewStrategy(Strategy):
    """
    Checks for a simple 3-bar down close.
    """
    def __init__(self):
        # 1. Define your properties
        self._instrument = "EUR_USD"
        self._timeframe = "H1"
        self._required_candles = 4 # Need 3 + 1 for indexing
        self.last_checked_timestamp = None
        print(f"MyNewStrategy initialized for {self.instrument} ({self.timeframe})")

    # 2. Implement the abstract properties
    @property
    def instrument(self):
        return self._instrument

    @property
    def timeframe(self):
        return self._timeframe

    @property
    def required_candles(self):
        return self._required_candles

    # 3. Implement the core check logic
    def check(self, candles):
        # This check prevents duplicate alerts for the same candle
        current_timestamp = candles[-1]['time']
        if current_timestamp == self.last_checked_timestamp:
            return False # We've already checked this candle
        
        # This is a new candle, so check it and update the state
        self.last_checked_timestamp = current_timestamp
        print(f"\nChecking MyNewStrategy: {current_timestamp}")
        
        # OANDA candles: candles[-1] is the most recent completed candle
        candle_1 = candles[-1]
        candle_2 = candles[-2]
        candle_3 = candles[-3]

        # Your strategy logic
        is_bear_1 = float(candle_1['mid']['c']) < float(candle_1['mid']['o'])
        is_bear_2 = float(candle_2['mid']['c']) < float(candle_2['mid']['o'])
        is_bear_3 = float(candle_3['mid']['c']) < float(candle_3['mid']['o'])

        if is_bear_1 and is_bear_2 and is_bear_3:
            print(f"*** STRATEGY MET: MyNewStrategy on {self.instrument} ***")
            return True # Condition met
        
        print("Strategy fail: Not 3 bear candles.")
        return False
```

Step 2: Register the Strategy
Open main.py. Import your new class and add an instance of it to the strategy_list.

```python
# ... other imports
from src.strategies import EngulfingStrategy, MyNewStrategy  # <-- 1. Import it

def main():
    # ...
    
    # 3. Create and list all strategies
    print("Initializing strategies...")
    strategy_list = [
        EngulfingStrategy(),
        MyNewStrategy(),  # <-- 2. Add an instance here
    ]

    # ...
```

When you rebuild and run your Docker container, the StrategyRunner will automatically pick up and check your new strategy.



