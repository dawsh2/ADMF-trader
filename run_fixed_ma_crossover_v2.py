#!/usr/bin/env python3
"""
Run MA Crossover with enhanced debugging for signal direction groups.
This script runs the fixed MA Crossover implementation with detailed logging
to diagnose and fix issues with signal groups and trade tracking.
"""

import os
import sys
import datetime
import logging
import uuid
import csv

# Configure logging - use a more focused logging approach
log_timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = f"ma_crossover_fixed_{log_timestamp}.log"

# Set up file handler with INFO level
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
file_handler.setFormatter(file_formatter)

# Set up console handler with higher threshold to reduce output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)  # Only show WARNING and above in console
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

# Create our own logger
logger = logging.getLogger("ma_crossover_fix")
logger.setLevel(logging.INFO)

def setup_enhanced_logging():
    """Setup enhanced logging for key components with reduced verbosity"""
    # Only log important components at INFO level
    logging.getLogger("src.strategy.implementations.ma_crossover").setLevel(logging.INFO)
    logging.getLogger("src.risk.managers.simple").setLevel(logging.INFO)  # CHANGED: Increased to INFO
    logging.getLogger("src.risk.portfolio.portfolio").setLevel(logging.WARNING)  # Less verbose
    logging.getLogger("src.execution.order_manager").setLevel(logging.WARNING)  # Less verbose
    logging.getLogger("DIAGNOSTICS").setLevel(logging.WARNING)  # Reduce diagnostic noise
    
    # Reduce noise from these components
    logging.getLogger("src.core.events.event_bus").setLevel(logging.WARNING)
    logging.getLogger("src.execution.broker.broker_simulator").setLevel(logging.WARNING)
    
    # Create a special handler for strategy logs with distinctive formatting
    strategy_handler = logging.FileHandler(f"ma_strategy_{log_timestamp}.log")
    strategy_handler.setFormatter(logging.Formatter('[%(levelname)s] - %(asctime)s - %(message)s'))
    logging.getLogger("src.strategy.implementations.ma_crossover").addHandler(strategy_handler)
    
    # Create a special handler for risk manager logs
    risk_handler = logging.FileHandler(f"risk_manager_{log_timestamp}.log")
    risk_handler.setFormatter(logging.Formatter('[%(levelname)s] - %(asctime)s - %(message)s'))
    logging.getLogger("src.risk.managers.simple").addHandler(risk_handler)
    
    logger.info("Enhanced logging configured")

def patch_risk_manager():
    """Apply critical patches to ensure risk manager resets properly"""
    try:
        from src.risk.managers.simple import SimpleRiskManager
        
        # Add a diagnostic method to verify state
        def print_state(self):
            """Print diagnostic state information for debugging"""
            rule_id_count = len(self.processed_rule_ids)
            signal_count = len(self.processed_signals)
            logger.info(f"RISK MANAGER STATE: {rule_id_count} rule_ids, {signal_count} signals")
            if rule_id_count > 0:
                logger.info(f"Rule IDs: {sorted(list(self.processed_rule_ids))}")
            return rule_id_count, signal_count
        
        # Add method to the class
        SimpleRiskManager.print_state = print_state
        
        # Get original reset method reference
        original_reset = SimpleRiskManager.reset
        
        # Create patched version with enhanced logging
        def enhanced_reset(self):
            """Enhanced reset with better diagnostics"""
            # Print state before reset
            rule_count, signal_count = self.print_state()
            
            logger.info(f"=== RISK MANAGER RESET STARTED with {rule_count} rule_ids ===")
            
            # Call original reset
            original_reset(self)
            
            # Print state after reset
            new_rule_count, new_signal_count = self.print_state()
            
            # Verify reset was effective
            logger.info(f"=== RISK MANAGER RESET COMPLETED: {rule_count} -> {new_rule_count} rule_ids ===")
            
            # Explicitly verify the collections are empty
            if new_rule_count > 0:
                logger.warning(f"WARNING: processed_rule_ids not properly cleared! {new_rule_count} remain")
            
            return True
            
        # Apply patch
        SimpleRiskManager.reset = enhanced_reset
        logger.info("Risk manager patched with enhanced diagnostics")
        
        return True
    except Exception as e:
        logger.error(f"Failed to patch risk manager: {e}")
        return False

