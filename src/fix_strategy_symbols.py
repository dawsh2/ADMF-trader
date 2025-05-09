import logging
import importlib
import os
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_strategy_symbols.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fix_symbols')

def fix_ma_crossover_strategy():
    """Fix the MA Crossover strategy to properly handle symbols"""
    
    # Find all potential strategy implementations
    implementations_dir = os.path.join('src', 'strategy', 'implementations')
    strategy_files = []
    
    # Search in main implementations directory
    for file in os.listdir(implementations_dir):
        if file.endswith('.py') and 'ma_crossover' in file.lower():
            strategy_files.append(os.path.join(implementations_dir, file))
    
    # Search in backup directory
    backup_dir = os.path.join(implementations_dir, 'backup')
    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            if file.endswith('.py') and 'ma_crossover' in file.lower():
                strategy_files.append(os.path.join(backup_dir, file))
    
    logger.info(f"Found {len(strategy_files)} MA Crossover strategy files: {strategy_files}")
    
    # Fix each file
    for strategy_file in strategy_files:
        logger.info(f"Checking strategy file: {strategy_file}")
        
        # Read the file
        with open(strategy_file, 'r') as f:
            content = f.read()
        
        # Make a backup
        with open(f"{strategy_file}.bak.fix", 'w') as f:
            f.write(content)
        
        # Check if the file initializes symbols properly
        if 'self.symbols = self.parameters.get(\'symbols\'' in content:
            logger.info(f"Strategy already initializes symbols from parameters")
            
            # Check if it handles symbols from data handler properly
            if 'if hasattr(data_handler, \'get_symbols\')' in content:
                logger.info(f"Strategy already handles symbols from data handler")
            else:
                # Add better symbol handling
                new_content = content.replace(
                    'self.symbols = self.parameters.get(\'symbols\', [])',
                    """self.symbols = self.parameters.get('symbols', [])
        
        # Get symbols from data handler if available and needed
        if not self.symbols and hasattr(data_handler, 'get_symbols') and callable(data_handler.get_symbols):
            try:
                handler_symbols = data_handler.get_symbols()
                if handler_symbols:
                    self.symbols = handler_symbols
                    logger.info(f"Got symbols from data handler: {self.symbols}")
            except Exception as e:
                logger.warning(f"Error getting symbols from data handler: {e}")
                
        # As a fallback, check if data handler has a data dictionary with keys as symbols
        if not self.symbols and hasattr(data_handler, 'data') and isinstance(data_handler.data, dict):
            self.symbols = list(data_handler.data.keys())
            logger.info(f"Got symbols from data handler data keys: {self.symbols}")
                    
        # Final fallback - use backtest symbols if available
        if not self.symbols and hasattr(data_handler, 'data_config') and isinstance(data_handler.data_config, dict):
            sources = data_handler.data_config.get('sources', [])
            if sources:
                self.symbols = [source.get('symbol') for source in sources if source.get('symbol')]
                logger.info(f"Got symbols from data config sources: {self.symbols}")"""
                )
                
                # Write the modified content
                with open(strategy_file, 'w') as f:
                    f.write(new_content)
                
                logger.info(f"Added better symbol handling to {strategy_file}")
        
        # Check if the file initializes parameters properly in __init__
        if '__init__' in content and not 'self.symbols =' in content:
            # Add symbols initialization
            new_content = content.replace(
                'def __init__(self, event_bus, data_handler, name=None, parameters=None):',
                """def __init__(self, event_bus, data_handler, name=None, parameters=None):
        # Added logger for debugging
        import logging
        global logger
        logger = logging.getLogger(__name__)
        logger.debug(f"Initializing strategy with parameters: {parameters}")"""
            )
            
            # Add symbols initialization after parameters
            if 'self.parameters = parameters or {}' in new_content:
                new_content = new_content.replace(
                    'self.parameters = parameters or {}',
                    """self.parameters = parameters or {}
        
        # Initialize symbols - check different sources
        self.symbols = self.parameters.get('symbols', [])
        
        # Get symbols from data handler if available and needed
        if not self.symbols and hasattr(data_handler, 'get_symbols') and callable(data_handler.get_symbols):
            try:
                handler_symbols = data_handler.get_symbols()
                if handler_symbols:
                    self.symbols = handler_symbols
                    logger.debug(f"Got symbols from data handler: {self.symbols}")
            except Exception as e:
                logger.warning(f"Error getting symbols from data handler: {e}")
                
        # As a fallback, check if data handler has a data dictionary with keys as symbols
        if not self.symbols and hasattr(data_handler, 'data') and isinstance(data_handler.data, dict):
            self.symbols = list(data_handler.data.keys())
            logger.debug(f"Got symbols from data handler data keys: {self.symbols}")
                    
        # Final fallback - hardcode symbol if nothing else works
        if not self.symbols:
            self.symbols = ['HEAD']  # Default symbol
            logger.debug(f"Using default symbol: {self.symbols}")"""
                )
            
            # Write the modified content
            with open(strategy_file, 'w') as f:
                f.write(new_content)
            
            logger.info(f"Added symbols initialization to {strategy_file}")
        
        # Fix the on_bar method to avoid ignoring symbols we don't know about
        if 'on_bar' in content and 'if symbol not in self.symbols:' in content:
            # Replace the "skip if not in symbols" check with a more resilient approach
            new_content = content.replace(
                "if symbol not in self.symbols:",
                """# If this symbol isn't in our list, add it
        if symbol not in self.symbols:
            logger.info(f"Adding new symbol {symbol} to strategy symbols list")
            self.symbols.append(symbol)
            
        # Legacy code - keeping commented out for reference
        # if symbol not in self.symbols:"""
            )
            
            # Write the modified content
            with open(strategy_file, 'w') as f:
                f.write(new_content)
            
            logger.info(f"Fixed on_bar method in {strategy_file} to accept new symbols")

def force_config_symbols():
    """Create a fixed optimization config with explicit symbols"""
    config_content = """# ma_crossover_fixed_symbols.yaml
# Fixed configuration for MA crossover optimization with explicit symbols

strategy:
  name: ma_crossover
  parameters:
    fast_window: 5
    slow_window: 20
    symbols: ['HEAD']  # Explicitly specify symbol in strategy parameters

risk:
  position_manager:
    config:
      fixed_quantity: 10
      max_positions: 1
      enforce_single_position: true
      position_sizing_method: fixed
      allow_multiple_entries: false

backtest:
  initial_capital: 100000.0
  symbols: ['HEAD']  # Trading the HEAD symbol
  timeframe: 1min    # Using 1-minute data

data:
  source_type: csv
  sources:
    - symbol: HEAD
      file: data/HEAD_1min.csv
      date_column: timestamp
      price_column: Close
      date_format: "%Y-%m-%d %H:%M:%S"

optimization:
  objective: sharpe_ratio
  method: grid
  
# Only test a few combinations for faster results
parameter_space:
  - name: fast_window
    type: integer
    min: 5
    max: 10
    step: 5
    description: "Fast moving average window"
  - name: slow_window
    type: integer
    min: 20
    max: 40
    step: 20
    description: "Slow moving average window"
"""
    
    config_path = "config/ma_crossover_fixed_symbols.yaml"
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        logger.info(f"Created fixed config with explicit symbols at {config_path}")
        return config_path
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        return None