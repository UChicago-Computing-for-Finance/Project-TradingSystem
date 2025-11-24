import os
import json
import asyncio
import websockets
from dotenv import load_dotenv
from utils.order_book import OrderBook
from typing import Optional
import sys
from datetime import datetime

load_dotenv()

class MarketDataStreamSecond:
    """
    Market data stream that resubscribes every second to get initial orderbook snapshots.
    This simulates second-by-second market data instead of tick-by-tick updates.
    """
    
    def __init__(self, order_book: Optional[OrderBook] = None, symbol: str = "BTC/USD", verbose: bool = False):
        """
        Initialize the second-based market data stream.
        
        Args:
            order_book: Optional OrderBook instance to update with incoming snapshots
            symbol: Trading symbol to subscribe to (default: "BTC/USD")
            verbose: If True, print messages (slows down processing)
        """
        self.api_key = os.getenv("ALPACA_KEY")
        self.api_secret = os.getenv("ALPACA_SECRET")
        self.order_book = order_book
        self.symbol = symbol
        self.ws_url = "wss://stream.data.alpaca.markets/v1beta3/crypto/us"
        self.ws = None
        self.verbose = verbose
        self.message_count = 0
        self.snapshot_count = 0
        self.running = False
        self.snapshot_event = None  # Event to signal snapshot received
        self.is_subscribed = False  # Track subscription state
        self.last_snapshot_timestamp = None  # Track last processed snapshot
        self.duplicate_detected = False  # Track if duplicate snapshot was detected
        
    async def connect(self):
        """Connect to WebSocket and maintain connection"""
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
                
                message_task = asyncio.create_task(self.process_messages(websocket))
                
                # Start the periodic subscription loop
                try:
                    await self.subscription_loop(websocket)
                finally:
                    message_task.cancel()
                    try:
                        await message_task
                    except asyncio.CancelledError:
                        pass
                    
        except Exception as e:
            print(f"Connection error: {e}", file=sys.stderr, flush=True)
            raise
    
    async def process_messages(self, websocket):
        """
        Background task to process all incoming messages.
        Looks for snapshots and signals when found.
        """
        try:
            async for message in websocket:
                if self.is_subscribed:
                    snapshot = await self.process_snapshot(message)
                    if snapshot and self.snapshot_event and not self.snapshot_event.is_set():
                        self.snapshot_event.set()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if self.verbose:
                print(f"Error in message processing: {e}", file=sys.stderr, flush=True)
    
    async def subscription_loop(self, websocket):
        """
        Main loop that subscribes/unsubscribes
        """
        self.running = True

        unsubscribe_message = {
            "action": "unsubscribe",
            "orderbooks": [self.symbol]
        }

        subscribe_message = {
            "action": "subscribe",
            "orderbooks": [self.symbol] # BTC/USD
        }
        
        while self.running:
            try:
                # Create event to track snapshot reception
                self.snapshot_event = asyncio.Event()
                self.is_subscribed = True  # Mark as subscribed
                self.duplicate_detected = False  # Track if duplicate was detected

                # SUBSCRIBE
                await websocket.send(json.dumps(subscribe_message))
                
                start_time = asyncio.get_event_loop().time()
                try:
                    await asyncio.wait_for(self.snapshot_event.wait(), timeout=1.5)

                    if self.duplicate_detected:
                        # UN-SUBSCRIBE
                        self.is_subscribed = False
                        await websocket.send(json.dumps(unsubscribe_message))

                        await asyncio.sleep(0.5)
                        continue

                    
                    # UN-SUBSCRIBE
                    self.is_subscribed = False
                    await websocket.send(json.dumps(unsubscribe_message))
                    

                    elapsed = asyncio.get_event_loop().time() - start_time
                    remaining_time = max(0, 1.5 - elapsed)
                    if remaining_time > 0:
                        await asyncio.sleep(remaining_time)
                    
                    continue  # Restart loop

                except asyncio.TimeoutError:

                    # unsubscribe
                    self.is_subscribed = False
                    await websocket.send(json.dumps(unsubscribe_message))
                    continue
                
            except asyncio.CancelledError:
                # Handle cancellation gracefully
                self.is_subscribed = False
                self.running = False
                raise
            except Exception as e:
                self.is_subscribed = False
                if self.verbose:
                    print(f"Error in subscription loop: {e}", file=sys.stderr, flush=True)
                await asyncio.sleep(0.1)
    
    async def process_snapshot(self, message: str) -> Optional[dict]:
        """
        Process raw WebSocket message and return snapshot if found.
        """
        try:
            data = json.loads(message)
            
            # Handle list of messages
            messages = data if isinstance(data, list) else [data]
            
            for msg in messages:
                # Check if it's an orderbook message with r: true
                if (isinstance(msg, dict) and 
                    msg.get('T') == 'o' and 
                    msg.get('S') == self.symbol and 
                    msg.get('r', False)):
                    
                    # Check for duplicate
                    snapshot_timestamp = msg.get('t')
                    if snapshot_timestamp == self.last_snapshot_timestamp:
                        if self.verbose:
                            print(f"[{datetime.now().strftime('%H:%M:%S.%f')}] Duplicate snapshot detected with timestamp {snapshot_timestamp}", flush=True)
                        self.duplicate_detected = True
                        if self.snapshot_event:
                            self.snapshot_event.set()
                        return None
                    
                    # Process valid snapshot
                    self.last_snapshot_timestamp = snapshot_timestamp
                    self.snapshot_count += 1
                    self.message_count += 1
                    
                    if self.verbose:
                        print(f"Received snapshot #{self.snapshot_count} at {msg.get('t', 'N/A')}", flush=True)
                    
                    if self.order_book is not None:
                        loop = asyncio.get_event_loop()
                        loop.run_in_executor(None, self.order_book.update, msg)
                        self.order_book.print_orderbook()
                    
                    return msg
                    
        except Exception as e:
            if self.verbose:
                print(f"Error parsing message: {e}", file=sys.stderr, flush=True)
        
        return None
    
    def start(self):
        """Start the async WebSocket stream"""
        try:
            asyncio.run(self.connect())
        except KeyboardInterrupt:
            if self.verbose:
                print(f"\nProcessed {self.snapshot_count} snapshots", flush=True)
            self.running = False
    
    def stop(self):
        """Stop the WebSocket stream"""
        self.running = False