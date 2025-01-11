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
            # Portfolio table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    quantity INTEGER NOT NULL,
                    entry_price FLOAT NOT NULL,
                    entry_date TIMESTAMP NOT NULL,
                    exit_price FLOAT,
                    exit_date TIMESTAMP,
                    strategy VARCHAR(50) NOT NULL
                )
            """)
            
            # Trading signals table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    signal_type VARCHAR(10) NOT NULL,
                    strategy VARCHAR(50) NOT NULL,
                    confidence FLOAT NOT NULL,
                    timestamp TIMESTAMP NOT NULL
                )
            """)
            
            self.conn.commit()

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
