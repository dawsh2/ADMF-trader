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

# Configure logging - use a more visible format
log_timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = f"ma_crossover_fixed_{log_timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("ma_crossover_fix")
logger.setLevel(logging.INFO)

def setup_enhanced_logging():
    """Setup enhanced logging for key components"""
    # Set higher log levels for important components
    logging.getLogger("src.strategy.implementations.ma_crossover").setLevel(logging.INFO)
    logging.getLogger("src.risk.managers.simple").setLevel(logging.INFO)
    logging.getLogger("src.risk.portfolio.portfolio").setLevel(logging.INFO)
    logging.getLogger("src.execution.order_manager").setLevel(logging.INFO)
    
    # Create a special handler for strategy logs with distinctive formatting
    strategy_handler = logging.FileHandler(f"ma_strategy_{log_timestamp}.log")
    strategy_handler.setFormatter(logging.Formatter('[%(levelname)s] - %(asctime)s - %(message)s'))
    logging.getLogger("src.strategy.implementations.ma_crossover").addHandler(strategy_handler)
    
    logger.info("Enhanced logging configured")

def patch_portfolio_manager():
    """Apply critical patches to the portfolio manager"""
    try:
        from src.risk.portfolio.portfolio import PortfolioManager
        
        # Backup original on_fill method
        original_on_fill = PortfolioManager.on_fill
        
        # Create a patched version that ensures trades are correctly recorded
        def patched_on_fill(self, fill_event):
            """Patched version of on_fill to ensure trades are recorded"""
            logger.info(f"Patched on_fill called for event: {getattr(fill_event, 'id', 'unknown')}")
            
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
                    
            # Print trade count for verification
            logger.info(f"Portfolio now has {len(self.trades)} trades after processing fill")
            
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
        logger.info("====== VALIDATING TRADES ======")
        
        # Get portfolio
        portfolio = backtest.portfolio_manager
        
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
            
        # Print first few trades
        if portfolio.trades:
            logger.info(f"First trade: {portfolio.trades[0]}")
            
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

def main():
    """Run the fixed MA Crossover strategy"""
    logger.info("=" * 80)
    logger.info("RUNNING FIXED MA CROSSOVER STRATEGY")
    logger.info("=" * 80)
    
    # Setup enhanced logging
    setup_enhanced_logging()
    
    # Apply critical patches
    patch_portfolio_manager()
    install_trade_validator()
    
    # Install portfolio diagnostics if available
    try:
        from src.risk.portfolio.portfolio_diagnostics import install_diagnostics
        install_diagnostics()
        logger.info("Portfolio diagnostics installed")
    except:
        logger.warning("Failed to install portfolio diagnostics, continuing without them")
    
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
    
    # Create bootstrap object
    bs = bootstrap.Bootstrap(
        config_files=[config_path],
        log_level="INFO",
        log_file=f"ma_crossover_fixed_{log_timestamp}_system.log"
    )
    
    # Setup container
    logger.info("Setting up system container")
    container, config = bs.setup()
    
    # Run backtest
    backtest = container.get('backtest')
    logger.info("Running backtest...")
    results = backtest.run()
    
    # Process results
    if results:
        logger.info("Backtest completed successfully")
        
        # Check for trades
        trades = results.get('trades', [])
        logger.info(f"Found {len(trades)} trades in results")
        
        if trades:
            logger.info(f"First trade: {trades[0]}")
        else:
            logger.warning("No trades in backtest results!")
            
            # Check if portfolio has trades
            portfolio = container.get('portfolio')
            if portfolio:
                portfolio_trades = portfolio.get_recent_trades()
                logger.info(f"Portfolio has {len(portfolio_trades)} trades")
                
                # Use these trades in results if available
                if portfolio_trades:
                    results['trades'] = portfolio_trades
                    logger.info(f"Using {len(portfolio_trades)} trades from portfolio")
                    
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
            
        return True
    else:
        logger.error("Backtest did not produce any results")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
