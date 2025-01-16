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
from strategies.resistance_strategy import ResistanceStrategy
from agents.trading_agents import TradingAgent
from agents.market_trend_agents import MarketTrendAgent
from agents.sentiment_agents import SentimentAgent
from agents.supervisor_agent import SupervisorAgent
from agents.resistance_agent import ResistanceAnalysisAgent
from agents.recommendation_agent import StrategyRecommendationAgent # Added import
from learning.trading_lessons import TradingEducation  # Add this import at the top


# Initialize components
db = Database()
market_data = MarketData()

# Initialize strategies and agents
strategies = {
    'MACD': MACDStrategy(),
    'Fibonacci': FibonacciStrategy(),
    'Bollinger': BollingerStrategy(),
    'Fractal': FractalStrategy(),
    'Resistance': ResistanceStrategy()  # Add the new resistance strategy
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

resistance_agent = ResistanceAnalysisAgent() # Added resistance agent initialization

recommendation_agent = StrategyRecommendationAgent() # Added recommendation agent initialization

supervisor = SupervisorAgent()

# Initialize education module (add this after other initializations)
education = TradingEducation()

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

    # Add resistance analysis for each strategy's entry/exit points
    resistance_analysis = {}
    try:
        for name, signal in signals.items():
            if signal.get('buy', False):  # Only analyze resistance for buy signals
                try:
                    entry_point, exit_point = calculate_trade_points(data)
                    print(f"Analyzing resistance for {name} - Entry: ${entry_point:.2f}, Exit: ${exit_point:.2f}")

                    resistance_check = resistance_agent.analyze_resistance(data, entry_point, exit_point)
                    resistance_analysis[name] = resistance_check

                    # Save resistance analysis to database
                    analysis_text = f"{'DO NOT BUY' if resistance_check['recommendation'] == 'DO_NOT_BUY' else 'PROCEED'} - "
                    analysis_text += f"Found {len(resistance_check['resistance_levels'])} resistance levels. "
                    analysis_text += resistance_check['explanation']

                    db.save_trading_decision(
                        st.session_state.symbol,
                        analysis_text,
                        resistance_check['confidence'],
                        f"resistance_{name.lower()}"
                    )
                    print(f"Completed resistance analysis for {name}")
                except Exception as e:
                    print(f"Error in resistance analysis for {name}: {str(e)}")
                    st.error(f"Error in resistance analysis for {name}: {str(e)}")
    except Exception as e:
        print(f"Error in resistance analysis block: {str(e)}")
        st.error(f"Error in resistance analysis block: {str(e)}")

    decision = supervisor.make_decision(signals, trend_analysis, sentiment_analysis, resistance_analysis)
    return signals, trend_analysis, sentiment_analysis, resistance_analysis, decision

def calculate_trade_points(data):
    """Calculate entry and exit points based on technical indicators"""
    current_price = data['Close'].iloc[-1]

    # Use Bollinger Bands for support/resistance levels
    upper_band = data['Upper_Band'].iloc[-1]
    lower_band = data['Lower_Band'].iloc[-1]

    # Calculate entry point (near support) and exit point (near resistance)
    band_range = upper_band - lower_band
    entry_point = current_price - (band_range * 0.1)  # 10% below current price
    exit_point = current_price + (band_range * 0.2)   # 20% above current price

    return round(entry_point, 2), round(exit_point, 2)

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

    # Calculate entry and exit points
    entry_point, exit_point = calculate_trade_points(data)

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

        # Update watchlist with entry/exit points if it's a buy signal
        if signals[name].get('buy', False):
            db.add_to_watchlist(symbol, entry_price=entry_point, exit_price=exit_point)
            db.update_watchlist_signal(symbol, 'BUY')
        elif signals[name].get('sell', False):
            db.update_watchlist_signal(symbol, 'SELL')

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

    # Save supervisor decision with explicit decision text
    supervisor_action = extract_trading_action(decision['decision'])
    supervisor_decision = f"{supervisor_action} - {decision['decision'][:100]}..."  # Include first 100 chars of analysis
    db.save_trading_decision(symbol, supervisor_decision, 0.9, 'supervisor')

    # Clear the progress display
    progress_placeholder.empty()

    return supervisor_decision, 0.9


# Streamlit UI
st.title("AI Hedge Fund Dashboard")

# Initialize session state for storing analysis results
if 'signals' not in st.session_state:
    st.session_state.signals = None
if 'trend_analysis' not in st.session_state:
    st.session_state.trend_analysis = None
if 'sentiment_analysis' not in st.session_state:
    st.session_state.sentiment_analysis = None
if 'resistance_analysis' not in st.session_state: #Added for resistance analysis
    st.session_state.resistance_analysis = None
if 'decision' not in st.session_state:
    st.session_state.decision = None
if 'symbol' not in st.session_state:
    st.session_state.symbol = "AAPL"

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["Trading Dashboard", "Watchlist", "Portfolio", "Learning Center"]) # Update the tabs creation line

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
             st.session_state.resistance_analysis,
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

    # Resistance Analysis
    st.subheader("Resistance Analysis")
    if st.session_state.resistance_analysis:
        for strategy, analysis in st.session_state.resistance_analysis.items():
            st.write(f"**{strategy} Resistance Check**")
            st.write(analysis['explanation'])
            st.write(f"Recommendation: {analysis['recommendation']}")
            st.write(f"Confidence: {analysis['confidence']:.2f}")
            st.write("---")
    else:
        st.info("Click 'Analyze Trading Signals' to view resistance analysis")

    # Supervisor Decision
    st.subheader("Trading Decision")
    if st.session_state.decision:
        # Create an expander for detailed trading decision
        with st.expander("Trading Decision Analysis", expanded=True):
            st.markdown("### Final Decision")
            st.write(st.session_state.decision['decision'])

            st.markdown("### Analysis Details")
            st.write("Based on:")
            if st.session_state.signals:
                strategies = [name for name, signal in st.session_state.signals.items() 
                            if signal.get('buy', False) or signal.get('sell', False)]
                st.write(f"- Trading Signals: {', '.join(strategies)}")

            if st.session_state.resistance_analysis:
                resistance_checks = [f"{strategy} ({analysis['recommendation']})" 
                                  for strategy, analysis in st.session_state.resistance_analysis.items()]
                st.write(f"- Resistance Analysis: {', '.join(resistance_checks)}")

            st.write(f"Confidence: {st.session_state.decision.get('confidence', 0.0):.2f}")
    else:
        st.info("Click 'Analyze Trading Signals' to view trading decision")


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

                        # Get previous decisions before updating
                        previous_decisions = db.get_all_agent_decisions(stock['symbol'])

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

                        # Add entry/exit points display
                        if stock['entry_price']:
                            st.write(f"Entry Point: ${stock['entry_price']:.2f}")
                        if stock['exit_price']:
                            st.write(f"Exit Point: ${stock['exit_price']:.2f}")
                        if stock['last_signal_type']:
                            signal_color = "green" if stock['last_signal_type'] == 'BUY' else "red"
                            st.markdown(f"Signal: <span style='color:{signal_color}'>{stock['last_signal_type']}</span>", unsafe_allow_html=True)


                    with col3:
                        st.write("**Agent Decisions Comparison:**")
                        # Create a DataFrame for agent decisions
                        decisions_df = pd.DataFrame(columns=['Agent', 'Previous Decision', 'Current Decision'])

                        # Get the two most recent decisions for each agent
                        agent_decisions = db.get_all_agent_decisions(stock['symbol'])
                        for agent_name in set(d['agent_name'] for d in agent_decisions):
                            agent_specific_decisions = [d for d in agent_decisions if d['agent_name'] == agent_name]
                            agent_specific_decisions.sort(key=lambda x: x['created_at'], reverse=True)

                            current_decision = agent_specific_decisions[0] if agent_specific_decisions else None
                            previous_decision = agent_specific_decisions[1] if len(agent_specific_decisions) > 1 else None

                            # Format the decision text
                            current_text = f"{extract_trading_action(current_decision['decision'])} ({current_decision['confidence']:.2f})" if current_decision else "N/A"
                            previous_text = f"{extract_trading_action(previous_decision['decision'])} ({previous_decision['confidence']:.2f})" if previous_decision else "N/A"

                            # Add to DataFrame
                            decisions_df.loc[len(decisions_df)] = [
                                agent_name.replace('strategy_', '').replace('resistance_', '🎯 ').upper(),
                                previous_text,
                                current_text
                            ]

                        # Display the decisions comparison table
                        st.dataframe(decisions_df, hide_index=True)

                        # Display entry/exit points for supervisor's final decision
                        supervisor_decisions = [d for d in agent_decisions if d['agent_name'] == 'supervisor']
                        if supervisor_decisions:
                            current = supervisor_decisions[0]
                            action = extract_trading_action(current['decision'])

                            st.write("---")
                            st.write("**📊 Final Trading Decision:**")
                            st.write(f"Decision: {action}")
                            st.write(f"Analysis: {current['decision']}")
                            st.write(f"Confidence: {current['confidence']:.2f}")
                            st.write(f"As of: {current['created_at'].strftime('%Y-%m-%d %H:%M')}")

                            if action == 'BUY':
                                entry, exit = calculate_trade_points(stock_data)
                                st.write(f"Recommended Entry: ${entry}")
                                st.write(f"Recommended Exit: ${exit}")
                        else:
                            st.write("No supervisor decision available yet. Click 'Update All Trading Recommendations' to analyze.")

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


