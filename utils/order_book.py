from sortedcontainers import SortedDict
from typing import Optional, List, Tuple, Dict

import json


class OrderBook:
    """
    Maintains a local order book for a single symbol.
    Updates based on incoming WebSocket messages from Alpaca.
    Maintains configurable depth (default 10 levels) above and below mid price.
    """
    
    def __init__(self, symbol: str, max_levels: int = 10, trim_frequency: int = 100, full: bool = False):
        """
        Initialize an order book for a given symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USD")
            max_levels: Maximum number of price levels to maintain above/below mid price
        """
        self.symbol = symbol
        self.max_levels = max_levels
        self.trim_frequency = trim_frequency
        self.update_count = 0
        self.full = full
        
        # Bids: use negated prices as keys for descending order (highest first)
        # Values are sizes at each price level
        self.bids = SortedDict()
        
        # Asks: use regular prices as keys for ascending order (lowest first)
        # Values are sizes at each price level
        self.asks = SortedDict()
        
        self.last_update_time: Optional[str] = None
    
    def _update_bids(self, bid_updates: List[Dict[str, float]]) -> None:
        """
        Update bid levels from incoming message.
        
        Args:
            bid_updates: List of dicts with 'p' (price) and 's' (size) keys
        """
        for update in bid_updates:
            price = update['p']
            size = update['s']
            
            # Use negated price as key for descending order
            negated_price = -price
            
            if size == 0:
                # Remove the price level
                if negated_price in self.bids:
                    del self.bids[negated_price]
            else:
                # Add or update the price level
                self.bids[negated_price] = size
    
    def _update_asks(self, ask_updates: List[Dict[str, float]]) -> None:
        """
        Update ask levels from incoming message.
        
        Args:
            ask_updates: List of dicts with 'p' (price) and 's' (size) keys
        """
        for update in ask_updates:
            price = update['p']
            size = update['s']
            
            if size == 0:
                # Remove the price level
                if price in self.asks:
                    del self.asks[price]
            else:
                # Add or update the price level
                self.asks[price] = size
    
    def _reset_book(self, bids: List[Dict[str, float]], asks: List[Dict[str, float]]) -> None:
        """
        Reset the entire order book with new data.
        Called when 'r': true in the message.
        
        Args:
            bids: Complete list of bid levels
            asks: Complete list of ask levels
        """
        self.bids.clear()
        self.asks.clear()
        
        # Rebuild bids
        for bid in bids:
            if bid['s'] > 0:  # Only add non-zero sizes
                negated_price = -bid['p']
                self.bids[negated_price] = bid['s']
        
        # Rebuild asks
        for ask in asks:
            if ask['s'] > 0:  # Only add non-zero sizes
                self.asks[ask['p']] = ask['s']
    
    def _trim_to_max_levels(self) -> None:
        """
        Trim the order book to maintain only max_levels above and below mid price.
        """
        if not self.bids or not self.asks:
            return
        
        # Fast path: if we have fewer levels than max, no trimming needed
        if len(self.bids) <= self.max_levels and len(self.asks) <= self.max_levels:
            return
        
        # Get best prices (already cached in SortedDict)
        best_bid_price = -self.bids.keys()[0] if self.bids else None
        best_ask_price = self.asks.keys()[0] if self.asks else None
        
        if best_bid_price is None or best_ask_price is None:
            return
        
        # Trim bids: keep only top max_levels (highest prices)
        if len(self.bids) > self.max_levels:
            # SortedDict is already sorted, just keep first max_levels
            keys_to_remove = list(self.bids.keys())[self.max_levels:]
            for key in keys_to_remove:
                del self.bids[key]
        
        # Trim asks: keep only top max_levels (lowest prices)
        if len(self.asks) > self.max_levels:
            # SortedDict is already sorted, just keep first max_levels
            keys_to_remove = list(self.asks.keys())[self.max_levels:]
            for key in keys_to_remove:
                del self.asks[key]
    
    def _get_price_increment(self) -> float:
        """
        Estimate price increment based on current best bid/ask.
        For BTC/USD, typical tick size is around 0.01-1.0.
        This is a simple heuristic - can be refined later.
        """
        best_bid = self.get_best_bid_price()
        best_ask = self.get_best_ask_price()
        
        if best_bid and best_ask:
            spread = best_ask - best_bid
            # Use 1% of spread as increment, with minimum of 0.01
            return max(0.01, spread * 0.01)
        
        return 1.0  # Default fallback
    
    def update(self, message: Dict) -> None:
        """
        Update the order book based on an incoming WebSocket message.
        
        Args:
            message: Dictionary containing order book update with keys:
                    - 'T': message type (should be 'o')
                    - 'S': symbol
                    - 't': timestamp
                    - 'b': bids array
                    - 'a': asks array
                    - 'r': reset flag (boolean)
        """
        # Validate that message is a dictionary
        if not isinstance(message, dict):
            return
        
        # Validate message type
        if message.get('T') != 'o':
            return
        
        # Validate symbol matches
        if message.get('S') != self.symbol:
            return
        
        # Update timestamp
        self.last_update_time = message.get('t')
        
        # Handle reset
        if message.get('r', False):
            self._reset_book(
                message.get('b', []),
                message.get('a', [])
            )
        else:
            # Handle incremental updates
            if 'b' in message and message['b']:
                self._update_bids(message['b'])
            
            if 'a' in message and message['a']:
                self._update_asks(message['a'])
        
        # Only trim periodically for speed (trimming is expensive)
        self.update_count += 1
        if self.update_count % self.trim_frequency == 0:
            self._trim_to_max_levels()
    
    def get_best_bid_price(self) -> Optional[float]:
        """Get the best (highest) bid price."""
        if not self.bids:
            return None
        # Last key in bids (since keys are negated, last = highest price)
        return -self.bids.keys()[0]
    
    def get_best_bid_size(self) -> Optional[float]:
        """Get the size at the best bid price."""
        if not self.bids:
            return None
        return self.bids.values()[0]
    
    def get_best_ask_price(self) -> Optional[float]:
        """Get the best (lowest) ask price."""
        if not self.asks:
            return None
        return self.asks.keys()[0]
    
    def get_best_ask_size(self) -> Optional[float]:
        """Get the size at the best ask price."""
        if not self.asks:
            return None
        return self.asks.values()[0]
    
    def get_spread(self) -> Optional[float]:
        """Get the bid-ask spread."""
        best_bid = self.get_best_bid_price()
        best_ask = self.get_best_ask_price()
        
        if best_bid is None or best_ask is None:
            return None
        
        return best_ask - best_bid
    
    def get_mid_price(self) -> Optional[float]:
        """Get the mid price (average of best bid and ask)."""
        best_bid = self.get_best_bid_price()
        best_ask = self.get_best_ask_price()
        
        if best_bid is None or best_ask is None:
            return None
        
        return (best_bid + best_ask) / 2
    
    def get_bids(self, max_levels: Optional[int] = None) -> List[Tuple[float, float]]:
        """
        Get bid levels as list of (price, size) tuples, sorted lowest to highest.
        
        Args:
            max_levels: Optional limit on number of levels to return
        """
        if max_levels is None:
            max_levels = len(self.bids)
        
        result = []
        all_negated_prices = list(self.bids.keys())
        
        for negated_price in all_negated_prices[:max_levels]:
            actual_price = -negated_price
            size = self.bids[negated_price]
            result.append((actual_price, size))
        
        return result
    
    def get_asks(self, max_levels: Optional[int] = None) -> List[Tuple[float, float]]:
        """
        Get ask levels as list of (price, size) tuples, sorted highest to lowest.
        
        Args:
            max_levels: Optional limit on number of levels to return
        """
        if max_levels is None:
            max_levels = len(self.asks)
        
        result = []

        all_prices = list(self.asks.keys())[:max_levels]  # Get lowest N asks
    
        for price in reversed(all_prices):
            size = self.asks[price]
            result.append((price, size))
        
        return result

        # for price in list(self.asks.keys())[:max_levels]:
        #     size = self.asks[price]
        #     result.append((price, size))
        
        # return result
    
    def __repr__(self) -> str:
        """String representation of the order book."""
        best_bid = self.get_best_bid_price()
        best_ask = self.get_best_ask_price()
        spread = self.get_spread()
        
        return (f"OrderBook(symbol={self.symbol}, "
                f"best_bid={best_bid}, best_ask={best_ask}, "
                f"spread={spread}, bid_levels={len(self.bids)}, "
                f"ask_levels={len(self.asks)})")

    def print_orderbook(self, num_levels: Optional[int] = None) -> None:
        """
        Print a formatted visualization of the order book.
        Shows asks above, spread separator, and bids below in a 2-column table.
        
        Args:
            num_levels: Number of levels to display on each side (default: all available)
        """
        if num_levels is None:
            num_levels = min(len(self.bids), len(self.asks), self.max_levels)
        
        bids = self.get_bids(num_levels)
        asks = self.get_asks(num_levels)
        
        best_bid = self.get_best_bid_price()
        best_ask = self.get_best_ask_price()
        best_bid_size = self.get_best_bid_size()
        best_ask_size = self.get_best_ask_size()
        spread = self.get_spread()
        mid_price = self.get_mid_price()

        print("\n")
        if self.last_update_time:
            print(f"===== Last Update: {self.last_update_time} =======")
        else:
            print(f"================================================")

        if self.full:
            for ask in asks:
                print(f"Ask: {ask}")
        print(f"Best Ask: {best_ask}, {best_ask_size}")
        print("--------------------------------")
        print(f"Spread: ${spread} , Mid Price: ${mid_price}")
        print("--------------------------------")
        print(f"Best Bid: {best_bid}, {best_bid_size}")
        if self.full:
            for bid in bids:
                print(f"Bid: {bid}")
        print(f"================================================")
        print("\n")
    
    def record_orderbook(self, num_levels: int = 10, filename: str = "order_book.json") -> None:
        """
        Record the order book to a JSON file.
        Appends to an array in the file, or creates a new array if file doesn't exist.
        
        Args:
            num_levels: Number of bid/ask levels to record (default: 10)
            filename: Output filename (default: "order_book.json")
        """
        if not self.last_update_time:
            return  # Skip if no timestamp
        
        # Get bids (highest to lowest) - need to reverse current get_bids() output
        bids_list = self.get_bids(num_levels)
        bids_list.reverse()  # Reverse to get highest first
        
        # Get asks (lowest to highest) - need to reverse current get_asks() output  
        asks_list = self.get_asks(num_levels)
        asks_list.reverse()  # Reverse to get lowest first
        
        # Format bids as list of dicts
        bids_data = [{"price": float(price), "size": float(size)} for price, size in bids_list]
        
        # Format asks as list of dicts
        asks_data = [{"price": float(price), "size": float(size)} for price, size in asks_list]
        
        # Create JSON object
        orderbook_record = {
            "asset": self.symbol,
            "time": self.last_update_time,
            "data": {
                "bids": bids_data,
                "asks": asks_data
            }
        }
        
        # Read existing data or create new array
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []
        
        # Append new record
        data.append(orderbook_record)
        
        # Write back to file
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)