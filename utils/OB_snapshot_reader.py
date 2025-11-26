
import json
import asyncio
from typing import Optional
from utils.order_book import OrderBook
from utils.events import Event, EventType
from datetime import datetime


class OrderBookSnapshotReader:
    """Reads saved orderbook snapshots and replays them with a delay"""
    
    def __init__(self, filepath: str, order_book: OrderBook, 
                 out_q: Optional[asyncio.Queue] = None,
                 delay: float = 1.0, verbose: bool = False):
        """
        Initialize the snapshot reader
        
        Args:
            filepath: Path to JSON file with saved snapshots
            order_book: OrderBook instance to update
            out_q: Queue to send events to
            delay: Delay between snapshots in seconds (default: 1.0)
            verbose: Print debug messages
        """
        self.filepath = filepath
        self.order_book = order_book
        self.out_q = out_q
        self.delay = delay
        self.verbose = verbose
        self.running = False
        self.snapshots = []
        
    def load_snapshots(self):
        """Load all snapshots from file"""
        with open(self.filepath, 'r') as f:
            self.snapshots = json.load(f)
        
        if self.verbose:
            print(f"Loaded {len(self.snapshots)} snapshots from {self.filepath}")
    
    async def connect(self):
        """Simulate connection - replay snapshots with delay"""
        self.load_snapshots()
        self.running = True
        
        snapshot_count = 0
        
        for snapshot in self.snapshots:
            if not self.running:
                break
            
            # Update orderbook
            self._update_orderbook(snapshot)
            
            # Send event if queue exists
            if self.out_q:
                event = Event(
                    type=EventType.ORDERBOOK_UPDATE,
                    payload=self.order_book
                )
                await self.out_q.put(event)
            
            snapshot_count += 1
            
            if self.verbose and snapshot_count % 10 == 0:
                print(f"Processed {snapshot_count}/{len(self.snapshots)} snapshots")
            
            # Wait before next snapshot
            await asyncio.sleep(self.delay)
        
        if self.verbose:
            print(f"Finished replaying {snapshot_count} snapshots")
        
        self.running = False
    
    def _update_orderbook(self, snapshot: dict):
        """Update orderbook from snapshot data"""
        data = snapshot.get('data', {})
        
        # Clear existing orderbook
        self.order_book.bids.clear()
        self.order_book.asks.clear()
        
        # Update bids
        for bid in data.get('bids', []):
            price = bid.get('price')
            size = bid.get('size')
            if price and size:
                self.order_book.bids[price] = size
        
        # Update asks
        for ask in data.get('asks', []):
            price = ask.get('price')
            size = ask.get('size')
            if price and size:
                self.order_book.asks[price] = size
        
        # Update timestamp if available
        if 'time' in snapshot:
            self.order_book.last_update = snapshot['time']