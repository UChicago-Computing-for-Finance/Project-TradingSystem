import asyncio
from typing import Optional
from utils.events import Event, EventType, Signal
from utils.order_book import OrderBook
from Strats.strat_base import StrategyBase

class StrategyRunner:
    """Runs strategy on orderbook updates and produces signals"""
    
    def __init__(self, in_q: asyncio.Queue, out_q: asyncio.Queue, strategy: StrategyBase):
        self._in_q = in_q
        self._out_q = out_q
        self._strategy = strategy
        
    async def run(self):
        """Main loop: read orderbook updates, run strategy, emit signals"""
        while True:
            try:
                event = await self._in_q.get()
                
                if event.type != EventType.ORDERBOOK_UPDATE:
                    continue
                
                orderbook: OrderBook = event.payload
                
                # Run strategy
                signal: Optional[Signal] = self._strategy.on_data(orderbook)
                
                if signal:
                    print("strategy runner: signal")
                    # Emit signal event
                    signal_event = Event(
                        type=EventType.SIGNAL,
                        payload=signal
                    )
                    await self._out_q.put(signal_event)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in strategy runner: {e}", flush=True)