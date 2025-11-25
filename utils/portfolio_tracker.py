import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import matplotlib.pyplot as plt


class Trade:
    """Represents a single trade execution"""
    def __init__(self, timestamp, symbol: str, action: str, quantity: float, 
                 price: float, commission: float = 0.0):
        self.timestamp = timestamp
        self.symbol = symbol
        self.action = action  # 'buy' or 'sell'
        self.quantity = quantity
        self.price = price
        self.commission = commission
        self.value = quantity * price
        
    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'action': self.action,
            'quantity': self.quantity,
            'price': self.price,
            'commission': self.commission,
            'value': self.value
        }


class PositionSnapshot:
    """Snapshot of a position at a point in time"""
    def __init__(self, timestamp, symbol: str, quantity: float, 
                 avg_entry_price: float, current_price: float):
        self.timestamp = timestamp
        self.symbol = symbol
        self.quantity = quantity
        self.avg_entry_price = avg_entry_price
        self.current_price = current_price
        self.market_value = quantity * current_price
        self.cost_basis = quantity * avg_entry_price
        self.unrealized_pnl = self.market_value - self.cost_basis
        
    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'avg_entry_price': self.avg_entry_price,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'cost_basis': self.cost_basis,
            'unrealized_pnl': self.unrealized_pnl
        }


