from .strategy_base import TradingStrategy
import pandas as pd

class BollingerStrategy(TradingStrategy):
    def __init__(self):
        super().__init__("Bollinger Bands")

    def generate_signals(self, data: pd.DataFrame) -> dict:
        signals = {
            'buy': False,
            'sell': False,
            'strength': 0.0
        }

        if len(data) < 20:
            return signals

        current_price = data['Close'].iloc[-1]
        lower_band = data['Lower_Band'].iloc[-1]
        upper_band = data['Upper_Band'].iloc[-1]
        
        # Calculate % distance from bands
        lower_band_dist = (current_price - lower_band) / lower_band
        upper_band_dist = (upper_band - current_price) / current_price
        
        # Buy signal when price is near lower band
        if lower_band_dist < 0.02:
            signals['buy'] = True
            signals['strength'] = 1 - lower_band_dist
        
        # Sell signal when price is near upper band
        elif upper_band_dist < 0.02:
            signals['sell'] = True
            signals['strength'] = 1 - upper_band_dist

        return signals

    def get_prompt(self) -> str:
        return """
        You are a Bollinger Bands trading expert. Analyze the given data and provide trading signals based on:
        1. Price position relative to bands
        2. Band width (volatility)
        3. Price momentum
        4. Band walking patterns
        
        Consider:
        - Band squeeze and expansion patterns
        - Price touching or breaking bands
        - Volume confirmation
        - Overall trend direction
        
        Provide your analysis in the following format:
        1. Band position analysis
        2. Volatility assessment
        3. Signal type (buy/sell)
        4. Confidence level (0-1)
        5. Risk considerations
        """
