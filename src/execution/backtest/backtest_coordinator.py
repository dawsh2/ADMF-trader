"""
BacktestCoordinator with enhanced broker integration and component lifecycle management.

This implementation addresses the architectural issues in the original
BacktestCoordinator, particularly with component coupling and
event processing order dependencies. It also integrates the enhanced
broker module for more realistic market simulation.

Key features:
- Clean component lifecycle management
- Enhanced broker integration with realistic market simulation
- Configurable slippage and commission models
- Daily position closing option for overnight risk management
- Proper state isolation for optimization
"""

from src.core.component import Component
from src.core.events.event_types import Event, EventType
from src.core.trade_repository import TradeRepository
import logging
import datetime
# Import analytics metrics
from src.analytics.metrics.functional import (
    calculate_all_metrics,
    total_return,
    sharpe_ratio,
    profit_factor,
    max_drawdown,
    win_rate
)

# Import broker components
from src.execution.broker.simulated_broker import SimulatedBroker
from src.execution.broker.market_simulator import MarketSimulator
from src.execution.broker.slippage_model import FixedSlippageModel, VariableSlippageModel
from src.execution.broker.commission_model import CommissionModel

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
        
        # Trading settings from config
        self.close_positions_eod = self.config.get('close_positions_eod', False)
        self.current_day = None  # Track current day for EOD processing
        
        # Track simulation state
        self.last_bar_timestamp = None
        self.previous_trading_day = None
        
        # Broker configuration
        self.broker_config = self.config.get('broker', {})
        
        # Initialize statistics tracking
        self.stats = {
            'bars_processed': 0,
            'signals_generated': 0,
            'orders_created': 0,
            'trades_executed': 0,
            'positions_closed_eod': 0
        }
        
    def initialize(self, context):
        """
        Initialize with dependencies.
        
        Args:
            context (dict): Context containing required components
        """
        # Debug logging for initialization
        logger.info(f"Initializing backtest coordinator with context: {context.keys()}")
        
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
        
        # Create and configure broker components if not provided
        self._setup_broker_components()
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.BACKTEST_END, self.on_backtest_end)
        self.event_bus.subscribe(EventType.PORTFOLIO, self.on_portfolio_update)
        
        # Subscribe to bar events for EOD position handling
        if self.close_positions_eod:
            self.event_bus.subscribe(EventType.BAR, self.on_bar_eod_check)
            logger.info("Enabled end-of-day position closing")
        
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
        # Get required components from context
        self.event_bus = self.shared_context.get('event_bus')
        
        # If components haven't been added yet, try to find them in the shared context
        if not self.components:
            # Add components from context if available
            for component_key in ['data_handler', 'strategy', 'portfolio', 'risk_manager', 'broker', 'market_simulator']:
                if component_key in self.shared_context:
                    component = self.shared_context.get(component_key)
                    self.add_component(component_key, component)
            
            self.logger.info(f"Added {len(self.components)} components from context")
        
        # Ensure the market simulator is properly linked to the data handler
        data_handler = self.components.get('data_handler')
        market_simulator = self.components.get('market_simulator')
        
        if data_handler and market_simulator:
            # Add data handler to market simulator's context for direct initialization
            market_sim_context = {
                'data_handler': data_handler,
                'event_bus': self.event_bus
            }
            # Initialize market simulator with data handler
            market_simulator.initialize(market_sim_context)
            self.logger.info("Linked market simulator to data handler for direct data access")
        
        # Initialize all components with the shared context
        for name, component in self.components.items():
            if hasattr(component, 'initialize') and callable(getattr(component, 'initialize')):
                try:
                    component.initialize(self.shared_context)
                    self.logger.info(f"Initialized component: {name}")
                except Exception as e:
                    self.logger.warning(f"Error initializing component {name}: {e}")
            else:
                self.logger.info(f"Component {name} does not have initialize method, skipping initialization")
            
        # Start all components
        for name, component in self.components.items():
            if hasattr(component, 'start') and callable(getattr(component, 'start')):
                try:
                    component.start()
                    self.logger.info(f"Started component: {name}")
                except Exception as e:
                    self.logger.warning(f"Error starting component {name}: {e}")
            else:
                self.logger.info(f"Component {name} does not have start method, skipping start")
            
        self.logger.info("Backtest components initialized and started")
    
    def close_all_open_trades(self):
        """
        Close all open trades at the end of the backtest using last available prices.
        This ensures all PnL is realized and metrics are based on closed trades only.
        """
        # Get the portfolio manager
        portfolio = self.components.get('portfolio')
        if not portfolio:
            self.logger.warning("Cannot close open trades - no portfolio component found")
            return
            
        # Get current time for close timestamp
        current_time = datetime.datetime.now()
        
        # Try different approaches to get the latest timestamp from data
        data_handler = self.components.get('data_handler')
        if data_handler:
            # Try various methods that might exist on the data handler
            if hasattr(data_handler, 'get_current_timestamp'):
                current_time = data_handler.get_current_timestamp()
            elif hasattr(data_handler, 'latest_timestamp'):
                current_time = data_handler.latest_timestamp
            # For CSV data handler, try to get the last timestamp from a symbol's latest bar
            elif hasattr(data_handler, 'get_latest_bar') and hasattr(data_handler, 'symbols'):
                for symbol in data_handler.symbols:
                    bar = data_handler.get_latest_bar(symbol)
                    if bar and hasattr(bar, 'timestamp'):
                        current_time = bar.timestamp
                        break
        
        # Use the portfolio manager to close all positions
        if hasattr(portfolio, 'close_all_positions'):
            closed_trades = portfolio.close_all_positions(current_time)
            if closed_trades:
                self.logger.info(f"Closed {len(closed_trades)} positions at end of backtest")
            else:
                self.logger.info("No open trades to close at end of backtest")
        else:
            self.logger.warning("Portfolio manager doesn't support close_all_positions method")
            
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
        
        # Get required components
        data_handler = self.components.get('data_handler')
        if not data_handler:
            raise ValueError("No data_handler component registered")
            
        # Get the market simulator to ensure it's initialized properly
        market_simulator = self.components.get('market_simulator')
        if market_simulator:
            self.logger.info("Ensuring market simulator has current price data")
            # Make sure market simulator has access to data handler in its context
            # FIXED: Explicitly set the data handler regardless, to ensure it's the current instance
            market_simulator.data_handler = data_handler
            self.logger.info(f"Set data_handler reference directly in market_simulator")
            
            # FIXED: Also ensure broker has access to market simulator
            broker = self.components.get('broker')
            if broker:
                broker.market_simulator = market_simulator
                self.logger.info(f"Set market_simulator reference directly in broker")
        
            # Pre-initialize with first bar for each symbol if possible
            for symbol in data_handler.get_symbols():
                bar = data_handler.get_latest_bar(symbol)
                if bar and hasattr(market_simulator, 'update_price_data'):
                    success = market_simulator.update_price_data(symbol, bar)
                    if success:
                        self.logger.info(f"Pre-loaded price data for {symbol} in market simulator")
                    else:
                        self.logger.warning(f"Failed to pre-load price data for {symbol} in market simulator")
                    
                    # Verify price data was successfully loaded
                    if symbol in market_simulator.current_prices:
                        close_price = market_simulator.current_prices[symbol]['close']
                        self.logger.info(f"Verified price data for {symbol}: close={close_price:.4f}")
                    else:
                        self.logger.warning(f"Price verification failed for {symbol} - not in current_prices")
        
        # Get strategy from components
        strategy = self.components.get('strategy')
        if not strategy:
            self.logger.warning("No strategy component registered")
        
        # Load data for symbols from config
        symbols = self.shared_context.get('symbols', [])
        if not symbols:
            symbols = [source.get('symbol') for source in self.config.get('data', {}).get('sources', [])]
        
        if not symbols:
            raise ValueError("No symbols specified for backtest")
        
        self.logger.info(f"Loading data for symbols: {symbols}")
        data_handler.load_data(symbols)
        
        # Initialize other components
        if 'portfolio' in self.components:
            portfolio = self.components['portfolio']
            self.logger.info(f"Using portfolio: {portfolio.name}")
        
        # Debug info before starting
        self.logger.info(f"Beginning backtest with {len(symbols)} symbols: {symbols}")
        
        # Run through all data
        has_more_data = True
        bar_count = 0
        
        while has_more_data:
            # Process the next bar
            has_more_data = data_handler.update_bars()  # This should emit bar events to the event bus
            bar_count += 1
            
            if bar_count % 100 == 0:  # Only log occasionally
                self.logger.info(f"Processed {bar_count} bars")
            
            # Check if we've reached a limit
            max_bars = self.shared_context.get('max_bars')
            if max_bars and bar_count >= max_bars:
                self.logger.info(f"Reached bar limit of {max_bars}, stopping backtest")
                break
        
        # Close all open trades at the end of the backtest
        self.close_all_open_trades()
            
        # Signal end of backtest
        self.event_bus.publish(Event(EventType.BACKTEST_END, {}))
        
        # Return the results
        self.logger.info(f"Backtest completed after processing {bar_count} bars")
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
            if hasattr(component, 'stop') and callable(getattr(component, 'stop')):
                try:
                    component.stop()
                    self.logger.info(f"Stopped component: {name}")
                except Exception as e:
                    self.logger.warning(f"Error stopping component {name}: {e}")
            else:
                self.logger.info(f"Component {name} does not have stop method, skipping stop")
            
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
            
        # Get trades directly from the portfolio - this is a more elegant approach
        # than using a separate trade repository as a middleman
        trades = []
        if hasattr(portfolio, 'get_trades'):
            trades = portfolio.get_trades()
            self.logger.info(f"Retrieved {len(trades)} trades directly from portfolio")
        
        # CRITICAL VERIFICATION: Verify trades vs equity curve consistency
        initial_capital = getattr(portfolio, 'initial_capital', None)
        if initial_capital is None:
            initial_capital = getattr(portfolio, 'initial_cash', 100000)
            self.logger.info(f"Using initial_cash ({initial_capital}) as initial_capital")
        is_consistent = self.verify_trades_vs_equity(trades, initial_capital)
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
        
        # Run advanced analytics and generate reports if configured
        analytics_config = self.config.get('analytics', {})
        if analytics_config.get('enabled', False):
            self._run_analytics(trades, analytics_config)
    
    def _run_analytics(self, trades, analytics_config):
        """
        Run advanced analytics and generate reports.
        
        Args:
            trades: List of trade dictionaries
            analytics_config: Analytics configuration
        """
        # Get portfolio from components if available
        portfolio = None
        if 'portfolio' in self.components:
            portfolio = self.components['portfolio']
        try:
            import os
            import pandas as pd
            from datetime import datetime
            
            from src.analytics.analysis.performance import PerformanceAnalyzer
            from src.analytics.reporting.text_report import TextReportBuilder
            from src.analytics.reporting.html_report import HTMLReportBuilder
            
            self.logger.info("Running advanced analytics...")
            
            # Convert equity curve to DataFrame
            equity_data = []
            for point in self.equity_curve:
                equity_point = {
                    'timestamp': point.get('timestamp', datetime.now()),
                    'equity': point.get('equity', 0),
                    'cash': point.get('cash', 0),
                    'market_value': point.get('market_value', 0),
                    'closed_pnl': point.get('closed_pnl', 0)
                }
                equity_data.append(equity_point)
            
            # If we don't have any equity data points, create at least one with initial values
            if not equity_data:
                self.logger.warning("No equity data points available for analytics, creating a minimal placeholder")
                # Create a single data point with initial capital
                initial_capital = portfolio.initial_capital if hasattr(portfolio, 'initial_capital') else 100000
                equity_data.append({
                    'timestamp': datetime.now(),
                    'equity': initial_capital,
                    'cash': initial_capital,
                    'market_value': 0,
                    'closed_pnl': 0
                })
            
            equity_df = pd.DataFrame(equity_data)
            
            # Set timestamp as index if present
            if 'timestamp' in equity_df.columns:
                equity_df.set_index('timestamp', inplace=True)
            
            # Create analyzer
            analyzer = PerformanceAnalyzer(
                equity_curve=equity_df,
                trades=trades
            )
            
            # Run analysis
            analysis_config = analytics_config.get('analysis', {})
            risk_free_rate = analysis_config.get('risk_free_rate', 0.0)
            periods_per_year = analysis_config.get('periods_per_year', 252)
            
            self.logger.info("Running performance analysis...")
            metrics = analyzer.analyze_performance(
                risk_free_rate=risk_free_rate,
                periods_per_year=periods_per_year
            )
            
            # Generate reports if enabled
            reporting_config = analytics_config.get('reporting', {})
            if reporting_config.get('enabled', False):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = reporting_config.get('output_directory', './results/reports')
                
                # Ensure output directory exists
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                # Get report formats
                formats = reporting_config.get('formats', ['text'])
                
                # Generate text report
                if 'text' in formats:
                    text_config = reporting_config.get('text', {})
                    width = text_config.get('width', 80)
                    
                    self.logger.info("Generating text report...")
                    text_builder = TextReportBuilder(
                        analyzer=analyzer,
                        title=f"{self.config.get('name', 'Backtest')} - Performance Report",
                        width=width
                    )
                    
                    text_file = os.path.join(output_dir, f"backtest_report_{timestamp}.txt")
                    text_builder.save(text_file)
                    self.logger.info(f"Text report saved to: {text_file}")
                
                # Generate HTML report
                if 'html' in formats:
                    html_config = reporting_config.get('html', {})
                    
                    self.logger.info("Generating HTML report...")
                    html_builder = HTMLReportBuilder(
                        analyzer=analyzer,
                        title=html_config.get('title', f"{self.config.get('name', 'Backtest')} - Performance Report"),
                        description=html_config.get('description', "")
                    )
                    
                    html_file = os.path.join(output_dir, f"backtest_report_{timestamp}.html")
                    html_builder.save(html_file)
                    self.logger.info(f"HTML report saved to: {html_file}")
            
            self.logger.info("Analytics processing completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error running analytics: {e}", exc_info=True)
        
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
        initial_capital = getattr(portfolio, 'initial_capital', None)
        if initial_capital is None:
            initial_capital = getattr(portfolio, 'initial_cash', 100000)
            self.logger.info(f"Using initial_cash ({initial_capital}) as initial_capital")
            
        stats = {
            'initial_capital': initial_capital,
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
            equity_change = portfolio.get_capital() - initial_capital  # Use the initial_capital we determined earlier
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
            try:
                if hasattr(component, 'reset') and callable(getattr(component, 'reset')):
                    component.reset()
                    self.logger.info(f"Reset component: {name}")
                else:
                    self.logger.warning(f"Component {name} does not have reset method, skipping reset")
            except Exception as e:
                self.logger.warning(f"Error resetting component {name}: {e}")
            
    def _setup_broker_components(self):
        """
        Create and configure broker components if not provided.
        
        This method creates and initializes the necessary broker components
        for backtesting, including the simulated broker, market simulator,
        slippage model, and commission model.
        """
        # Check if broker components already exist in context
        if 'broker' in self.components:
            logger.info("Using existing broker component")
            return
            
        # Get broker configuration
        broker_config = self.config.get('broker', {})
        
        # Create market simulator
        market_simulator = MarketSimulator("market_simulator", broker_config.get('market_simulator', {}))
        
        # Create slippage model based on configuration
        slippage_config = broker_config.get('slippage', {})
        slippage_type = slippage_config.get('model', 'fixed')
        
        if slippage_type.lower() == 'variable':
            slippage_model = VariableSlippageModel()
        else:
            slippage_model = FixedSlippageModel()
            
        # Configure slippage model
        slippage_model.configure(slippage_config)
        
        # Create commission model
        commission_model = CommissionModel()
        commission_model.configure(broker_config.get('commission', {}))
        
        # Create simulated broker
        broker = SimulatedBroker("simulated_broker", broker_config)
        
        # Add components to shared context
        self.shared_context['market_simulator'] = market_simulator
        self.shared_context['slippage_model'] = slippage_model
        self.shared_context['commission_model'] = commission_model
        
        # Register broker components
        self.add_component('market_simulator', market_simulator)
        self.add_component('broker', broker)
        
        # Log
        logger.info("Broker components created and configured")
        
        # Initialize with order types if specified
        if 'allowed_order_types' in broker_config:
            logger.info(f"Restricting to order types: {broker_config['allowed_order_types']}")
            
        # Debug
        logger.debug(f"Broker configuration: {broker_config}")
        logger.debug(f"Slippage model: {slippage_model.__class__.__name__}")
        logger.debug(f"Commission model: {commission_model.commission_type}, rate={commission_model.rate}")
    
    def on_bar_eod_check(self, event):
        """
        Check for end-of-day position closing.
        
        This method monitors bars and detects when the trading day changes.
        When a new day is detected, it can optionally close all positions.
        
        Args:
            event (Event): Bar event
        """
        # Early exit if EOD closing is disabled
        if not self.close_positions_eod:
            return
            
        # Get bar data
        if hasattr(event, 'get_data') and callable(event.get_data):
            bar_data = event.get_data()
        elif hasattr(event, 'data'):
            bar_data = event.data
        else:
            return
            
        # Get timestamp
        timestamp = bar_data.get('timestamp')
        if not timestamp:
            return
            
        # Extract date (ignoring time)
        if hasattr(timestamp, 'date'):
            current_date = timestamp.date()
        else:
            # Try to convert string to datetime if needed
            try:
                from datetime import datetime
                current_date = datetime.fromisoformat(str(timestamp)).date()
            except (ValueError, TypeError):
                logger.warning(f"Could not parse timestamp: {timestamp}")
                return
        
        # First bar of the backtest - initialize the day tracking
        if self.current_day is None:
            self.current_day = current_date
            return
            
        # Check if day has changed
        if current_date != self.current_day:
            # Day has changed - close positions from previous day
            logger.info(f"Day changed from {self.current_day} to {current_date}, closing positions")
            
            # Close positions
            self._close_all_positions(self.current_day)
            
            # Update current day
            self.current_day = current_date
    
    def _close_all_positions(self, trading_day):
        """
        Close all open positions at the end of a trading day.
        
        Args:
            trading_day: The trading day that's ending
        """
        # Get portfolio from components
        portfolio = self.components.get('portfolio')
        if not portfolio:
            logger.warning("Cannot close positions - no portfolio component found")
            return
            
        # Get position manager if available - should be provided by the portfolio
        position_manager = portfolio.get_position_manager() if hasattr(portfolio, 'get_position_manager') else None
        
        # Determine which component to use for position closing
        if position_manager:
            # Get all open positions
            open_positions = position_manager.get_all_positions()
            
            if not open_positions:
                logger.info(f"No open positions to close for trading day {trading_day}")
                return
                
            logger.info(f"Closing {len(open_positions)} positions at end of trading day {trading_day}")
            
            # Close each position by creating a neutralizing order
            for symbol, position in open_positions.items():
                # Skip if no position quantity
                quantity = position.get('quantity', 0)
                if quantity == 0:
                    continue
                    
                # Create closing order with opposite direction
                direction = "SELL" if quantity > 0 else "BUY"
                close_quantity = abs(quantity)
                
                # Create order event
                close_order = {
                    'id': f"eod_close_{symbol}_{trading_day}",
                    'symbol': symbol,
                    'order_type': 'MARKET',
                    'direction': direction,
                    'quantity': close_quantity,
                    'timestamp': datetime.datetime.now(),
                    'status': 'CREATED',
                    'reason': 'EOD_POSITION_CLOSE'
                }
                
                # Publish order event
                self.event_bus.publish(Event(EventType.ORDER, close_order))
                
                logger.info(f"Created EOD closing order for {symbol}: {direction} {close_quantity}")
                
                # Update stats
                self.stats['positions_closed_eod'] += 1
        else:
            # Fallback to portfolio's close_all_positions method if available
            if hasattr(portfolio, 'close_all_positions'):
                logger.info(f"Using portfolio.close_all_positions() for EOD position closing")
                portfolio.close_all_positions(reason="EOD_POSITION_CLOSE")
            else:
                logger.warning("Cannot close positions - no position manager or portfolio.close_all_positions method found")
                
        logger.info(f"End of day position closing completed for {trading_day}")
