"""
Logging configuration for ADMF-Trader.

This module provides centralized logging configuration with features for:
1. Controlling global log level
2. Setting module-specific log levels
3. Directing logs to files or console
4. Supporting debug mode for additional verbosity
"""

import logging
import os
import sys
from typing import Dict, Optional, List, Set, Any

# Default logs directory
DEFAULT_LOGS_DIR = "logs"

# Module name prefixes
CORE_PREFIX = "src.core"
DATA_PREFIX = "src.data"
STRATEGY_PREFIX = "src.strategy"
RISK_PREFIX = "src.risk"
EXECUTION_PREFIX = "src.execution"
ANALYTICS_PREFIX = "src.analytics"

# Log format with timestamps, level, and module information
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SIMPLE_FORMAT = "%(levelname)s - %(message)s"

class LoggingConfig:
    """
    Manages logging configuration for the entire system.
    
    Features:
    - Global log level setting
    - Module-specific log levels
    - Console and/or file logging
    - Debug mode for verbose output
    """
    
    def __init__(self):
        """Initialize the logging configuration with defaults."""
        # Module-specific log levels
        self.module_levels: Dict[str, int] = {
            CORE_PREFIX: logging.INFO,
            DATA_PREFIX: logging.INFO,
            STRATEGY_PREFIX: logging.INFO,
            RISK_PREFIX: logging.INFO,
            EXECUTION_PREFIX: logging.INFO,
            ANALYTICS_PREFIX: logging.INFO,
            "root": logging.WARNING
        }
        
        # Default settings
        self.log_to_console = True
        self.log_to_file = False
        self.log_file_path = None
        self.log_format = DEFAULT_FORMAT
        self.debug_mode = False
        self.debug_modules: Set[str] = set()
        
    def set_debug_mode(self, debug: bool = True, modules: Optional[List[str]] = None) -> None:
        """
        Set debug mode globally or for specific modules.
        
        Args:
            debug: Whether to enable debug mode
            modules: Optional list of module prefixes to enable debug for (e.g., 'src.core.event_system')
                     If None, debug is enabled for all modules
        """
        self.debug_mode = debug
        
        if debug:
            # Set all modules to DEBUG level if no specific modules provided
            if not modules:
                for module in self.module_levels:
                    self.module_levels[module] = logging.DEBUG
                    self.debug_modules.add(module)
                # Apply the levels to existing loggers
                for logger_name in logging.root.manager.loggerDict:
                    logging.getLogger(logger_name).setLevel(logging.DEBUG)
            else:
                # Set specific modules to DEBUG level
                for module in modules:
                    self.module_levels[module] = logging.DEBUG
                    self.debug_modules.add(module)
                    # Apply the level to existing loggers matching this module
                    for logger_name in logging.root.manager.loggerDict:
                        if logger_name.startswith(module):
                            logging.getLogger(logger_name).setLevel(logging.DEBUG)
        else:
            # Reset debug modules to INFO level
            for module in self.debug_modules:
                self.module_levels[module] = logging.INFO
                # Apply the level to existing loggers matching this module
                for logger_name in logging.root.manager.loggerDict:
                    if logger_name.startswith(module):
                        logging.getLogger(logger_name).setLevel(logging.INFO)
            self.debug_modules.clear()
    
    def configure_logging(self, log_file: Optional[str] = None) -> None:
        """
        Configure the logging system based on current settings.
        
        Args:
            log_file: Optional file path for logging output
        """
        # Reset existing logging configuration
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Set root logger level
        root_logger.setLevel(self.module_levels.get("root", logging.WARNING))
        
        # Create formatter
        formatter = logging.Formatter(self.log_format)
        
        # Configure console logging if enabled
        if self.log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # Configure file logging if enabled
        if self.log_to_file or log_file:
            # Use provided log file or default
            log_path = log_file or self.log_file_path
            
            if log_path:
                # Ensure logs directory exists
                log_dir = os.path.dirname(log_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                    
                file_handler = logging.FileHandler(log_path)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
        
        # Set module-specific log levels
        for module_prefix, level in self.module_levels.items():
            if module_prefix != "root":
                logging.getLogger(module_prefix).setLevel(level)
    
    def set_module_level(self, module: str, level: int) -> None:
        """
        Set the log level for a specific module.
        
        Args:
            module: Module name or prefix
            level: Logging level (e.g., logging.DEBUG, logging.INFO)
        """
        self.module_levels[module] = level
        logging.getLogger(module).setLevel(level)
    
    def get_module_level(self, module: str) -> int:
        """
        Get the log level for a specific module.
        
        Args:
            module: Module name or prefix
            
        Returns:
            int: Logging level
        """
        # Check exact match
        if module in self.module_levels:
            return self.module_levels[module]
            
        # Check prefix match
        for prefix, level in self.module_levels.items():
            if module.startswith(prefix):
                return level
                
        # Default to root logger level
        return self.module_levels.get("root", logging.WARNING)
        
    def log_to_file_only(self, log_file: str) -> None:
        """
        Configure logging to go to a file only (not console).
        
        Args:
            log_file: Path to log file
        """
        self.log_to_console = False
        self.log_to_file = True
        self.log_file_path = log_file
        
    def reset(self) -> None:
        """Reset logging configuration to defaults."""
        self.__init__()

# Singleton instance for global access
logging_config = LoggingConfig()

def configure_logging(debug: bool = False, 
                     debug_modules: Optional[List[str]] = None,
                     log_file: Optional[str] = None,
                     console: bool = True) -> None:
    """
    Configure the logging system.
    
    Args:
        debug: Enable debug mode globally or for specific modules
        debug_modules: List of module prefixes to enable debug for
        log_file: Optional file path for logging
        console: Whether to log to console
    """
    # Reset existing logging configuration
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(DEFAULT_FORMAT)
    
    # Configure console logging if enabled
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Configure file logging if enabled
    if log_file:
        # Ensure logs directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set default levels
    root_logger.setLevel(logging.INFO)
    
    # Set up module-specific logging
    if debug:
        # Set all loggers to DEBUG if no specific modules
        if not debug_modules:
            root_logger.setLevel(logging.DEBUG)
        else:
            # Set specific modules to DEBUG
            for module in debug_modules:
                module_logger = logging.getLogger(module)
                module_logger.setLevel(logging.DEBUG)
                # Ensure log propagation
                module_logger.propagate = True
    
    # Store the configuration for reference
    logging_config.log_to_console = console
    logging_config.log_to_file = bool(log_file)
    logging_config.log_file_path = log_file
    logging_config.debug_mode = debug
    
    if debug_modules:
        logging_config.debug_modules = set(debug_modules)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger configured according to system settings.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger: Configured logger
    """
    logger = logging.getLogger(name)
    
    # Set level based on debug settings
    if logging_config.debug_mode:
        if not logging_config.debug_modules:
            # Full debug mode
            logger.setLevel(logging.DEBUG)
        else:
            # Check if this logger is in a debugged module
            for module in logging_config.debug_modules:
                if name == module or name.startswith(f"{module}."):
                    logger.setLevel(logging.DEBUG)
                    break
    
    return logger