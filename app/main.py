import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

from db.database import Database
from data.market_data import MarketData
from strategies.macd_strategy import MACDStrategy
from strategies.fibonacci_strategy import FibonacciStrategy
from strategies.bollinger_strategy import BollingerStrategy
from strategies.fractal_strategy import FractalStrategy
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
    'Bollinger': BollingerStrategy(),
    'Fractal': FractalStrategy()
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

def analyze_trading_signals(data):
    """Analyze trading signals for the given data"""
    signals = {
        name: agent.analyze(data)
        for name, agent in trading_agents.items()
    }

    trend_analysis = {
        timeframe: agent.analyze_trend(data)
        for timeframe, agent in market_trend_agents.items()
    }

    sentiment_analysis = {
        timeframe: agent.analyze_sentiment(st.session_state.symbol)
        for timeframe, agent in sentiment_agents.items()
    }

    decision = supervisor.make_decision(signals, trend_analysis, sentiment_analysis)

    return signals, trend_analysis, sentiment_analysis, decision

def analyze_watchlist_stock(symbol, data):
    """Analyze a single watchlist stock using our AI agents"""
    signals = {
        name: agent.analyze(data)
        for name, agent in trading_agents.items()
    }

    trend_analysis = {
        timeframe: agent.analyze_trend(data)
        for timeframe, agent in market_trend_agents.items()
    }

    sentiment_analysis = {
        timeframe: agent.analyze_sentiment(symbol)
        for timeframe, agent in sentiment_agents.items()
    }

    decision = supervisor.make_decision(signals, trend_analysis, sentiment_analysis)
    return decision

# Streamlit UI
st.title("AI Hedge Fund Dashboard")

# Initialize session state for storing analysis results
if 'signals' not in st.session_state:
    st.session_state.signals = None
if 'trend_analysis' not in st.session_state:
    st.session_state.trend_analysis = None
if 'sentiment_analysis' not in st.session_state:
    st.session_state.sentiment_analysis = None
if 'decision' not in st.session_state:
    st.session_state.decision = None
if 'symbol' not in st.session_state:
    st.session_state.symbol = "AAPL"

# Create tabs
tab1, tab2 = st.tabs(["Trading Dashboard", "Watchlist"])

with tab1:
    # Sidebar for symbol selection and controls
    st.session_state.symbol = st.sidebar.text_input("Stock Symbol", value=st.session_state.symbol)
    analyze_button = st.sidebar.button("Analyze Trading Signals")

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Price Chart")
        data = market_data.get_stock_data(st.session_state.symbol)
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

    # Only analyze signals when the button is clicked
    if analyze_button:
        with st.spinner("Analyzing trading signals..."):
            (st.session_state.signals, 
             st.session_state.trend_analysis, 
             st.session_state.sentiment_analysis,
             st.session_state.decision) = analyze_trading_signals(data)

    with col2:
        st.subheader("Trading Signals")
        if st.session_state.signals:
            for strategy, signal in st.session_state.signals.items():
                st.write(f"**{strategy}**")
                st.write(f"Signal: {'Buy' if signal['buy'] else 'Sell' if signal['sell'] else 'Hold'}")
                st.write(f"Confidence: {signal['confidence']:.2f}")
                st.write("---")
        else:
            st.info("Click 'Analyze Trading Signals' to view signals")

    # Market Trends
    st.subheader("Market Trends")
    if st.session_state.trend_analysis:
        col1, col2, col3 = st.columns(3)
        for col, (timeframe, analysis) in zip([col1, col2, col3], st.session_state.trend_analysis.items()):
            with col:
                st.write(f"**{timeframe} Analysis**")
                st.write(analysis['analysis'])
    else:
        st.info("Click 'Analyze Trading Signals' to view market trends")

    # Sentiment Analysis
    st.subheader("Market Sentiment")
    if st.session_state.sentiment_analysis:
        col1, col2, col3 = st.columns(3)
        for col, (timeframe, analysis) in zip([col1, col2, col3], st.session_state.sentiment_analysis.items()):
            with col:
                st.write(f"**{timeframe} Sentiment**")
                st.write(analysis['analysis'])
    else:
        st.info("Click 'Analyze Trading Signals' to view sentiment analysis")

    # Supervisor Decision
    st.subheader("Trading Decision")
    if st.session_state.decision:
        st.write(st.session_state.decision['decision'])
    else:
        st.info("Click 'Analyze Trading Signals' to view trading decision")

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

with tab2:
    st.subheader("Watchlist")

    # Add stock to watchlist
    new_symbol = st.text_input("Enter Stock Symbol").upper()
    notes = st.text_area("Notes (optional)", height=100)

    if st.button("Add to Watchlist") and new_symbol:
        try:
            # Get current stock data
            stock_data = market_data.get_stock_data(new_symbol)
            if not stock_data.empty:
                current_price = stock_data['Close'].iloc[-1]
                avg_volume = stock_data['Volume'].mean()

                # Get company name
                ticker = yf.Ticker(new_symbol)
                company_name = ticker.info.get('longName', new_symbol)

                # Save to watchlist
                db.add_to_watchlist(new_symbol, notes)
                # Update screened stocks table
                db.upsert_screened_stock(new_symbol, company_name, current_price, avg_volume)
                st.success(f"Added {new_symbol} to watchlist")
            else:
                st.error(f"Could not fetch data for {new_symbol}")
        except Exception as e:
            st.error(f"Error adding {new_symbol} to watchlist: {str(e)}")

    # Display watchlist with current data
    watchlist = db.get_watchlist()
    if watchlist:
        st.write("Your Watchlist:")
        for stock in watchlist:
            try:
                # Get current stock data (using 5d to ensure we have enough data)
                stock_data = market_data.get_stock_data(stock['symbol'], period='5d')
                if not stock_data.empty and len(stock_data) >= 2:
                    today_price = stock_data['Close'].iloc[-1]
                    yesterday_price = stock_data['Close'].iloc[-2]
                    price_change = today_price - yesterday_price
                    price_change_pct = (price_change / yesterday_price) * 100
                    volume = stock_data['Volume'].iloc[-1]

                    # Add technical indicators for analysis
                    stock_data = market_data.calculate_technical_indicators(stock_data)

                    # Get AI trading decision
                    with st.spinner(f"Analyzing {stock['symbol']}..."):
                        decision = analyze_watchlist_stock(stock['symbol'], stock_data)

                    # Display stock info in columns
                    col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 3, 1])
                    with col1:
                        st.write(f"**{stock['symbol']}**")
                        if stock['notes']:
                            st.write(stock['notes'])
                    with col2:
                        st.write(f"Today: ${today_price:.2f}")
                        st.write(f"Yesterday: ${yesterday_price:.2f}")
                        color = "green" if price_change >= 0 else "red"
                        st.markdown(f"Change: <span style='color:{color}'>${price_change:.2f} ({price_change_pct:.1f}%)</span>", unsafe_allow_html=True)
                    with col3:
                        st.write(f"Volume: {volume:,.0f}")
                    with col4:
                        st.write("**AI Decision:**")
                        st.write(decision['decision'])
                    with col5:
                        if st.button("Remove", key=f"remove_{stock['symbol']}"):
                            db.remove_from_watchlist(stock['symbol'])
                            st.experimental_rerun()
                    st.write("---")
                else:
                    st.error(f"Insufficient data for {stock['symbol']}")
            except Exception as e:
                st.error(f"Error fetching data for {stock['symbol']}: {str(e)}")
    else:
        st.info("Your watchlist is empty. Add symbols above.")