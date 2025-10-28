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

    def get_candles(self, instrument, timeframe, count):
        params = {
            "granularity": timeframe,
            "count": count,
            "price": "M"  # Midpoint candles (o, h, l, c)
        }
        r = instruments.InstrumentsCandles(instrument=instrument, params=params)
        
        try:
            self.client.request(r)
            # Filter for *only* completed candles
            completed_candles = [c for c in r.response.get('candles', []) if c['complete']]
            return completed_candles
        except oandapyV20.exceptions.V20Error as err:
            print(f"OANDA API Error: {err}")
            return None