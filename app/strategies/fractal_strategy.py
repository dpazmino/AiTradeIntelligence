from .strategy_base import TradingStrategy
import pandas as pd
import numpy as np

class FractalStrategy(TradingStrategy):
    def __init__(self):
        super().__init__("Fractal")
        self.window_size = 5  # Default window for fractal pattern identification

    def calculate_fractal_dimension(self, prices):
        """Calculate the fractal dimension using box-counting method"""
        if len(prices) < self.window_size:
            return 1.0
            
        # Normalize prices to [0,1] range
        normalized = (prices - prices.min()) / (prices.max() - prices.min())
        
        # Calculate box counts at different scales
        scales = np.logspace(-3, 0, num=20)
        counts = []
        
        for scale in scales:
            boxes = np.ceil(normalized / scale)
            counts.append(len(np.unique(boxes)))
            
        # Fit line to log-log plot
        coeffs = np.polyfit(np.log(scales), np.log(counts), 1)
        return -coeffs[0]  # Fractal dimension is the negative slope

    def identify_fractals(self, data):
        """Identify bullish and bearish fractal patterns"""
        if len(data) < self.window_size:
            return pd.DataFrame(columns=['bullish', 'bearish'])
            
        fractals = pd.DataFrame(index=data.index, columns=['bullish', 'bearish'])
        fractals['bullish'] = False
        fractals['bearish'] = False
        
        for i in range(2, len(data) - 2):
            # Bullish fractal (lower low with higher values around)
            if (data['Low'].iloc[i-2:i].min() > data['Low'].iloc[i] and 
                data['Low'].iloc[i+1:i+3].min() > data['Low'].iloc[i]):
                fractals.iloc[i, fractals.columns.get_loc('bullish')] = True
                
            # Bearish fractal (higher high with lower values around)
            if (data['High'].iloc[i-2:i].max() < data['High'].iloc[i] and 
                data['High'].iloc[i+1:i+3].max() < data['High'].iloc[i]):
                fractals.iloc[i, fractals.columns.get_loc('bearish')] = True
                
        return fractals

    def generate_signals(self, data: pd.DataFrame) -> dict:
        signals = {
            'buy': False,
            'sell': False,
            'strength': 0.0
        }

        if len(data) < self.window_size:
            return signals

        # Calculate fractal dimension
        fractal_dim = self.calculate_fractal_dimension(data['Close'])
        
        # Identify fractal patterns
        fractals = self.identify_fractals(data)
        
        # Generate signals based on recent fractals and dimension
        recent_fractals = fractals.iloc[-3:]
        
        if recent_fractals['bullish'].any():
            signals['buy'] = True
            signals['strength'] = min(1.0, fractal_dim / 2)  # Normalize strength
            
        elif recent_fractals['bearish'].any():
            signals['sell'] = True
            signals['strength'] = min(1.0, fractal_dim / 2)

        return signals

    def get_prompt(self) -> str:
        return """
        You are a fractal trading pattern expert. Analyze the given data and provide trading signals based on:
        1. Fractal pattern formations (bullish/bearish)
        2. Fractal dimension analysis
        3. Self-similarity across timeframes
        4. Price action geometry
        
        Consider:
        - The strength and clarity of fractal patterns
        - Market phase transitions
        - Harmonic pattern completions
        - Time/price symmetry
        - Fractal dimension trends
        
        Provide your analysis in the following format:
        1. Identified fractal patterns
        2. Current market phase
        3. Signal type (buy/sell)
        4. Confidence level (0-1)
        5. Risk assessment
        6. Projected pattern completion levels
        """
