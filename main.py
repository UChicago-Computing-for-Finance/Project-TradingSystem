import asyncio
from utils.order_book import OrderBook
from utils.market_data_second import MarketDataStreamSecond
from utils.events import Event, EventType
from utils.execution_engine import ExecutionEngine
from Strats.strategy_runner import StrategyRunner
from Strats.ob_imbalance import OrderBookImbalanceStrategy
from order_manager import OrderManager

async def main():
    """Main trading system with queue-based architecture"""
    
    # Create queues
    orderbook_q = asyncio.Queue()
    signal_q = asyncio.Queue()
    
    # Create orderbook
    order_book = OrderBook(symbol="BTC/USD", max_levels=10, trim_frequency=10)
    
    # Create order manager
    order_manager = OrderManager()
    
    # Create strategy
    strategy = OrderBookImbalanceStrategy(order_manager=order_manager)
    strategy.initialize()
    
    # Create components
    data_feed = MarketDataStreamSecond(
        order_book=order_book,
        symbol="BTC/USD",
        verbose=True,
        out_q=orderbook_q
    )
    
    strategy_runner = StrategyRunner(
        in_q=orderbook_q,
        out_q=signal_q,
        strategy=strategy
    )
    
    exec_engine = ExecutionEngine(
        in_q=signal_q,
        order_manager=order_manager
    )
    
    # Create tasks
    tasks = [
        asyncio.create_task(data_feed.connect(), name="data_feed"),
        asyncio.create_task(strategy_runner.run(), name="strategy"),
        asyncio.create_task(exec_engine.run(), name="execution"),
    ]
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)
    finally:
        # Cancel all tasks
        for task in tasks:
            task.cancel()
        
        # Wait for tasks to finish cancellation
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop data feed
        data_feed.running = False

if __name__ == "__main__":
    asyncio.run(main())