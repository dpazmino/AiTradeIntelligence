from .strategy_base import TradingStrategy
import pandas as pd

class MACDStrategy(TradingStrategy):
    def __init__(self):
        super().__init__("MACD")

    def generate_signals(self, data: pd.DataFrame) -> dict:
        signals = {
            'buy': False,
            'sell': False,
            'strength': 0.0
        }

        if len(data) < 2:
            return signals

        # Check if MACD crosses above signal line
        if (data['MACD'].iloc[-2] <= data['Signal_Line'].iloc[-2] and 
            data['MACD'].iloc[-1] > data['Signal_Line'].iloc[-1]):
            signals['buy'] = True
            signals['strength'] = abs(data['MACD'].iloc[-1] - data['Signal_Line'].iloc[-1])

        # Check if MACD crosses below signal line
        elif (data['MACD'].iloc[-2] >= data['Signal_Line'].iloc[-2] and 
              data['MACD'].iloc[-1] < data['Signal_Line'].iloc[-1]):
            signals['sell'] = True
            signals['strength'] = abs(data['MACD'].iloc[-1] - data['Signal_Line'].iloc[-1])

        return signals

    def get_prompt(self) -> str:
        return """
        You are a MACD trading strategy expert. Analyze the given data and provide trading signals based on:
        1. MACD line crossing above/below signal line
        2. MACD histogram momentum
        3. Trend confirmation using price action
        4. Volume confirmation
        
        Consider:
        - The strength of the crossover
        - The overall trend direction
        - Recent price momentum
        - Historical reliability of similar signals
        
        Provide your analysis in the following format:
        1. Signal type (buy/sell)
        2. Confidence level (0-1)
        3. Supporting rationale
        4. Risk assessment
        """