class PortfolioTracker:
    """Tracks portfolio positions, PnL, and performance metrics over time"""
    
    def __init__(self, initial_cash: float = 100000.0, commission_rate: float = 0.0):
        """
        Initialize portfolio tracker
        
        Args:
            initial_cash: Starting cash balance
            commission_rate: Commission rate as decimal (e.g., 0.001 for 0.1%)
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission_rate = commission_rate
        
        # Current positions: {symbol: {'quantity': float, 'avg_price': float}}
        self.positions: Dict[str, Dict] = {}
        
        # Historical data
        self.trades: List[Trade] = []
        self.portfolio_snapshots: List[Dict] = []
        self.position_snapshots: List[PositionSnapshot] = []
        
        # Performance tracking
        self.realized_pnl = 0.0
        self.total_commissions = 0.0
        
    def record_trade(self, timestamp, symbol: str, action: str, 
                     quantity: float, price: float) -> Trade:
        """
        Record a trade execution and update positions
        
        Args:
            timestamp: Trade timestamp
            symbol: Trading symbol
            action: 'buy' or 'sell'
            quantity: Trade quantity
            price: Execution price
            
        Returns:
            Trade object
        """
        commission = quantity * price * self.commission_rate
        if action == "buy":
            trade_created = self._execute_buy(symbol, quantity, price, commission)
        elif action == "sell":
            trade_created = self._execute_sell(symbol, quantity, price, commission)
        elif action == "close":
            trade_created = self.close_position(symbol, price)

        if trade_created:
            trade = Trade(timestamp, symbol, action, quantity, price, commission)
            self.trades.append(trade)
            self.total_commissions += commission
    
            return trade
    
    def _execute_buy(self, symbol: str, quantity: float, price: float, commission: float):
        """Execute a buy order"""
        cost = quantity * price + commission
        
        if cost > self.cash:
            print(f"Warning: Insufficient cash for buy. Need {cost}, have {self.cash}")
            return False
            
        self.cash -= cost
        
        if symbol in self.positions:
            # Update average price for existing position
            current_qty = self.positions[symbol]['quantity']
            current_avg = self.positions[symbol]['avg_price']
            new_qty = current_qty + quantity
            new_avg = ((current_qty * current_avg) + (quantity * price)) / new_qty
            
            self.positions[symbol]['quantity'] = new_qty
            self.positions[symbol]['avg_price'] = new_avg
        else:
            # New position
            self.positions[symbol] = {
                'quantity': quantity,
                'avg_price': price
            }
        return True

    def _execute_sell(self, symbol: str, quantity: float, price: float, commission: float):
        """Execute a sell order"""
        if symbol not in self.positions:
            print(f"Warning: No position in {symbol} to sell")
            return False
            
        if self.positions[symbol]['quantity'] < quantity:
            print(f"Warning: Insufficient quantity to sell. Have {self.positions[symbol]['quantity']}, trying to sell {quantity}")
            quantity = self.positions[symbol]['quantity']  # Sell what we have
            
        proceeds = quantity * price - commission
        self.cash += proceeds
        
        # Calculate realized PnL
        avg_price = self.positions[symbol]['avg_price']
        realized = (price - avg_price) * quantity - commission
        self.realized_pnl += realized
        
        # Update position
        self.positions[symbol]['quantity'] -= quantity
        
        # Remove position if quantity is zero or negative
        if self.positions[symbol]['quantity'] <= 1e-8:  # Account for floating point precision
            del self.positions[symbol]

        return True
    
    def close_position(self, symbol: str, price: float):
        #check if long or short and then execute sell or buy accordingly
        position = self.get_current_position(symbol)
        if not position:
            print(f"No position to close for {symbol}")
            return False
        
        if position['quantity'] > 0:
            return self._execute_sell(symbol, position['quantity'], price, position['quantity'] * price * self.commission_rate)
        elif position['quantity'] < 0:
            return self._execute_buy(symbol, abs(position['quantity']), price, abs(position['quantity']) * price * self.commission_rate)
        return True


    def record_portfolio_snapshot(self, timestamp, current_prices: Dict[str, float]):
        """
        Record a snapshot of the portfolio at a point in time
        
        Args:
            timestamp: Snapshot timestamp
            current_prices: Dict of {symbol: current_price}
        """
        # Calculate portfolio metrics
        total_position_value = 0.0
        unrealized_pnl = 0.0
        
        # Record individual position snapshots
        for symbol, position in self.positions.items():
            current_price = current_prices.get(symbol)
            if current_price is None:
                print(f"Warning: No price data for {symbol}")
                continue
                
            snapshot = PositionSnapshot(
                timestamp=timestamp,
                symbol=symbol,
                quantity=position['quantity'],
                avg_entry_price=position['avg_price'],
                current_price=current_price
            )
            self.position_snapshots.append(snapshot)
            
            total_position_value += snapshot.market_value
            unrealized_pnl += snapshot.unrealized_pnl
        
        # Record overall portfolio snapshot
        total_value = self.cash + total_position_value
        total_pnl = self.realized_pnl + unrealized_pnl
        
        portfolio_snapshot = {
            'timestamp': timestamp,
            'cash': self.cash,
            'position_value': total_position_value,
            'total_value': total_value,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': total_pnl,
            'total_return': (total_value - self.initial_cash) / self.initial_cash,
            'num_positions': len(self.positions),
            'commissions': self.total_commissions
        }
        
        self.portfolio_snapshots.append(portfolio_snapshot)
    
    def get_current_position(self, symbol: str) -> Optional[Dict]:
        """Get current position for a symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """Get all current positions"""
        return self.positions.copy()
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate current portfolio value"""
        position_value = sum(
            pos['quantity'] * current_prices.get(symbol, pos['avg_price'])
            for symbol, pos in self.positions.items()
        )
        return self.cash + position_value
    
    def get_trades_df(self) -> pd.DataFrame:
        """Get trade history as DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame([t.to_dict() for t in self.trades])
    
    def get_portfolio_df(self) -> pd.DataFrame:
        """Get portfolio snapshots as DataFrame"""
        if not self.portfolio_snapshots:
            return pd.DataFrame()
        return pd.DataFrame(self.portfolio_snapshots)
    
    def get_positions_df(self) -> pd.DataFrame:
        """Get position snapshots as DataFrame"""
        if not self.position_snapshots:
            return pd.DataFrame()
        return pd.DataFrame([p.to_dict() for p in self.position_snapshots])
    
    def calculate_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not self.portfolio_snapshots:
            return {}
        
        df = self.get_portfolio_df()
        
        # Total return
        final_value = df['total_value'].iloc[-1]
        total_return = (final_value - self.initial_cash) / self.initial_cash
        
        # Calculate returns series
        returns = df['total_value'].pct_change().dropna()
        
        # Sharpe ratio (assuming 252 trading days per year, 86400 seconds per day)
        if len(returns) > 1 and returns.std() > 0:
            # Estimate periods per year based on timestamp differences
            if len(df) > 1:
                time_diff = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0])
                if hasattr(time_diff, 'total_seconds'):
                    total_seconds = time_diff.total_seconds()
                else:
                    total_seconds = float(time_diff)
                    
                periods_per_year = 365.25 * 24 * 3600 / (total_seconds / len(df))
            else:
                periods_per_year = 252  # Default to daily
                
            sharpe = returns.mean() / returns.std() * np.sqrt(periods_per_year)
        else:
            sharpe = 0.0
        
        # Max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0.0
        
        # Win rate
        trades_df = self.get_trades_df()
        if len(trades_df) > 0:
            # Calculate PnL per trade (for closed positions)
            num_trades = len(trades_df)
        else:
            num_trades = 0
        
        metrics = {
            'initial_capital': self.initial_cash,
            'final_value': final_value,
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'realized_pnl': self.realized_pnl,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown * 100,
            'num_trades': num_trades,
            'total_commissions': self.total_commissions,
        }
        
        return metrics
    
    def plot_portfolio_value(self, save_path: Optional[str] = None):
        """Plot portfolio value over time"""
        df = self.get_portfolio_df()
        if df.empty:
            print("No data to plot")
            return
        
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        # Portfolio value
        axes[0].plot(df['timestamp'], df['total_value'], label='Total Value')
        axes[0].plot(df['timestamp'], df['cash'], label='Cash', alpha=0.7)
        axes[0].plot(df['timestamp'], df['position_value'], label='Position Value', alpha=0.7)
        axes[0].set_ylabel('Value ($)')
        axes[0].set_title('Portfolio Value Over Time')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # PnL
        axes[1].plot(df['timestamp'], df['total_pnl'], label='Total PnL')
        axes[1].plot(df['timestamp'], df['realized_pnl'], label='Realized PnL', alpha=0.7)
        axes[1].plot(df['timestamp'], df['unrealized_pnl'], label='Unrealized PnL', alpha=0.7)
        axes[1].axhline(y=0, color='black', linestyle='--', alpha=0.3)
        axes[1].set_ylabel('PnL ($)')
        axes[1].set_title('Profit & Loss')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Returns
        axes[2].plot(df['timestamp'], df['total_return'] * 100)
        axes[2].axhline(y=0, color='black', linestyle='--', alpha=0.3)
        axes[2].set_xlabel('Time')
        axes[2].set_ylabel('Return (%)')
        axes[2].set_title('Cumulative Returns')
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        
        plt.show()
    
    def export_results(self, output_dir: str = "./backtest_results"):
        """Export all results to CSV files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Export trades
        trades_df = self.get_trades_df()
        if not trades_df.empty:
            trades_df.to_csv(f"{output_dir}/trades.csv", index=False)
            print(f"Trades exported to {output_dir}/trades.csv")
        
        # Export portfolio snapshots
        portfolio_df = self.get_portfolio_df()
        if not portfolio_df.empty:
            portfolio_df.to_csv(f"{output_dir}/portfolio.csv", index=False)
            print(f"Portfolio history exported to {output_dir}/portfolio.csv")
        
        # Export position snapshots
        positions_df = self.get_positions_df()
        if not positions_df.empty:
            positions_df.to_csv(f"{output_dir}/positions.csv", index=False)
            print(f"Position history exported to {output_dir}/positions.csv")
        
        # Export metrics
        metrics = self.calculate_metrics()
        if metrics:
            metrics_df = pd.DataFrame([metrics])
            metrics_df.to_csv(f"{output_dir}/metrics.csv", index=False)
            print(f"Metrics exported to {output_dir}/metrics.csv")
    
    def print_summary(self):
        """Print a summary of the backtest results"""
        metrics = self.calculate_metrics()
        
        print("\n" + "="*60)
        print("BACKTEST SUMMARY")
        print("="*60)
        print(f"Initial Capital:    ${metrics.get('initial_capital', 0):,.2f}")
        print(f"Final Value:        ${metrics.get('final_value', 0):,.2f}")
        print(f"Total Return:       {metrics.get('total_return_pct', 0):.2f}%")
        print(f"Realized PnL:       ${metrics.get('realized_pnl', 0):,.2f}")
        print(f"Sharpe Ratio:       {metrics.get('sharpe_ratio', 0):.3f}")
        print(f"Max Drawdown:       {metrics.get('max_drawdown_pct', 0):.2f}%")
        print(f"Number of Trades:   {metrics.get('num_trades', 0)}")
        print(f"Total Commissions:  ${metrics.get('total_commissions', 0):.2f}")
        print("="*60 + "\n")
