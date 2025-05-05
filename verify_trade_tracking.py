#!/usr/bin/env python3
"""
Verify trade tracking in ADMF-Trader.
"""
import logging
import sys
import os
from datetime import datetime
import json

# Configure logging
log_file = f"trade_tracking_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

# Try to import from src directory
try:
    from src.core.system_bootstrap import Bootstrap
    from src.core.config.config import Config
except ImportError:
    logger.error("Unable to import ADMF-Trader modules. Make sure you're running from the project root directory.")
    sys.exit(1)

def print_separator(message=""):
    """Print a separator line with optional message."""
    line = "-" * 80
    if message:
        print(f"\n{line}\n{message}\n{line}")
    else:
        print(f"\n{line}\n")

def inspect_trades(trades, label=""):
    """Inspect trade data structure and consistency."""
    print_separator(f"TRADE INSPECTION {label}")
    print(f"Total trades: {len(trades)}")
    
    if not trades:
        print("No trades to inspect")
        return
    
    # Check for required fields
    required_fields = ['id', 'symbol', 'direction', 'price', 'quantity', 'pnl']
    missing_fields = {}
    for i, trade in enumerate(trades):
        for field in required_fields:
            if field not in trade:
                if field not in missing_fields:
                    missing_fields[field] = []
                missing_fields[field].append(i)
    
    if missing_fields:
        print("Missing required fields:")
        for field, indices in missing_fields.items():
            print(f"  {field}: missing in {len(indices)} trades")
    else:
        print("All trades have required fields")
    
    # Check PnL values
    pnl_values = [trade.get('pnl', 0) for trade in trades]
    total_pnl = sum(pnl_values)
    print(f"PnL summary: Total={total_pnl:.2f}, Min={min(pnl_values):.2f}, Max={max(pnl_values):.2f}")
    
    # Sample trades
    print("\nFirst trade:")
    print(json.dumps(trades[0], indent=2, default=str))
    
    if len(trades) > 1:
        print("\nLast trade:")
        print(json.dumps(trades[-1], indent=2, default=str))

def main():
    """Run verification test."""
    logger.info("Starting trade tracking verification test")
    
    # Load configuration
    config_file = "config/mini_test.yaml"  # Using an existing config file
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    if not os.path.exists(config_file):
        logger.error(f"Configuration file not found: {config_file}")
        sys.exit(1)
    
    logger.info(f"Loading configuration from {config_file}")
    config = Config()
    config.load_file(config_file)
    
    # Set up the system
    bootstrap = Bootstrap(
        config_files=[config_file],
        log_level="INFO"
    )
    
    logger.info("Setting up system")
    container, loaded_config = bootstrap.setup()
    
    # Get components
    backtest = container.get("backtest")
    portfolio = container.get("portfolio")
    
    # Run backtest
    logger.info("Running backtest")
    results = backtest.run()
    
    # Verify trade tracking
    if portfolio:
        print_separator("PORTFOLIO INSPECTION")
        print(f"Portfolio ID: {portfolio.name}")
        print(f"Initial cash: ${portfolio.initial_cash:.2f}")
        print(f"Final cash: ${portfolio.cash:.2f}")
        print(f"Final equity: ${portfolio.equity:.2f}")
        print(f"Trade statistics:")
        stats = portfolio.get_stats()
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        
        logger.info("Verifying trade tracking in portfolio")
        if hasattr(portfolio, 'debug_trade_tracking'):
            trade_count = portfolio.debug_trade_tracking()
            logger.info(f"Portfolio reports {trade_count} trades")
        else:
            logger.warning("Portfolio does not have debug_trade_tracking method")
    else:
        logger.error("Portfolio not found in container")
    
    # Check results
    if results and isinstance(results, dict):
        trades = results.get('trades', [])
        metrics = results.get('metrics', {})
        
        # Inspect trades from results
        inspect_trades(trades, "FROM RESULTS")
        
        # Directly get trades from portfolio
        if portfolio:
            portfolio_trades = portfolio.get_recent_trades()
            inspect_trades(portfolio_trades, "FROM PORTFOLIO DIRECTLY")
        
        logger.info(f"Results contain {len(trades)} trades")
        logger.info(f"Metrics report {metrics.get('trade_count', 0)} trades")
        
        # Verify consistency
        if len(trades) != metrics.get('trade_count', 0):
            logger.warning(f"Inconsistency: trades list has {len(trades)} items but metrics reports {metrics.get('trade_count', 0)}")
        
        # Check some metrics
        print_separator("PERFORMANCE METRICS")
        metrics_to_print = [
            'total_return', 'sharpe_ratio', 'sortino_ratio', 'max_drawdown', 
            'win_rate', 'profit_factor', 'trade_count'
        ]
        for metric in metrics_to_print:
            value = metrics.get(metric, 'N/A')
            if isinstance(value, float):
                print(f"{metric}: {value:.4f}")
            else:
                print(f"{metric}: {value}")
    else:
        logger.error("Invalid or empty results returned from backtest")
    
    print_separator()
    print(f"Log file saved to: {log_file}")
    logger.info("Trade tracking verification complete")

if __name__ == "__main__":
    main()
