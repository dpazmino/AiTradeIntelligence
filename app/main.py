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

def calculate_trade_points(data):
    """Calculate entry and exit points based on technical indicators"""
    current_price = data['Close'].iloc[-1]

    # Use Bollinger Bands for support/resistance levels
    upper_band = data['Upper_Band'].iloc[-1]
    lower_band = data['Lower_Band'].iloc[-1]

    # Calculate entry point (near support) and exit point (near resistance)
    entry_point = round(lower_band + (current_price - lower_band) * 0.1, 2)  # 10% above support
    exit_point = round(upper_band - (upper_band - current_price) * 0.1, 2)   # 10% below resistance

    return entry_point, exit_point

def get_agent_decisions(symbol, data):
    """Get individual trading agent decisions"""
    agent_decisions = {}

    # Get trading signals from each strategy agent
    for name, agent in trading_agents.items():
        signals = agent.analyze(data)
        action = 'BUY' if signals.get('buy', False) else 'SELL' if signals.get('sell', False) else 'HOLD'
        agent_decisions[name] = {
            'action': action,
            'confidence': signals.get('confidence', 0.0)
        }

    return agent_decisions

def extract_trading_action(decision_text):
    """Extract basic trading action from decision text"""
    decision_text = decision_text.lower()
    if 'buy' in decision_text:
        return 'BUY'
    elif 'sell' in decision_text:
        return 'SELL'
    return 'HOLD'

def analyze_watchlist_stock(symbol, data):
    """Analyze a single watchlist stock using our AI agents"""
    signals = {}

    # Create a placeholder for progress
    progress_placeholder = st.empty()

    # Show trading agents analysis progress
    progress_placeholder.write("🤖 Trading Agents Analysis:")
    for name, agent in trading_agents.items():
        progress_placeholder.write(f"  ↳ {name} Strategy Agent analyzing {symbol}...")
        signals[name] = agent.analyze(data)
        # Save each agent's decision
        action = 'BUY' if signals[name].get('buy', False) else 'SELL' if signals[name].get('sell', False) else 'HOLD'
        db.save_trading_decision(symbol, action, signals[name].get('confidence', 0.0), f"strategy_{name.lower()}")

    # Show market trend analysis progress
    progress_placeholder.write("📈 Market Trend Analysis:")
    trend_analysis = {}
    for timeframe, agent in market_trend_agents.items():
        progress_placeholder.write(f"  ↳ {timeframe} Trend Agent analyzing market conditions...")
        trend_analysis[timeframe] = agent.analyze_trend(data)
        # Save trend analysis
        db.save_trading_decision(symbol, trend_analysis[timeframe]['analysis'], 
                               0.8, f"trend_{timeframe}")

    # Show sentiment analysis progress
    progress_placeholder.write("📰 Sentiment Analysis:")
    sentiment_analysis = {}
    for timeframe, agent in sentiment_agents.items():
        progress_placeholder.write(f"  ↳ {timeframe} Sentiment Agent analyzing news and social media...")
        sentiment_analysis[timeframe] = agent.analyze_sentiment(symbol)
        # Save sentiment analysis
        db.save_trading_decision(symbol, sentiment_analysis[timeframe]['analysis'], 
                               0.7, f"sentiment_{timeframe}")

    # Show supervisor decision making
    progress_placeholder.write("🎯 Supervisor Agent making final decision...")
    decision = supervisor.make_decision(signals, trend_analysis, sentiment_analysis)

    # Save supervisor decision
    db.save_trading_decision(symbol, decision['decision'], 
                           0.9, 'supervisor')

    # Clear the progress display
    progress_placeholder.empty()

    return decision['decision'], 0.9


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

    # Add update recommendations button
    if st.button("Update All Trading Recommendations"):
        with st.spinner("Updating trading recommendations..."):
            # Add a progress bar for overall progress
            progress_bar = st.progress(0)
            watchlist = db.get_watchlist()

            for i, stock in enumerate(watchlist):
                try:
                    # Create an expander for each stock's analysis process
                    with st.expander(f"Analyzing {stock['symbol']}", expanded=True):
                        st.write(f"🔄 Processing {stock['symbol']}...")

                        stock_data = market_data.get_stock_data(stock['symbol'], period='5d')
                        if not stock_data.empty and len(stock_data) >= 2:
                            stock_data = market_data.calculate_technical_indicators(stock_data)
                            decision_text, confidence = analyze_watchlist_stock(stock['symbol'], stock_data)
                            db.save_trading_decision(stock['symbol'], decision_text, confidence)
                            st.write(f"✅ Analysis completed for {stock['symbol']}")
                        else:
                            st.error(f"Insufficient data for {stock['symbol']}")

                    # Update progress bar
                    progress = (i + 1) / len(watchlist)
                    progress_bar.progress(progress)

                except Exception as e:
                    st.error(f"Error updating recommendations for {stock['symbol']}: {str(e)}")

            progress_bar.empty()  # Clear the progress bar
            st.success("Trading recommendations updated!")

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

    # Display watchlist with current data and trading decisions
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

                    # Calculate technical indicators
                    stock_data = market_data.calculate_technical_indicators(stock_data)

                    # Get all stored agent decisions
                    agent_decisions = db.get_all_agent_decisions(stock['symbol'])

                    # Display stock info in columns
                    col1, col2, col3 = st.columns([2, 2, 3])

                    with col1:
                        st.write(f"**{stock['symbol']}**")
                        if stock['notes']:
                            st.write(stock['notes'])

                    with col2:
                        st.write(f"Price: ${today_price:.2f}")
                        color = "green" if price_change >= 0 else "red"
                        st.markdown(f"Change: <span style='color:{color}'>${price_change:.2f} ({price_change_pct:.1f}%)</span>", unsafe_allow_html=True)
                        st.write(f"Volume: {volume:,.0f}")

                    with col3:
                        st.write("**Agent Decisions:**")
                        for decision in agent_decisions:
                            if decision['agent_name'].startswith('strategy_'):
                                strategy_name = decision['agent_name'].replace('strategy_', '').upper()
                                action = extract_trading_action(decision['decision'])
                                st.write(f"{strategy_name}: {action} (conf: {decision['confidence']:.2f})")

                                # Show entry/exit points for buy signals
                                if action == 'BUY':
                                    entry, exit = calculate_trade_points(stock_data)
                                    st.write(f"  ↳ Entry: ${entry} | Exit: ${exit}")

                        st.write("**Supervisor Decision:**")
                        supervisor_decisions = [d for d in agent_decisions if d['agent_name'] == 'supervisor']
                        if supervisor_decisions:
                            current = supervisor_decisions[0]
                            action = extract_trading_action(current['decision'])
                            st.write(f"({current['created_at'].strftime('%Y-%m-%d')}): {action}")

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