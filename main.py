import schedule
import time
import os
import argparse
from dotenv import load_dotenv

# Import custom modules
from src.oanda_connector import OandaConnector
from src.webhook_notifier import WebhookNotifier
from src.strategies import EngulfingStrategy, SRBreakout
from src.strategy_runner import StrategyRunner
from src.backtester import Backtester

def get_strategies(strategy_names, instrument, timeframe):
    """Initializes and returns a list of strategy objects based on names."""
    all_strategies = {
        "EngulfingStrategy": EngulfingStrategy(instrument=instrument, timeframe=timeframe),
        "SRBreakout": SRBreakout(instrument=instrument, timeframe=timeframe),
        # Add any new strategies here
    }
    
    if "all" in strategy_names:
        return list(all_strategies.values())
    
    selected_strategies = []
    for name in strategy_names:
        if name in all_strategies:
            selected_strategies.append(all_strategies[name])
        else:
            print(f"Warning: Strategy '{name}' not found. Skipping.")
    return selected_strategies

def main():
    # Load .env file from the project's root directory
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="OANDA Strategy Scanner and Backtester.")
    parser.add_argument("--mode", type=str, choices=['live', 'backtest'], default='live',
                        help="Operating mode: 'live' for real-time scanning or 'backtest' for simulation.")
    
    # Backtesting arguments (only required if mode is backtest)
    parser.add_argument("--instrument", type=str, default=os.getenv("OANDA_INSTRUMENT", "XAU_USD"),
                        help="Instrument to run strategies on (e.g., EUR_USD).")
    parser.add_argument("--timeframe", type=str, default=os.getenv("OANDA_TIMEFRAME", "M30"),
                        help="Timeframe for the strategy (e.g., H1, M30).")
    parser.add_argument("--strategies", nargs='+', default=['all'],
                        help="List of strategy names to run or 'all'.")
    parser.add_argument("--start-date", type=str, help="Start date for backtest (YYYY-MM-DDTHH:MM:SSZ). Required in backtest mode.")
    parser.add_argument("--end-date", type=str, help="End date for backtest (YYYY-MM-DDTHH:MM:SSZ). Required in backtest mode.")
    
    args = parser.parse_args()
    
    print(f"Starting strategy bot in {args.mode.upper()} mode...")
    
    try:
        connector = OandaConnector()
        notifier = WebhookNotifier()
        
        # Determine the instrument and timeframe to use based on mode
        instrument = args.instrument
        timeframe = args.timeframe
        
        # Initialize strategies
        strategy_list = get_strategies(args.strategies, instrument, timeframe)
        
        if not strategy_list:
            print("No valid strategies found or initialized. Exiting.")
            return

        if args.mode == 'live':
            print(f"Initializing LIVE Strategy Runner for {len(strategy_list)} strategies.")
            runner = StrategyRunner(connector, notifier, strategy_list)
            runner.start()
            
        elif args.mode == 'backtest':
            if not args.start_date or not args.end_date:
                raise ValueError("Backtest mode requires --start-date and --end-date arguments.")

            print(f"Initializing BACKTESTER for {len(strategy_list)} strategies on {instrument}/{timeframe}.")
            backtester = Backtester(
                connector, 
                strategy_list, 
                instrument, 
                timeframe, 
                args.start_date, 
                args.end_date
            )
            backtester.run_backtest()

    except ValueError as e:
        print(f"Configuration Error: {e}")
    except KeyboardInterrupt:
        print("\nStopping application...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()