from typing import Dict, Any, List, Tuple, Type, Optional, Union

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
