#!/usr/bin/env python
"""
Run the optimization with improved logging to debug position management issues.

This script executes the optimization with more detailed logging to help
identify and debug issues with position management.
"""

import logging
import sys
import os
import argparse
import yaml
from datetime import datetime

# Configure logging
log_file = f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run optimization with improved logging")
    parser.add_argument("--config", default="config/ma_crossover_optimization.yaml", 
                      help="Path to configuration file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.config):
        logger.error(f"Configuration file not found: {args.config}")
        return 1
        
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    logger.info(f"Loaded configuration from {args.config}")
    
    # Ensure risk management settings are present
    if 'risk' not in config:
        config['risk'] = {}
    if 'position_manager' not in config['risk']:
        config['risk']['position_manager'] = {}
        
    # Set risk management parameters
    config['risk']['position_manager'].update({
        'max_positions': 1,
        'fixed_quantity': 10,
        'enforce_single_position': True,
        'position_sizing_method': 'fixed'
    })
    
    logger.info(f"Using risk configuration: {config['risk']}")
    
    # Run the optimization
    try:
        from src.strategy.optimization.optimizer import StrategyOptimizer
        
        # Create the optimizer
        optimizer = StrategyOptimizer(config)
        
        # Run the optimization
        logger.info("Starting optimization...")
        results = optimizer.optimize()
        
        # Print results summary
        if results and 'best_parameters' in results:
            logger.info(f"Optimization complete. Best parameters: {results['best_parameters']}")
            
            # Print overall statistics
            stats = results.get('statistics', {})
            logger.info(f"Return: {stats.get('return_pct', 0):.2f}%")
            logger.info(f"Sharpe ratio: {stats.get('sharpe_ratio', 0):.2f}")
            logger.info(f"Profit factor: {stats.get('profit_factor', 0):.2f}")
            logger.info(f"Max drawdown: {stats.get('max_drawdown', 0):.2f}%")
            
            # Trade statistics
            trades = results.get('trades', [])
            logger.info(f"Total trades: {len(trades)}")
            
            closed_trades = [t for t in trades if t.get('closed', True)]
            logger.info(f"Closed trades: {len(closed_trades)}")
            
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
            logger.info(f"Winners: {len(winning_trades)}, Losers: {len(losing_trades)}")
            
            # Check consistency
            consistency = results.get('trades_equity_consistent', False)
            if not consistency:
                logger.warning("⚠️ Trade PnL doesn't match equity curve change - metrics may be inconsistent")
        else:
            logger.error("Optimization failed to return valid results")
            
        logger.info(f"Log file created: {log_file}")
        return 0
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
