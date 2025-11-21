from utils.market_data import MarketDataStream

# Create and start the stream
# stream = MarketDataStream()
# stream.start()  # This will run forever until stopped



from utils.account_info import AccountInfo

account = AccountInfo()
#print(account.get_position("NVDA"))
print(account.get_positions())