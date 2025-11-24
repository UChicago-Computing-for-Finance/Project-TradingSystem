# ------------------------------------------------------------
# market data

# from utils.market_data import MarketDataStream
# stream = MarketDataStream()
# stream.start()  # This will run forever until stopped

# ------------------------------------------------------------
# account info - ALSO CHECK NOTEBOOK

# from utils.account_info import AccountInfo
# account = AccountInfo()
# # print(account.get_position("NVDA"))
# print(account.get_positions())

# ------------------------------------------------------------
# order book stream

from utils.order_book import OrderBook
from utils.market_data import MarketDataStream

# Create order book for BTC/USD
order_book = OrderBook(symbol="BTC/USD", max_levels=10)

# Create market data stream and pass the order book
stream = MarketDataStream(order_book=order_book)

# Start streaming (this will update the order book automatically)
stream.start()


# ------------------------------------------------------------
# order manager

# from order_manager import OrderManager
# order_manager = OrderManager()
# order_manager.buy(symbol="BTC/USD", limit_price=100000, quantity=0.01)
