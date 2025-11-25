import asyncio
from json.tool import main
from utils.order_book import OrderBook
from utils.OB_snapshot_reader import OrderBookSnapshotReader
from utils.backtesting_engine import BacktestingEngine
from utils.portfolio_tracker import PortfolioTracker
from Strats.strategy_runner import StrategyRunner
from Strats.ob_imbalance import OrderBookImbalanceStrategy

class Backtester:
    """Backtester for trading strategies using historical data"""
    def __init__(self, data_file: str = "order_book.json", 
                 initial_cash: float = 100000.0, 
                 commission_rate: float = 0.0,
                 delay: float = 1.0):
        self.data_file = data_file
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.delay = delay
        self.portfolio_tracker = None
    
    async def load_data(self):
        pass

    async def run_backtest(self):
        
        # Create queues
        orderbook_q = asyncio.Queue()
        signal_q = asyncio.Queue()
        
        # Create orderbook
        order_book = OrderBook(symbol="BTC/USD", max_levels=10, trim_frequency=10)
        
        # Create portfolio tracker
        self.portfolio_tracker = PortfolioTracker(
            initial_cash=self.initial_cash,
            commission_rate=self.commission_rate
        )
        
        # Create strategy
        strategy = OrderBookImbalanceStrategy()
        strategy.initialize()
        
        # Create components
        data_feed = OrderBookSnapshotReader(
            filepath=self.data_file,
            order_book=order_book,
            out_q=orderbook_q,
            delay=self.delay,
            verbose=True
        )
        
        strategy_runner = StrategyRunner(
            in_q=orderbook_q,
            out_q=signal_q,
            strategy=strategy,
        )
        
        exec_engine = BacktestingEngine(
            in_q=signal_q,
            portfolio_tracker=self.portfolio_tracker
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
            
            # Print backtest results
            self._print_results()
    
    def _print_results(self):
        """Print backtest results and export data"""
        if self.portfolio_tracker:
            print("\n" + "="*60)
            print("BACKTEST COMPLETED")
            print("="*60)
            
            # Print summary
            self.portfolio_tracker.print_summary()
            
            # Export results
            try:
                self.portfolio_tracker.export_results("./backtest_results")
                print("Results exported to ./backtest_results/")
            except Exception as e:
                print(f"Error exporting results: {e}")
            
            # Try to plot (will fail if matplotlib not installed)
            try:
                self.portfolio_tracker.plot_portfolio_value("./backtest_results/portfolio_chart.png")
            except Exception as e:
                print(f"Could not generate plots (install matplotlib): {e}")

if __name__ == "__main__":
    backtest = Backtester()
    asyncio.run(backtest.run_backtest())