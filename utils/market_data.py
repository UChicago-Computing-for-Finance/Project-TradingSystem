import pandas as pd
import os
import json
import websocket
from dotenv import load_dotenv
from utils.order_book import OrderBook
from typing import Optional

load_dotenv()

Alpaca_endpoint = os.getenv("ALPACA_ENDPOINT")
Alpaca_key = os.getenv("ALPACA_KEY")
Alpaca_secret = os.getenv("ALPACA_SECRET")

class MarketDataStream:
    
    def __init__(self, order_book: Optional[OrderBook] = None):
        """
        Initialize the market data stream.
        
        Args:
            order_book: Optional OrderBook instance to update with incoming data
        """
        self.ws = None
        self.api_key = Alpaca_key
        self.api_secret = Alpaca_secret
        self.order_book = order_book

        # self.ws_url = "wss://stream.data.alpaca.markets/v2/test"
        self.ws_url = "wss://stream.data.alpaca.markets/v1beta3/crypto/us"
        
    def on_message(self, ws, message):
        """Handle incoming messages from the WebSocket"""
        data = json.loads(message)
        
        # Handle both single messages and arrays of messages
        if isinstance(data, list):
            # If it's a list, process each message
            for msg in data:
                # Update order book if provided
                if self.order_book is not None and isinstance(msg, dict):
                    self.order_book.update(msg)
                print(f"Received: {msg}")
                # self.order_book.print_orderbook()
                # self.order_book.record_orderbook()
        else:
            # Single message (dict)
            # Update order book if provided
            if self.order_book is not None and isinstance(data, dict):
                self.order_book.update(data)

            print(f"Received: {data}")
            # self.order_book.print_orderbook()
            # self.order_book.record_orderbook()
            
    def on_message_quotes(self, ws, message):
        """Handle incoming messages from the WebSocket"""
        data = json.loads(message)
        
        # Handle both single messages and arrays of messages
        if isinstance(data, list):
            for msg in data:
                print(f"Received: {msg}")
        else:
            print(f"Received: {data}")
        
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"Error: {error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        print("Connection closed")
        
    def on_open(self, ws):
        """Called when WebSocket connection is opened"""
        # Authenticate within 10 seconds of connection
        auth_message = {
            "action": "auth",
            "key": self.api_key,
            "secret": self.api_secret
        }
        ws.send(json.dumps(auth_message))
        
        # Subscribe to FAKEPACA trades
        subscribe_message = {
            "action": "subscribe",
            # "quotes": ["BTC/USD"]
            "orderbooks": ["BTC/USD"]
        }
        ws.send(json.dumps(subscribe_message))
        print("Subscribed to BTCUSD")
        
    def start(self):
        """Start the WebSocket stream"""
        self.ws = websocket.WebSocketApp(
            self.ws_url,

            # if want to check quotes
            on_message=self.on_message,
            # on_message=self.on_message_quotes,

            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        self.ws.run_forever()
        
    def stop(self):
        """Stop the WebSocket stream"""
        if self.ws:
            self.ws.close()