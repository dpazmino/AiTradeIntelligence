from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import pandas as pd

class MarketTrendAgent:
    def __init__(self, timeframe, model="gpt-4"):
        # Map timeframes to valid yfinance periods
        self.timeframe_mapping = {
            '30d': '1mo',
            '15d': '15d',
            '3d': '5d'
        }
        self.timeframe = self.timeframe_mapping.get(timeframe, '1mo')
        self.chat_model = ChatOpenAI(model=model)

    def analyze_trend(self, market_data):
        if market_data.empty:
            return {
                'timeframe': self.timeframe,
                'analysis': f"No market data available for the specified timeframe: {self.timeframe}",
                'timestamp': pd.Timestamp.now()
            }

        system_prompt = self._get_system_prompt()
        market_context = self._prepare_market_context(market_data)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=market_context)
        ]

        response = self.chat_model(messages)
        return self._parse_response(response.content)

    def _get_system_prompt(self):
        return f"""
        You are a market trend analysis expert focusing on {self.timeframe} trends.
        Analyze the provided market data and provide:
        1. Overall trend direction (bullish/bearish/neutral)
        2. Trend strength (0-1)
        3. Key support and resistance levels
        4. Volume analysis
        5. Market structure analysis
        6. Potential reversal signals

        Consider:
        - Price action patterns
        - Volume confirmation
        - Technical indicator convergence/divergence
        - Market breadth
        """

    def _prepare_market_context(self, market_data):
        if market_data.empty:
            return "No market data available for analysis."

        return f"""
        Market Analysis for {self.timeframe}:

        Price Movement:
        Start: {market_data['Close'].iloc[0]:.2f}
        End: {market_data['Close'].iloc[-1]:.2f}
        Change: {((market_data['Close'].iloc[-1] - market_data['Close'].iloc[0]) / market_data['Close'].iloc[0] * 100):.2f}%

        Volume Analysis:
        Average Volume: {market_data['Volume'].mean():.0f}
        Latest Volume: {market_data['Volume'].iloc[-1]:.0f}

        Technical Indicators:
        RSI: {market_data['RSI'].iloc[-1]:.2f}
        MACD: {market_data['MACD'].iloc[-1]:.3f}
        """

    def _parse_response(self, response):
        return {
            'timeframe': self.timeframe,
            'analysis': response,
            'timestamp': pd.Timestamp.now()
        }