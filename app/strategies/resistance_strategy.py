from .strategy_base import TradingStrategy
import pandas as pd
import numpy as np

class ResistanceStrategy(TradingStrategy):
    def __init__(self):
        super().__init__("Resistance")
        self.window_size = 20  # For calculating local highs/lows

    def identify_resistance_levels(self, data):
        """Identify potential resistance levels using price action"""
        highs = data['High'].rolling(window=self.window_size, center=True).max()
        resistance_levels = []
        
        # Find local maxima that could act as resistance
        for i in range(self.window_size, len(data) - self.window_size):
            if highs.iloc[i] == data['High'].iloc[i]:
                resistance_levels.append(data['High'].iloc[i])
        
        return sorted(set(resistance_levels))  # Remove duplicates and sort

    def calculate_resistance_strength(self, price, resistance_level, data):
        """Calculate the strength of a resistance level"""
        # Calculate how many times price tested this level
        tests = sum(abs(data['High'] - resistance_level) / resistance_level < 0.01)
        
        # Calculate proximity to current price
        proximity = abs(price - resistance_level) / resistance_level
        
        # Combine factors for overall strength
        strength = min(1.0, (tests * 0.2) * (1 - proximity))
        return strength

    def generate_signals(self, data: pd.DataFrame) -> dict:
        signals = {
            'buy': False,
            'sell': False,
            'strength': 0.0
        }

        if len(data) < self.window_size * 2:
            return signals

        current_price = data['Close'].iloc[-1]
        resistance_levels = self.identify_resistance_levels(data)
        
        if not resistance_levels:
            return signals

        # Find nearest resistance level above current price
        levels_above = [level for level in resistance_levels if level > current_price]
        if not levels_above:
            signals['buy'] = True
            signals['strength'] = 0.8  # High confidence if no resistance above
            return signals

        nearest_resistance = min(levels_above)
        resistance_strength = self.calculate_resistance_strength(
            current_price, nearest_resistance, data
        )

        # Generate signals based on resistance analysis
        price_to_resistance = (nearest_resistance - current_price) / current_price
        
        if price_to_resistance > 0.1:  # More than 10% to resistance
            signals['buy'] = True
            signals['strength'] = 1 - resistance_strength  # Lower strength if strong resistance
        else:
            signals['sell'] = True  # Sell signal when near strong resistance
            signals['strength'] = resistance_strength

        return signals

    def get_prompt(self) -> str:
        return """
        You are a technical analyst specializing in resistance level analysis.
        Analyze the given market data focusing on:
        1. Historical price rejection points
        2. Volume confirmation of resistance levels
        3. Multiple timeframe resistance confluence
        4. Price action around key levels
        5. Breakout potential
        
        Consider:
        - The strength of each resistance level
        - Number of times level was tested
        - Volume profile at resistance
        - Recent price momentum
        - Market structure
        
        Provide analysis in the following format:
        1. Identified resistance levels
        2. Strength of each level (0-1)
        3. Trading recommendation (buy/sell/hold)
        4. Risk assessment
        5. Potential profit targets
        """
