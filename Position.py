from typing import Dict, List, Optional


class Position:
    """Represents a single position from the Alpaca API"""
    
    def __init__(self, data: dict):
        self.asset_class: str = data.get("asset_class", "")
        self.asset_id: str = data.get("asset_id", "")
        self.asset_marginable: bool = data.get("asset_marginable", False)
        self.avg_entry_price: float = float(data.get("avg_entry_price", 0))
        self.change_today: float = float(data.get("change_today", 0))
        self.cost_basis: float = float(data.get("cost_basis", 0))
        self.current_price: float = float(data.get("current_price", 0))
        self.exchange: str = data.get("exchange", "")
        self.lastday_price: float = float(data.get("lastday_price", 0))
        self.market_value: float = float(data.get("market_value", 0))
        self.qty: float = float(data.get("qty", 0))
        self.qty_available: float = float(data.get("qty_available", 0))
        self.side: str = data.get("side", "")
        self.symbol: str = data.get("symbol", "")
        self.unrealized_intraday_pl: float = float(data.get("unrealized_intraday_pl", 0))
        self.unrealized_intraday_plpc: float = float(data.get("unrealized_intraday_plpc", 0))
        self.unrealized_pl: float = float(data.get("unrealized_pl", 0))
        self.unrealized_plpc: float = float(data.get("unrealized_plpc", 0))
    
    def __repr__(self) -> str:
        return (f"Position(symbol={self.symbol}, qty={self.qty}, "
                f"current_price={self.current_price}, market_value={self.market_value}, "
                f"unrealized_pl={self.unrealized_pl})")
    
    def to_dict(self) -> dict:
        """Convert position back to dictionary format"""
        return {
            "asset_class": self.asset_class,
            "asset_id": self.asset_id,
            "asset_marginable": self.asset_marginable,
            "avg_entry_price": str(self.avg_entry_price),
            "change_today": str(self.change_today),
            "cost_basis": str(self.cost_basis),
            "current_price": str(self.current_price),
            "exchange": self.exchange,
            "lastday_price": str(self.lastday_price),
            "market_value": str(self.market_value),
            "qty": str(self.qty),
            "qty_available": str(self.qty_available),
            "side": self.side,
            "symbol": self.symbol,
            "unrealized_intraday_pl": str(self.unrealized_intraday_pl),
            "unrealized_intraday_plpc": str(self.unrealized_intraday_plpc),
            "unrealized_pl": str(self.unrealized_pl),
            "unrealized_plpc": str(self.unrealized_plpc)
        }


class PositionManager:
    """Manages a collection of positions with quick symbol-based access"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
    
    def update_from_api_response(self, api_positions: List) -> None:
        """
        Update positions from API response.
        Handles both dict and Position objects from alpaca_trade_api.
        
        Args:
            api_positions: List of position data from API
        """
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
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol"""
        return self.positions.get(symbol, None)
    
    def has_position(self, symbol: str) -> bool:
        """Check if a position exists for the given symbol"""
        return symbol in self.positions
    
    def get_all_symbols(self) -> List[str]:
        """Get list of all symbols with positions"""
        return list(self.positions.keys())
    
    def get_total_market_value(self) -> float:
        """Calculate total market value across all positions"""
        return sum(pos.market_value for pos in self.positions.values())
    
    def get_total_unrealized_pl(self) -> float:
        """Calculate total unrealized P&L across all positions"""
        return sum(pos.unrealized_pl for pos in self.positions.values())
    
    def __repr__(self) -> str:
        return f"PositionManager({len(self.positions)} positions: {list(self.positions.keys())})"
    
    def __len__(self) -> int:
        return len(self.positions)
