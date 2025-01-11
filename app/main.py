import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from db.database import Database
from data.market_data import MarketData
from strategies.macd_strategy import MACDStrategy
from strategies.fibonacci_strategy import FibonacciStrategy
from strategies.bollinger_strategy import BollingerStrategy
from agents.trading_agents import TradingAgent
from agents.market_trend_agents import MarketTrendAgent
from agents.sentiment_agents import SentimentAgent
from agents.supervisor_agent import SupervisorAgent

# Initialize components
db = Database()
market_data = MarketData()

# Initialize strategies and agents
strategies = {
    'MACD': MACDStrategy(),
    'Fibonacci': FibonacciStrategy(),
    'Bollinger': BollingerStrategy()
}

trading_agents = {
    name: TradingAgent(strategy) for name, strategy in strategies.items()
}

market_trend_agents = {
    timeframe: MarketTrendAgent(timeframe)
    for timeframe in ['30d', '15d', '3d']
}

sentiment_agents = {
    timeframe: SentimentAgent(timeframe)
    for timeframe in ['30d', '15d', '3d']
}

supervisor = SupervisorAgent()

# Streamlit UI
st.title("AI Hedge Fund Dashboard")

# Sidebar for symbol selection and controls
symbol = st.sidebar.text_input("Stock Symbol", value="AAPL")
refresh = st.sidebar.button("Refresh Data")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Price Chart")
    data = market_data.get_stock_data(symbol)
    data = market_data.calculate_technical_indicators(data)
    
    fig = go.Figure()
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='OHLC'
    ))
    
    # Bollinger Bands
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['Upper_Band'],
        name='Upper Band',
        line=dict(color='gray', dash='dash')
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['Lower_Band'],
        name='Lower Band',
        line=dict(color='gray', dash='dash'),
        fill='tonexty'
    ))
    
    st.plotly_chart(fig)

with col2:
    st.subheader("Trading Signals")
    
    # Get trading signals
    signals = {
        name: agent.analyze(data)
        for name, agent in trading_agents.items()
    }
    
    for strategy, signal in signals.items():
        st.write(f"**{strategy}**")
        st.write(f"Signal: {'Buy' if signal['buy'] else 'Sell' if signal['sell'] else 'Hold'}")
        st.write(f"Confidence: {signal['confidence']:.2f}")
        st.write("---")

# Market Trends
st.subheader("Market Trends")
col1, col2, col3 = st.columns(3)

trend_analysis = {
    timeframe: agent.analyze_trend(data)
    for timeframe, agent in market_trend_agents.items()
}

for col, (timeframe, analysis) in zip([col1, col2, col3], trend_analysis.items()):
    with col:
        st.write(f"**{timeframe} Analysis**")
        st.write(analysis['analysis'])

# Sentiment Analysis
st.subheader("Market Sentiment")
col1, col2, col3 = st.columns(3)

sentiment_analysis = {
    timeframe: agent.analyze_sentiment(symbol)
    for timeframe, agent in sentiment_agents.items()
}

for col, (timeframe, analysis) in zip([col1, col2, col3], sentiment_analysis.items()):
    with col:
        st.write(f"**{timeframe} Sentiment**")
        st.write(analysis['analysis'])

# Supervisor Decision
st.subheader("Trading Decision")
decision = supervisor.make_decision(signals, trend_analysis, sentiment_analysis)
st.write(decision['decision'])

# Portfolio Performance
st.subheader("Portfolio Performance")
positions = db.get_open_positions()
if positions:
    df = pd.DataFrame(positions)
    st.dataframe(df)
    
    # Calculate total P&L
    current_prices = {
        pos['symbol']: market_data.get_stock_data(pos['symbol'])['Close'].iloc[-1]
        for pos in positions
    }
    
    total_pnl = sum(
        (current_prices[pos['symbol']] - pos['entry_price']) * pos['quantity']
        for pos in positions
    )
    
    st.metric("Total P&L", f"${total_pnl:,.2f}")
