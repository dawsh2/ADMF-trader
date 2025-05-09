"""
Fixed version of BacktestCoordinator that addresses:
1. The division by zero in unexplained PnL percentage calculation
2. The empty equity curve issue in the verification
"""

import logging
from src.core.component import Component
from src.core.event_bus import Event, EventType
from src.core.trade_repository import TradeRepository
from src.analytics.metrics.functional import (
    calculate_all_metrics,
    total_return,
    sharpe_ratio,
    profit_factor,
    max_drawdown,
    win_rate
)

class FixedBacktestCoordinator(Component):
    """
    Fixed version of the BacktestCoordinator with improved PnL calculation.
    
    This class addresses the division by zero error and improves equity tracking.
    """
    
    def __init__(self, name, config):
        """Initialize with proper logger."""
        super().__init__(name)
        self.config = config
        self.components = {}
        self.results = {}
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
    def initialize(self, context):
        """Initialize with dependencies."""
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
        self.event_bus.subscribe(EventType.PORTFOLIO_UPDATE, self.on_portfolio_update)
        
    def on_portfolio_update(self, event):
        """
        Handle portfolio update event by recording equity.
        
        Args:
            event (Event): Portfolio update event
        """
        update_data = event.get_data()
        
        # Ensure we have all required fields
        if 'capital' not in update_data:
            self.logger.warning("Portfolio update missing 'capital' field - skipping equity update")
            return
            
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
        
        # Ensure closed_only_equity and full_equity have valid values
        if equity_point['closed_only_equity'] is None:
            equity_point['closed_only_equity'] = update_data.get('capital', 0.0)
            
        if equity_point['full_equity'] is None:
            equity_point['full_equity'] = update_data.get('capital', 0.0) + update_data.get('market_value', 0.0)
            
        if equity_point['equity'] is None:
            equity_point['equity'] = equity_point['full_equity']
        
        # Log detailed equity point for debugging (only at debug level to avoid verbosity)
        self.logger.debug(f"Equity point: Cash={equity_point['cash']:.2f}, "
                         f"Market Value={equity_point['market_value']:.2f}, "
                         f"Full Equity={equity_point['full_equity']:.2f}")
        
        # Store the equity point
        self.equity_curve.append(equity_point)
        
    def verify_trades_vs_equity(self, trades, initial_capital):
        """
        Verify that trades match the equity curve changes.
        
        Args:
            trades: List of trade records
            initial_capital: Initial capital
        
        Returns:
            bool: True if consistent, False otherwise
        """
        # IMPROVED: Only use closed trades for consistency check
        closed_trades = [t for t in trades if t.get('closed', True)]
        total_pnl = sum(t.get('pnl', 0) for t in closed_trades if t.get('pnl') is not None)
        
        # Check if we have an equity curve to verify against
        if not self.equity_curve or len(self.equity_curve) <= 1:
            # If no equity curve, we can't verify
            self.logger.warning("Cannot verify with empty equity curve")
            # Default to initial capital for comparison
            equity_change = 0.0
            return False
        else:
            # Use closed_only_equity to ensure consistency with trade PnL
            final_closed_equity = self.equity_curve[-1].get('closed_only_equity')
            if final_closed_equity is not None:
                equity_change = final_closed_equity - initial_capital
            else:
                # Fall back to full equity if closed_only_equity not available
                final_equity = self.equity_curve[-1].get('equity', initial_capital)
                equity_change = final_equity - initial_capital
                self.logger.warning("Using full equity change instead of closed-only change")
        
        # More detailed consistency check with tolerances
        if abs(equity_change) < 100:
            # Use fixed tolerance of $1 for small equity changes
            is_consistent = abs(total_pnl - equity_change) < 1.0
        else:
            # Use 1% relative tolerance for larger equity changes
            is_consistent = abs(total_pnl - equity_change) < 0.01 * abs(equity_change)
        
        if not is_consistent:
            self.logger.warning(f"Inconsistency detected: Trade PnL ({total_pnl:.2f}) vs Equity Change ({equity_change:.2f})")
            
            # Detailed analysis of the inconsistency
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
            
            # Calculate unexplained PnL with safe percentage calculation
            unexplained_pnl = equity_change - total_pnl
            
            # FIXED: Avoid division by zero when reporting percentage
            if abs(equity_change) > 0.001:  # Small threshold to avoid near-zero division issues
                pct_unexplained = (unexplained_pnl / abs(equity_change)) * 100
                self.logger.warning(f"Unexplained PnL: {unexplained_pnl:.2f} ({pct_unexplained:.2f}% of equity change)")
            else:
                self.logger.warning(f"Unexplained PnL: {unexplained_pnl:.2f} (equity change near zero, percentage undefined)")
            
            # Sample trade analysis
            if closed_trades:
                self.logger.info("Sample closed trades (first 5):")
                for i, t in enumerate(closed_trades[:min(5, len(closed_trades))]):
                    self.logger.info(f"{i}: PnL={t.get('pnl', 'None')}, Entry={t.get('entry_price')}, Exit={t.get('close_price')}")
            else:
                self.logger.info("No closed trades to analyze")
        
        return is_consistent