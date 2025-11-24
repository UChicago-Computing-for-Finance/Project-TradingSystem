import asyncio
from utils.events import Event, EventType, Signal
from order_manager import OrderManager

class ExecutionEngine:
    """Executes trading signals using OrderManager"""
    
    def __init__(self, in_q: asyncio.Queue, order_manager: OrderManager):
        self._in_q = in_q
        self._order_manager = order_manager
        
    async def run(self):
        """Main loop: read signals and execute trades"""
        while True:
            try:
                event = await self._in_q.get()
                
                if event.type != EventType.SIGNAL:
                    continue
                
                signal: Signal = event.payload
                
                # Execute trade based on signal
                if signal.action == "buy":
                    self._order_manager.buy(
                        symbol=signal.symbol,
                        limit_price=signal.limit_price,
                        quantity=signal.quantity
                    )
                elif signal.action == "sell":
                    self._order_manager.sell(
                        symbol=signal.symbol,
                        limit_price=signal.limit_price,
                        quantity=signal.quantity
                    )
                elif signal.action == "close":
                    self._order_manager.liquidate(
                        symbol=signal.symbol,
                        limit_price=signal.limit_price
                    )
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in execution engine: {e}", flush=True)