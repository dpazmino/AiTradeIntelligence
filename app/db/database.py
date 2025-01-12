import os
import mysql.connector
from mysql.connector import Error
import time
from datetime import datetime

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
                self.conn = mysql.connector.connect(
                    host='127.0.0.1',
                    user='runner',  # Using the runner user that was created during initialization
                    password='',    # No password was set during initialization
                    database='ai_hedge_fund',
                    port=3306
                )

                print("Successfully connected to MySQL database!")
                return
            except Error as e:
                retry_count += 1
                print(f"Database connection error: {str(e)}")
                print("Current connection details (without password):")
                print(f"Host: 127.0.0.1")
                print(f"Database: ai_hedge_fund")
                print(f"User: runner")

                if retry_count == self.max_retries:
                    raise Exception(f"Failed to connect to database after {self.max_retries} attempts: {str(e)}")
                print(f"Connection attempt {retry_count} failed, retrying in 5 seconds...")
                time.sleep(5)

    def ensure_connection(self):
        """Ensure database connection is active"""
        try:
            if self.conn and self.conn.is_connected():
                return True
            print("Connection lost, attempting to reconnect...")
            self.connect_with_retry()
        except Error:
            print("Connection verification failed, reconnecting...")
            self.connect_with_retry()

    def create_tables(self):
        """Create necessary database tables"""
        self.ensure_connection()
        cursor = self.conn.cursor()
        try:
            # First, create the database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS ai_hedge_fund")
            cursor.execute("USE ai_hedge_fund")

            # Create tables with auto-incrementing IDs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    quantity INT NOT NULL,
                    entry_price FLOAT NOT NULL,
                    entry_date DATETIME NOT NULL,
                    exit_price FLOAT,
                    exit_date DATETIME,
                    strategy VARCHAR(50) NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    signal_type VARCHAR(10) NOT NULL,
                    strategy VARCHAR(50) NOT NULL,
                    confidence FLOAT NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS screened_stocks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL UNIQUE,
                    company_name VARCHAR(100),
                    current_price DECIMAL(10, 2) NOT NULL,
                    average_volume BIGINT NOT NULL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist_stocks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL UNIQUE,
                    notes TEXT,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_decisions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    decision TEXT NOT NULL,
                    confidence FLOAT NOT NULL,
                    agent_name VARCHAR(50) NOT NULL DEFAULT 'supervisor',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_decision (symbol, agent_name, DATE(created_at))
                )
            """)

            self.conn.commit()
            print("Database tables created successfully")
        except Error as e:
            self.conn.rollback()
            print(f"Error creating tables: {str(e)}")
            raise
        finally:
            cursor.close()

    def execute_with_retry(self, operation):
        """Execute database operation with retry logic"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.ensure_connection()
                return operation()
            except Error as e:
                if attempt == max_attempts - 1:
                    raise
                print(f"Database operation failed, retrying... ({attempt + 1}/{max_attempts})")
                time.sleep(2)

    def add_position(self, symbol, quantity, entry_price, strategy):
        def operation():
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO portfolio (symbol, quantity, entry_price, entry_date, strategy)
                    VALUES (%s, %s, %s, %s, %s)
                    """, (symbol, quantity, entry_price, datetime.now(), strategy))
                self.conn.commit()
            finally:
                cursor.close()
        self.execute_with_retry(operation)

    def close_position(self, position_id, exit_price):
        def operation():
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    UPDATE portfolio 
                    SET exit_price = %s, exit_date = %s
                    WHERE id = %s
                    """, (exit_price, datetime.now(), position_id))
                self.conn.commit()
            finally:
                cursor.close()
        self.execute_with_retry(operation)

    def get_open_positions(self):
        def operation():
            cursor = self.conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT * FROM portfolio 
                    WHERE exit_date IS NULL
                    """)
                return cursor.fetchall()
            finally:
                cursor.close()
        return self.execute_with_retry(operation)

    def add_signal(self, symbol, signal_type, strategy, confidence):
        def operation():
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO trading_signals 
                    (symbol, signal_type, strategy, confidence, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    """, (symbol, signal_type, strategy, confidence, datetime.now()))
                self.conn.commit()
            finally:
                cursor.close()
        self.execute_with_retry(operation)

    def upsert_screened_stock(self, symbol, company_name, current_price, average_volume):
        def operation():
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
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
            finally:
                cursor.close()
        self.execute_with_retry(operation)

    def get_screened_stocks(self):
        def operation():
            cursor = self.conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT * FROM screened_stocks 
                    ORDER BY symbol ASC
                    """)
                return cursor.fetchall()
            finally:
                cursor.close()
        return self.execute_with_retry(operation)

    def clear_old_screened_stocks(self, hours=24):
        def operation():
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    DELETE FROM screened_stocks 
                    WHERE last_updated < DATE_SUB(NOW(), INTERVAL %s HOUR)
                    """, (hours,))
                self.conn.commit()
            finally:
                cursor.close()
        self.execute_with_retry(operation)

    def add_to_watchlist(self, symbol, notes=None):
        def operation():
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO watchlist_stocks (symbol, notes)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE
                        notes = VALUES(notes),
                        added_date = CURRENT_TIMESTAMP
                    """, (symbol.upper(), notes))
                self.conn.commit()
            finally:
                cursor.close()
        self.execute_with_retry(operation)

    def remove_from_watchlist(self, symbol):
        def operation():
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    DELETE FROM watchlist_stocks 
                    WHERE symbol = %s
                    """, (symbol.upper(),))
                self.conn.commit()
            finally:
                cursor.close()
        self.execute_with_retry(operation)

    def get_watchlist(self):
        def operation():
            cursor = self.conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT * FROM watchlist_stocks 
                    ORDER BY added_date DESC
                    """)
                return cursor.fetchall()
            finally:
                cursor.close()
        return self.execute_with_retry(operation)

    def save_trading_decision(self, symbol: str, decision: str, confidence: float, agent_name: str = 'supervisor'):
        def operation():
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO trading_decisions (symbol, decision, confidence, agent_name)
                    VALUES (%s, %s, %s, %s)
                    """, (symbol, decision, confidence, agent_name))
                self.conn.commit()
            finally:
                cursor.close()
        self.execute_with_retry(operation)

    def get_latest_trading_decisions(self, symbol: str, limit: int = 2):
        def operation():
            cursor = self.conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT decision, confidence, agent_name, created_at
                    FROM trading_decisions
                    WHERE symbol = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """, (symbol, limit))
                return cursor.fetchall()
            finally:
                cursor.close()
        return self.execute_with_retry(operation)

    def get_all_agent_decisions(self, symbol: str):
        def operation():
            cursor = self.conn.cursor(dictionary=True)
            try:
                cursor.execute("""
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
                    ORDER BY agent_name
                    """, (symbol,))
                return cursor.fetchall()
            finally:
                cursor.close()
        return self.execute_with_retry(operation)