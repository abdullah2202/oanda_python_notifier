import schedule
import time
import os
from dotenv import load_dotenv

# Import custom modules
from src.oanda_connector import OandaConnector
from src.webhook_notifier import WebhookNotifier
from src.strategies import EngulfingStrategy, SRBreakout
from src.strategy_runner import StrategyRunner

def main():
    # Load .env file from the project's root directory
    load_dotenv()
    
    print("Starting strategy bot...")
    
    try:
        connector = OandaConnector()

        notifier = WebhookNotifier()

        print("Initializing strategies...")
        strategy_list = [
            EngulfingStrategy(),
            SRBreakout(),
        ]

        runner = StrategyRunner(connector, notifier, strategy_list)

        print("Scheduling job to run every 1 minute.")
        # Run the check once immediately, then every minute
        runner._run_all_checks() 
        
        schedule.every(1).minute.do(runner._run_all_checks)

        print("Scheduler started. Waiting for jobs... (Press Ctrl+C to stop)")
        while True:
            schedule.run_pending()
            time.sleep(1)
            
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()