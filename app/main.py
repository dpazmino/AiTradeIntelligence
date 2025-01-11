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

# Streamlit UI
st.title("AI Hedge Fund Dashboard")

# Create tabs
tab1, tab2 = st.tabs(["Trading Dashboard", "Stock Screener"])

with tab1:
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

with tab2:
    st.subheader("Stock Screener")
    st.write("Stocks between $20-30, daily volume > 1M shares, not in hedge funds")

    def get_stock_universe():
        """Get a list of stocks to screen from major indices"""
        try:
            # Get stocks from S&P 600 Small Cap (more likely to be in our price range)
            sp600 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_600_companies')[0]
            symbols = sp600['Symbol'].tolist()

            # Add stocks from Russell 2000 (another source of mid-range stocks)
            russell2000 = pd.read_html('https://en.wikipedia.org/wiki/List_of_Russell_2000_companies')[0]
            symbols.extend(russell2000['Ticker'].tolist())

            # Remove duplicates and clean symbols
            symbols = list(set([sym.strip() for sym in symbols if isinstance(sym, str)]))
            return symbols
        except Exception as e:
            st.error(f"Error fetching stock universe: {str(e)}")
            return []

    def screen_stock(symbol):
        """Screen individual stock based on our criteria"""
        try:
            stock_data = market_data.get_stock_data(symbol)
            if not stock_data.empty:
                current_price = stock_data['Close'].iloc[-1]
                avg_volume = stock_data['Volume'].mean()

                # Check if stock meets our criteria
                if 20 <= current_price <= 30 and avg_volume > 1_000_000:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    company_name = info.get('longName', symbol)

                    # Additional check for institutional ownership
                    inst_holders = ticker.institutional_holders
                    if inst_holders is not None and len(inst_holders) < 100:  # Less institutional ownership
                        return (symbol, company_name, current_price, avg_volume)
        except Exception as e:
            print(f"Error screening {symbol}: {str(e)}")
        return None


    # Add refresh button for screener
    if st.button("Refresh Screener"):
        with st.spinner("Fetching stock universe..."):
            symbols = get_stock_universe()
            st.info(f"Screening {len(symbols)} stocks...")

            # Clear old screened stocks
            db.clear_old_screened_stocks(hours=24)

            # Screen stocks with progress bar
            progress_bar = st.progress(0)
            screened_count = 0

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(screen_stock, symbol) for symbol in symbols]
                total = len(futures)

                for i, future in enumerate(futures):
                    result = future.result()
                    if result:
                        symbol, company_name, current_price, avg_volume = result
                        db.upsert_screened_stock(symbol, company_name, current_price, avg_volume)
                        screened_count += 1
                    progress_bar.progress((i + 1) / total)

            st.success(f"Found {screened_count} stocks matching criteria")

    # Display screened stocks
    screened_stocks = db.get_screened_stocks()
    if screened_stocks:
        df = pd.DataFrame(screened_stocks)
        df['last_updated'] = pd.to_datetime(df['last_updated'])
        df = df[['symbol', 'company_name', 'current_price', 'average_volume', 'last_updated']]
        df.columns = ['Symbol', 'Company Name', 'Price ($)', 'Avg Volume', 'Last Updated']
        st.dataframe(df)
    else:
        st.info("No stocks currently meet the screening criteria. Click 'Refresh Screener' to scan for matches.")