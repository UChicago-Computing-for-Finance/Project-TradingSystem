
# Import Dependencies
import numpy as np
import pandas as pd
import alpaca_trade_api as tradeapi
import datetime as dt

import os
from dotenv import load_dotenv

load_dotenv()

Alpaca_endpoint = os.getenv("BASE_URL")
Alpaca_key = os.getenv("ALPACA_KEY")
Alpaca_secret = os.getenv("ALPACA_SECRET")

class AccountInfo:
    def __init__(self):
        self.api = tradeapi.REST(Alpaca_key, Alpaca_secret, Alpaca_endpoint)

    def get_positions(self):
        return self.api.list_positions()

    def get_position(self, symbol):

        positions = self.api.list_positions()
        for p in positions:
            if p.symbol == symbol:
                return float(p.qty)
        return 0

    

# api = tradeapi.REST(Alpaca_key, Alpaca_secret, Alpaca_endpoint)

# def check_positions(symbol):
#     positions = api.list_positions()
#     for p in positions:
#         if p.symbol == symbol:
#             return float(p.qty)
#     return 0