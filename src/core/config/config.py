import os
import yaml
import json
from typing import Dict, Any, Optional, Union, List, Type, TypeVar, cast, Tuple
from src.core.di.container import Container

T = TypeVar('T')

class ConfigSection:
    """A section of configuration values."""
    
    def __init__(self, name: str, values: Dict[str, Any] = None):
        self.name = name
        self._values = values or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._values.get(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get a configuration value as an integer."""
        value = self.get(key, default)
        return int(value)
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a configuration value as a float."""
        value = self.get(key, default)
        return float(value)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a configuration value as a boolean."""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', 'y', '1')
        return bool(value)
    
    def get_list(self, key: str, default: List = None) -> List:
        """Get a configuration value as a list."""
        value = self.get(key, default or [])
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return value.split(',')
        return [value]
    
    def get_section(self, name: str) -> 'ConfigSection':
        """Get a nested configuration section."""
        value = self.get(name, {})
        if not isinstance(value, dict):
            value = {}
        return ConfigSection(f"{self.name}.{name}", value)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._values[key] = value
    
    def update(self, values: Dict[str, Any]) -> None:
        """Update multiple configuration values."""
        self._values.update(values)
    
    def as_dict(self) -> Dict[str, Any]:
        """Get all values as a dictionary."""
        return dict(self._values)

class ConfigSchema:
    """Schema validator for configuration."""
    
    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize with a schema definition.
        
        Schema format:
        {
            'section_name': {
                'property_name': {
                    'type': type or tuple of types,
                    'required': bool,
                    'default': any,
                    'min': number, # for numeric values
                    'max': number, # for numeric values
                    'options': list, # for enum-like values
                    'pattern': str,  # regex pattern for strings
                }
            }
        }
        """
        self.schema = schema
    
    def validate(self, config: 'Config') -> Tuple[bool, List[str]]:
        """
        Validate configuration against schema.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Validate each section
        for section_name, section_schema in self.schema.items():
            section = config.get_section(section_name)
            section_dict = section.as_dict()
            
            # Validate each property
            for prop_name, prop_schema in section_schema.items():
                prop_value = section_dict.get(prop_name)
                
                # Check if required
                if prop_schema.get('required', False) and prop_value is None:
                    errors.append(f"Missing required property: {section_name}.{prop_name}")
                    continue
                
                # Skip validation if value is None
                if prop_value is None:
                    continue
                
                # Type validation
                expected_type = prop_schema.get('type')
                if expected_type:
                    if isinstance(expected_type, tuple):
                        if not isinstance(prop_value, expected_type):
                            errors.append(
                                f"Type mismatch for {section_name}.{prop_name}: "
                                f"expected one of {[t.__name__ for t in expected_type]}, "
                                f"got {type(prop_value).__name__}"
                            )
                    elif not isinstance(prop_value, expected_type):
                        errors.append(
                            f"Type mismatch for {section_name}.{prop_name}: "
                            f"expected {expected_type.__name__}, "
                            f"got {type(prop_value).__name__}"
                        )
                
                # Numeric constraints
                if isinstance(prop_value, (int, float)):
                    # Min value
                    min_val = prop_schema.get('min')
                    if min_val is not None and prop_value < min_val:
                        errors.append(
                            f"Value too small for {section_name}.{prop_name}: "
                            f"minimum is {min_val}, got {prop_value}"
                        )
                    
                    # Max value
                    max_val = prop_schema.get('max')
                    if max_val is not None and prop_value > max_val:
                        errors.append(
                            f"Value too large for {section_name}.{prop_name}: "
                            f"maximum is {max_val}, got {prop_value}"
                        )
                
                # String constraints
                if isinstance(prop_value, str):
                    # Pattern matching
                    pattern = prop_schema.get('pattern')
                    if pattern:
                        import re
                        if not re.match(pattern, prop_value):
                            errors.append(
                                f"Pattern mismatch for {section_name}.{prop_name}: "
                                f"value '{prop_value}' doesn't match pattern '{pattern}'"
                            )
                
                # Option constraints
                options = prop_schema.get('options')
                if options is not None and prop_value not in options:
                    errors.append(
                        f"Invalid value for {section_name}.{prop_name}: "
                        f"must be one of {options}, got {prop_value}"
                    )
                
                # Custom validation
                validator = prop_schema.get('validator')
                if validator and callable(validator):
                    valid, message = validator(prop_value)
                    if not valid:
                        errors.append(
                            f"Validation failed for {section_name}.{prop_name}: {message}"
                        )
        
        return len(errors) == 0, errors
    
    def apply_defaults(self, config: 'Config') -> None:
        """
        Apply schema defaults to configuration.
        
        Args:
            config: Configuration to update with defaults
        """
        for section_name, section_schema in self.schema.items():
            section = config.get_section(section_name)
            
            for prop_name, prop_schema in section_schema.items():
                if 'default' in prop_schema and section.get(prop_name) is None:
                    section.set(prop_name, prop_schema['default'])
    
    

class Config:
    """Hierarchical configuration system."""
    
    def __init__(self):
        self._sections = {}  # name -> ConfigSection
        self._defaults = {}  # name -> defaults dict
    
    def register_defaults(self, section_name: str, defaults: Dict[str, Any]) -> None:
        """Register default values for a section."""
        self._defaults[section_name] = defaults
        # Ensure section exists
        if section_name not in self._sections:
            self._sections[section_name] = ConfigSection(section_name, dict(defaults))
        else:
            # Update existing section with defaults for missing keys
            section = self._sections[section_name]
            for key, value in defaults.items():
                if key not in section.as_dict():
                    section.set(key, value)
    
    def load_file(self, filepath: str) -> None:
        """Load configuration from a file (YAML or JSON)."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        # Determine file type from extension
        _, ext = os.path.splitext(filepath)
        
        try:
            with open(filepath, 'r') as f:
                if ext.lower() in ('.yaml', '.yml'):
                    config_data = yaml.safe_load(f)
                elif ext.lower() == '.json':
                    config_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported configuration file format: {ext}")
            
            # Update sections with loaded data
            self._update_from_dict(config_data)
        except Exception as e:
            raise ValueError(f"Error loading configuration file: {e}")
    
    def load_env(self, prefix: str = 'APP_') -> None:
        """Load configuration from environment variables."""
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert APP_SECTION_KEY to section.key
                parts = key[len(prefix):].lower().split('_')
                if len(parts) > 1:
                    section_name = parts[0]
                    setting_key = '_'.join(parts[1:])
                    
                    # Ensure section exists
                    if section_name not in self._sections:
                        self._sections[section_name] = ConfigSection(section_name)
                    
                    # Update setting
                    self._sections[section_name].set(setting_key, value)
    
    def get_section(self, name: str) -> ConfigSection:
        """Get a configuration section."""
        if name not in self._sections:
            # Create section with defaults if available
            defaults = self._defaults.get(name, {})
            self._sections[name] = ConfigSection(name, dict(defaults))
        
        return self._sections[name]
    
    def _update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update configuration from a dictionary."""
        for section_name, section_data in data.items():
            if isinstance(section_data, dict):
                section = self.get_section(section_name)
                section.update(section_data)


    def validate(self, schema: ConfigSchema) -> Tuple[bool, List[str]]:
        """
        Validate configuration against a schema.

        Args:
            schema: Schema to validate against

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        return schema.validate(self)

    def apply_schema_defaults(self, schema: ConfigSchema) -> None:
        """
        Apply defaults from schema.

        Args:
            schema: Schema to get defaults from
        """
        schema.apply_defaults(self)                

              


class ConfigurableContainer(Container):
    """Container with configuration integration."""
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config or Config()
    
    def register_from_config(self, section_name: str, base_type=None):
        """
        Register components defined in a configuration section.
        
        Args:
            section_name: Name of the configuration section
            base_type: Optional base type for verification
            
        Returns:
            Dictionary of registered component names to instances
        """
        section = self.config.get_section(section_name)
        registered = {}
        
        for component_name, component_config in section.as_dict().items():
            if not isinstance(component_config, dict) or not component_config.get('enabled', True):
                continue
                
            # Get class information
            class_path = component_config.get('class')
            if not class_path:
                continue
                
            try:
                # Import class
                module_path, class_name = class_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                component_class = getattr(module, class_name)
                
                # Verify base type if provided
                if base_type and not issubclass(component_class, base_type):
                    logger.warning(
                        f"Component class {class_path} does not inherit from {base_type.__name__}"
                    )
                    continue
                
                # Register component
                component_id = f"{section_name}.{component_name}"
                self.register(component_id, component_class)
                
                # Configure if component has configure method
                component = self.get(component_id)
                if hasattr(component, 'configure'):
                    params = component_config.get('parameters', {})
                    component.configure(params)
                
                registered[component_id] = component
            except Exception as e:
                logger.error(f"Error registering component {component_name}: {e}", exc_info=True)
        
        return registered
    
    def get_configured(self, component_id: str, config_section: str = None):
        """
        Get a component and configure it.
        
        Args:
            component_id: Component ID
            config_section: Configuration section path (defaults to component_id)
            
        Returns:
            Configured component
        """
        # Get component
        component = self.get(component_id)
        
        # Configure if requested
        if config_section and hasattr(component, 'configure'):
            section_path = config_section
            section = self.config.get_section(section_path)
            component.configure(section)
        
        return component


