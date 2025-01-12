import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import time

class Database:
    def __init__(self, max_retries=3):
        self.max_retries = max_retries
        self.conn = None
        self.connect_with_retry()
        self.create_tables()

    def connect_with_retry(self):
        """Establish database connection with retry logic"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # Connect using the PostgreSQL environment variables provided by Replit
                self.conn = psycopg2.connect(
                    dbname=os.environ.get('PGDATABASE'),
                    user=os.environ.get('PGUSER'),
                    password=os.environ.get('PGPASSWORD'),
                    host='localhost',  # Use localhost for Replit's PostgreSQL
                    port=os.environ.get('PGPORT', 5432)  # Default to 5432 if not specified
                )
                self.conn.autocommit = False
                print("Successfully connected to Replit PostgreSQL database!")
                return
            except Exception as e:
                retry_count += 1
                if retry_count == self.max_retries:
                    raise Exception(f"Failed to connect to database after {self.max_retries} attempts: {str(e)}")
                print(f"Connection attempt {retry_count} failed, retrying in 5 seconds...")
                time.sleep(5)

    def ensure_connection(self):
        """Ensure database connection is active"""
        try:
            # Try to execute a simple query to test connection
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
        except Exception:
            print("Connection lost, attempting to reconnect...")
            self.connect_with_retry()

    def create_tables(self):
        """Create necessary database tables"""
        self.ensure_connection()
        with self.conn.cursor() as cur:
            try:
                # Keep existing sequences
                cur.execute("""
                    CREATE SEQUENCE IF NOT EXISTS portfolio_id_seq;
                    CREATE SEQUENCE IF NOT EXISTS trading_signals_id_seq;
                    CREATE SEQUENCE IF NOT EXISTS watchlist_stocks_id_seq;
                    CREATE SEQUENCE IF NOT EXISTS trading_decisions_id_seq;
                """)

                # Create tables
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio (
                        id INTEGER PRIMARY KEY DEFAULT nextval('portfolio_id_seq'),
                        symbol VARCHAR(10) NOT NULL,
                        quantity INTEGER NOT NULL,
                        entry_price FLOAT NOT NULL,
                        entry_date TIMESTAMP NOT NULL,
                        exit_price FLOAT,
                        exit_date TIMESTAMP,
                        strategy VARCHAR(50) NOT NULL
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trading_signals (
                        id INTEGER PRIMARY KEY DEFAULT nextval('trading_signals_id_seq'),
                        symbol VARCHAR(10) NOT NULL,
                        signal_type VARCHAR(10) NOT NULL,
                        strategy VARCHAR(50) NOT NULL,
                        confidence FLOAT NOT NULL,
                        timestamp TIMESTAMP NOT NULL
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS screened_stocks (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(10) NOT NULL,
                        company_name VARCHAR(100),
                        current_price DECIMAL(10, 2) NOT NULL,
                        average_volume BIGINT NOT NULL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol)
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS watchlist_stocks (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(10) NOT NULL UNIQUE,
                        notes TEXT,
                        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trading_decisions (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(10) NOT NULL,
                        decision TEXT NOT NULL,
                        confidence FLOAT NOT NULL,
                        agent_name VARCHAR(50) NOT NULL DEFAULT 'supervisor',
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol, agent_name, date(created_at))
                    )
                """)

                self.conn.commit()
                print("Database tables created successfully")
            except Exception as e:
                self.conn.rollback()
                print(f"Error creating tables: {str(e)}")
                raise

    def execute_with_retry(self, operation):
        """Execute database operation with retry logic"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.ensure_connection()
                return operation()
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_attempts - 1:
                    raise
                print(f"Database operation failed, retrying... ({attempt + 1}/{max_attempts})")
                time.sleep(2)

    def add_position(self, symbol, quantity, entry_price, strategy):
        def operation():
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO portfolio (symbol, quantity, entry_price, entry_date, strategy)
                    VALUES (%s, %s, %s, %s, %s)
                    """, (symbol, quantity, entry_price, datetime.now(), strategy))
                self.conn.commit()
        self.execute_with_retry(operation)

    def close_position(self, position_id, exit_price):
        def operation():
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE portfolio 
                    SET exit_price = %s, exit_date = %s
                    WHERE id = %s
                    """, (exit_price, datetime.now(), position_id))
                self.conn.commit()
        self.execute_with_retry(operation)

    def get_open_positions(self):
        def operation():
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM portfolio 
                    WHERE exit_date IS NULL
                    """)
                return cur.fetchall()
        return self.execute_with_retry(operation)

    def add_signal(self, symbol, signal_type, strategy, confidence):
        def operation():
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trading_signals 
                    (symbol, signal_type, strategy, confidence, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    """, (symbol, signal_type, strategy, confidence, datetime.now()))
                self.conn.commit()
        self.execute_with_retry(operation)

    def upsert_screened_stock(self, symbol, company_name, current_price, average_volume):
        def operation():
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO screened_stocks 
                    (symbol, company_name, current_price, average_volume, last_updated)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (symbol) 
                    DO UPDATE SET 
                        company_name = EXCLUDED.company_name,
                        current_price = EXCLUDED.current_price,
                        average_volume = EXCLUDED.average_volume,
                        last_updated = EXCLUDED.last_updated
                    """, (symbol, company_name, current_price, average_volume, datetime.now()))
                self.conn.commit()
        self.execute_with_retry(operation)

    def get_screened_stocks(self):
        def operation():
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM screened_stocks 
                    ORDER BY symbol ASC
                    """)
                return cur.fetchall()
        return self.execute_with_retry(operation)

    def clear_old_screened_stocks(self, hours=24):
        def operation():
            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM screened_stocks 
                    WHERE last_updated < NOW() - INTERVAL '%s hours'
                    """, (hours,))
                self.conn.commit()
        self.execute_with_retry(operation)

    def add_to_watchlist(self, symbol, notes=None):
        def operation():
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO watchlist_stocks (symbol, notes)
                    VALUES (%s, %s)
                    ON CONFLICT (symbol) DO UPDATE SET
                        notes = EXCLUDED.notes,
                        added_date = CURRENT_TIMESTAMP
                    """, (symbol.upper(), notes))
                self.conn.commit()
        self.execute_with_retry(operation)

    def remove_from_watchlist(self, symbol):
        def operation():
            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM watchlist_stocks 
                    WHERE symbol = %s
                    """, (symbol.upper(),))
                self.conn.commit()
        self.execute_with_retry(operation)

    def get_watchlist(self):
        def operation():
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM watchlist_stocks 
                    ORDER BY added_date DESC
                    """)
                return cur.fetchall()
        return self.execute_with_retry(operation)

    def save_trading_decision(self, symbol: str, decision: str, confidence: float, agent_name: str = 'supervisor'):
        def operation():
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trading_decisions (symbol, decision, confidence, agent_name)
                    VALUES (%s, %s, %s, %s)
                    """, (symbol, decision, confidence, agent_name))
                self.conn.commit()
        self.execute_with_retry(operation)

    def get_latest_trading_decisions(self, symbol: str, limit: int = 2):
        def operation():
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT decision, confidence, agent_name, created_at
                    FROM trading_decisions
                    WHERE symbol = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """, (symbol, limit))
                return cur.fetchall()
        return self.execute_with_retry(operation)

    def get_all_agent_decisions(self, symbol: str):
        def operation():
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    WITH RankedDecisions AS (
                        SELECT 
                            symbol,
                            decision,
                            confidence,
                            agent_name,
                            created_at,
                            ROW_NUMBER() OVER (PARTITION BY agent_name ORDER BY created_at DESC) as rn
                        FROM trading_decisions
                        WHERE symbol = %s
                    )
                    SELECT symbol, decision, confidence, agent_name, created_at
                    FROM RankedDecisions
                    WHERE rn = 1
                    ORDER BY agent_name;
                    """, (symbol,))
                return cur.fetchall()
        return self.execute_with_retry(operation)