import autogen
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

class TradingAgent:
    def __init__(self, strategy, model="gpt-4"):
        self.strategy = strategy
        self.chat_model = ChatOpenAI(model=model)
        
    def analyze(self, market_data):
        # Get strategy-specific signals
        signals = self.strategy.generate_signals(market_data)
        
        # Prepare the prompt
        system_prompt = self.strategy.get_prompt()
        market_context = self._prepare_market_context(market_data)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=market_context)
        ]
        
        # Get LLM response
        response = self.chat_model(messages)
        
        # Combine quantitative and qualitative signals
        final_signal = self._combine_signals(signals, response.content)
        
        return final_signal
    
    def _prepare_market_context(self, market_data):
        return f"""
        Recent market data:
        Close price: {market_data['Close'].iloc[-1]:.2f}
        Volume: {market_data['Volume'].iloc[-1]}
        Price change: {(market_data['Close'].iloc[-1] - market_data['Close'].iloc[-2]) / market_data['Close'].iloc[-2] * 100:.2f}%
        
        Technical indicators:
        MACD: {market_data['MACD'].iloc[-1]:.3f}
        RSI: {market_data['RSI'].iloc[-1]:.2f}
        Bollinger Bands position: {self._calculate_bb_position(market_data)}
        """
    
    def _calculate_bb_position(self, market_data):
        current_price = market_data['Close'].iloc[-1]
        upper_band = market_data['Upper_Band'].iloc[-1]
        lower_band = market_data['Lower_Band'].iloc[-1]
        
        if current_price > upper_band:
            return "Above upper band"
        elif current_price < lower_band:
            return "Below lower band"
        else:
            return "Within bands"
    
    def _combine_signals(self, quantitative_signals, llm_response):
        # Parse LLM response and combine with quantitative signals
        combined_signal = {
            'buy': quantitative_signals['buy'],
            'sell': quantitative_signals['sell'],
            'confidence': quantitative_signals['strength'],
            'analysis': llm_response
        }
        
        return combined_signal
