import yfinance as yf
import pandas as pd
import quandl
from datetime import datetime, timedelta

class MarketData:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes

    def get_stock_data(self, symbol, period='1mo', interval='1d'):
        cache_key = f"{symbol}_{period}_{interval}"

        # Check cache first
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_timeout):
                return data

        try:
            # Fetch new data
            stock = yf.Ticker(symbol)
            data = stock.history(period=period, interval=interval)

            # Ensure we have data
            if data.empty:
                return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

            # Cache the result
            self.cache[cache_key] = (data, datetime.now())

            return data
        except Exception as e:
            print(f"Error fetching data for {symbol}: {str(e)}")
            return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

    def get_quandl_data(self, dataset_code, start_date, end_date):
        cache_key = f"quandl_{dataset_code}_{start_date}_{end_date}"

        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_timeout):
                return data

        try:
            data = quandl.get(dataset_code, start_date=start_date, end_date=end_date)
            self.cache[cache_key] = (data, datetime.now())
            return data
        except Exception as e:
            print(f"Error fetching Quandl data: {str(e)}")
            return pd.DataFrame()

    def calculate_technical_indicators(self, df):
        if df.empty:
            return df

        try:
            # MACD
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

            # Bollinger Bands
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['20dSTD'] = df['Close'].rolling(window=20).std()
            df['Upper_Band'] = df['MA20'] + (df['20dSTD'] * 2)
            df['Lower_Band'] = df['MA20'] - (df['20dSTD'] * 2)

            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            return df
        except Exception as e:
            print(f"Error calculating technical indicators: {str(e)}")
            return df