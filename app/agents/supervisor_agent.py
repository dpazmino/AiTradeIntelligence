from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import pandas as pd

class SupervisorAgent:
    def __init__(self, model="gpt-4"):
        self.chat_model = ChatOpenAI(model=model)

    def make_decision(self, trading_signals, market_trends, sentiment_analysis):
        system_prompt = self._get_system_prompt()
        context = self._prepare_context(trading_signals, market_trends, sentiment_analysis)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context)
        ]

        response = self.chat_model(messages)
        return self._parse_decision(response.content)

    def _get_system_prompt(self):
        return """
        You are the chief investment officer of an AI-driven hedge fund.
        Your role is to analyze signals from multiple sources and make final trading decisions.

        Consider:
        1. Trading strategy signals
        2. Market trend analysis across timeframes
        3. Sentiment analysis
        4. Risk management
        5. Portfolio exposure

        Provide decisions in the following format:
        1. Trading action (buy/sell/hold)
        2. Confidence level (0-1)
        3. Position size recommendation (%)
        4. Risk assessment
        5. Supporting rationale
        """

    def _prepare_context(self, trading_signals, market_trends, sentiment_analysis):
        return f"""
        Trading Signals Summary:
        {self._format_trading_signals(trading_signals)}

        Market Trends:
        {self._format_market_trends(market_trends)}

        Sentiment Analysis:
        {self._format_sentiment(sentiment_analysis)}

        Please provide a comprehensive trading decision based on this information.
        """

    def _format_trading_signals(self, signals):
        formatted_signals = []
        for strategy, signal in signals.items():
            signal_type = 'Buy' if signal.get('buy', False) else 'Sell' if signal.get('sell', False) else 'Hold'
            confidence = signal.get('confidence', 0.0)
            formatted_signals.append(
                f"Strategy: {strategy}\n"
                f"Signal: {signal_type}\n"
                f"Confidence: {confidence:.2f}\n"
            )
        return "\n".join(formatted_signals)

    def _format_market_trends(self, trends):
        formatted_trends = []
        for timeframe, analysis in trends.items():
            formatted_trends.append(
                f"Timeframe: {timeframe}\n"
                f"Analysis: {analysis.get('analysis', 'No analysis available')}\n"
            )
        return "\n".join(formatted_trends)

    def _format_sentiment(self, sentiment):
        formatted_sentiment = []
        for timeframe, analysis in sentiment.items():
            formatted_sentiment.append(
                f"Timeframe: {timeframe}\n"
                f"Analysis: {analysis.get('analysis', 'No analysis available')}\n"
            )
        return "\n".join(formatted_sentiment)

    def _parse_decision(self, response):
        return {
            'decision': response,
            'timestamp': pd.Timestamp.now()
        }