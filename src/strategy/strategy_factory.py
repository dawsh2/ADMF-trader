"""
Robust strategy factory for reliable strategy discovery and instantiation.

This implementation fixes the strategy discovery issue by providing
clearer error messages and more robust strategy lookup.
"""

import importlib
import inspect
import os
import sys
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategyFactory:
    """
    Factory for creating strategy instances.
    
    This implementation provides more robust strategy discovery and
    better error handling.
    """
    
    def __init__(self, strategy_dirs=None):
        """
        Initialize the strategy factory.
        
        Args:
            strategy_dirs (list, optional): Directories to search for strategies
        """
        self.strategy_dirs = strategy_dirs or []
        self.strategies = {}
        self.strategy_modules = {}
        
        # Add default strategy directory
        default_dir = os.path.join(os.path.dirname(__file__), 'implementations')
        if os.path.exists(default_dir) and default_dir not in self.strategy_dirs:
            self.strategy_dirs.append(default_dir)
            
        # Discovery strategies
        self._discover_strategies()
        
    def _discover_strategies(self):
        """Discover available strategies in strategy directories."""
        for directory in self.strategy_dirs:
            self._discover_strategies_in_dir(directory)
            
    def _discover_strategies_in_dir(self, directory):
        """
        Discover strategies in a directory.
        
        Args:
            directory (str): Directory to search
        """
        # Check if directory exists
        if not os.path.exists(directory) or not os.path.isdir(directory):
            logger.warning(f"Strategy directory not found: {directory}")
            return
            
        # Get all Python files in the directory
        strategy_files = list(Path(directory).glob('**/*.py'))
        
        # Add the directory to the Python path if not already there
        if directory not in sys.path:
            sys.path.insert(0, directory)
            
        # Import each file and look for strategies
        for file_path in strategy_files:
            # Skip __init__.py and private files
            if file_path.name.startswith('_'):
                continue
                
            # Generate module name from file path
            # Remove .py extension and replace / with .
            rel_path = os.path.relpath(file_path, directory)
            module_name = os.path.splitext(rel_path)[0].replace(os.sep, '.')
            
            try:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Look for strategy classes in the module
                self._register_strategies_from_module(module, module_name)
                
            except Exception as e:
                logger.error(f"Error importing strategy module {module_name}: {e}")
                
    def _register_strategies_from_module(self, module, module_name):
        """
        Register strategies from a module.
        
        Args:
            module (module): Module to search for strategies
            module_name (str): Name of the module
        """
        # Find all classes in the module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Skip imported classes
            if obj.__module__ != module_name:
                continue
                
            # Check if the class has a 'is_strategy' attribute or follows naming convention
            if hasattr(obj, 'is_strategy') or 'strategy' in name.lower():
                # Generate strategy name from class name (convert CamelCase to snake_case)
                strategy_name = self._class_name_to_strategy_name(name)
                
                # Log discovery
                logger.info(f"Discovered strategy: {strategy_name} from {module_name}.{name}")
                
                # Store the strategy class
                self.strategies[strategy_name] = obj
                self.strategy_modules[strategy_name] = module
                
                # Also register under the original class name as a fallback
                if name.lower() not in self.strategies:
                    self.strategies[name.lower()] = obj
                    self.strategy_modules[name.lower()] = module
                    
    def _class_name_to_strategy_name(self, class_name):
        """
        Convert class name to strategy name.
        
        Args:
            class_name (str): Class name in CamelCase
            
        Returns:
            str: Strategy name in snake_case
        """
        # Handle known strategy names explicitly
        name_map = {
            'SimpleMovingAverageCrossoverStrategy': 'simple_ma_crossover',
            'MovingAverageCrossoverStrategy': 'ma_crossover',
            'SimpleMACrossoverStrategy': 'simple_ma_crossover',
            'RSIStrategy': 'rsi'
            # Add more mappings as needed
        }
        
        if class_name in name_map:
            return name_map[class_name]
            
        # Convert CamelCase to snake_case
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        strategy_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
        # Remove "strategy" suffix if present
        strategy_name = strategy_name.replace('_strategy', '')
        
        return strategy_name
        
    def get_strategy_names(self):
        """
        Get names of available strategies.
        
        Returns:
            list: Names of available strategies
        """
        return list(self.strategies.keys())
        
    def create_strategy(self, strategy_name, **kwargs):
        """
        Create a strategy instance with proper dependency handling.
        
        Args:
            strategy_name (str): Name of the strategy to create
            **kwargs: Arguments to pass to the strategy constructor
            
        Returns:
            object: Strategy instance
            
        Raises:
            ValueError: If the strategy is not found
        """
        # Try exact match first
        strategy_class = self.strategies.get(strategy_name)
        
        if not strategy_class:
            # Try case-insensitive match
            for name, cls in self.strategies.items():
                if name.lower() == strategy_name.lower():
                    strategy_class = cls
                    break
                    
        if not strategy_class:
            # If still not found, try partial match
            matches = [name for name in self.strategies.keys() 
                     if strategy_name.lower() in name.lower()]
            
            if len(matches) == 1:
                strategy_class = self.strategies[matches[0]]
            elif len(matches) > 1:
                raise ValueError(f"Multiple strategies match '{strategy_name}': {matches}")
                
        if not strategy_class:
            # Give detailed error message
            available = ", ".join(self.get_strategy_names())
            raise ValueError(f"Strategy '{strategy_name}' not found. Available strategies: {available}")
            
        # Collect required arguments for this class
        import inspect
        sig = inspect.signature(strategy_class.__init__)
        params = sig.parameters
        required_params = {}
        optional_params = {}
        
        # Skip 'self' parameter
        for name, param in list(params.items())[1:]:
            # Required parameters have no default
            if param.default == inspect.Parameter.empty:
                if name in kwargs:
                    required_params[name] = kwargs[name]
                else:
                    # This is a required param not in kwargs
                    logger.warning(f"Required parameter '{name}' for {strategy_class.__name__} not provided")
            else:
                # Optional parameter with default value
                if name in kwargs:
                    optional_params[name] = kwargs[name]
                # Otherwise use default value from signature
        
        # Add remaining kwargs to optional params (they might be for setting later)
        remaining_kwargs = {k: v for k, v in kwargs.items() 
                          if k not in required_params and k not in optional_params}
        
        # Create and return the strategy instance
        try:
            # First try with all provided kwargs
            return strategy_class(**required_params, **optional_params)
        except Exception as e1:
            logger.warning(f"Failed to create {strategy_class.__name__} with all params: {e1}")
            try:
                # Try with only required params
                strategy = strategy_class(**required_params)
                
                # Now try to set optional parameters one by one
                for name, value in {**optional_params, **remaining_kwargs}.items():
                    try:
                        # Try direct attribute setting
                        if hasattr(strategy, name):
                            setattr(strategy, name, value)
                        # Try setting via parameters dict if available
                        elif hasattr(strategy, 'parameters') and isinstance(strategy.parameters, dict):
                            strategy.parameters[name] = value
                    except Exception as e3:
                        logger.warning(f"Could not set {name}={value} on strategy: {e3}")
                        
                return strategy
            except Exception as e2:
                raise ValueError(f"Error creating strategy '{strategy_name}': {e2}")
            
    def print_debug_info(self):
        """Print debug information about the factory."""
        logger.info("=== Strategy Factory Debug Info ===")
        logger.info(f"Strategy directories: {self.strategy_dirs}")
        logger.info(f"Found {len(self.strategies)} strategies")
        
        for name, cls in self.strategies.items():
            module_name = cls.__module__
            logger.info(f"  - {name}: {module_name}.{cls.__name__}")
            
        logger.info("===================================")
