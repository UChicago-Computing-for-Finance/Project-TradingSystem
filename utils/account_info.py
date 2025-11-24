# Import Dependencies
import numpy as np
import pandas as pd
import alpaca_trade_api as tradeapi
import datetime as dt
from typing import Dict, List, Optional

import os
from dotenv import load_dotenv

load_dotenv()

Alpaca_endpoint = os.getenv("ALPACA_ENDPOINT")
Alpaca_key = os.getenv("ALPACA_KEY")
Alpaca_secret = os.getenv("ALPACA_SECRET")


class Position:
    """Represents a single position from the Alpaca API"""
    
    def __init__(self, data: dict):
        self.qty: float = float(data.get("qty", 0))
        self.unrealized_pl: float = float(data.get("unrealized_pl", 0))
        self.side: str = data.get("side", "")
        self.symbol: str = data.get("symbol", "")
        self.market_value: float = float(data.get("market_value", 0))


class AccountInfo:
    """Manages account information and positions from Alpaca API"""
    
    def __init__(self):
        self.api = tradeapi.REST(Alpaca_key, Alpaca_secret, Alpaca_endpoint)
        self._account = None
        self.positions: Dict[str, Position] = {}
        self._refresh_account()
        self._refresh_positions()
    
    def _refresh_account(self):
        """Refresh account information from API"""
        self._account = self.api.get_account()
    
    def _refresh_positions(self):
        """Refresh positions from API"""
        api_positions = self.api.list_positions()
        self.positions.clear()
        
        for pos_data in api_positions:
            # Handle if it's already a Position object from alpaca library
            if hasattr(pos_data, '__dict__'):
                # Convert alpaca Position object to dict
                if hasattr(pos_data, '_raw'):
                    pos_dict = pos_data._raw
                else:
                    pos_dict = {k: v for k, v in pos_data.__dict__.items() if not k.startswith('_')}
            else:
                pos_dict = pos_data
            
            position = Position(pos_dict)
            self.positions[position.symbol] = position
    
    def refresh(self):
        """Refresh both account info and positions"""
        self._refresh_account()
        self._refresh_positions()
    
    # Account Information Methods
    def get_account(self):
        """Get full account object"""
        self._refresh_account()
        return self._account
    
    def get_account_balance(self) -> float:
        """Get account balance"""
        self._refresh_account()
        return float(self._account.cash)
    
    def get_buying_power(self) -> float:
        """Get buying power"""
        self._refresh_account()
        return float(self._account.buying_power)
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value (cash + positions)"""
        self._refresh_account()
        return float(self._account.portfolio_value)
    
    def get_equity(self) -> float:
        """Get account equity"""
        self._refresh_account()
        return float(self._account.equity)
    
    # Position Methods
    def get_positions(self) -> List[Position]:
        """Get all positions as Position objects"""
        self._refresh_positions()
        return list(self.positions.values())
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol. Returns Position object or None if no position exists."""
        self._refresh_positions()
        return self.positions.get(symbol, None)
    
    def has_position(self, symbol: str) -> bool:
        """Check if a position exists for the given symbol"""
        self._refresh_positions()
        return symbol in self.positions
    
    def get_all_position_symbols(self) -> List[str]:
        """Get list of all symbols with positions"""
        self._refresh_positions()
        return list(self.positions.keys())
    
    # Portfolio Metrics
    def get_total_market_value(self) -> float:
        """Get total market value of all positions"""
        self._refresh_positions()
        return sum(pos.market_value for pos in self.positions.values())
    
    def get_total_unrealized_pl(self) -> float:
        """Get total unrealized P&L across all positions"""
        self._refresh_positions()
        return sum(pos.unrealized_pl for pos in self.positions.values())