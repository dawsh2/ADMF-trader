"""
Hooks for adding functionality to the backtest coordinator.
"""

import logging
from src.execution.backtest.backtest_coordinator import BacktestCoordinator
from src.util.event_logger import EventLogger

logger = logging.getLogger(__name__)

def install_hooks():
    """Install hooks for debugging"""
    logger.info("Installing backtest hooks")
    
    # Store the original run method
    original_run = BacktestCoordinator.run
    
    # Create a new run method with debugging
    def debug_run(self, *args, **kwargs):
        logger.info(f"BACKTEST START: {self.name}")
        
        # Log components
        if hasattr(self, 'components'):
            logger.info(f"BACKTEST COMPONENTS:")
            for name, component in self.components.items():
                logger.info(f"  - {name}: {component.__class__.__name__}")
        
        # Check for symbols in data handler
        data_handler = None
        if hasattr(self, 'data_handler'):
            data_handler = self.data_handler
        elif hasattr(self, 'components') and 'data_handler' in self.components:
            data_handler = self.components['data_handler']
        
        if data_handler:
            logger.info(f"DATA HANDLER: {data_handler.__class__.__name__}")
            
            # Try to get symbols
            if hasattr(data_handler, 'get_symbols') and callable(data_handler.get_symbols):
                symbols = data_handler.get_symbols()
                logger.info(f"SYMBOLS: {symbols}")
            elif hasattr(data_handler, 'data') and isinstance(data_handler.data, dict):
                symbols = list(data_handler.data.keys())
                logger.info(f"SYMBOLS (from data keys): {symbols}")
            else:
                logger.warning("No symbols found in data handler")
        
        # Check for strategy
        strategy = None
        if hasattr(self, 'strategy'):
            strategy = self.strategy
        elif hasattr(self, 'components') and 'strategy' in self.components:
            strategy = self.components['strategy']
        elif hasattr(self, 'components') and 'strategy_adapter' in self.components:
            strategy_adapter = self.components['strategy_adapter']
            if hasattr(strategy_adapter, 'strategy'):
                strategy = strategy_adapter.strategy
        
        if strategy:
            logger.info(f"STRATEGY: {strategy.__class__.__name__}")
            
            # Check for symbols in strategy
            if hasattr(strategy, 'symbols'):
                logger.info(f"STRATEGY SYMBOLS: {strategy.symbols}")
            
            # Check for parameters
            if hasattr(strategy, 'parameters'):
                logger.info(f"STRATEGY PARAMETERS: {strategy.parameters}")
        
        # Attach event logger
        event_logger = EventLogger(self.event_bus, "backtest_event_logger")
        
        # Run the original method
        result = original_run(self, *args, **kwargs)
        
        # Print event summary
        if event_logger:
            event_logger.print_summary()
        
        logger.info(f"BACKTEST END: {self.name}")
        return result
    
    # Install the debug run method
    BacktestCoordinator.run = debug_run
    logger.info("Backtest hooks installed")
    
    return True
