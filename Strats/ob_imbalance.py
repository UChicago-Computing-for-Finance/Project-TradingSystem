from Strats.strat_base import StrategyBase
from order_manager import OrderManager
from utils.events import Signal
from utils.order_book import OrderBook
from typing import Optional

class OrderBookImbalanceStrategy(StrategyBase):
    def __init__(self, order_manager: OrderManager): # start_date, end_date, symbols, cash
        super().__init__()
        self.order_manager = order_manager
        self.threshold_buy = 0.45
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
        
        if best_bid is None or best_ask is None:
            return None
        
        # Calculate total bid and ask volumes
        bids = data.get_bids()
        asks = data.get_asks()
        
        bid_volume = sum(size for _, size in bids)
        ask_volume = sum(size for _, size in asks)
        
        if bid_volume + ask_volume == 0:
            return None
        
        # Calculate bid proportion
        bid_proportion = bid_volume / (bid_volume + ask_volume)
        
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