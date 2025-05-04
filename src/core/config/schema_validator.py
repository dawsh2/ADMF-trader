"""
Schema validation for configuration files.

This module provides comprehensive schema validation for configuration files
using JSON Schema standards, with additional custom validation capabilities.
"""

import json
import re
import logging
from typing import Dict, Any, List, Tuple, Optional, Union, Callable, Type

from src.core.exceptions import ConfigError, SchemaValidationError

logger = logging.getLogger(__name__)

# Type definitions
ValidationFunction = Callable[[Any], Tuple[bool, Optional[str]]]
SchemaType = Dict[str, Any]


class SchemaValidator:
    """Validator for configuration schemas."""
    
    def __init__(self, schema: Dict[str, Any]):
        """Initialize schema validator.
        
        Args:
            schema: Schema definition
        """
        self.schema = schema
        self._validate_schema()  # Ensure schema itself is valid
    
    def _validate_schema(self) -> None:
        """Validate that the schema itself is well-formed.
        
        Raises:
            ConfigError: If schema is invalid
        """
        if not isinstance(self.schema, dict):
            raise ConfigError("Schema must be a dictionary")
        
        # TODO: Add more schema validation logic if needed
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration against schema.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Validate against schema
        self._validate_object(config, self.schema, "", errors)
        
        return len(errors) == 0, errors
    
    def _validate_object(self, obj: Dict[str, Any], schema: Dict[str, Any], 
                        path: str, errors: List[str]) -> None:
        """Validate an object against a schema.
        
        Args:
            obj: Object to validate
            schema: Schema to validate against
            path: Current path in the object (for error messages)
            errors: List to collect error messages
        """
        # Validate type
        if not isinstance(obj, dict):
            errors.append(f"{path}: Expected object, got {type(obj).__name__}")
            return
        
        # Check for required properties
        for prop in schema.get("required", []):
            if prop not in obj:
                errors.append(f"{path}: Missing required property '{prop}'")
        
        # Validate properties
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            prop_path = f"{path}.{prop_name}" if path else prop_name
            
            if prop_name in obj:
                self._validate_value(obj[prop_name], prop_schema, prop_path, errors)
        
        # Check for additional properties
        if schema.get("additionalProperties") is False:
            extra_props = set(obj.keys()) - set(properties.keys())
            if extra_props:
                errors.append(
                    f"{path}: Additional properties not allowed: {', '.join(extra_props)}"
                )
        elif "additionalProperties" in schema and isinstance(schema["additionalProperties"], dict):
            # Validate additional properties against schema
            extra_props = set(obj.keys()) - set(properties.keys())
            for prop in extra_props:
                prop_path = f"{path}.{prop}" if path else prop
                self._validate_value(
                    obj[prop], 
                    schema["additionalProperties"], 
                    prop_path, 
                    errors
                )
    
    def _validate_array(self, arr: List[Any], schema: Dict[str, Any], 
                       path: str, errors: List[str]) -> None:
        """Validate an array against a schema.
        
        Args:
            arr: Array to validate
            schema: Schema to validate against
            path: Current path in the object (for error messages)
            errors: List to collect error messages
        """
        # Validate type
        if not isinstance(arr, list):
            errors.append(f"{path}: Expected array, got {type(arr).__name__}")
            return
        
        # Validate items
        if "items" in schema:
            for i, item in enumerate(arr):
                item_path = f"{path}[{i}]"
                self._validate_value(item, schema["items"], item_path, errors)
        
        # Validate length
        if "minItems" in schema and len(arr) < schema["minItems"]:
            errors.append(
                f"{path}: Array has too few items ({len(arr)}), "
                f"minimum is {schema['minItems']}"
            )
        
        if "maxItems" in schema and len(arr) > schema["maxItems"]:
            errors.append(
                f"{path}: Array has too many items ({len(arr)}), "
                f"maximum is {schema['maxItems']}"
            )
        
        # Validate uniqueness
        if schema.get("uniqueItems", False) and len(arr) != len(set(map(str, arr))):
            errors.append(f"{path}: Array items must be unique")
    
    def _validate_value(self, value: Any, schema: Dict[str, Any], 
                       path: str, errors: List[str]) -> None:
        """Validate a value against a schema.
        
        Args:
            value: Value to validate
            schema: Schema to validate against
            path: Current path in the object (for error messages)
            errors: List to collect error messages
        """
        # Handle null values
        if value is None:
            if not schema.get("nullable", False):
                errors.append(f"{path}: Value cannot be null")
            return
        
        # Validate type
        type_spec = schema.get("type")
        if type_spec:
            if isinstance(type_spec, list):
                valid_types = type_spec
            else:
                valid_types = [type_spec]
            
            # Map JSON schema types to Python types
            type_map = {
                "string": str,
                "integer": int,
                "number": (int, float),
                "boolean": bool,
                "array": list,
                "object": dict
            }
            
            valid_python_types = []
            for t in valid_types:
                if t in type_map:
                    mapped_type = type_map[t]
                    if isinstance(mapped_type, tuple):
                        valid_python_types.extend(mapped_type)
                    else:
                        valid_python_types.append(mapped_type)
            
            if not any(isinstance(value, t) for t in valid_python_types):
                errors.append(
                    f"{path}: Expected {' or '.join(valid_types)}, "
                    f"got {type(value).__name__}"
                )
                return
        
        # Validate by type
        value_type = type(value).__name__
        
        if isinstance(value, dict):
            self._validate_object(value, schema, path, errors)
        
        elif isinstance(value, list):
            self._validate_array(value, schema, path, errors)
        
        elif isinstance(value, str):
            # String-specific validations
            if "minLength" in schema and len(value) < schema["minLength"]:
                errors.append(
                    f"{path}: String too short ({len(value)}), "
                    f"minimum is {schema['minLength']}"
                )
            
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                errors.append(
                    f"{path}: String too long ({len(value)}), "
                    f"maximum is {schema['maxLength']}"
                )
            
            if "pattern" in schema:
                pattern = schema["pattern"]
                if not re.match(pattern, value):
                    errors.append(
                        f"{path}: String does not match pattern {pattern}"
                    )
            
            if "enum" in schema and value not in schema["enum"]:
                errors.append(
                    f"{path}: Value must be one of {schema['enum']}"
                )
        
        elif isinstance(value, (int, float)):
            # Number-specific validations
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(
                    f"{path}: Value too small ({value}), "
                    f"minimum is {schema['minimum']}"
                )
            
            if "maximum" in schema and value > schema["maximum"]:
                errors.append(
                    f"{path}: Value too large ({value}), "
                    f"maximum is {schema['maximum']}"
                )
            
            if "multipleOf" in schema:
                multiple = schema["multipleOf"]
                if isinstance(value, int) and isinstance(multiple, int):
                    if value % multiple != 0:
                        errors.append(
                            f"{path}: Value {value} is not a multiple of {multiple}"
                        )
                else:
                    # For floats, check with some tolerance
                    ratio = value / multiple
                    if abs(round(ratio) - ratio) > 1e-10:
                        errors.append(
                            f"{path}: Value {value} is not a multiple of {multiple}"
                        )
        
        # Custom validations
        if "custom" in schema and callable(schema["custom"]):
            valid, message = schema["custom"](value)
            if not valid:
                errors.append(f"{path}: {message}")
    
    def apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply schema defaults to configuration.
        
        Args:
            config: Configuration to update with defaults
            
        Returns:
            Updated configuration with defaults
        """
        result = dict(config)  # Create a copy
        self._apply_defaults_to_object(result, self.schema)
        return result
    
    def _apply_defaults_to_object(self, obj: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Apply defaults to an object according to schema.
        
        Args:
            obj: Object to update with defaults
            schema: Schema containing defaults
        """
        # Apply property defaults
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            if "default" in prop_schema and prop_name not in obj:
                obj[prop_name] = prop_schema["default"]
            
            # Recursively apply defaults to nested objects
            if (prop_name in obj and isinstance(obj[prop_name], dict) and 
                    prop_schema.get("type") == "object"):
                self._apply_defaults_to_object(obj[prop_name], prop_schema)
            
            # Apply defaults to array items if they are objects
            if (prop_name in obj and isinstance(obj[prop_name], list) and 
                    prop_schema.get("type") == "array" and 
                    "items" in prop_schema and 
                    prop_schema["items"].get("type") == "object"):
                
                for item in obj[prop_name]:
                    if isinstance(item, dict):
                        self._apply_defaults_to_object(item, prop_schema["items"])


