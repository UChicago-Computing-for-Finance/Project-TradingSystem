import requests
import os
from dotenv import load_dotenv
from utils.account_info import AccountInfo
from Position import PositionManager

class OrderManager:

    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(OrderManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, PositionManager: PositionManager):
        load_dotenv()
        self.api_key = os.getenv("APCA_API_KEY_ID")
        self.api_secret = os.getenv("APCA_API_SECRET_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.account_info = AccountInfo()
        self.position_manager = PositionManager

    def buy(self, symbol, bestask, quantity = 1):
        if self.position_manager.has_position(symbol):
            position = self.position_manager.get_position(symbol)
            if position.qty > 0: # we are already long, do nothing for strat v1
                pass
            else:
                self.order_limit(symbol, quantity, bestask, 'buy')
    
    def sell(self, symbol, bestbid, quantity = 1):
        if self.position_manager.has_position(symbol):
            position = self.position_manager.get_position(symbol)
            if position.qty > 0: # we are already long, do nothing for strat v1
                pass
            else:
                self.order_limit(symbol, quantity, bestbid, 'sell')

    def close_position(self, symbol, bestask, bestbid):
        # Logic to close a position
        if self.position_manager.has_position(symbol):
            position = self.position_manager.get_position(symbol)
            if position.qty > 0 and position.unrealized_pl > 0:
                if position.side  == "long":
                    self.order_limit(symbol, position.qty, bestbid, 'sell')
                elif position.side == "short":
                    self.order_limit(symbol, position.qty, bestask, 'buy')


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

        response = requests.post(endpoint, json=payload, headers=headers)

        #print(response.text)


    

    def cancel_order(self, order_id):
        # Logic to cancel an order
        pass

    def get_order_status(self, order_id):
        # Logic to get the status of an order
        pass