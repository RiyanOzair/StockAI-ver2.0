"""
StockAI Trade Recording System
==============================
Efficient batch-write system for trade and stock records.
Uses in-memory accumulation with periodic flushing to reduce I/O operations.
"""

import pandas as pd
import os
import atexit
from pathlib import Path
from typing import List, Dict, Any
from threading import Lock


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH RECORD MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class BatchRecordManager:
    """
    Manages batch writing of records to reduce I/O operations.
    Accumulates records in memory and flushes periodically or on shutdown.
    """
    
    _trade_buffer: List[List[Any]] = []
    _stock_buffer: List[List[Any]] = []
    _agent_daily_buffer: List[List[Any]] = []
    _agent_session_buffer: List[List[Any]] = []
    _lock = Lock()
    _flush_threshold = 100  # Flush after this many records
    _initialized = False
    
    # Column definitions (English for better compatibility)
    TRADE_COLUMNS = ["Day", "Session", "Stock", "Buyer", "Seller", "Quantity", "Price"]
    STOCK_COLUMNS = ["Day", "Session", "Stock_A_Price", "Stock_B_Price"]
    AGENT_DAILY_COLUMNS = ["Agent", "Day", "Has_Loan", "Loan_Type", "Loan_Amount",
                           "Will_Loan", "Will_Buy_A", "Will_Sell_A", "Will_Buy_B", "Will_Sell_B"]
    AGENT_SESSION_COLUMNS = ["Agent", "Day", "Session", "Total_Assets", "Cash", 
                             "Stock_A_Value", "Stock_B_Value", "Action_Type", 
                             "Action_Stock", "Amount", "Price"]
    
    @classmethod
    def initialize(cls):
        """Initialize the manager and register shutdown handler."""
        if not cls._initialized:
            atexit.register(cls.flush_all)
            cls._initialized = True
    
    @classmethod
    def add_trade(cls, date: int, session: int, stock_type: str, buyer: str, 
                  seller: str, quantity: int, price: float):
        """Add a trade record to the buffer."""
        cls.initialize()
        with cls._lock:
            cls._trade_buffer.append([date, session, stock_type, buyer, seller, quantity, price])
            if len(cls._trade_buffer) >= cls._flush_threshold:
                cls._flush_trades()
    
    @classmethod
    def add_stock(cls, date: int, session: int, stock_a_price: float, stock_b_price: float):
        """Add a stock price record to the buffer."""
        cls.initialize()
        with cls._lock:
            cls._stock_buffer.append([date, session, stock_a_price, stock_b_price])
            if len(cls._stock_buffer) >= cls._flush_threshold:
                cls._flush_stocks()
    
    @classmethod
    def add_agent_daily(cls, agent: str, date: int, has_loan: str, loan_type: int,
                        loan_amount: float, will_loan: str, will_buy_a: str,
                        will_sell_a: str, will_buy_b: str, will_sell_b: str):
        """Add an agent daily record to the buffer."""
        cls.initialize()
        with cls._lock:
            cls._agent_daily_buffer.append([agent, date, has_loan, loan_type, loan_amount,
                                           will_loan, will_buy_a, will_sell_a, will_buy_b, will_sell_b])
            if len(cls._agent_daily_buffer) >= cls._flush_threshold:
                cls._flush_agent_daily()
    
    @classmethod
    def add_agent_session(cls, agent: str, date: int, session: int, total_assets: float,
                          cash: float, stock_a_value: float, stock_b_value: float,
                          action_type: str, action_stock: str, amount: int, price: float):
        """Add an agent session record to the buffer."""
        cls.initialize()
        with cls._lock:
            cls._agent_session_buffer.append([agent, date, session, total_assets, cash,
                                              stock_a_value, stock_b_value, action_type,
                                              action_stock, amount, price])
            if len(cls._agent_session_buffer) >= cls._flush_threshold:
                cls._flush_agent_session()
    
    @classmethod
    def _ensure_dir(cls, file_path: str):
        """Ensure the directory for a file exists."""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def _flush_to_excel(cls, buffer: List[List[Any]], columns: List[str], file_name: str):
        """Flush a buffer to an Excel file."""
        if not buffer:
            return
        
        cls._ensure_dir(file_name)
        
        try:
            if os.path.isfile(file_name):
                existing_df = pd.read_excel(file_name)
            else:
                existing_df = pd.DataFrame(columns=columns)
            
            new_df = pd.DataFrame(buffer, columns=columns)
            all_records_df = pd.concat([existing_df, new_df], ignore_index=True)
            all_records_df.to_excel(file_name, index=False)
        except Exception as e:
            print(f"Warning: Failed to flush records to {file_name}: {e}")
    
    @classmethod
    def _flush_trades(cls):
        """Flush trade buffer to Excel."""
        cls._flush_to_excel(cls._trade_buffer, cls.TRADE_COLUMNS, "res/trades.xlsx")
        cls._trade_buffer.clear()
    
    @classmethod
    def _flush_stocks(cls):
        """Flush stock buffer to Excel."""
        cls._flush_to_excel(cls._stock_buffer, cls.STOCK_COLUMNS, "res/stocks.xlsx")
        cls._stock_buffer.clear()
    
    @classmethod
    def _flush_agent_daily(cls):
        """Flush agent daily buffer to Excel."""
        cls._flush_to_excel(cls._agent_daily_buffer, cls.AGENT_DAILY_COLUMNS, "res/agent_day_record.xlsx")
        cls._agent_daily_buffer.clear()
    
    @classmethod
    def _flush_agent_session(cls):
        """Flush agent session buffer to Excel."""
        cls._flush_to_excel(cls._agent_session_buffer, cls.AGENT_SESSION_COLUMNS, "res/agent_session_record.xlsx")
        cls._agent_session_buffer.clear()
    
    @classmethod
    def flush_all(cls):
        """Flush all buffers to their respective files."""
        with cls._lock:
            cls._flush_trades()
            cls._flush_stocks()
            cls._flush_agent_daily()
            cls._flush_agent_session()
    
    @classmethod
    def get_buffer_stats(cls) -> Dict[str, int]:
        """Get current buffer sizes for monitoring."""
        return {
            "trades": len(cls._trade_buffer),
            "stocks": len(cls._stock_buffer),
            "agent_daily": len(cls._agent_daily_buffer),
            "agent_session": len(cls._agent_session_buffer)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY COMPATIBILITY CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class TradeRecord:
    """Trade record - now uses batch manager for efficient writes."""
    
    def __init__(self, date, session, stock_type, buyer, seller, quantity, price):
        self.date = date
        self.session = session
        self.stock_type = stock_type
        self.buyer = buyer
        self.seller = seller
        self.quantity = quantity
        self.price = price

    def write_to_excel(self, file_name="res/trades.xlsx"):
        """Write to Excel using batch manager."""
        BatchRecordManager.add_trade(
            self.date, self.session, self.stock_type,
            self.buyer, self.seller, self.quantity, self.price
        )


def create_trade_record(date, stage, stock, buy_trader, sell_trader, amount, price):
    """Create and queue a trade record for batch writing."""
    BatchRecordManager.add_trade(date, stage, stock, buy_trader, sell_trader, amount, price)


class StockRecord:
    """Stock price record - now uses batch manager for efficient writes."""
    
    def __init__(self, date, session, stock_a_price, stock_b_price):
        self.date = date
        self.session = session
        self.stock_a_price = stock_a_price
        self.stock_b_price = stock_b_price

    def write_to_excel(self, file_name="res/stocks.xlsx"):
        """Write to Excel using batch manager."""
        BatchRecordManager.add_stock(
            self.date, self.session, self.stock_a_price, self.stock_b_price
        )


def create_stock_record(date, session, stock_a_price, stock_b_price):
    """Create and queue a stock record for batch writing."""
    BatchRecordManager.add_stock(date, session, stock_a_price, stock_b_price)


class AgentRecordDaily:
    """Agent daily record - now uses batch manager for efficient writes."""
    
    def __init__(self, agent, date, loan_json):
        self.agent = agent
        self.date = date
        self.if_loan = loan_json.get("loan", "no")
        self.loan_type = 0
        self.loan_amount = 0
        if self.if_loan == "yes":
            self.loan_type = loan_json.get("loan_type", 0)
            self.loan_amount = loan_json.get("amount", 0)
        self.will_loan = "no"
        self.will_buy_a = "no"
        self.will_sell_a = "no"
        self.will_buy_b = "no"
        self.will_sell_b = "no"

    def add_estimate(self, js):
        self.will_loan = js.get("loan", "no")
        self.will_buy_a = js.get("buy_A", "no")
        self.will_sell_a = js.get("sell_A", "no")
        self.will_buy_b = js.get("buy_B", "no")
        self.will_sell_b = js.get("sell_B", "no")

    def write_to_excel(self, file_name="res/agent_day_record.xlsx"):
        """Write to Excel using batch manager."""
        BatchRecordManager.add_agent_daily(
            self.agent, self.date, self.if_loan, self.loan_type, self.loan_amount,
            self.will_loan, self.will_buy_a, self.will_sell_a, self.will_buy_b, self.will_sell_b
        )

class AgentRecordSession:
    """Agent session record - now uses batch manager for efficient writes."""
    
    def __init__(self, agent, date, session, proper, cash, stock_a_value, stock_b_value, action_json):
        self.agent = agent
        self.date = date
        self.session = session
        self.proper = proper
        self.cash = cash
        self.stock_a_value = stock_a_value
        self.stock_b_value = stock_b_value
        self.action_stock = "-"
        self.amount = 0
        self.price = 0
        self.action_type = action_json.get("action_type", "no")
        if self.action_type != "no":
            self.action_stock = action_json.get("stock", "-")
            self.amount = action_json.get("amount", 0)
            self.price = action_json.get("price", 0)

    def write_to_excel(self, file_name="res/agent_session_record.xlsx"):
        """Write to Excel using batch manager."""
        BatchRecordManager.add_agent_session(
            self.agent, self.date, self.session, self.proper, self.cash,
            self.stock_a_value, self.stock_b_value, self.action_type,
            self.action_stock, self.amount, self.price
        )


def create_agentses_record(agent, date, session, proper, cash, stock_a_value, stock_b_value, action_json):
    """Create and queue an agent session record for batch writing."""
    record = AgentRecordSession(agent, date, session, proper, cash, stock_a_value, stock_b_value, action_json)
    record.write_to_excel()

