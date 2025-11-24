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
                
                if self.verbose:
                    print(f"Authenticated to Alpaca WebSocket", flush=True)
                
                # Start message processing task
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
                    snapshot = await self.wait_for_snapshot(message)
                    if snapshot and self.snapshot_event and not self.snapshot_event.is_set():
                        self.snapshot_event.set()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if self.verbose:
                print(f"Error in message processing: {e}", file=sys.stderr, flush=True)
    
    async def subscription_loop(self, websocket):
        """
        Main loop that subscribes/unsubscribes every second to get snapshots.
        """
        self.running = True
        
        while self.running:
            try:
                # Create event to track snapshot reception
                self.snapshot_event = asyncio.Event()
                self.is_subscribed = True  # Mark as subscribed
                self.duplicate_detected = False  # Track if duplicate was detected

                
                # Subscribe to get initial snapshot
                subscribe_message = {
                    "action": "subscribe",
                    "orderbooks": [self.symbol] # BTC/USD
                }
                await websocket.send(json.dumps(subscribe_message))
                
                if self.verbose:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Subscribed to {self.symbol}", flush=True)
                
                # Wait for snapshot with 1.5 second total timeout (allowing retries)
                start_time = asyncio.get_event_loop().time()
                snapshot_received = False
                max_wait_time = 1.5
                
                while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
                    # Reset duplicate flag for this iteration
                    self.duplicate_detected = False
                    self.snapshot_event.clear()  # Clear event for new wait
                    
                    try:
                        remaining_time = max_wait_time - (asyncio.get_event_loop().time() - start_time)
                        if remaining_time <= 0:
                            break
                            
                        await asyncio.wait_for(self.snapshot_event.wait(), timeout=remaining_time)
                        
                        # If duplicate was detected, wait 0.2s and retry
                        if self.duplicate_detected:
                            if self.verbose:
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Duplicate detected, waiting 0.2s to retry", flush=True)
                            await asyncio.sleep(0.2)
                            continue  # Retry waiting for snapshot
                        
                        # Valid snapshot received
                        snapshot_received = True
                        if self.verbose:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Snapshot received", flush=True)
                        break
                        
                    except asyncio.TimeoutError:
                        # No snapshot arrived within remaining time
                        break
                
                if not snapshot_received:
                    if self.verbose:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Timeout: No snapshot received, skipping", flush=True)
                
                # Mark as unsubscribed BEFORE unsubscribing to prevent race conditions
                self.is_subscribed = False
                
                # Unsubscribe
                unsubscribe_message = {
                    "action": "unsubscribe",
                    "orderbooks": [self.symbol]
                }
                await websocket.send(json.dumps(unsubscribe_message))
                
                if self.verbose:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Unsubscribed", flush=True)
                
                # Wait until next second boundary
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, 1 - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
            except Exception as e:
                self.is_subscribed = False  # Mark as not subscribed
                if self.verbose:
                    print(f"Error in subscription loop: {e}", file=sys.stderr, flush=True)
                # Wait a bit before retrying
                await asyncio.sleep(0.1)
    
    async def wait_for_snapshot(self, message: str) -> Optional[dict]:
        """
        Process message and return snapshot if it has r: true flag.
        
        Args:
            message: Raw WebSocket message string
            
        Returns:
            Snapshot message dict if found, None otherwise
        """
        try:
            data = json.loads(message)
            
            # Handle list of messages
            if isinstance(data, list):
                for msg in data:
                    snapshot = self._check_for_snapshot(msg)
                    if snapshot:
                        return snapshot
            else:
                return self._check_for_snapshot(data)
                
        except Exception as e:
            if self.verbose:
                print(f"Error parsing message: {e}", file=sys.stderr, flush=True)
        
        return None
    
    def _check_for_snapshot(self, msg: dict) -> Optional[dict]:
        """
        Check if message is an orderbook snapshot (r: true) and update orderbook.
        
        Args:
            msg: Message dictionary
            
        Returns:
            Message dict if it's a snapshot, None otherwise
        """
        # Check if it's an orderbook message with r: true
        if (isinstance(msg, dict) and 
            msg.get('T') == 'o' and 
            msg.get('S') == self.symbol and 
            msg.get('r', False)):

            # Check if we've already processed this exact snapshot (by timestamp)
            snapshot_timestamp = msg.get('t')
            if snapshot_timestamp == self.last_snapshot_timestamp:
                if self.verbose:
                    print(f"Duplicate snapshot detected with timestamp {snapshot_timestamp}", flush=True)
                # Set flag to indicate duplicate was detected
                self.duplicate_detected = True
                # Set event so subscription loop can handle the retry
                if self.snapshot_event:
                    self.snapshot_event.set()
                return None

            self.last_snapshot_timestamp = snapshot_timestamp
            self.snapshot_count += 1
            self.message_count += 1
            
            if self.verbose:
                print(f"Received snapshot #{self.snapshot_count} at {msg.get('t', 'N/A')}", flush=True)
            
            # Update order book with snapshot
            if self.order_book is not None:
                # Run CPU-bound work in executor to avoid blocking event loop
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, self.order_book.update, msg)
                # loop.run_in_executor(None, self.order_book.print_orderbook)
                self.order_book.print_orderbook()
            
            return msg
        
        return None
    
    def start(self):
        """Start the async WebSocket stream"""
        try:
            asyncio.run(self.connect())
        except KeyboardInterrupt:
            if self.verbose:
                print(f"\nProcessed {self.snapshot_count} snapshots", flush=True)
            self.stop()
    
    def stop(self):
        """Stop the WebSocket stream"""
        self.running = False
        if self.ws:
            asyncio.create_task(self.ws.close())