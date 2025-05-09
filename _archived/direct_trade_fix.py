#!/usr/bin/env python
"""
Direct trade recording fix for ADMF-trader.

This script focuses exclusively on ensuring trades are created and recorded
when orders are filled, by directly intervening in the trade repository.
"""

import os
import sys
import logging
import importlib
import inspect
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("direct_trade_fix.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('direct_trade_fix')

def find_class_in_module(module, class_name_partial):
    """Find a class in a module based on partial name matching"""
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and class_name_partial.lower() in name.lower():
            logger.info(f"Found class {name} in module {module.__name__}")
            return obj
    return None

def find_module_by_name(name_partial):
    """Find a module based on partial name matching"""
    for module_name in list(sys.modules.keys()):
        if name_partial.lower() in module_name.lower():
            logger.info(f"Found module {module_name}")
            return sys.modules[module_name]
    return None

def create_mock_trade_class():
    """Create a mock Trade class if one can't be found"""
    class MockTrade:
        def __init__(self, symbol, quantity, price, timestamp, direction, rule_id=None):
            self.symbol = symbol
            self.quantity = quantity
            self.price = price
            self.timestamp = timestamp
            self.direction = direction
            self.rule_id = rule_id
            
        def __repr__(self):
            return f"Trade(symbol={self.symbol}, quantity={self.quantity}, price={self.price}, direction={self.direction}, rule_id={self.rule_id})"
    
    logger.info("Created mock Trade class")
    return MockTrade

def insert_trades_directly():
    """Insert trades directly into the trade repository or portfolio"""
    try:
        # Try to find the trade repository
        trade_repo = None
        repo_module = None
        
        # Try to find modules related to trade repository
        possible_modules = [
            'src.execution.trade_repository',
            'src.core.trade_repository',
            'src.trade_repository',
            'src.repository',
            'src.execution.repository'
        ]
        
        for module_name in possible_modules:
            try:
                repo_module = importlib.import_module(module_name)
                logger.info(f"Found repository module: {module_name}")
                break
            except ImportError:
                continue
        
        if not repo_module:
            # Try to find by searching loaded modules
            repo_module = find_module_by_name('repository')
            
        if repo_module:
            # Find the repository class
            repo_class = find_class_in_module(repo_module, 'repository')
            
            if repo_class:
                # Try to get the singleton instance if it exists
                if hasattr(repo_class, 'get_instance'):
                    trade_repo = repo_