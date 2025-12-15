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
In the root directory, create a file named `.env`. This file holds all the secret keys and configuration. A sample file has been added `.env_sample`. You can use this file and rename it to `.env`.

### 3. Build the Docker Image
From the project's root directory, run:
```bash
docker build -t oanda-scanner .
```

## Running the Bot
The `main.py` script now uses a `--mode` argument to switch between the two primary functions.

### 1. Live Scanning Mode (Default)
In this mode, the bot uses `schedule` to run a check every minute. It fetches the latest candles, checks your strategies, and sends webhook alerts if a signal is generated.

Command:

```bash
docker run --env-file .env -d --name my-oanda-bot oanda-scanner --mode live
```
*Note: If you omit `--mode live`, it defaults to this behaviour.*

### 2. Backtesting Mode (High-Speed Simulation)
This mode runs the simulation instantly over a historical data range. It requires specific arguments to define a test.

*Require Date Formats: Dates must be in OANDA's required ISO 8601 format: `YYY-MM-DDTHH:MM:SSZ` (e.g., `2023-10-01T00:00:00Z`)

#### Command Structure

```bash
docker run --env-file .env --rm --name backtest-run oanda-scanner \
  --mode backtest \
  --instrument <INSTRUMENT> \
  --start-date <START_DATE_ISO8601> \
  --end-date <END_DATE_ISO8601> \
  --strategies <LIST_OF_STRATEGIES> 
```

#### Example (Running two specific strategies)

```bash 
docker run --env-file .env --rm --name backtest-run oanda-scanner \
  --mode backtest \
  --instrument XAU_USD \
  --timeframe M30 \
  --start-date 2023-11-01T00:00:00Z \
  --end-date 2023-11-30T00:00:00Z \
  --strategies EngulfingStrategy SRBreakout
```

#### Example (Running all registered strategies)

```bash
docker run --env-file .env --rm --name backtest-run-all oanda-scanner \
  --mode backtest \
  --instrument EUR_USD \
  --timeframe H4 \
  --start-date 2022-01-01T00:00:00Z \
  --end-date 2023-01-01T00:00:00Z \
  --strategies all
```

*Note: The `--rm` flag automatically cleans up the container after the backtest is complete*


## Managing the Bot
### Viewing Logs
To see the real-time output of the bot (live-mode) or the backtest results:
```bash
docker logs -f my-oanda-bot
```

### Stopping the Bot (Live-Mode)
To stop and remove the container running in live mode:
```bash
# Stop the running container
docker stop my-oanda-bot

# Remove the container
docker rm my-oanda-bot
```

## How to Add a New Strategy
This project is designed to be easily extendable. The base class now automatically handles the `instrument` and `timeframe` you pass to it.

### Step 1: Create the Strategy Class
Open the relevant strategy file (e.g., `src/strategies.py` or a dedicated file like `src/my_strategy.py`) and add a new class that inherits from `Strategy`.

#### Important Changes:

1. Use `super().__init__(instrument, timeframe)`: Pass the arguments up to the parent.

2. Override attributes directly: Define `self.required_candles` and `self.min_required_completed_candles` directly on `self`. Do not use private attributes (`_`) or `@property` decorators for these four attributes, as they are now handled by the base class.


Example Template:

```python
from .base_strategy import Strategy

class MyNewStrategy(Strategy):
    """
    Checks for a simple 3-bar down close.
    """
    # 1. Implement the required constructor
    def __init__(self, instrument, timeframe):
        super().__init__(instrument, timeframe) 
        
        # 2. Override the base class defaults
        self.required_candles = 4 # Total candles to request (3 completed + 1 for safety/indexing)
        self.min_required_completed_candles = 3 # Minimum needed for logic
        
        # NOTE: last_checked_timestamp logic has been moved to the StrategyRunner/Backtester
        
        print(f"MyNewStrategy initialized for {self.instrument} ({self.timeframe})")

    # 3. Implement the core check logic
    def check(self, candles):
        # The StrategyRunner/Backtester handles the new candle check, so no timestamp logic needed here.

        if len(candles) < self.min_required_completed_candles:
             return False, "Not enough candles."
        
        # OANDA candles: candles[-1] is the most recent completed candle
        candle_1 = candles[-1]
        candle_2 = candles[-2]
        candle_3 = candles[-3]

        # Strategy logic
        is_bear_1 = float(candle_1['mid']['c']) < float(candle_1['mid']['o'])
        is_bear_2 = float(candle_2['mid']['c']) < float(candle_2['mid']['o'])
        is_bear_3 = float(candle_3['mid']['c']) < float(candle_3['mid']['o'])

        if is_bear_1 and is_bear_2 and is_bear_3:
            return True, "3 Consecutive Bear Candles Detected."
        
        return False, "No 3 bear candles."
```

### Step 2: Register the Strategy
Open `main.py` and ensure your new strategy class is imported and registered in the `all_strategies` dictionary within the `get_strategies` function:

```python
# ... other imports
# ... (in main.py)
from src.strategies import EngulfingStrategy, SRBreakout, MyNewStrategy # example import

def get_strategies(strategy_names, instrument, timeframe):
    """Initializes and returns a list of strategy objects based on names."""
    all_strategies = {
        "EngulfingStrategy": EngulfingStrategy(instrument=instrument, timeframe=timeframe),
        "SRBreakout": SRBreakout(instrument=instrument, timeframe=timeframe),
        "MyNewStrategy": MyNewStrategy(instrument=instrument, timeframe=timeframe), # Add it here
        # Add any new strategies here
    }
# ...
```

When you rebuild and run your Docker container, the StrategyRunner or Backtester will automatically pick up and run your new strategy.