with tab3:
    st.subheader("Portfolio Performance")

    # Add Position Form
    with st.expander("Add New Position", expanded=False):
        st.subheader("Add New Position")
        col1, col2 = st.columns(2)

        with col1:
            new_symbol = st.text_input("Stock Symbol").upper()
            quantity = st.number_input("Number of Shares", min_value=1, value=100)
            entry_price = st.number_input("Entry Price ($)", min_value=0.01, value=100.00, step=0.01)
            entry_date = st.date_input("Entry Date", value=datetime.now())

        with col2:
            strategy = st.selectbox("Strategy", options=list(strategies.keys()))
            exit_price = st.number_input("Exit Price ($) (Optional)", min_value=0.0, value=0.0, step=0.01)
            exit_date = st.date_input("Exit Date (Optional)", value=None) if exit_price > 0 else None

        # Calculate potential gain/loss
        if entry_price > 0 and quantity > 0:
            if exit_price > 0:
                gain_loss = (exit_price - entry_price) * quantity
                gain_loss_pct = ((exit_price - entry_price) / entry_price) * 100
                st.metric("Potential Gain/Loss", 
                         f"${gain_loss:,.2f}",
                         f"{gain_loss_pct:,.1f}%")
            else:
                # Show current gain/loss based on market price
                try:
                    current_price = market_data.get_stock_data(new_symbol)['Close'].iloc[-1]
                    gain_loss = (current_price - entry_price) * quantity
                    gain_loss_pct = ((current_price - entry_price) / entry_price) * 100
                    st.metric("Unrealized Gain/Loss", 
                             f"${gain_loss:,.2f}",
                             f"{gain_loss_pct:,.1f}%")
                except:
                    st.warning("Enter a valid symbol to see potential gain/loss")

        if st.button("Add Position"):
            if new_symbol and entry_price > 0 and quantity > 0:
                try:
                    # Validate the symbol
                    stock_data = market_data.get_stock_data(new_symbol)
                    if not stock_data.empty:
                        # Add position to database
                        db.add_position(
                            symbol=new_symbol,
                            quantity=quantity,
                            entry_price=entry_price,
                            entry_date=entry_date, #Added entry date
                            strategy=strategy,
                            exit_price=exit_price, #Added exit price
                            exit_date=exit_date #Added exit date

                        )
                        st.success(f"Added position for {new_symbol}")
                        st.experimental_rerun()
                    else:
                        st.error(f"Could not validate symbol {new_symbol}")
                except Exception as e:
                    st.error(f"Error adding position: {str(e)}")
            else:
                st.error("Please fill in all required fields")

    # Display existing positions
    positions = db.get_open_positions()
    if positions:
        # Calculate current prices first so it's available for both sections
        current_prices = {
            pos['symbol']: market_data.get_stock_data(pos['symbol'])['Close'].iloc[-1]
            for pos in positions
        }

        # Display positions table
        df = pd.DataFrame(positions)
        st.dataframe(df)

        # Calculate total P&L
        total_pnl = sum(
            (current_prices[pos['symbol']] - pos['entry_price']) * pos['quantity']
            for pos in positions
        )

        st.metric("Total P&L", f"${total_pnl:,.2f}")

        # Portfolio Composition
        st.subheader("Portfolio Composition")
        composition = pd.DataFrame(positions).groupby('symbol').agg({
            'quantity': 'sum',
            'entry_price': 'mean'
        }).reset_index()

        # Calculate current value for each position
        composition['current_price'] = composition['symbol'].map(current_prices)
        composition['current_value'] = composition['quantity'] * composition['current_price']
        composition['pnl'] = (composition['current_price'] - composition['entry_price']) * composition['quantity']
        composition['pnl_percent'] = (composition['current_price'] - composition['entry_price']) / composition['entry_price'] * 100

        # Display composition
        st.dataframe(composition.style.format({
            'entry_price': '${:.2f}',
            'current_price': '${:.2f}',
            'current_value': '${:,.2f}',
            'pnl': '${:,.2f}',
            'pnl_percent': '{:.1f}%'
        }))

        # Add Share Performance button
        st.write("---")
        share_col1, share_col2 = st.columns([1, 3])
        with share_col1:
            if st.button("🔄 Share Performance"):
                try:
                    # Create a container for the shareable content
                    share_container = st.container()
                    with share_container:
                        st.markdown("### 📊 Portfolio Performance Summary")
                        st.markdown(f"**Total P&L:** ${total_pnl:,.2f}")

                        # Top Performers
                        if not composition.empty:
                            top_performers = composition.nlargest(3, 'pnl_percent')
                            st.markdown("**🌟 Top Performers:**")
                            for _, pos in top_performers.iterrows():
                                st.markdown(f"• {pos['symbol']}: {pos['pnl_percent']:.1f}% (${pos['pnl']:,.2f})")

                            # Portfolio Stats
                            total_value = composition['current_value'].sum()
                            st.markdown(f"**📈 Portfolio Value:** ${total_value:,.2f}")

                            # Calculate performance metrics
                            profitable_positions = len(composition[composition['pnl'] > 0])
                            total_positions = len(composition)
                            win_rate = (profitable_positions / total_positions) * 100 if total_positions > 0 else 0

                            st.markdown(f"**🎯 Win Rate:** {win_rate:.1f}%")

                        st.markdown(f"**📅 As of:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

                        # Add social sharing context
                        st.markdown("---")
                        st.markdown("*Generated by AI Hedge Fund Dashboard*")

                    st.success("Performance summary generated! You can now take a screenshot to share.")
                except Exception as e:
                    st.error(f"Error generating performance summary: {str(e)}")

        with share_col2:
            st.markdown("""
            📱 **Sharing Tips:**
            - Use your device's screenshot tool to capture the summary
            - Share directly to Twitter, LinkedIn, or other platforms
            - Performance metrics are real-time and verified
            """)
    else:
        st.info("No open positions in portfolio")

    st.subheader("Strategy Recommendations")
    with st.expander("Customize Your Trading Profile", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            risk_tolerance = st.select_slider(
                "Risk Tolerance",
                options=['Very Low', 'Low', 'Medium', 'High', 'Very High'],
                value='Medium'
            )
            experience_level = st.select_slider(
                "Trading Experience",
                options=['Beginner', 'Intermediate', 'Advanced', 'Expert'],
                value='Intermediate'
            )

        with col2:
            investment_horizon = st.select_slider(
                "Investment Horizon",
                options=['Very Short', 'Short', 'Medium', 'Long', 'Very Long'],
                value='Medium'
            )
            initial_capital = st.number_input(
                "Initial Capital ($)",
                min_value=1000,
                value=10000,
                step=1000
            )

    if st.button("Generate Strategy Recommendations"):
        with st.spinner("Analyzing your profile and market conditions..."):
            # Prepare user profile
            user_profile = {
                'risk_tolerance': risk_tolerance,
                'experience_level': experience_level,
                'investment_horizon': investment_horizon,
                'initial_capital': initial_capital
            }

            # Get market data for analysis
            symbol = st.session_state.symbol if 'symbol' in st.session_state else 'SPY'
            market_data = market_data.get_stock_data(symbol)

            # Get trading history from database
            trading_history = pd.DataFrame(db.get_open_positions())

            # Calculate strategy performance
            if not trading_history.empty:
                strategy_performance = recommendation_agent.calculate_strategy_performance(trading_history)
            else:
                strategy_performance = {
                    strategy: {
                        'win_rate': 'N/A',
                        'avg_return': 'N/A',
                        'max_drawdown': 'N/A',
                        'total_trades': 0
                    } for strategy in strategies.keys()
                }

            # Generate recommendations
            recommendations = recommendation_agent.recommend_strategies(
                user_profile,
                market_data,
                strategy_performance
            )

            # Display recommendations in a well-formatted way
            st.markdown("### 📊 Personalized Strategy Recommendations")
            st.markdown(recommendations['recommendations'])
            st.markdown(f"*Last updated: {recommendations['timestamp'].strftime('%Y-%m-%d %H:%M')}*")

            # Add a quick-start guide
            st.markdown("### 🚀 Quick Start Guide")
            st.markdown("""
            To implement these recommendations:
            1. Review the suggested strategy combinations
            2. Set up your watchlist with suitable stocks
            3. Configure alerts for entry/exit points
            4. Start with small position sizes to test the strategies
            5. Monitor andadjust based on performance
            """)


with tab4:
    st.title("📚 Trading Strategy Learning Center")

    # Sidebar for lesson navigation
    selected_lesson = st.sidebar.selectbox(
        "Select Lesson",
        options=[lesson.lesson_id for lesson in education.get_all_lessons()],
        format_func=lambda x: education.get_lesson(x).title
    )

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        lesson = education.get_lesson(selected_lesson)
        if lesson:
            st.header(f"{lesson.title} ({lesson.difficulty})")
            st.markdown(lesson.content)

            # Interactive quiz section
            st.subheader("📝 Knowledge Check")
            for i, quiz in enumerate(lesson.quiz_questions):
                answer = st.radio(
                    f"Question {i+1}: {quiz['question']}",
                    options=quiz['options'],
                    key=f"quiz_{selected_lesson}_{i}"
                )

                if st.button(f"Check Answer #{i+1}", key=f"check_{selected_lesson}_{i}"):
                    selectedindex = quiz['options'].index(answer)
                    if education.check_quiz_answer(selected_lesson, i, selectedindex):
                        st.success("Correct! 🎉")
                        # Check if user should earn an achievement
                        education.unlock_achievement('quiz_ace')
                    else:
                        st.error("Try again! 💪")

    with col2:
        # Achievements section
        st.subheader("🏆 Your Achievements")
        achievements = education.get_achievements()
        for achievement in achievements:
            if achievement.unlocked:
                st.success(f"{achievement.icon} {achievement.name}")
                st.caption(f"Earned on: {achievement.unlocked_at.strftime('%Y-%m-%d')}")
            else:
                st.info(f"🔒 {achievement.name}")
                st.caption(achievement.description)

        # Progress tracking
        st.subheader("📊 Learning Progress")
        total_lessons = len(education.get_all_lessons())
        completed_achievements = len([a for a in achievements if a.unlocked])
        st.progress(completed_achievements / len(achievements))
        st.caption(f"Achievements: {completed_achievements}/{len(achievements)}")