def patch_portfolio_manager():
    """Apply critical patches to the portfolio manager"""
    try:
        from src.risk.portfolio.portfolio import PortfolioManager
        
        # Backup original on_fill method
        original_on_fill = PortfolioManager.on_fill
        
        # Create a patched version that ensures trades are correctly recorded
        def patched_on_fill(self, fill_event):
            """Patched version of on_fill to ensure trades are recorded"""
            logger.info(f"Processing fill event: {getattr(fill_event, 'id', 'unknown')}")
            
            # Ensure trades list exists
            if not hasattr(self, 'trades') or not isinstance(self.trades, list):
                logger.warning("Initializing missing trades list in portfolio")
                self.trades = []
                
            # Call original method
            result = original_on_fill(self, fill_event)
            
            # Check if the trade was added to the trades list
            fill_data = getattr(fill_event, 'data', {})
            order_id = fill_data.get('order_id')
            
            # Verify trade was added
            if order_id:
                trade_found = False
                for trade in self.trades:
                    if trade.get('id') == order_id or trade.get('order_id') == order_id:
                        trade_found = True
                        break
                        
                if not trade_found:
                    logger.warning(f"Trade not found for order_id {order_id}, forcing creation")
                    
                    # Create a minimal trade record
                    timestamp = getattr(fill_event, 'timestamp', datetime.datetime.now())
                    symbol = fill_data.get('symbol', 'UNKNOWN')
                    direction = fill_data.get('direction', 'BUY')
                    quantity = fill_data.get('size', 1)
                    price = fill_data.get('fill_price', 0.0)
                    
                    # Generate a minimal trade record
                    trade = {
                        'id': str(uuid.uuid4()),
                        'order_id': order_id,
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'direction': direction,
                        'quantity': quantity,
                        'price': price,
                        'pnl': 0.0  # No PnL calculation in this fallback
                    }
                    
                    # Force-add to trades list
                    self.trades.append(trade)
                    logger.info(f"Manually added trade {trade['id']} for order {order_id}")
            
            return result
            
        # Apply patch
        PortfolioManager.on_fill = patched_on_fill
        logger.info("Portfolio manager patched successfully")
        
        return True
    except Exception as e:
        logger.error(f"Failed to patch portfolio manager: {e}")
        return False

def install_trade_validator():
    """Install a validator to ensure trades are correctly recorded"""
    from src.core.events.event_types import EventType
    from src.analytics.reporting.report_generator import ReportGenerator
    
    # Create a validator for BacktestCoordinator
    def validate_trades(backtest, results):
        """Validates trade recording between portfolio and results"""
        logger.info("Validating trades between portfolio and results")
        
        # Get portfolio - FIXED: use backtest.portfolio instead of portfolio_manager
        portfolio = backtest.portfolio
        
        # Check if portfolio has trades
        if not hasattr(portfolio, 'trades') or not portfolio.trades:
            logger.warning("No trades found in portfolio!")
            return
            
        # Log trade counts
        logger.info(f"Portfolio trade count: {len(portfolio.trades)}")
        logger.info(f"Results trade count: {len(results.get('trades', []))}")
        
        # Check if trades were properly transferred to results
        if len(portfolio.trades) > 0 and len(results.get('trades', [])) == 0:
            logger.warning("Trades found in portfolio but not in results! Fixing...")
            
            # Fix results by copying trades from portfolio
            results['trades'] = portfolio.trades
            logger.info(f"Copied {len(portfolio.trades)} trades from portfolio to results")
            
            # Recalculate performance metrics
            report_gen = ReportGenerator()
            metrics = report_gen.calculate_metrics(portfolio.trades, portfolio.get_equity_curve_df())
            results['metrics'] = metrics
            logger.info("Recalculated performance metrics")
    
    # Install validator to BacktestCoordinator
    try:
        from src.execution.backtest.backtest import BacktestCoordinator
        
        # Patch _process_results
        original_process = BacktestCoordinator._process_results
        
        def patched_process_results(self):
            """Patched method to ensure trades are correctly processed"""
            # Call original method
            results = original_process(self)
            
            # Validate results
            if results:
                validate_trades(self, results)
                
            return results
            
        # Apply patch
        BacktestCoordinator._process_results = patched_process_results
        logger.info("Trade validator installed")
        
        return True
    except Exception as e:
        logger.error(f"Failed to install trade validator: {e}")
        return False

