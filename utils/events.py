from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass

class EventType(Enum):
    """Event types for the trading system"""
    ORDERBOOK_UPDATE = "orderbook_update"
    SIGNAL = "signal"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"

@dataclass
class Event:
    """Event container for queue-based communication"""
    type: EventType
    payload: Any
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            import time
            self.timestamp = time.time()

@dataclass
class Signal:
    """Trading signal from strategy"""
    action: str  # "buy", "sell", "close"
    symbol: str
    limit_price: float
    quantity: float = 1.0