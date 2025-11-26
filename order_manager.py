import requests
import os
from dotenv import load_dotenv
from utils.account_info import AccountInfo

class OrderManager:

    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(OrderManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("ALPACA_KEY")
        self.api_secret = os.getenv("ALPACA_SECRET")
        self.base_url = os.getenv("ALPACA_ENDPOINT")
        self.account_info = AccountInfo()

    def buy(self, symbol, limit_price, quantity = 1):
        # if self.position_manager.has_position(symbol):
        #     position = self.position_manager.get_position(symbol)
        #     if position.qty > 0: # we are already long, do nothing for strat v1
        #         pass
        #     else:
        #         self.order_limit(symbol, quantity, bestask, 'buy')

        return self.order_limit(symbol, quantity, limit_price, 'buy')
    
    def sell(self, symbol, limit_price, quantity = 1):
        # if self.position_manager.has_position(symbol):
        #     position = self.position_manager.get_position(symbol)
        #     if position.qty > 0: # we are already long, do nothing for strat v1
        #         pass
        #     else:
        #         self.order_limit(symbol, quantity, bestbid, 'sell')
        return self.order_limit(symbol, quantity, limit_price, 'sell')

    # def close_position(self, symbol, bestask, bestbid):
    #     # Logic to close a position
    #     if self.position_manager.has_position(symbol):
    #         position = self.position_manager.get_position(symbol)
    #         if position.qty > 0 and position.unrealized_pl > 0:
    #             if position.side  == "long":
    #                 self.order_limit(symbol, position.qty, bestbid, 'sell')
    #             elif position.side == "short":
    #                 self.order_limit(symbol, position.qty, bestask, 'buy')

    def liquidate(self, symbol, limit_price=None):
        """
        Liquidate (close) an existing position for a symbol.
        """

        position = self.account_info.get_position(symbol)
        
        if not position or position.qty == 0:
            print(f"No position found for {symbol}")
            return None
    
        if position.side == "long":
            side = 'sell'
            qty = abs(position.qty)
        elif position.side == "short":
            side = 'buy'
            qty = abs(position.qty)
        
        return self.order_limit(symbol, qty, limit_price, side)


    def order_limit(self, symbol, quantity, limit_price, side):
        endpoint = f"{self.base_url}/v2/orders"
        payload = {
            "type": "limit",
            "time_in_force": "ioc", # immediate or cancel
            "symbol": symbol,
            "qty": quantity,
            "side": side,
            "limit_price": limit_price
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret
        }

        try:
            response = requests.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            print(f"{side} {quantity} {symbol} @ {limit_price}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"{e}")
            return None


    def cancel_order(self, order_id):
        # Logic to cancel an order
        pass

    def get_order_status(self, order_id):
        # Logic to get the status of an order
        pass