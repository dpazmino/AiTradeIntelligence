from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
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
        return "\n".join([
            f"Strategy: {strategy}\n"
            f"Signal: {'Buy' if signal['buy'] else 'Sell' if signal['sell'] else 'Hold'}\n"
            f"Confidence: {signal['confidence']:.2f}\n"
            for strategy, signal in signals.items()
        ])
    
    def _format_market_trends(self, trends):
        return "\n".join([
            f"Timeframe: {trend['timeframe']}\n"
            f"Analysis: {trend['analysis']}\n"
            for trend in trends
        ])
    
    def _format_sentiment(self, sentiment):
        return "\n".join([
            f"Timeframe: {s['timeframe']}\n"
            f"Analysis: {s['analysis']}\n"
            for s in sentiment
        ])
    
    def _parse_decision(self, response):
        return {
            'decision': response,
            'timestamp': pd.Timestamp.now()
        }
