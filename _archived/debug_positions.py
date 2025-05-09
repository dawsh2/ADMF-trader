#!/usr/bin/env python
"""
Debug script for tracking positions and signals during a backtest.

This script adds detailed logging of position management during the backtest
process to help identify issues with multiple positions and state leakage.
"""

import logging
import sys
import argparse
import os
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug_positions.log')
    ]
)
logger = logging.getLogger(__name__)

def setup_debug_hooks():
    """Set up debugging hooks in key components."""
    try:
        # Hook into signal processing
        from src.core.event_bus import Event, EventType
        
        # Save the original publish method
        original_publish = Event.publish if hasattr(Event, 'publish') else None
        
        # Define our debug wrapper
        def debug_publish(self, event_bus):
            # Log signal events
            if self.type == EventType.SIGNAL:
                data = self.get_data()
                logger.info(f"SIGNAL: symbol={data.get('symbol')}, direction={data.get('direction')}, "
                           f"rule_id={data.get('rule_id')}")
                
            # Log fill events
            elif self.type == EventType.FILL:
                data = self.get_data()
                logger.info(f"FILL: symbol={data.get('symbol')}, direction={data.get('direction')}, "
                           f"quantity={data.get('quantity')}, order_id={data.get('order_id')}")
                
            # Log trade events
            elif self.type == EventType.TRADE_OPEN:
                data = self.get_data()
                logger.info(f"TRADE_OPEN: symbol={data.get('symbol')}, direction={data.get('direction')}, "
                           f"id={data.get('id')}")
            elif self.type == EventType.TRADE_CLOSE:
                data = self.get_data()
                logger.info(f"TRADE_CLOSE: symbol={data.get('symbol')}, pnl={data.get('pnl')}, "
                           f"id={data.get('id')}")
                
            # Call the original method
            if original_publish:
                return original_publish(self, event_bus)
            else:
                # Fallback implementation
                event_bus._dispatch_event(self)
                
        # Replace the method if it exists
        if original_publish:
            Event.publish = debug_publish
            logger.info("Installed debug hooks for Event.publish")
        
        # Hook into portfolio position tracking
        from src.execution.portfolio import Portfolio
        
        # Save the original on_fill method
        original_on_fill = Portfolio.on_fill
        
        # Define our debug wrapper
        def debug_on_fill(self, event):
            # Log pre-fill positions
            logger.info(f"PRE-FILL POSITIONS: {self.positions}")
            
            # Call the original method
            result = original_on_fill(self, event)
            
            # Log post-fill positions
            logger.info(f"POST-FILL POSITIONS: {self.positions}")
            
            return result
            
        # Replace the method
        Portfolio.on_fill = debug_on_fill
        logger.info("Installed debug hooks for Portfolio.on_fill")
        
        # Hook into trade repository as well
        from src.core.trade_repository import TradeRepository
        
        # Save the original add_trade method
        original_add_trade = TradeRepository.add_trade
        
        # Define our debug wrapper
        def debug_add_trade(self, trade):
            # Call the original method
            result = original_add_trade(self, trade)
            
            # Log the trade
            logger.info(f"NEW TRADE: id={trade.get('id')}, symbol={trade.get('symbol')}, "
                      f"direction={trade.get('direction')}, quantity={trade.get('quantity')}")
            
            # Log open trades count
            open_count = sum(len(trades) for trades in self.open_trades.values())
            logger.info(f"OPEN TRADES COUNT: {open_count}")
            
            return result
            
        # Replace the method
        TradeRepository.add_trade = debug_add_trade
        logger.info("Installed debug hooks for TradeRepository.add_trade")
        
        # Also hook into the close_trade method
        original_close_trade = TradeRepository.close_trade
        
        # Define our debug wrapper
        def debug_close_trade(self, trade_id, close_price, close_time, quantity=None):
            # Log pre-close state
            logger.info(f"CLOSING TRADE: id={trade_id}, price={close_price}, time={close_time}, quantity={quantity}")
            
            # Call the original method
            result = original_close_trade(self, trade_id, close_price, close_time, quantity)
            
            # Log open trades count
            open_count = sum(len(trades) for trades in self.open_trades.values())
            logger.info(f"OPEN TRADES COUNT AFTER CLOSE: {open_count}")
            
            return result
            
        # Replace the method
        TradeRepository.close_trade = debug_close_trade
        logger.info("Installed debug hooks for TradeRepository.close_trade")
        
        return True
    except Exception as e:
        logger.error(f"Error setting up debug hooks: {e}")
        return False

def print_component_summary():
    """Print summary of components in the system."""
    try:
        # Import key components
        from src.core.component import Component
        from src.execution.backtest.backtest_coordinator import BacktestCoordinator
        
        # List all registered components
        logger.info(f"Components registered in system: {len(Component.registry)}")
        for name, component in Component.registry.items():
            logger.info(f"  - {name}: {component.__class__.__name__}")
        
        return True
    except Exception as e:
        logger.error(f"Error printing component summary: {e}")
        return False

def run_debug_backtest(config_file):
    """Run a backtest with debug logging."""
    try:
        # Set up debug hooks
        setup_debug_hooks()
        
        # Import required modules
        from src.execution.backtest.optimizing_backtest import OptimizingBacktest
        from src.strategy.optimization.optimizer import StrategyOptimizer
        
        # Load configuration
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Loaded configuration from {config_file}")
        logger.info(f"Risk configuration: {config.get('risk', {})}")
        
        # Create optimizer
        optimizer = StrategyOptimizer(config)
        
        # Run optimization
        logger.info("Starting optimization with debug logging")
        results = optimizer.optimize()
        
        # Print result summary
        logger.info(f"Optimization completed with {len(results.get('trades', []))} trades")
        logger.info(f"Final capital: {results.get('final_capital', 0)}")
        logger.info(f"Return percentage: {results.get('statistics', {}).get('return_pct', 0)}%")
        
        # Print any warnings
        if not results.get('trades_equity_consistent', True):
            logger.warning("⚠️ Trade PnL doesn't match equity curve change")
        
        # Print position counts
        from collections import Counter
        position_counts = Counter()
        for trade in results.get('trades', []):
            symbol = trade.get('symbol', 'unknown')
            position_counts[symbol] += 1
        
        logger.info(f"Position counts by symbol: {dict(position_counts)}")
        
        return True
    except Exception as e:
        logger.error(f"Error running debug backtest: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main entry point for the debug script."""
    parser = argparse.ArgumentParser(description="Debug ADMF-Trader position management")
    parser.add_argument("--config", default="config/ma_crossover_optimization.yaml", 
                      help="Path to configuration file")
    
    args = parser.parse_args()
    
    logger.info("Starting ADMF-Trader debug script")
    logger.info(f"Using configuration file: {args.config}")
    
    try:
        # Check if the configuration file exists
        if not os.path.exists(args.config):
            logger.error(f"Configuration file not found: {args.config}")
            return 1
        
        # Print component summary
        print_component_summary()
        
        # Run debug backtest
        success = run_debug_backtest(args.config)
        
        if success:
            logger.info("Debug backtest completed successfully")
        else:
            logger.error("Debug backtest failed")
            return 1
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
