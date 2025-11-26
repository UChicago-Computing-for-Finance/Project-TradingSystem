from Strats.strat_base import StrategyBase
from order_manager import OrderManager
from utils.events import Signal
from utils.order_book import OrderBook
from typing import Optional

class OrderBookImbalanceStrategy(StrategyBase):
    def __init__(self): # start_date, end_date, symbols, cash
        super().__init__()
        self.threshold_buy = 0.5995
        self.threshold_sell = 1 - self.threshold_buy
        self.symbol = "BTC/USD"

    def initialize(self) -> None:
        pass

    def execute(self, data: OrderBook) -> None:
        pass

    def on_data(self, data: OrderBook) -> Optional[Signal]:

        print("on_data")
        
        best_bid = data.get_best_bid_price()
        best_ask = data.get_best_ask_price()
        
        # Calculate total bid and ask volumes
        bids = data.get_bids()
        asks = data.get_asks()
        
        if best_bid is None or best_ask is None:
            best_bid = max(bid['price'] for bid in bids)
            best_ask = min(ask['price'] for ask in asks)
        
        mid_price = (best_bid + best_ask) / 2
        

        bid_weighted_volume = sum(
                                    bid.get('size', 0) * (1 - abs(bid.get('price', 0) - mid_price) / mid_price) # weight by proximity to mid price
                                    for bid in bids
                                )
        ask_weighted_volume = sum(
                                    ask.get('size', 0) * (1 - abs(ask.get('price', 0) - mid_price) / mid_price) # weight by proximity to mid price
                                    for ask in asks
                                )
    
        if bid_weighted_volume + ask_weighted_volume == 0:
            return None
        

        # Calculate bid proportion
        bid_proportion = bid_weighted_volume / (bid_weighted_volume + ask_weighted_volume)
        
        # Make trading decision
        if bid_proportion > self.threshold_buy:
            # Strong buying pressure - place buy order
            print("ob_imbalance: buy signal")
            return Signal(
                action="buy",
                symbol=self.symbol,
                limit_price=best_ask,  # Buy at ask price
                quantity=0.001
            )
        elif bid_proportion < self.threshold_sell:
            # Strong selling pressure - place sell order
            print("ob_imbalance: sell signal")
            return Signal(
                action="sell",
                symbol=self.symbol,
                limit_price=best_bid,  # Sell at bid price
                quantity=0.001
            )
        else:
            # Neutral - close positions
            print("ob_imbalance: close signal")
            return Signal(
                action="close",
                symbol=self.symbol,
                limit_price=best_ask  # Will use best_ask for liquidate
            )