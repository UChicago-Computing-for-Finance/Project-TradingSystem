import asyncio
from utils.events import Event, EventType, Signal
from utils.portfolio_tracker import PortfolioTracker
from typing import Optional
from datetime import datetime


class BacktestingEngine:
    """Executes trading signals in backtesting mode with portfolio tracking"""

    def __init__(self, in_q: asyncio.Queue, portfolio_tracker: Optional[PortfolioTracker] = None,
                 initial_cash: float = 100000.0, commission_rate: float = 0.0):
        self._in_q = in_q
        self._positions = {}  # Track positions for backtesting
        
        # Initialize portfolio tracker
        if portfolio_tracker is None:
            self.portfolio_tracker = PortfolioTracker(
                initial_cash=initial_cash,
                commission_rate=commission_rate
            )
        else:
            self.portfolio_tracker = portfolio_tracker
        
        self._last_prices = {}  # Track last known prices for each symbol
        
        
    async def run(self):
        """Main loop: read signals and execute trades"""
        while True:
            try:
                event = await self._in_q.get()
                
                if event.type != EventType.SIGNAL:
                    continue
                
                signal: Signal = event.payload
                timestamp = datetime.now()
                
                # Update last known price
                if signal.limit_price is not None:
                    self._last_prices[signal.symbol] = signal.limit_price
                
                if signal.action in ["buy", "sell", "close"]:
                    self.portfolio_tracker.record_trade(
                        timestamp=timestamp,
                        symbol=signal.symbol,
                        action=signal.action,
                        quantity=signal.quantity,
                        price=signal.limit_price,
                        best_bid=signal.best_prices[0],
                        best_ask=signal.best_prices[1]                        
                    )
                
                # Record portfolio snapshot after each trade
                self.portfolio_tracker.record_portfolio_snapshot(
                    timestamp=timestamp,
                    current_prices=self._last_prices
                )
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in execution engine: {e}", flush=True)