import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import os

class OandaConnector:
    def __init__(self):
        self.api_key = os.getenv("OANDA_API_KEY")
        self.account_id = os.getenv("OANDA_ACCOUNT_ID")
        env = os.getenv("OANDA_ENV", "practice")
        
        if not self.api_key or not self.account_id:
            raise ValueError("OANDA_API_KEY and OANDA_ACCOUNT_ID must be set in .env file")

        self.client = oandapyV20.API(access_token=self.api_key, environment=env)
        print(f"OandaConnector initialized for '{env}' environment.")

    # FIX: Added optional from_date and to_date parameters
    def get_candles(self, instrument, timeframe, count=None, from_date=None, to_date=None):
        params = {
            "granularity": timeframe,
            "price": "M"  # Midpoint candles (o, h, l, c)
        }
        
        # Determine the request type: count-based for live, date-based for backtest
        if from_date and to_date:
            params["from"] = from_date
            params["to"] = to_date
        elif count is not None:
            # Fallback to count if dates are not provided (used by live runner)
            params["count"] = count
        else:
            # Default to a small count if no specific instructions are given
            params["count"] = 5 
            
        r = instruments.InstrumentsCandles(instrument=instrument, params=params)
        
        try:
            self.client.request(r)
            # Filter for *only* completed candles
            # Note: This filtering is mainly for live data. Historical data is typically all complete.
            completed_candles = [c for c in r.response.get('candles', []) if c['complete']]
            return completed_candles
        except oandapyV20.exceptions.V20Error as err:
            # Limit the error string to avoid massive console output
            error = str(err)[:100] 
            print(f"OANDA API Error: {error}")
            return None