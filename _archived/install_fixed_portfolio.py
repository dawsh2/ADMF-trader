#!/usr/bin/env python
"""
Install the fixed portfolio manager
"""
import os
import sys
import importlib
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("fix_installer")

def install_fixed_portfolio():
    """Install the fixed portfolio manager"""
    try:
        logger.info("Installing fixed portfolio manager")
        
        # Import the original portfolio manager
        from src.risk.portfolio.portfolio import PortfolioManager
        
        # Import the fixed implementation - we need to modify sys.path to find it
        sys.path.insert(0, os.path.abspath('.'))
        from src.risk.portfolio.fixed_portfolio import FixedPortfolioManager
        
        # Copy methods from fixed implementation to original class
        logger.info("Copying methods from fixed implementation to original class")
        
        # Methods to copy
        method_names = [
            'on_fill',
            'reset',
            'get_recent_trades',
            'update_equity',
            'on_bar',
            'get_equity_curve_df'
        ]
        
        for method_name in method_names:
            if hasattr(FixedPortfolioManager, method_name):
                logger.info(f"Installing fixed method: {method_name}")
                setattr(PortfolioManager, method_name, getattr(FixedPortfolioManager, method_name))
        
        # Now modify the __init__ method
        original_init = PortfolioManager.__init__
        
        def fixed_init(self, event_bus=None, name=None, initial_cash=10000.0):
            """Fixed initialization method"""
            # Call original init first
            original_init(self, event_bus, name, initial_cash)
            
            # Extra fixes for reliable trade tracking
            
            # 1. Create a trades list if not exists
            if not hasattr(self, 'trades') or self.trades is None:
                self.trades = []
                logger.info(f"Created new trades list with ID: {id(self.trades)}")
                
            # 2. Add trade registry as backup
            self._trade_registry = {}
            
            # 3. Add initial equity point
            self.equity_curve.append({
                'timestamp': datetime.datetime.now(),
                'equity': self.equity,
                'cash': self.cash,
                'positions_value': 0.0
            })
            
            logger.info(f"Enhanced portfolio manager initialized: {self._name}")
        
        # Install fixed init
        PortfolioManager.__init__ = fixed_init
        
        logger.info("Fixed portfolio manager successfully installed")
        return True
    except Exception as e:
        logger.error(f"Error installing fixed portfolio manager: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = install_fixed_portfolio()
    sys.exit(0 if success else 1)
