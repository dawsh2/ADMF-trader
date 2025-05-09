"""
Configuration system for ADMF-Trader.

This module provides a hierarchical configuration system that supports
loading from YAML files, environment variables, and defaults.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, Union, List, Set

logger = logging.getLogger(__name__)

class Config:
    """
    Hierarchical configuration system.
    
    Features:
    - Load configuration from YAML files
    - Hierarchical access with dot notation
    - Environment variable overrides
    - Default values
    - Configuration sections
    """
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration.
        
        Args:
            config_dict: Initial configuration dictionary
        """
        self.data = config_dict or {}
        
    @classmethod
    def from_file(cls, file_path: str) -> 'Config':
        """
        Create a configuration from a YAML file.
        
        Args:
            file_path: Path to YAML configuration file
            
        Returns:
            Config: Configuration object
            
        Raises:
            FileNotFoundError: If file not found
            yaml.YAMLError: If file is not valid YAML
        """
        logger.info(f"Loading configuration from {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                config_dict = yaml.safe_load(f)
                
            if not isinstance(config_dict, dict):
                raise ValueError(f"Configuration file {file_path} must contain a dictionary")
                
            return cls(config_dict)
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {file_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML in {file_path}: {e}")
            raise
            
    @classmethod
    def from_files(cls, file_paths: List[str], ignore_missing: bool = False) -> 'Config':
        """
        Create a configuration from multiple YAML files.
        
        Later files override values from earlier files.
        
        Args:
            file_paths: List of paths to YAML configuration files
            ignore_missing: Whether to ignore missing files
            
        Returns:
            Config: Configuration object
        """
        config = cls()
        
        for file_path in file_paths:
            try:
                file_config = cls.from_file(file_path)
                config.update(file_config)
            except FileNotFoundError:
                if ignore_missing:
                    logger.warning(f"Ignoring missing configuration file: {file_path}")
                else:
                    raise
                    
        return config
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Any: Configuration value or default
        """
        # Check for environment variable override
        env_var = self._key_to_env_var(key)
        if env_var in os.environ:
            return self._convert_value(os.environ[env_var])
            
        # Navigate the configuration hierarchy
        value = self.data
        for part in key.split('.'):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
                
        return value
        
    def get_section(self, key: str) -> 'Config':
        """
        Get a configuration section as a new Config object.
        
        Args:
            key: Section key (supports dot notation)
            
        Returns:
            Config: Configuration section
        """
        value = self.get(key, {})
        if not isinstance(value, dict):
            return Config({})
            
        return Config(value)
        
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a boolean configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            bool: Configuration value as boolean
        """
        value = self.get(key, default)
        
        if isinstance(value, bool):
            return value
            
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
            
        return bool(value)
        
    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get an integer configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            int: Configuration value as integer
        """
        value = self.get(key, default)
        
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
            
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Get a float configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            float: Configuration value as float
        """
        value = self.get(key, default)
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
            
    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]:
        """
        Get a list configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            List: Configuration value as list
        """
        value = self.get(key, default or [])
        
        if isinstance(value, list):
            return value
            
        if isinstance(value, str):
            return [item.strip() for item in value.split(',')]
            
        return [value]
        
    def update(self, other: Union[Dict[str, Any], 'Config']) -> None:
        """
        Update configuration with values from another config or dictionary.
        
        Args:
            other: Config object or dictionary to update from
        """
        if isinstance(other, Config):
            self._update_dict(self.data, other.data)
        else:
            self._update_dict(self.data, other)
            
    def _update_dict(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively update a dictionary.
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with new values
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # Recursively update nested dictionaries
                self._update_dict(target[key], value)
            else:
                # Replace or add values
                target[key] = value
                
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        parts = key.split('.')
        target = self.data
        
        # Navigate to the target dictionary
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
            
        # Set the value
        target[parts[-1]] = value
        
    def as_dict(self) -> Dict[str, Any]:
        """
        Get the configuration as a dictionary.
        
        Returns:
            Dict: Configuration dictionary
        """
        return self.data.copy()
        
    def _key_to_env_var(self, key: str) -> str:
        """
        Convert a configuration key to an environment variable name.
        
        Args:
            key: Configuration key (dot notation)
            
        Returns:
            str: Environment variable name (UPPER_CASE with underscores)
        """
        return f"ADMF_{key.upper().replace('.', '_')}"
        
    def _convert_value(self, value: str) -> Any:
        """
        Convert a string value to an appropriate type.
        
        Args:
            value: String value
            
        Returns:
            Any: Converted value
        """
        # Try to convert to numeric types
        try:
            if value.isdigit():
                return int(value)
            if value.replace('.', '', 1).isdigit() and value.count('.') <= 1:
                return float(value)
        except (ValueError, AttributeError):
            pass
            
        # Convert boolean values
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        if value.lower() in ('false', 'no', 'off', '0'):
            return False
            
        # Convert null values
        if value.lower() in ('null', 'none'):
            return None
            
        # Convert lists
        if ',' in value:
            return [self._convert_value(v.strip()) for v in value.split(',')]
            
        # Return as string
        return value