class SchemaRegistry:
    """Registry for configuration schemas."""
    
    # Default schemas
    _default_schemas = {
        # Base component schema
        "component": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "enabled": {"type": "boolean", "default": True}
            }
        },
        
        # Strategy base schema
        "strategy": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "enabled": {"type": "boolean", "default": True},
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["name"]
        },
        
        # Moving Average Crossover schema
        "ma_crossover": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "enabled": {"type": "boolean", "default": True},
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "fast_window": {"type": "integer", "minimum": 1, "maximum": 500},
                "slow_window": {"type": "integer", "minimum": 2, "maximum": 500},
                "price_key": {"type": "string", "enum": ["open", "high", "low", "close"]}
            },
            "required": ["fast_window", "slow_window"]
        },
        
        # Risk Manager schema
        "risk_manager": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "enabled": {"type": "boolean", "default": True},
                "position_size": {"type": "integer", "minimum": 1},
                "max_position_pct": {"type": "number", "minimum": 0, "maximum": 1}
            },
            "required": ["position_size"]
        }
    }
    
    def __init__(self):
        """Initialize schema registry with default schemas."""
        self.schemas: Dict[str, Dict[str, Any]] = dict(self._default_schemas)
        self.validators: Dict[str, SchemaValidator] = {}
    
    def register_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """Register a schema.
        
        Args:
            name: Name to register schema under
            schema: Schema definition
            
        Raises:
            ConfigError: If schema is invalid
        """
        try:
            validator = SchemaValidator(schema)
            self.schemas[name] = schema
            self.validators[name] = validator
            logger.debug(f"Registered schema '{name}'")
        except Exception as e:
            raise ConfigError(f"Failed to register schema '{name}': {e}")
    
    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a schema by name.
        
        Args:
            name: Name of schema
            
        Returns:
            Schema definition if found, None otherwise
        """
        return self.schemas.get(name)
    
    def get_validator(self, name: str) -> Optional[SchemaValidator]:
        """Get a validator by schema name.
        
        Args:
            name: Name of schema
            
        Returns:
            SchemaValidator if found, None otherwise
        """
        # Create validator if it doesn't exist
        if name in self.schemas and name not in self.validators:
            self.validators[name] = SchemaValidator(self.schemas[name])
        
        return self.validators.get(name)
    
    def validate(self, config: Dict[str, Any], schema_name: str) -> Tuple[bool, List[str]]:
        """Validate configuration against a schema.
        
        Args:
            config: Configuration to validate
            schema_name: Name of schema to use
            
        Returns:
            Tuple of (is_valid, list of error messages)
            
        Raises:
            ConfigError: If schema does not exist
        """
        validator = self.get_validator(schema_name)
        if validator is None:
            raise ConfigError(f"Schema '{schema_name}' not found")
        
        return validator.validate(config)
    
    def apply_defaults(self, config: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
        """Apply schema defaults to configuration.
        
        Args:
            config: Configuration to update with defaults
            schema_name: Name of schema to use
            
        Returns:
            Updated configuration with defaults
            
        Raises:
            ConfigError: If schema does not exist
        """
        validator = self.get_validator(schema_name)
        if validator is None:
            raise ConfigError(f"Schema '{schema_name}' not found")
        
        return validator.apply_defaults(config)
    
    def list_schemas(self) -> List[str]:
        """List all registered schemas.
        
        Returns:
            List of schema names
        """
        return list(self.schemas.keys())


# Global registry instance
schema_registry = SchemaRegistry()


def validate_config(config: Dict[str, Any], schema_name: str) -> Tuple[bool, List[str]]:
    """Validate configuration against a named schema.
    
    Args:
        config: Configuration to validate
        schema_name: Name of schema to use
        
    Returns:
        Tuple of (is_valid, list of error messages)
        
    Raises:
        ConfigError: If schema does not exist
    """
    return schema_registry.validate(config, schema_name)


def apply_defaults(config: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
    """Apply schema defaults to configuration.
    
    Args:
        config: Configuration to update with defaults
        schema_name: Name of schema to use
        
    Returns:
        Updated configuration with defaults
        
    Raises:
        ConfigError: If schema does not exist
    """
    return schema_registry.apply_defaults(config, schema_name)


def register_schema(name: str, schema: Dict[str, Any]) -> None:
    """Register a schema with the global registry.
    
    Args:
        name: Name to register schema under
        schema: Schema definition
        
    Raises:
        ConfigError: If schema is invalid
    """
    schema_registry.register_schema(name, schema)


def get_schema(name: str) -> Optional[Dict[str, Any]]:
    """Get a schema by name from the global registry.
    
    Args:
        name: Name of schema
        
    Returns:
        Schema definition if found, None otherwise
    """
    return schema_registry.get_schema(name)


def list_schemas() -> List[str]:
    """List all registered schemas in the global registry.
    
    Returns:
        List of schema names
    """
    return schema_registry.list_schemas()
