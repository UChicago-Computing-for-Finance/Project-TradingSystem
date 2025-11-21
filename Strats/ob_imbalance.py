from strat_base import StrategyBase

class OrderBookImbalanceStrategy(StrategyBase):
    def __init__(self): # start_date, end_date, symbols, cash
        super().__init__()
        self.thresold_buy = 0.45
        self.thresold_sell = 1 - self.thresold_buy

    def initialize(self) -> None:
        pass

    def execute(self, data: pd.DataFrame) -> None:
        pass

    def on_data(self, data: pd.DataFrame) -> None:
        
        bid_volume = abs(data['bid_volume'])
        ask_volume = abs(data['ask_volume'])
        
        bid_proportion = bid_volume / (bid_volume + ask_volume)

        if bid_proportion > self.thresold_buy:
            # Place buy order
            pass
        elif bid_proportion < self.thresold_sell:
            # Place sell order
            pass
        else:
            # Close positions
            pass

