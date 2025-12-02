from Strats.strat_base import StrategyBase
from order_manager import OrderManager
from utils.events import Signal
from utils.order_book import OrderBook
from typing import Optional
from collections import deque

class OrderBookImbalanceStrategy(StrategyBase):
    def __init__(self): # start_date, end_date, symbols, cash
        super().__init__()
        self.threshold_buy = 0.55
        self.threshold_sell = 1 - self.threshold_buy
        self.threshold_bid_proportion_change = 0.01 #in percentage
        self.symbol = "BTC/USD"
        self.midprice_window = deque(maxlen=10)
        self.bid_proportion_window = deque(maxlen=10)

    def initialize(self) -> None:
        pass

    def execute(self, data: OrderBook) -> None:
        pass

    def on_data(self, data: OrderBook) -> Optional[Signal]:

        print("on_data")
        
        best_bid = data.get_best_bid_price()
        best_ask = data.get_best_ask_price()
        
        # Calculate total bid and ask volumes
        bids = data.get_bids()  # Returns list of (price, size) tuples
        asks = data.get_asks()  # Returns list of (price, size) tuples
        
        if best_bid is None or best_ask is None:
            best_bid = max(price for price, size in bids) if bids else 0
            best_ask = min(price for price, size in asks) if asks else 0
        
        new_mid_price = (best_bid + best_ask) / 2
        self.midprice_window.append(new_mid_price)
        mid_price = new_mid_price #sum(self.midprice_window) / len(self.midprice_window)

        bid_weighted_volume = sum(
                                    size * (1 - abs(price - mid_price) / mid_price) # weight by proximity to mid price
                                    for price, size in bids
                                )
        ask_weighted_volume = sum(
                                    size * (1 - abs(price - mid_price) / mid_price) # weight by proximity to mid price
                                    for price, size in asks
                                )
    
        if bid_weighted_volume + ask_weighted_volume == 0:
            return None
        

        # Calculate bid proportion
        bid_proportion = bid_weighted_volume / (bid_weighted_volume + ask_weighted_volume)
        self.bid_proportion_window.append(bid_proportion)
        avg_bid_proportion = sum(self.bid_proportion_window) / len(self.bid_proportion_window)

        print(f"Bid Proportion: {bid_proportion:.4f}, Avg Bid Proportion: {avg_bid_proportion:.4f}")
        # Make trading decision
        #if bid_proportion > self.threshold_buy:
        if (avg_bid_proportion - bid_proportion) < -self.threshold_bid_proportion_change:
            # Strong buying pressure - place buy order
            print("ob_imbalance: buy signal")
            return Signal(
                action="buy",
                symbol=self.symbol,
                limit_price=best_ask,  # Buy at ask price
                quantity=0.001, # getaccountvalue/getmidprice * 0.1
                best_prices=(best_bid, best_ask)
            )
        #elif bid_proportion < self.threshold_sell:
        elif (avg_bid_proportion - bid_proportion) > self.threshold_bid_proportion_change:
            # Strong selling pressure - place sell order
            print("ob_imbalance: sell signal")
            return Signal(
                action="sell",
                symbol=self.symbol,
                limit_price=best_bid,  # Sell at bid price
                quantity=0.001,
                best_prices=(best_bid, best_ask)
            )
        else:
            print("hold")
            # Neutral - close positions
            # print("ob_imbalance: close signal")
            # return Signal(
            #     action="close",
            #     symbol=self.symbol,
            #     limit_price=best_ask,  # Will use best_ask for liquidate
            #     best_prices=(best_bid, best_ask)
            # )
            pass