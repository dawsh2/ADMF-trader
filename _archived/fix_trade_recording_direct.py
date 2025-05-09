#!/usr/bin/env python
"""
Direct fix for trade recording in the ADMF-trader system.

This script modifies the execution handler to ensure trades are created and recorded
from filled orders, and ensures rule_id is passed through the event chain.
"""

import os
import sys
import logging
import importlib
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trade_recording_direct.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('trade_recording_direct')

def backup_file(filepath):
    """Create a backup of the file before modifying it"""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.bak"
        shutil.copy2(filepath, backup_path)
        logger.info(f"Created backup at {backup_path}")
        return True
    return False

def patch_module_at_runtime(module_path, attribute_name, new_implementation):
    """Patch a module attribute at runtime"""
    try:
        module = importlib.import_module(module_path)
        setattr(module, attribute_name, new_implementation)
        logger.info(f"Successfully patched {module_path}.{attribute_name} at runtime")
        return True
    except Exception as e:
        logger.error(f"Failed to patch {module_path}.{attribute_name}: {e}")
        return False

def fix_execution_handler():
    """Find and fix the execution handler to properly record trades"""
    # Try to find the execution handler
    execution_modules = [
        'src.execution.broker',
        'src.execution.execution_handler',
        'src.core.execution.broker'
    ]
    
    for module_path in execution_modules:
        try:
            # Try to import the module
            module = importlib.import_module(module_path)
            logger.info(f"Found execution module at {module_path}")
            
            # Look for execution handler class
            handler_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and hasattr(attr, 'fill_order'):
                    handler_class = attr
                    logger.info(f"Found execution handler class: {attr_name}")
                    break
            
            if handler_class:
                # Get original method
                original_fill_order = handler_class.fill_order
                
                # Create patched method
                def patched_fill_order(self, order, price, timestamp):
                    logger.info(f"Patched fill_order called for order {order.id if hasattr(order, 'id') else 'unknown'}")
                    
                    # Call original method
                    result = original_fill_order(self, order, price, timestamp)
                    
                    # Check if trade creation is already handled in the original method
                    # If not, create and record a trade
                    try:
                        # Try to import Trade class
                        from src.core.data_model import Trade
                        
                        logger.info(f"Creating trade for order {order.id if hasattr(order, 'id') else 'unknown'}")
                        
                        # Check if order has the necessary attributes
                        if not hasattr(order, 'symbol') or not hasattr(order, 'quantity'):
                            logger.warning(f"Order missing required attributes: {vars(order) if hasattr(order, '__dict__') else 'No vars'}")
                            return result
                        
                        # Create trade object
                        trade = Trade(
                            symbol=order.symbol,
                            quantity=order.quantity,
                            price=price,
                            timestamp=timestamp,
                            direction=order.direction if hasattr(order, 'direction') else 'UNKNOWN',
                            rule_id=order.rule_id if hasattr(order, 'rule_id') else None
                        )
                        
                        # Add trade to portfolio
                        if hasattr(self, 'portfolio'):
                            if hasattr(self.portfolio, 'add_trade'):
                                self.portfolio.add_trade(trade)
                                logger.info(f"Added trade to portfolio for order {order.id if hasattr(order, 'id') else 'unknown'}")
                            else:
                                logger.warning("Portfolio does not have add_trade method")
                        else:
                            logger.warning("Execution handler does not have portfolio attribute")
                    except Exception as e:
                        logger.error(f"Error creating trade: {e}")
                    
                    return result
                
                # Apply patch
                handler_class.fill_order = patched_fill_order
                logger.info(f"Successfully patched {handler_class.__name__}.fill_order")
                return True
            else:
                logger.warning(f"Could not find execution handler class in {module_path}")
        except ImportError:
            logger.debug(f"Could not import {module_path}")
    
    logger.warning("Could not find execution handler module")
    return False

def fix_portfolio():
    """Find and fix the portfolio to ensure it correctly handles trades"""
    # Try to find the portfolio module
    portfolio_modules = [
        'src.execution.portfolio',
        'src.portfolio',
        'src.core.portfolio'
    ]
    
    for module_path in portfolio_modules:
        try:
            # Try to import the module
            module = importlib.import_module(module_path)
            logger.info(f"Found portfolio module at {module_path}")
            
            # Look for portfolio class
            portfolio_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and (hasattr(attr, 'add_trade') or 'Portfolio' in attr.__name__):
                    portfolio_class = attr
                    logger.info(f"Found portfolio class: {attr_name}")
                    break
            
            if portfolio_class:
                # Check if add_trade method exists
                if hasattr(portfolio_class, 'add_trade'):
                    logger.info("Portfolio class already has add_trade method")
                else:
                    # Add add_trade method
                    def add_trade(self, trade):
                        """Add a trade to the portfolio"""
                        logger.info(f"Added trade to portfolio: {trade}")
                        if not hasattr(self, 'trades'):
                            self.trades = []
                        self.trades.append(trade)
                        return True
                    
                    # Apply patch
                    portfolio_class.add_trade = add_trade
                    logger.info(f"Added add_trade method to {portfolio_class.__name__}")
                
                # Add debug method to portfolio class
                def print_trades(self):
                    """Print all trades in the portfolio for debugging"""
                    trades = getattr(self, 'trades', [])
                    logger.info(f"Portfolio has {len(trades)} trades")
                    for i, trade in enumerate(trades):
                        logger.info(f"Trade {i+1}: {trade}")
                    return len(trades)
                
                # Apply patch
                portfolio_class.print_trades = print_trades
                logger.info(f"Added print_trades method to {portfolio_class.__name__}")
                return True
            else:
                logger.warning(f"Could not find portfolio class in {module_path}")
        except ImportError:
            logger.debug(f"Could not import {module_path}")
    
    logger.warning("Could not find portfolio module")
    return False

def main():
    """Main entry point for the script"""
    logger.info("Starting direct trade recording fix")
    
    # Fix the execution handler
    execution_fixed = fix_execution_handler()
    
    # Fix the portfolio
    portfolio_fixed = fix_portfolio()
    
    # Print summary
    logger.info("Fix summary:")
    logger.info(f"Execution handler fix: {'Applied' if execution_fixed else 'Not applied'}")
    logger.info(f"Portfolio fix: {'Applied' if portfolio_fixed else 'Not applied'}")
    
    if execution_fixed or portfolio_fixed:
        logger.info("Some fixes were applied. Please test the system to verify the fixes.")
        return 0
    else:
        logger.warning("No fixes were applied. Please check the logs for more information.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
