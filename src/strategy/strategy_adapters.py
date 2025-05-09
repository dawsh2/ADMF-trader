"""
Strategy adapters to make various strategy implementations compatible
with the Component-based architecture used in the backtest system.
"""

import logging
from src.core.component import Component

logger = logging.getLogger(__name__)

class StrategyAdapter(Component):
    """
    Adapter to make any strategy compatible with the Component-based architecture.
    
    This adapter wraps a strategy instance and provides the required Component
    interface methods (initialize, start, stop, reset).
    """
    
    def __init__(self, name, strategy_instance):
        """
        Initialize the adapter.
        
        Args:
            name (str): Component name
            strategy_instance: Strategy instance to adapt
        """
        super().__init__(name)
        self.strategy = strategy_instance
        logger.info(f"Created StrategyAdapter for {strategy_instance.__class__.__name__}")
        
    def initialize(self, context):
        """
        Initialize the strategy with dependencies.
        
        Args:
            context (dict): Context containing dependencies
        """
        # Initialize parent first
        super().initialize(context)
        
        # Set critical dependencies on the strategy
        if hasattr(self.strategy, 'event_bus') and context.get('event_bus'):
            self.strategy.event_bus = context.get('event_bus')
            # Also register/subscribe to events if needed
            if hasattr(self.strategy, 'on_bar'):
                from src.core.events.event_types import EventType
                # Handle both register and subscribe methods
                if hasattr(self.strategy.event_bus, 'subscribe'):
                    self.strategy.event_bus.subscribe(EventType.BAR, self.strategy.on_bar)
                    logger.info(f"Subscribed strategy to BAR events")
                elif hasattr(self.strategy.event_bus, 'register'):
                    self.strategy.event_bus.register(EventType.BAR, self.strategy.on_bar)
                    logger.info(f"Registered strategy for BAR events")
                
        if hasattr(self.strategy, 'data_handler') and context.get('data_handler'):
            self.strategy.data_handler = context.get('data_handler')
            
        # Check for symbols in the data handler
        data_handler = context.get('data_handler')
        if data_handler:
            # Try to get symbols from data_handler
            symbols = None
            
            # First, try get_symbols method
            if hasattr(data_handler, 'get_symbols') and callable(data_handler.get_symbols):
                symbols = data_handler.get_symbols()
                logger.info(f"Available symbols in data_handler: {symbols}")
                
                # Pass symbols to strategy if it has a symbols attribute
                if hasattr(self.strategy, 'symbols'):
                    if not self.strategy.symbols and symbols:
                        self.strategy.symbols = symbols
                        logger.info(f"Updated strategy symbols: {self.strategy.symbols}")
                    elif self.strategy.symbols:
                        logger.info(f"Strategy already has symbols: {self.strategy.symbols}")
            else:
                # Try to get symbols from data property
                if hasattr(data_handler, 'data') and isinstance(data_handler.data, dict):
                    symbols = list(data_handler.data.keys())
                    logger.info(f"Got symbols from data_handler.data keys: {symbols}")
                    
                    # Pass symbols to strategy if it has a symbols attribute
                    if hasattr(self.strategy, 'symbols'):
                        if not self.strategy.symbols and symbols:
                            self.strategy.symbols = symbols
                            logger.info(f"Updated strategy symbols from data keys: {self.strategy.symbols}")
                        elif self.strategy.symbols:
                            logger.info(f"Strategy already has symbols: {self.strategy.symbols}")
                    
                # Final fallback - check for backtest configuration
                elif hasattr(data_handler, 'data_config') and isinstance(data_handler.data_config, dict):
                    # Try to extract symbols from the configuration
                    sources = data_handler.data_config.get('sources', [])
                    if sources:
                        symbols = [source.get('symbol') for source in sources if source.get('symbol')]
                        if symbols:
                            logger.info(f"Got symbols from data_config sources: {symbols}")
                            
                            # Pass symbols to strategy if it has a symbols attribute
                            if hasattr(self.strategy, 'symbols'):
                                if not self.strategy.symbols and symbols:
                                    self.strategy.symbols = symbols
                                    logger.info(f"Updated strategy symbols from config sources: {self.strategy.symbols}")
                                elif self.strategy.symbols:
                                    logger.info(f"Strategy already has symbols: {self.strategy.symbols}")
                
                # If we still don't have symbols, try to get from context or config
                if not symbols and context:
                    if 'config' in context and isinstance(context['config'], dict):
                        config_symbols = context['config'].get('symbols')
                        if config_symbols:
                            symbols = config_symbols
                            logger.info(f"Got symbols from context config: {symbols}")
                            
                            # Pass symbols to strategy if it has a symbols attribute
                            if hasattr(self.strategy, 'symbols'):
                                if not self.strategy.symbols and symbols:
                                    self.strategy.symbols = symbols
                                    logger.info(f"Updated strategy symbols from context config: {self.strategy.symbols}")
                                elif self.strategy.symbols:
                                    logger.info(f"Strategy already has symbols: {self.strategy.symbols}")
                
                # If still no symbols, use default symbol
                if not symbols:
                    logger.warning("Data handler has no get_symbols method or no symbols available")
                    
                    # Use predefined symbols from the strategy
                    if hasattr(self.strategy, 'symbols') and self.strategy.symbols:
                        logger.info(f"Using strategy's predefined symbols: {self.strategy.symbols}")
                    # Use default symbol as last resort
                    elif hasattr(self.strategy, 'symbols'):
                        default_symbol = "HEAD"  # Using HEAD as the default symbol
                        self.strategy.symbols = [default_symbol]
                        logger.info(f"Using default symbol: {default_symbol}")
            
        # Call strategy's initialize method if it exists
        if hasattr(self.strategy, 'initialize') and callable(getattr(self.strategy, 'initialize')):
            try:
                self.strategy.initialize(context)
                logger.info(f"Called strategy's initialize method")
            except Exception as e:
                logger.warning(f"Error calling strategy's initialize method: {e}")
                
        logger.info(f"Initialized strategy adapter for {self.strategy.__class__.__name__}")
        
    def start(self):
        """Start the strategy."""
        super().start()
        
        # Call strategy's start method if it exists
        if hasattr(self.strategy, 'start') and callable(getattr(self.strategy, 'start')):
            try:
                self.strategy.start()
                logger.info(f"Called strategy's start method")
            except Exception as e:
                logger.warning(f"Error calling strategy's start method: {e}")
                
        logger.info(f"Started strategy adapter for {self.strategy.__class__.__name__}")
        
    def stop(self):
        """Stop the strategy."""
        super().stop()
        
        # Call strategy's stop method if it exists
        if hasattr(self.strategy, 'stop') and callable(getattr(self.strategy, 'stop')):
            try:
                self.strategy.stop()
                logger.info(f"Called strategy's stop method")
            except Exception as e:
                logger.warning(f"Error calling strategy's stop method: {e}")
                
        logger.info(f"Stopped strategy adapter for {self.strategy.__class__.__name__}")
        
    def reset(self):
        """Reset the strategy state."""
        super().reset()
        
        # Call strategy's reset method if it exists
        if hasattr(self.strategy, 'reset') and callable(getattr(self.strategy, 'reset')):
            try:
                self.strategy.reset()
                logger.info(f"Called strategy's reset method")
            except Exception as e:
                logger.warning(f"Error calling strategy's reset method: {e}")
                
        logger.info(f"Reset strategy adapter for {self.strategy.__class__.__name__}")
