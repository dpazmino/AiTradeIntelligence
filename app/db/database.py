import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.environ['PGHOST'],
            database=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            port=os.environ['PGPORT']
        )
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cur:
            try:
                # Keep existing sequences
                cur.execute("""
                    CREATE SEQUENCE IF NOT EXISTS portfolio_id_seq;
                    CREATE SEQUENCE IF NOT EXISTS trading_signals_id_seq;
                    CREATE SEQUENCE IF NOT EXISTS watchlist_stocks_id_seq;
                    CREATE SEQUENCE IF NOT EXISTS trading_decisions_id_seq;
                """)

                # Keep existing tables
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

                # Add new table for trading decisions
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trading_decisions (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(10) NOT NULL,
                        decision TEXT NOT NULL,
                        confidence FLOAT NOT NULL,
                        agent_name VARCHAR(50) NOT NULL DEFAULT 'supervisor',
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE UNIQUE INDEX IF NOT EXISTS trading_decisions_daily_idx 
                    ON trading_decisions (symbol, date(created_at));
                """)

                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                print(f"Error creating tables: {str(e)}")
                raise

    def add_position(self, symbol, quantity, entry_price, strategy):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO portfolio (symbol, quantity, entry_price, entry_date, strategy)
                VALUES (%s, %s, %s, %s, %s)
                """, (symbol, quantity, entry_price, datetime.now(), strategy))
            self.conn.commit()

    def close_position(self, position_id, exit_price):
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE portfolio 
                SET exit_price = %s, exit_date = %s
                WHERE id = %s
                """, (exit_price, datetime.now(), position_id))
            self.conn.commit()

    def get_open_positions(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM portfolio 
                WHERE exit_date IS NULL
                """)
            return cur.fetchall()

    def add_signal(self, symbol, signal_type, strategy, confidence):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO trading_signals 
                (symbol, signal_type, strategy, confidence, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                """, (symbol, signal_type, strategy, confidence, datetime.now()))
            self.conn.commit()

    def upsert_screened_stock(self, symbol, company_name, current_price, average_volume):
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

    def get_screened_stocks(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM screened_stocks 
                ORDER BY symbol ASC
                """)
            return cur.fetchall()

    def clear_old_screened_stocks(self, hours=24):
        with self.conn.cursor() as cur:
            cur.execute("""
                DELETE FROM screened_stocks 
                WHERE last_updated < NOW() - INTERVAL '%s hours'
                """, (hours,))
            self.conn.commit()

    def add_to_watchlist(self, symbol, notes=None):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO watchlist_stocks (symbol, notes)
                VALUES (%s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    notes = EXCLUDED.notes,
                    added_date = CURRENT_TIMESTAMP
                """, (symbol.upper(), notes))
            self.conn.commit()

    def remove_from_watchlist(self, symbol):
        with self.conn.cursor() as cur:
            cur.execute("""
                DELETE FROM watchlist_stocks 
                WHERE symbol = %s
                """, (symbol.upper(),))
            self.conn.commit()

    def get_watchlist(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM watchlist_stocks 
                ORDER BY added_date DESC
                """)
            return cur.fetchall()

    def save_trading_decision(self, symbol: str, decision: str, confidence: float, agent_name: str = 'supervisor'):
        """Save a new trading decision for a stock"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO trading_decisions (symbol, decision, confidence, agent_name)
                VALUES (%s, %s, %s, %s)
                """, (symbol, decision, confidence, agent_name))
            self.conn.commit()

    def get_latest_trading_decisions(self, symbol: str, limit: int = 2):
        """Get the latest trading decisions for a stock"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT decision, confidence, agent_name, created_at
                FROM trading_decisions
                WHERE symbol = %s
                ORDER BY created_at DESC
                LIMIT %s
                """, (symbol, limit))
            return cur.fetchall()

    def get_all_agent_decisions(self, symbol: str):
        """Get the latest decision from each agent for a stock"""
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

    def get_latest_position_id(self, symbol: str) -> int:
        """Get the ID of the most recently added position for a symbol"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM portfolio 
                WHERE symbol = %s
                ORDER BY entry_date DESC 
                LIMIT 1
                """, (symbol,))
            result = cur.fetchone()
            return result[0] if result else None