def load_validation_data():
    """Load validation data from backtest_trades_grouped.csv"""
    validation_data = {
        'signals': [],
        'win_rate': 0,
        'net_pnl': 0
    }
    
    try:
        with open('backtest_trades_grouped.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            trades = list(reader)
            validation_data['signals'] = trades
            
            if trades:
                # Calculate win rate and net PnL
                win_count = sum(1 for t in trades if t.get('win') == 'True')
                validation_data['win_rate'] = (win_count / len(trades)) * 100
                
                # Sum PnL
                validation_data['net_pnl'] = sum(float(t.get('pnl', 0)) for t in trades)
    except Exception as e:
        logger.error(f"Error loading validation data: {e}")
    
    return validation_data

def analyze_discrepancies(validation_data, actual_results):
    """Analyze and report discrepancies between validation and actual results"""
    print("\n" + "=" * 50)
    print("COMPARING VALIDATION WITH ACTUAL RESULTS")
    print("=" * 50)
    
    # Check trade counts
    validation_trades = len(validation_data.get('signals', []))
    actual_trades = len(actual_results.get('trades', []))
    
    print(f"Validation signal direction changes: {validation_trades}")
    print(f"Actual trades executed: {actual_trades}")
    
    if validation_trades != actual_trades:
        print(f"DISCREPANCY DETECTED: Expected {validation_trades} trades but found {actual_trades}")
    else:
        print("✓ Trade count matches between validation and system")
    
    # Compare PnL and win rates
    validation_win_rate = validation_data.get('win_rate', 0)
    actual_win_rate = 0
    if actual_trades > 0:
        win_count = sum(1 for t in actual_results.get('trades', []) if t.get('pnl', 0) > 0)
        actual_win_rate = (win_count / actual_trades) * 100
    
    validation_pnl = validation_data.get('net_pnl', 0)
    actual_pnl = sum(t.get('pnl', 0) for t in actual_results.get('trades', []))
    
    print(f"Validation win rate: {validation_win_rate:.2f}%")
    print(f"Actual win rate: {actual_win_rate:.2f}%")
    
    if abs(validation_win_rate - actual_win_rate) > 1.0:  # 1% tolerance
        print(f"DISCREPANCY DETECTED: Win rate differs by {abs(validation_win_rate - actual_win_rate):.2f}%")
    else:
        print("✓ Win rates are comparable")
    
    print(f"Validation PnL: ${validation_pnl:.2f}")
    print(f"Actual PnL: ${actual_pnl:.2f}")
    
    if abs(validation_pnl - actual_pnl) > 0.5:  # $0.50 tolerance
        print(f"DISCREPANCY DETECTED: PnL differs by ${abs(validation_pnl - actual_pnl):.2f}")
    else:
        print("✓ PnL values are comparable")
    
    # Check for direction alternation
    if actual_trades > 1:
        trades = actual_results.get('trades', [])
        direction_alternates = True
        for i in range(1, len(trades)):
            if trades[i].get('direction') == trades[i-1].get('direction'):
                direction_alternates = False
                break
        
        if direction_alternates:
            print("✓ Trade directions properly alternate between BUY and SELL")
        else:
            print("DISCREPANCY DETECTED: Trade directions do not properly alternate")
    
    # Summary
    print("\nDISCREPANCY SUMMARY:")
    if validation_trades == actual_trades and abs(validation_win_rate - actual_win_rate) <= 1.0 and abs(validation_pnl - actual_pnl) <= 0.5:
        print("✓ No significant discrepancies found! The fix appears successful.")
    else:
        print("⚠ Discrepancies found. Further investigation may be needed.")

def main():
    """Run the fixed MA Crossover strategy"""
    logger.info("=" * 40)
    logger.info("RUNNING FIXED MA CROSSOVER STRATEGY")
    logger.info("=" * 40)
    
    # Setup enhanced logging with reduced verbosity
    setup_enhanced_logging()
    
    # Apply critical patches
    patch_risk_manager()  # ADDED: Patch risk manager first
    patch_portfolio_manager()
    install_trade_validator()
    
    # Load validation data
    validation_data = load_validation_data()
    logger.info(f"Loaded validation data with {len(validation_data.get('signals', []))} signal groups")
    
    # Install portfolio diagnostics if available
    try:
        from src.risk.portfolio.portfolio_diagnostics import install_diagnostics
        install_diagnostics()
        logger.info("Portfolio diagnostics installed")
    except Exception as e:
        logger.warning(f"Failed to install portfolio diagnostics: {e}")
    
    # Ensure dependencies are loaded
    try:
        # Verify our fix is being used - IMPORTANT check
        from src.risk.managers.simple import SimpleRiskManager
        from src.strategy.implementations.ma_crossover import MACrossoverStrategy
        
        # Print diagnostics to confirm our fix is in place
        logger.info("VERIFICATION: Checking if our fix is in place")
        
        # Check risk manager
        reset_method = getattr(SimpleRiskManager, "reset").__code__
        if "processed_rule_ids.clear" in str(reset_method):
            logger.info("✓ SimpleRiskManager has proper reset method with rule_id clearing")
        else:
            logger.warning("✗ SimpleRiskManager lacks proper rule_id clearing in reset method!")
        
        # Check strategy
        on_bar_method = getattr(MACrossoverStrategy, "on_bar").__code__
        if "rule_id = f\"{self.name}_{symbol}_{direction_name}_group_{group_id}\"" in str(on_bar_method):
            logger.info("✓ MACrossoverStrategy has proper rule_id format")
        else:
            logger.warning("✗ MACrossoverStrategy has incorrect rule_id format!")
    except Exception as e:
        logger.error(f"Verification error: {e}")
    
    # Import the standard modules
    try:
        import src.core.system_bootstrap as bootstrap
        from src.execution.backtest.backtest import BacktestCoordinator
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return False
    
    # Set up config path - use zero commission config by default
    config_path = "config/mini_test_zero_commission.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    logger.info(f"Using configuration: {config_path}")
    
    # Create bootstrap object with reduced log level to console
    bs = bootstrap.Bootstrap(
        config_files=[config_path],
        log_level="WARNING",  # Reduce console output
        log_file=f"ma_crossover_fixed_{log_timestamp}_system.log"
    )
    
    # Temporarily disable console output for system setup
    for handler in logging.root.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            handler.setLevel(logging.ERROR)  # Suppress most messages
    
    # Setup container
    logger.info("Setting up system container")
    container, config = bs.setup()
    
    # Re-enable console output for important messages
    for handler in logging.root.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            handler.setLevel(logging.WARNING)
    
    # Before running, ensure risk manager is properly initialized
    risk_manager = container.get('risk_manager')
    if hasattr(risk_manager, 'print_state'):
        logger.info("Initial risk manager state:")
        risk_manager.print_state()
    
    # Run backtest
    backtest = container.get('backtest')
    logger.info("Running backtest...")
    print("Running backtest...")  # User feedback
    results = backtest.run()
    
    # Process results
    if results:
        logger.info("Backtest completed successfully")
        
        # Check for trades
        trades = results.get('trades', [])
        logger.info(f"Found {len(trades)} trades in results")
        print(f"Backtest completed with {len(trades)} trades")  # User feedback
        
        if trades:
            # Display a few sample trades
            print("\nSample trades:")
            for i, trade in enumerate(trades[:3]):
                print(f"  Trade {i+1}: {trade.get('direction')} at {trade.get('price')}, PnL: {trade.get('pnl')}")
            
            # Calculate win rate and PnL
            win_count = sum(1 for t in trades if t.get('pnl', 0) > 0)
            win_rate = win_count / len(trades) * 100 if trades else 0
            total_pnl = sum(t.get('pnl', 0) for t in trades)
            
            print(f"\nWin Rate: {win_rate:.2f}%")
            print(f"Total PnL: ${total_pnl:.2f}")
            
        else:
            logger.warning("No trades in backtest results!")
            print("Warning: No trades in backtest results")
            
            # Check if portfolio has trades
            portfolio = container.get('portfolio')
            if portfolio:
                portfolio_trades = portfolio.get_recent_trades()
                logger.info(f"Portfolio has {len(portfolio_trades)} trades")
                
                # Use these trades in results if available
                if portfolio_trades:
                    results['trades'] = portfolio_trades
                    logger.info(f"Using {len(portfolio_trades)} trades from portfolio")
                    print(f"Recovered {len(portfolio_trades)} trades from portfolio")
                    
                    # Recalculate performance metrics
                    from src.analytics.reporting.report_generator import ReportGenerator
                    report_gen = ReportGenerator()
                    metrics = report_gen.calculate_metrics(portfolio_trades, portfolio.get_equity_curve_df())
                    results['metrics'] = metrics
        
        # Generate and save reports
        report_generator = container.get("report_generator")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save reports
        output_dir = f"./results/ma_crossover_fixed_{timestamp}"
        os.makedirs(output_dir, exist_ok=True)
        
        saved_files = report_generator.save_reports(
            results, 
            output_dir=output_dir,
            timestamp=timestamp
        )
        
        # Print summary
        print("\nMA Crossover Fixed Backtest Results Summary:")
        report_generator.print_summary(results)
        
        print(f"\nResults saved to {output_dir}")
        for file_path in saved_files:
            print(f"- {os.path.basename(file_path)}")
        
        # Compare validation with actual results
        analyze_discrepancies(validation_data, results)
            
        return True
    else:
        logger.error("Backtest did not produce any results")
        print("Error: Backtest did not produce any results")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
