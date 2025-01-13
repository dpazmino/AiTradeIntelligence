from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import pandas as pd
from datetime import datetime, timedelta

class StrategyRecommendationAgent:
    def __init__(self, model="gpt-4"):
        self.chat_model = ChatOpenAI(model=model)
        
    def recommend_strategies(self, user_profile, market_data, strategy_performance):
        """Generate personalized strategy recommendations"""
        system_prompt = self._get_system_prompt()
        analysis_context = self._prepare_context(user_profile, market_data, strategy_performance)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=analysis_context)
        ]
        
        response = self.chat_model(messages)
        return self._parse_response(response.content)
    
    def _get_system_prompt(self):
        return """
        You are an expert trading strategy advisor. Your role is to analyze user preferences,
        market conditions, and strategy performance to recommend the most suitable trading approaches.
        
        Consider the following factors:
        1. User's risk tolerance and investment goals
        2. Historical performance of available strategies
        3. Current market conditions and trends
        4. Strategy complexity and user experience level
        5. Portfolio diversification needs
        
        Provide recommendations in the following format:
        1. Primary Strategy Recommendation
        2. Secondary/Complementary Strategies
        3. Risk Assessment
        4. Implementation Tips
        5. Performance Expectations
        6. Market Condition Requirements
        
        Make your recommendations specific, actionable, and well-reasoned.
        """
    
    def _prepare_context(self, user_profile, market_data, strategy_performance):
        # Format market conditions
        market_summary = f"""
        Market Conditions:
        Current Price: ${market_data['Close'].iloc[-1]:.2f}
        30-day Change: {((market_data['Close'].iloc[-1] / market_data['Close'].iloc[0] - 1) * 100):.1f}%
        Volatility: {market_data['Close'].std() / market_data['Close'].mean() * 100:.1f}%
        Volume Trend: {'Increasing' if market_data['Volume'].iloc[-1] > market_data['Volume'].mean() else 'Decreasing'}
        """
        
        # Format strategy performance
        performance_summary = "\nStrategy Performance:\n"
        for strategy, metrics in strategy_performance.items():
            performance_summary += f"{strategy}:\n"
            for metric, value in metrics.items():
                performance_summary += f"  - {metric}: {value}\n"
        
        # Format user profile
        profile_summary = f"""
        User Profile:
        Risk Tolerance: {user_profile.get('risk_tolerance', 'Medium')}
        Experience Level: {user_profile.get('experience_level', 'Intermediate')}
        Investment Horizon: {user_profile.get('investment_horizon', 'Medium-term')}
        """
        
        return f"""
        Please analyze the following information and provide personalized strategy recommendations:
        
        {profile_summary}
        
        {market_summary}
        
        {performance_summary}
        """
    
    def _parse_response(self, response):
        return {
            'recommendations': response,
            'timestamp': pd.Timestamp.now(),
            'version': '1.0'
        }
    
    def calculate_strategy_performance(self, trading_history):
        """Calculate performance metrics for each strategy"""
        performance = {}
        
        for strategy in trading_history.groupby('strategy'):
            strategy_name, trades = strategy
            
            # Calculate basic performance metrics
            wins = trades[trades['exit_price'] > trades['entry_price']].shape[0]
            total_trades = trades.shape[0]
            win_rate = wins / total_trades if total_trades > 0 else 0
            
            # Calculate returns
            returns = ((trades['exit_price'] - trades['entry_price']) / trades['entry_price'])
            avg_return = returns.mean() if not returns.empty else 0
            max_drawdown = (returns + 1).cumprod().expanding().max() - (returns + 1).cumprod()
            max_drawdown = max_drawdown.max() if not max_drawdown.empty else 0
            
            performance[strategy_name] = {
                'win_rate': f"{win_rate:.1%}",
                'avg_return': f"{avg_return:.1%}",
                'max_drawdown': f"{max_drawdown:.1%}",
                'total_trades': total_trades
            }
        
        return performance
