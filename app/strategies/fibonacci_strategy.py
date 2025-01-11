from .strategy_base import TradingStrategy
import pandas as pd
import numpy as np

class FibonacciStrategy(TradingStrategy):
    def __init__(self):
        super().__init__("Fibonacci")
        self.fib_levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]

    def calculate_fib_levels(self, high, low):
        levels = {}
        diff = high - low
        
        for level in self.fib_levels:
            levels[level] = high - (diff * level)
        
        return levels

    def generate_signals(self, data: pd.DataFrame) -> dict:
        signals = {
            'buy': False,
            'sell': False,
            'strength': 0.0
        }

        if len(data) < 30:
            return signals

        # Find swing high and low
        high = data['High'].max()
        low = data['Low'].min()
        current_price = data['Close'].iloc[-1]
        
        fib_levels = self.calculate_fib_levels(high, low)
        
        # Check for buy signals near support levels
        for level in [0.236, 0.382, 0.618]:
            if abs(current_price - fib_levels[level]) / current_price < 0.02:
                signals['buy'] = True
                signals['strength'] = 1 - abs(current_price - fib_levels[level]) / current_price
                break

        return signals

    def get_prompt(self) -> str:
        return """
        You are a Fibonacci retracement trading expert. Analyze the given data and provide trading signals based on:
        1. Key Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%)
        2. Price action around these levels
        3. Trend direction and momentum
        4. Volume confirmation
        
        Consider:
        - The strength of the trend leading to retracement
        - Multiple timeframe confirmation
        - Support/resistance confluence
        - Market structure
        
        Provide your analysis in the following format:
        1. Identified retracement levels
        2. Signal type (buy/sell)
        3. Confidence level (0-1)
        4. Risk/reward ratio
        """
