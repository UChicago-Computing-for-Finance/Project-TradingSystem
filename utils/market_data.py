import os
import json
import asyncio
import websockets
from dotenv import load_dotenv
from utils.order_book import OrderBook
from typing import Optional
import sys

load_dotenv()

class MarketDataStream:
    
    def __init__(self, order_book: Optional[OrderBook] = None, verbose: bool = False):
        """
        Initialize the market data stream.
        
        Args:
            order_book: Optional OrderBook instance to update with incoming data
            verbose: If True, print messages (slows down processing)
        """
        self.api_key = os.getenv("ALPACA_KEY")
        self.api_secret = os.getenv("ALPACA_SECRET")
        self.order_book = order_book
        self.ws_url = "wss://stream.data.alpaca.markets/v1beta3/crypto/us"
        self.ws = None
        self.verbose = verbose
        self.message_count = 0
        
    async def connect(self):
        """Connect to WebSocket and handle messages"""
        try:
            async with websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                max_size=10**7  # 10MB max message size
            ) as websocket:
                self.ws = websocket
                
                # Authenticate
                auth_message = {
                    "action": "auth",
                    "key": self.api_key,
                    "secret": self.api_secret
                }
                await websocket.send(json.dumps(auth_message))
                
                # Subscribe
                subscribe_message = {
                    "action": "subscribe",
                    "orderbooks": ["BTC/USD"]
                }
                await websocket.send(json.dumps(subscribe_message))
                if self.verbose:
                    print("Subscribed to BTCUSD", flush=True)
                
                # Process messages asynchronously - this is the key for speed
                async for message in websocket:
                    # Process immediately without blocking
                    asyncio.create_task(self.on_message(message))
                    
        except Exception as e:
            print(f"Connection error: {e}", file=sys.stderr, flush=True)
            raise
    
    async def on_message(self, message):
        """Handle incoming messages asynchronously"""
        try:
            # Fast JSON parsing
            data = json.loads(message)
            
            if isinstance(data, list):
                # Process list of messages in parallel
                tasks = [self.process_message(msg) for msg in data]
                await asyncio.gather(*tasks)
            else:
                await self.process_message(data)
                
        except Exception as e:
            if self.verbose:
                print(f"Error processing message: {e}", file=sys.stderr, flush=True)
    
    async def process_message(self, msg):
        """Process a single message - optimized for speed"""
        self.message_count += 1
        
        # Only print if verbose (printing is slow!)
        if self.verbose:
            print(f"Received: {msg}", flush=True)
        
        # Update order book if provided
        if self.order_book is not None and isinstance(msg, dict):
            # Run CPU-bound work in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.order_book.update, msg)
    
    def start(self):
        """Start the async WebSocket stream"""
        try:
            asyncio.run(self.connect())
        except KeyboardInterrupt:
            if self.verbose:
                print(f"\nProcessed {self.message_count} messages", flush=True)
            self.stop()
    
    def stop(self):
        """Stop the WebSocket stream"""
        if self.ws:
            asyncio.create_task(self.ws.close())