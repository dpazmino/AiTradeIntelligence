from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import pandas as pd

class SupervisorAgent:
    def __init__(self, model="gpt-4"):
        self.chat_model = ChatOpenAI(model=model)

    def make_decision(self, trading_signals, market_trends, sentiment_analysis, resistance_analysis=None):
        system_prompt = self._get_system_prompt()
        context = self._prepare_context(trading_signals, market_trends, sentiment_analysis, resistance_analysis)

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
        4. Resistance analysis
        5. Risk management
        6. Portfolio exposure

        Provide decisions in the following format:
        1. Trading action (BUY/SELL/HOLD)
        2. Confidence level (0-1)
        3. Position size recommendation (%)
        4. Risk assessment (Low/Medium/High)
        5. Supporting rationale (Brief explanation)
        """

    def _prepare_context(self, trading_signals, market_trends, sentiment_analysis, resistance_analysis=None):
        context = f"""
        Trading Signals Summary:
        {self._format_trading_signals(trading_signals)}

        Market Trends:
        {self._format_market_trends(market_trends)}

        Sentiment Analysis:
        {self._format_sentiment(sentiment_analysis)}
        """

        if resistance_analysis:
            context += f"\nResistance Analysis:\n{self._format_resistance(resistance_analysis)}"

        context += "\nPlease provide a comprehensive trading decision based on this information."
        return context

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

    def _format_resistance(self, resistance_analysis):
        formatted_resistance = []
        for strategy, analysis in resistance_analysis.items():
            formatted_resistance.append(
                f"Strategy: {strategy}\n"
                f"Recommendation: {analysis['recommendation']}\n"
                f"Resistance Levels: {', '.join(f'${level:.2f}' for level in analysis['resistance_levels'])}\n"
                f"Confidence: {analysis['confidence']:.2f}\n"
                f"Explanation: {analysis['explanation']}\n"
            )
        return "\n".join(formatted_resistance)

    def _parse_decision(self, response):
        lines = response.strip().split('\n')
        decision_dict = {}

        # Extract key components from response
        for line in lines:
            if 'Trading action' in line.lower():
                decision_dict['action'] = line.split(':')[-1].strip()
            elif 'confidence' in line.lower():
                try:
                    confidence = float(line.split(':')[-1].strip())
                    decision_dict['confidence'] = min(1.0, max(0.0, confidence))
                except:
                    decision_dict['confidence'] = 0.8
            elif 'risk' in line.lower():
                decision_dict['risk'] = line.split(':')[-1].strip()
            elif 'rationale' in line.lower() or 'supporting rationale' in line.lower():
                # Get everything after the colon for rationale
                decision_dict['rationale'] = ': '.join(line.split(':')[1:]).strip()

        # Format the final decision text with complete rationale
        decision_text = (
            f"{decision_dict.get('action', 'HOLD')} - "
            f"Risk: {decision_dict.get('risk', 'Medium')}\n"
            f"Rationale: {decision_dict.get('rationale', 'Insufficient data for strong conviction')}"
        )

        return {
            'decision': decision_text,
            'confidence': decision_dict.get('confidence', 0.8),
            'timestamp': pd.Timestamp.now()
        }