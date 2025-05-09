"""
BacktestCoordinator with improved component lifecycle management.

This implementation addresses the architectural issues in the original
BacktestCoordinator, particularly with component coupling and
event processing order dependencies.
"""

from src.core.component import Component
from src.core.events.event_types import Event, EventType
from src.core.trade_repository import TradeRepository
import logging
# Import analytics metrics
from src.analytics.metrics.functional import (
    calculate_all_metrics,
    total_return,
    sharpe_ratio,
    profit_factor,
    max_drawdown,
    win_rate
)

# Set up logging
logger = logging.getLogger(__name__)

class BacktestCoordinator(Component):
    """
    Manages the backtest execution process.
    
    This implementation ensures proper component lifecycle management
    and explicitly stores trades in the results.
    """
    
    def __init__(self, name, config):
        """
        Initialize the backtest coordinator.
        
        Args:
            name (str): Component name
            config (dict): Backtest configuration
        """
        super().__init__(name)
        self.config = config
        self.components = {}
        self.results = {}
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
    def initialize(self, context):
        # Debug logging for initialization
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Initializing backtest coordinator with context: {context.keys()}")
        """
        Initialize with dependencies.
        
        Args:
            context (dict): Context containing required components
        """
        super().initialize(context)
        
        # Get event bus and trade repository from context
        self.event_bus = context.get('event_bus')
        
        if not self.event_bus:
            raise ValueError("BacktestCoordinator requires event_bus in context")
        
        # Create a shared context that all components will use
        self.shared_context = {
            'event_bus': self.event_bus,
            'trade_repository': context.get('trade_repository'),
            'config': self.config
        }
        
        # Create empty equity curve
        self.equity_curve = []
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.BACKTEST_END, self.on_backtest_end)
        self.event_bus.subscribe(EventType.PORTFOLIO, self.on_portfolio_update)
        
    def add_component(self, name, component):
        """
        Add a component to the backtest.
        
        Args:
            name (str): Component name/key
            component (Component): Component instance
        """
        self.components[name] = component
        
    def setup(self):
        """
        Set up the backtest by initializing all components.
        
        This ensures proper dependency injection instead of direct references.
        """
        # Initialize all components with the shared context
        for name, component in self.components.items():
            component.initialize(self.shared_context)
            
        # Start all components
        for name, component in self.components.items():
            component.start()
    
    def close_all_open_trades(self):
        # Get position manager from components
        position_manager = self.components.get('position_manager')
        if position_manager:
            self.logger.info("Using PositionManager to ensure clean position tracking")
            
        """
        Close all open trades at the end of the backtest using last available prices.
        This ensures all PnL is realized and metrics are based on closed trades only.
        """
        # Get data handler from components
        data_handler = self.components.get('data_handler')
        if not data_handler:
            logger.warning("Cannot close open trades - no data handler found")
            return
        
        # Get trade repository from context
        trade_repository = self.shared_context.get('trade_repository')
        if not trade_repository:
            logger.warning("Cannot close open trades - no trade repository found")
            return
            
        # Get all open trades
        all_open_trades = []
        for symbol_trades in trade_repository.open_trades.values():
            all_open_trades.extend(symbol_trades)
            
        if not all_open_trades:
            self.logger.info("No open trades to close at end of backtest")
            return
            
        self.logger.info(f"Closing {len(all_open_trades)} open trades at end of backtest")
        
        # Get current time for close timestamp
        current_time = data_handler.get_current_timestamp()
        
        # Close each open trade
        for trade in all_open_trades[:]:  # Create a copy to avoid modification during iteration
            symbol = trade.get('symbol')
            current_price = data_handler.get_current_price(symbol)
            
            if current_price is None:
                self.logger.warning(f"Cannot close trade for {symbol} - no current price available")
                continue
                
            # Close the trade
            trade_repository.close_trade(
                trade_id=trade.get('id'),
                close_price=current_price,
                close_time=current_time,
                quantity=trade.get('quantity')
            )
            
            self.logger.info(f"Closed trade {trade.get('id')} at end of backtest, "
                       f"symbol: {symbol}, price: {current_price}")
            
    def run(self):
        """
        Run the backtest.
        
        Returns:
            dict: Backtest results
        """
        # Ensure components are set up
        if not self.components:
            raise ValueError("No components registered with BacktestCoordinator")
            
        # Signal start of backtest
        self.event_bus.publish(Event(EventType.BACKTEST_START, {
            'config': self.config
        }))
        
        # Get data handler from components
        data_handler = self.components.get('data_handler')
        if not data_handler:
            raise ValueError("No data_handler component registered")
            
        # Run through all data
        has_more_data = True
        while has_more_data:
            has_more_data = data_handler.update()
            
        # Close all open trades at the end of the backtest
        self.close_all_open_trades()
            
        # Signal end of backtest
        self.event_bus.publish(Event(EventType.BACKTEST_END, {}))
        
        # Return the results
        return self.results
        
    def on_portfolio_update(self, event):
        """
        Handle portfolio update event by recording equity.
        
        Args:
            event (Event): Portfolio update event
        """
        update_data = event.get_data()
        
        # Record equity point with more comprehensive data
        equity_point = {
            'timestamp': update_data.get('timestamp'),
            'cash': update_data.get('capital'),  # Cash only
            'closed_pnl': update_data.get('closed_pnl', 0.0),  # Realized PnL
            'market_value': update_data.get('market_value', 0.0),  # Market value of positions
            'closed_only_equity': update_data.get('closed_only_equity'),  # Equity using only closed trades
            'full_equity': update_data.get('full_equity'),  # Total equity with market value
            'equity': update_data.get('full_equity')  # Set the 'equity' field to full_equity for compatibility
        }
        
        # Log detailed equity point for debugging
        self.logger.debug(f"Equity point: Cash={equity_point['cash']:.2f}, "
                         f"Market Value={equity_point['market_value']:.2f}, "
                         f"Full Equity={equity_point['full_equity']:.2f}")
        
        self.equity_curve.append(equity_point)
        
    def on_backtest_end(self, event):
        """
        Handle backtest end event by collecting results.
        
        Args:
            event (Event): Backtest end event
        """
        self._process_results()
        
        # Stop all components
        for name, component in self.components.items():
            component.stop()
            
    def verify_trades_vs_equity(self, trades, initial_capital):
        """
        Verify that trades match the equity curve changes.
        
        Args:
            trades: List of trade records
            initial_capital: Initial capital
        
        Returns:
            bool: True if consistent, False otherwise
        """
        import pandas as pd
        
        # IMPROVED: Only use closed trades for consistency check
        closed_trades = [t for t in trades if t.get('closed', True)]
        total_pnl = sum(t.get('pnl', 0) for t in closed_trades if t.get('pnl') is not None)
        
        # IMPROVED: Get closed-only equity from latest equity point
        if self.equity_curve and len(self.equity_curve) > 1:
            # Use closed_only_equity to ensure consistency with trade PnL
            final_closed_equity = self.equity_curve[-1].get('closed_only_equity')
            if final_closed_equity is not None:
                equity_change = final_closed_equity - initial_capital
            else:
                # Fall back to old behavior if closed_only_equity not available
                final_equity = self.equity_curve[-1].get('equity', initial_capital)
                equity_change = final_equity - initial_capital
                self.logger.warning("Using full equity change instead of closed-only change")
        else:
            self.logger.warning("Cannot verify with empty equity curve")
            return False
        
        # IMPROVED: More detailed consistency check with tolerances
        # For small equity changes, use absolute tolerance
        # For larger changes, use relative tolerance
        if abs(equity_change) < 100:
            # Use fixed tolerance of $1 for small equity changes
            is_consistent = abs(total_pnl - equity_change) < 1.0
        else:
            # Use 1% relative tolerance for larger equity changes
            is_consistent = abs(total_pnl - equity_change) < 0.01 * abs(equity_change)
        
        if not is_consistent:
            self.logger.warning(f"Inconsistency detected: Trade PnL ({total_pnl:.2f}) vs Equity Change ({equity_change:.2f})")
            
            # Detailed analysis
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
            
            self.logger.info(f"Closed trades: {len(closed_trades)}, Open trades: {len(trades) - len(closed_trades)}")
            self.logger.info(f"Winners: {len(winning_trades)}, Losers: {len(losing_trades)}")
            
            # Calculate gross profit and loss
            gross_profit = sum(t.get('pnl', 0) for t in winning_trades)
            gross_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
            
            self.logger.info(f"Gross profit: {gross_profit:.2f}, Gross loss: {gross_loss:.2f}")
            
            # Manual profit factor calculation
            if gross_loss > 0:
                profit_factor = gross_profit / gross_loss
                self.logger.info(f"Calculated profit factor: {profit_factor:.2f}")
            
            # Calculate unexplained PnL
            unexplained_pnl = equity_change - total_pnl
            
            # Avoid division by zero when reporting percentage
            if abs(equity_change) > 0.001:  # Small threshold to avoid near-zero division issues
                pct_unexplained = (unexplained_pnl / abs(equity_change)) * 100
                self.logger.warning(f"Unexplained PnL: {unexplained_pnl:.2f} ({pct_unexplained:.2f}% of equity change)")
            else:
                self.logger.warning(f"Unexplained PnL: {unexplained_pnl:.2f} (equity change near zero, percentage undefined)")
            
            # Trade-by-trade analysis for the first few trades
            self.logger.info("Sample closed trades (first 5):")
            for i, t in enumerate(closed_trades[:min(5, len(closed_trades))]):
                self.logger.info(f"{i}: PnL={t.get('pnl', 'None')}, Entry={t.get('entry_price')}, Exit={t.get('close_price')}")
        
        return is_consistent
        
    def _process_results(self):
        """Process and collect backtest results."""
        # Get portfolio and trades from components
        portfolio = self.components.get('portfolio')
        
        if not portfolio:
            raise ValueError("No portfolio component registered")
            
        # Get trades from the shared trade repository
        trade_repository = self.shared_context.get('trade_repository')
        trades = trade_repository.get_trades() if trade_repository else []
        
        self.logger.info(f"Processing results with {len(trades)} trades from trade repository")
        
        # If no trades found in trade repository, try to get them from portfolio
        if not trades and hasattr(portfolio, 'get_trades'):
            portfolio_trades = portfolio.get_trades()
            if portfolio_trades:
                self.logger.info(f"Retrieved {len(portfolio_trades)} trades from portfolio")
                trades = portfolio_trades
        
        # CRITICAL VERIFICATION: Verify trades vs equity curve consistency
        is_consistent = self.verify_trades_vs_equity(trades, portfolio.initial_capital)
        if not is_consistent:
            self.logger.warning("Trade PnL doesn't match equity curve change - this will cause metrics inconsistency")
        
        # Calculate statistics
        stats = self._calculate_statistics(portfolio, trades)
        
        # Verify metrics consistency
        metrics_consistent = True
        if 'return_pct' in stats and 'profit_factor' in stats:
            return_pct = stats['return_pct']
            profit_factor = stats['profit_factor']
            tolerance = 0.001
            
            if abs(return_pct) < tolerance:
                # Very small return, could be consistent with any profit factor
                pass
            elif (return_pct > 0 and profit_factor < 1) or (return_pct < 0 and profit_factor > 1):
                self.logger.warning(f"Metrics inconsistency detected: Return {return_pct:.2f}% but Profit Factor {profit_factor:.2f}")
                metrics_consistent = False
        
        # Store results
        self.results = {
            'final_capital': portfolio.get_capital(),
            'positions': portfolio.get_positions(),
            'trades': trades,  # CRITICAL FIX: Explicitly store trades in results
            'statistics': stats,
            'equity_curve': self.equity_curve,  # Add equity curve for performance analysis
            'trades_equity_consistent': is_consistent,  # Add consistency flag
            'metrics_consistent': metrics_consistent  # Add metrics consistency flag
        }
        
        self.logger.info(f"Backtest completed with {len(trades)} trades and final capital: {portfolio.get_capital():.2f}")
        
    def _calculate_statistics(self, portfolio, trades):
        """
        Calculate backtest statistics using the analytics module.
        
        Args:
            portfolio (Portfolio): Portfolio instance
            trades (list): List of trades
            
        Returns:
            dict: Calculated statistics
        """
        # Calculate basic statistics
        stats = {
            'initial_capital': portfolio.initial_capital,
            'final_capital': portfolio.get_capital(),
            'trades_executed': len(trades),
        }
        
        # Convert equity curve to pandas DataFrame for analytics functions
        import pandas as pd
        import numpy as np
        from datetime import datetime
        
        # CRITICAL FIX: Calculate returns based only on closed trades
        closed_trades = [t for t in trades if t.get('closed', True)]
        total_closed_pnl = sum(t.get('pnl', 0) for t in closed_trades if t.get('pnl') is not None)
        closed_return = total_closed_pnl / portfolio.initial_capital
        
        # Store the closed-trade return - this will be consistent with profit factor
        stats['return_pct_closed_only'] = closed_return * 100
        
        # Capture the realized PnL from portfolio if available - this should match closed trades
        if hasattr(portfolio, 'realized_pnl'):
            portfolio_realized_pnl = portfolio.realized_pnl
            portfolio_realized_return = portfolio_realized_pnl / portfolio.initial_capital * 100
            stats['portfolio_realized_return_pct'] = portfolio_realized_return
            
            # Check for consistency between portfolio and trade repository
            pnl_diff = abs(portfolio_realized_pnl - total_closed_pnl)
            if pnl_diff > 0.01:
                self.logger.warning(f"Inconsistency between portfolio realized PnL ({portfolio_realized_pnl:.2f}) "
                             f"and trade repository PnL ({total_closed_pnl:.2f})")
            else:
                self.logger.info(f"Portfolio and trade repository PnL are consistent: {portfolio_realized_pnl:.2f}")
        
        if self.equity_curve:
            # Create DataFrame from equity curve
            equity_data = []
            for point in self.equity_curve:
                timestamp = point.get('timestamp')
                # Use current time if timestamp is None
                if timestamp is None:
                    timestamp = datetime.now()
                equity_data.append({
                    'timestamp': timestamp,
                    'equity': point.get('equity', 0)
                })
            
            equity_df = pd.DataFrame(equity_data)
            if len(equity_df) > 0:
                # Set timestamp as index
                if 'timestamp' in equity_df.columns:
                    equity_df.set_index('timestamp', inplace=True)
                
                # Calculate return using analytics
                if len(equity_df) > 1:
                    # IMPROVED: Create two versions of equity DataFrame
                    # One with full equity (including open positions)
                    equity_df_full = equity_df.copy()
                    
                    # One with closed-only equity (for consistent metrics)
                    if 'closed_only_equity' in equity_df.columns:
                        equity_df_closed = equity_df.copy()
                        equity_df_closed['equity'] = equity_df_closed['closed_only_equity']
                    else:
                        equity_df_closed = equity_df.copy()
                    
                    # Calculate total return - both full and closed-only
                    ret_full = total_return(equity_df_full, trades)
                    ret_closed = total_return(equity_df_closed, trades) if 'closed_only_equity' in equity_df.columns else closed_return
                    
                    stats['return_pct_with_open'] = ret_full * 100  # Store full return
                    stats['return_pct_closed_only'] = ret_closed * 100  # Store closed-only return
                    
                    # CRITICAL FIX: Use the closed-trade return for consistency with profit factor
                    stats['return_pct'] = stats['return_pct_closed_only']
                    
                    # Calculate Sharpe ratio on CLOSED-ONLY equity for consistency
                    stats['sharpe_ratio'] = sharpe_ratio(equity_df_closed, trades)
                    stats['sharpe_ratio_full'] = sharpe_ratio(equity_df_full, trades)  # Also calculate for full equity
                    
                    # Calculate max drawdown on CLOSED-ONLY equity for consistency
                    stats['max_drawdown'] = max_drawdown(equity_df_closed, trades) * 100  # Convert to percentage
                    stats['max_drawdown_full'] = max_drawdown(equity_df_full, trades) * 100  # Also calculate for full equity
                else:
                    # Not enough data points
                    stats['return_pct'] = stats['return_pct_closed_only']
                    stats['sharpe_ratio'] = 0.0
                    stats['max_drawdown'] = 0.0
            else:
                # No equity data
                stats['return_pct'] = stats['return_pct_closed_only']
                stats['sharpe_ratio'] = 0.0
                stats['max_drawdown'] = 0.0
        else:
            # No equity curve, calculate return from closed trade PnL
            stats['return_pct'] = stats['return_pct_closed_only']
            stats['sharpe_ratio'] = 0.0
            stats['max_drawdown'] = 0.0
            
        # Calculate win/loss statistics if trades exist
        if trades:
            # Calculate win rate using analytics
            stats['win_rate'] = win_rate(trades)
            
            # IMPROVED: Only consider closed trades for most metrics
            closed_trades = [t for t in trades if t.get('closed', True)]
            
            # Count profitable trades for reporting
            profitable_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            loss_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
            break_even_trades = [t for t in closed_trades if t.get('pnl', 0) == 0]
            
            stats['profitable_trades'] = len(profitable_trades)
            stats['loss_trades'] = len(loss_trades)
            stats['break_even_trades'] = len(break_even_trades)
            stats['closed_trades'] = len(closed_trades)
            
            # Calculate average profits
            if profitable_trades:
                stats['avg_profit'] = sum(t.get('pnl', 0) for t in profitable_trades) / len(profitable_trades)
            else:
                stats['avg_profit'] = 0
                
            if loss_trades:
                stats['avg_loss'] = sum(t.get('pnl', 0) for t in loss_trades) / len(loss_trades)
            else:
                stats['avg_loss'] = 0
                
            # Calculate profit factor using analytics - this only uses closed trades
            stats['profit_factor'] = profit_factor(closed_trades)  # CRITICAL FIX: Use closed trades explicitly
            
            # IMPROVED: Calculate total PnL and verify consistency with equity curve
            total_pnl = sum(t.get('pnl', 0) for t in closed_trades if t.get('pnl') is not None)
            equity_change = portfolio.get_capital() - portfolio.initial_capital
            pnl_equity_diff = abs(total_pnl - equity_change)
            
            # Log diagnostic info
            self.logger.info(f"Trade PnL total: {total_pnl:.2f}, Equity change: {equity_change:.2f}, Difference: {pnl_equity_diff:.2f}")
            
            # Add field to show how much of equity change comes from open positions
            stats['open_position_value'] = equity_change - total_pnl
            
            # Check for significant inconsistency
            if pnl_equity_diff > 0.01 * abs(equity_change):
                self.logger.warning(f"Inconsistency between trade PnL total ({total_pnl:.2f}) and equity change ({equity_change:.2f})")
                stats['pnl_equity_consistency'] = False
            else:
                stats['pnl_equity_consistency'] = True
                
            # Verify consistency between return and profit factor
            # This should now always be consistent because we're using closed trades for both
            if (stats['return_pct'] > 0 and stats['profit_factor'] < 1) or (stats['return_pct'] < 0 and stats['profit_factor'] > 1):
                self.logger.warning(f"Inconsistency between return ({stats['return_pct']:.2f}%) and profit factor ({stats['profit_factor']:.2f})")
                stats['metrics_consistency'] = False
            else:
                stats['metrics_consistency'] = True
        
        return stats
    
    def reset(self):
        """Reset the backtest coordinator and all components."""
        super().reset()
        self.results = {}
        self.equity_curve = []
        
        # Reset all components
        for name, component in self.components.items():
            component.reset()
