import os
import mysql.connector
from mysql.connector import Error
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', ''),
            database=os.environ.get('DB_NAME', 'trading_db')
        )
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cur:
            try:
                # Create portfolio table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        symbol VARCHAR(10) NOT NULL,
                        quantity INTEGER NOT NULL,
                        entry_price FLOAT NOT NULL,
                        entry_date TIMESTAMP NOT NULL,
                        exit_price FLOAT,
                        exit_date TIMESTAMP,
                        strategy VARCHAR(50) NOT NULL
                    )
                """)

                # Create trading signals table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trading_signals (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        symbol VARCHAR(10) NOT NULL,
                        signal_type VARCHAR(10) NOT NULL,
                        strategy VARCHAR(50) NOT NULL,
                        confidence FLOAT NOT NULL,
                        timestamp TIMESTAMP NOT NULL
                    )
                """)

                # Create screened stocks table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS screened_stocks (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        symbol VARCHAR(10) NOT NULL,
                        company_name VARCHAR(100),
                        current_price DECIMAL(10, 2) NOT NULL,
                        average_volume BIGINT NOT NULL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_symbol (symbol)
                    )
                """)

                # Create watchlist stocks table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS watchlist_stocks (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        symbol VARCHAR(10) NOT NULL,
                        notes TEXT,
                        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_symbol (symbol)
                    )
                """)

                # Create trading decisions table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trading_decisions (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        symbol VARCHAR(10) NOT NULL,
                        decision TEXT NOT NULL,
                        confidence FLOAT NOT NULL,
                        agent_name VARCHAR(50) NOT NULL DEFAULT 'supervisor',
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY daily_decision (symbol, DATE(created_at), agent_name)
                    )
                """)

                self.conn.commit()
            except Error as e:
                self.conn.rollback()
                print(f"Error creating tables: {str(e)}")
                raise

    def _dict_row(self, cursor, row):
        """Convert a row tuple into a dictionary"""
        if row is None:
            return None
        return dict(zip([col[0] for col in cursor.description], row))

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
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM portfolio 
                WHERE exit_date IS NULL
                """)
            rows = cur.fetchall()
            return [self._dict_row(cur, row) for row in rows]

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
                ON DUPLICATE KEY UPDATE 
                    company_name = VALUES(company_name),
                    current_price = VALUES(current_price),
                    average_volume = VALUES(average_volume),
                    last_updated = VALUES(last_updated)
                """, (symbol, company_name, current_price, average_volume, datetime.now()))
            self.conn.commit()

    def get_screened_stocks(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM screened_stocks 
                ORDER BY symbol ASC
                """)
            rows = cur.fetchall()
            return [self._dict_row(cur, row) for row in rows]

    def clear_old_screened_stocks(self, hours=24):
        with self.conn.cursor() as cur:
            cur.execute("""
                DELETE FROM screened_stocks 
                WHERE last_updated < DATE_SUB(NOW(), INTERVAL %s HOUR)
                """, (hours,))
            self.conn.commit()

    def add_to_watchlist(self, symbol, notes=None):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO watchlist_stocks (symbol, notes)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE
                    notes = VALUES(notes),
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
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM watchlist_stocks 
                ORDER BY added_date DESC
                """)
            rows = cur.fetchall()
            return [self._dict_row(cur, row) for row in rows]

    def save_trading_decision(self, symbol: str, decision: str, confidence: float, agent_name: str = 'supervisor'):
        """Save a new trading decision for a stock"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO trading_decisions (symbol, decision, confidence, agent_name)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    decision = VALUES(decision),
                    confidence = VALUES(confidence),
                    created_at = CURRENT_TIMESTAMP
                """, (symbol, decision, confidence, agent_name))
            self.conn.commit()

    def get_latest_trading_decisions(self, symbol: str, limit: int = 2):
        """Get the latest trading decisions for a stock"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT decision, confidence, agent_name, created_at
                FROM trading_decisions
                WHERE symbol = %s
                ORDER BY created_at DESC
                LIMIT %s
                """, (symbol, limit))
            rows = cur.fetchall()
            return [self._dict_row(cur, row) for row in rows]

    def get_all_agent_decisions(self, symbol: str):
        """Get the latest decision from each agent for a stock"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT d1.* 
                FROM trading_decisions d1
                INNER JOIN (
                    SELECT agent_name, MAX(created_at) as max_date
                    FROM trading_decisions
                    WHERE symbol = %s
                    GROUP BY agent_name
                ) d2 
                ON d1.agent_name = d2.agent_name 
                AND d1.created_at = d2.max_date
                WHERE d1.symbol = %s
                ORDER BY d1.agent_name
                """, (symbol, symbol))
            rows = cur.fetchall()
            return [self._dict_row(cur, row) for row in rows]