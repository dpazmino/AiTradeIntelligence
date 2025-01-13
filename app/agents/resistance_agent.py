from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import pandas as pd

class ResistanceAnalysisAgent:
    def __init__(self, model="gpt-4"):
        self.chat_model = ChatOpenAI(model=model)

    def analyze_resistance(self, market_data, entry_price, exit_price):
        system_prompt = self._get_system_prompt()
        market_context = self._prepare_market_context(market_data, entry_price, exit_price)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=market_context)
        ]

        response = self.chat_model(messages)
        return self._parse_response(response.content)

    def _get_system_prompt(self):
        return """
        You are an expert technical analyst specializing in identifying resistance levels using candlestick patterns.
        Analyze the provided price data and determine if there are any significant resistance levels between the given entry and exit prices.

        Focus on:
        1. Historical price rejection points
        2. Major swing highs
        3. High-volume price levels
        4. Candlestick reversal patterns
        5. Previous support/resistance flips

        Provide your analysis in the following format:
        1. Resistance levels identified: [list of price levels]
        2. Strength of resistance (0-1 for each level)
        3. Volume confirmation (yes/no)
        4. Trading recommendation (PROCEED/DO_NOT_BUY)
        5. Confidence in analysis (0-1)
        6. Brief explanation
        """

    def _prepare_market_context(self, market_data, entry_price, exit_price):
        # Get key price levels
        high = market_data['High'].max()
        low = market_data['Low'].min()
        current_price = market_data['Close'].iloc[-1]
        avg_volume = market_data['Volume'].mean()
        
        # Get recent price action
        recent_highs = market_data['High'].tail(10).tolist()
        recent_volumes = market_data['Volume'].tail(10).tolist()

        return f"""
        Market Analysis Context:
        
        Target Range Analysis:
        Entry Price: ${entry_price:.2f}
        Exit Price: ${exit_price:.2f}
        Current Price: ${current_price:.2f}
        
        Historical Context:
        All-time High: ${high:.2f}
        All-time Low: ${low:.2f}
        Average Volume: {avg_volume:,.0f}
        
        Recent Price Action:
        Last 10 Highs: {recent_highs}
        Last 10 Volumes: {recent_volumes}
        
        Please analyze if there are significant resistance levels between ${entry_price:.2f} and ${exit_price:.2f} 
        that could impede price movement.
        """

    def _parse_response(self, response):
        lines = response.strip().split('\n')
        result = {
            'resistance_levels': [],
            'strength': 0.0,
            'volume_confirmed': False,
            'recommendation': 'PROCEED',
            'confidence': 0.0,
            'explanation': ''
        }

        for line in lines:
            line = line.lower().strip()
            if 'resistance levels' in line:
                try:
                    # Extract price levels from the response
                    levels = [float(x.strip('$').strip()) for x in line.split(':')[1].strip('[]').split(',')]
                    result['resistance_levels'] = levels
                except:
                    pass
            elif 'strength' in line:
                try:
                    result['strength'] = float(line.split(':')[1].strip())
                except:
                    pass
            elif 'volume confirmation' in line:
                result['volume_confirmed'] = 'yes' in line
            elif 'trading recommendation' in line:
                result['recommendation'] = 'DO_NOT_BUY' if 'do_not_buy' in line else 'PROCEED'
            elif 'confidence' in line:
                try:
                    result['confidence'] = float(line.split(':')[1].strip())
                except:
                    pass
            elif 'explanation' in line:
                result['explanation'] = line.split(':')[1].strip()

        return result
