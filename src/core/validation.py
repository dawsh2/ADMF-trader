"""
Parameter validation utilities for ADMF-Trader.

This module provides a comprehensive set of validators for checking parameter
values and constraints across the system.
"""

import re
import inspect
import functools
from typing import Dict, Any, List, Tuple, Optional, Union, Callable, Type, Set, TypeVar

from src.core.exceptions import ValidationError


T = TypeVar('T')


class ParameterValidator:
    """Utility class for validating parameters."""
    
    @staticmethod
    def validate_type(value: Any, expected_type: Union[Type, Tuple[Type, ...]], 
                     name: str = "parameter") -> bool:
        """Validate that a value has the expected type.
        
        Args:
            value: Value to validate
            expected_type: Expected type or tuple of types
            name: Parameter name for error message
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, expected_type):
            if isinstance(expected_type, tuple):
                type_names = [t.__name__ for t in expected_type]
                expected_str = " or ".join(type_names)
            else:
                expected_str = expected_type.__name__
            
            raise ValidationError(
                f"{name} must be of type {expected_str}",
                {"name": name, "value": value, "type": type(value).__name__}
            )
        
        return True
    
    @staticmethod
    def validate_range(value: Union[int, float], min_value: Optional[Union[int, float]] = None, 
                      max_value: Optional[Union[int, float]] = None, name: str = "parameter") -> bool:
        """Validate that a value is within a specified range.
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            name: Parameter name for error message
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(
                f"{name} must be a number",
                {"name": name, "value": value, "type": type(value).__name__}
            )
        
        if min_value is not None and value < min_value:
            raise ValidationError(
                f"{name} must be >= {min_value}",
                {"name": name, "value": value, "min": min_value}
            )
        
        if max_value is not None and value > max_value:
            raise ValidationError(
                f"{name} must be <= {max_value}",
                {"name": name, "value": value, "max": max_value}
            )
        
        return True
    
    @staticmethod
    def validate_in(value: Any, valid_values: Union[List, Set, Tuple], 
                   name: str = "parameter") -> bool:
        """Validate that a value is in a set of valid values.
        
        Args:
            value: Value to validate
            valid_values: Collection of valid values
            name: Parameter name for error message
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        if value not in valid_values:
            raise ValidationError(
                f"{name} must be one of {valid_values}",
                {"name": name, "value": value, "valid_values": valid_values}
            )
        
        return True
    
    @staticmethod
    def validate_length(value: Any, min_length: Optional[int] = None, 
                       max_length: Optional[int] = None, name: str = "parameter") -> bool:
        """Validate that a value has a length within specified bounds.
        
        Args:
            value: Value to validate
            min_length: Minimum allowed length (inclusive)
            max_length: Maximum allowed length (inclusive)
            name: Parameter name for error message
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        # Check if value has __len__ attribute
        if not hasattr(value, "__len__"):
            raise ValidationError(
                f"{name} must have a length",
                {"name": name, "value": value}
            )
        
        length = len(value)
        
        if min_length is not None and length < min_length:
            raise ValidationError(
                f"{name} must have length >= {min_length}",
                {"name": name, "length": length, "min_length": min_length}
            )
        
        if max_length is not None and length > max_length:
            raise ValidationError(
                f"{name} must have length <= {max_length}",
                {"name": name, "length": length, "max_length": max_length}
            )
        
        return True
    
    @staticmethod
    def validate_not_none(value: Any, name: str = "parameter") -> bool:
        """Validate that a value is not None.
        
        Args:
            value: Value to validate
            name: Parameter name for error message
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError(
                f"{name} must not be None",
                {"name": name}
            )
        
        return True
    
    @staticmethod
    def validate_string_pattern(value: str, pattern: str, name: str = "parameter") -> bool:
        """Validate that a string matches a regex pattern.
        
        Args:
            value: String to validate
            pattern: Regular expression pattern
            name: Parameter name for error message
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, str):
            raise ValidationError(
                f"{name} must be a string",
                {"name": name, "value": value, "type": type(value).__name__}
            )
        
        if not re.match(pattern, value):
            raise ValidationError(
                f"{name} must match pattern {pattern}",
                {"name": name, "value": value, "pattern": pattern}
            )
        
        return True
    
    @staticmethod
    def validate_positive(value: Union[int, float], name: str = "parameter") -> bool:
        """Validate that a value is positive (> 0).
        
        Args:
            value: Value to validate
            name: Parameter name for error message
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(
                f"{name} must be a number",
                {"name": name, "value": value, "type": type(value).__name__}
            )
        
        if value <= 0:
            raise ValidationError(
                f"{name} must be positive (> 0)",
                {"name": name, "value": value}
            )
        
        return True
    
    @staticmethod
    def validate_non_negative(value: Union[int, float], name: str = "parameter") -> bool:
        """Validate that a value is non-negative (>= 0).
        
        Args:
            value: Value to validate
            name: Parameter name for error message
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(
                f"{name} must be a number",
                {"name": name, "value": value, "type": type(value).__name__}
            )
        
        if value < 0:
            raise ValidationError(
                f"{name} must be non-negative (>= 0)",
                {"name": name, "value": value}
            )
        
        return True
    
    @staticmethod
    def validate_callable(value: Any, name: str = "parameter") -> bool:
        """Validate that a value is callable.
        
        Args:
            value: Value to validate
            name: Parameter name for error message
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        if not callable(value):
            raise ValidationError(
                f"{name} must be callable",
                {"name": name, "value": value, "type": type(value).__name__}
            )
        
        return True
    
    @staticmethod
    def validate_dict_keys(value: Dict, required_keys: List[str] = None, 
                          optional_keys: List[str] = None, name: str = "parameter") -> bool:
        """Validate that a dictionary contains required keys and only allowed keys.
        
        Args:
            value: Dictionary to validate
            required_keys: Keys that must be present
            optional_keys: Keys that may be present
            name: Parameter name for error message
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, dict):
            raise ValidationError(
                f"{name} must be a dictionary",
                {"name": name, "value": value, "type": type(value).__name__}
            )
        
        required_keys = required_keys or []
        optional_keys = optional_keys or []
        
        # Check for required keys
        missing_keys = [key for key in required_keys if key not in value]
        if missing_keys:
            raise ValidationError(
                f"{name} missing required keys: {missing_keys}",
                {"name": name, "missing_keys": missing_keys}
            )
        
        # Check for unknown keys
        allowed_keys = set(required_keys) | set(optional_keys)
        if allowed_keys:  # Only check if we specified some allowed keys
            unknown_keys = [key for key in value.keys() if key not in allowed_keys]
            if unknown_keys:
                raise ValidationError(
                    f"{name} contains unknown keys: {unknown_keys}",
                    {"name": name, "unknown_keys": unknown_keys, "allowed_keys": allowed_keys}
                )
        
        return True
    
    @staticmethod
    def validate_all(validators: List[Callable]) -> Callable:
        """Create a validator that runs multiple validators.
        
        Args:
            validators: List of validator functions
            
        Returns:
            Combined validator function
        """
        def combined_validator(value: Any, name: str = "parameter") -> bool:
            for validator in validators:
                validator(value, name=name)
            return True
        
        return combined_validator
    
    @staticmethod
    def validate_custom(value: Any, validator: Callable[[Any], Tuple[bool, Optional[str]]], 
                       name: str = "parameter") -> bool:
        """Run a custom validation function.
        
        Args:
            value: Value to validate
            validator: Function that returns (is_valid, error_message)
            name: Parameter name for error message
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        is_valid, error_message = validator(value)
        if not is_valid:
            raise ValidationError(
                f"{name}: {error_message or 'validation failed'}",
                {"name": name, "value": value}
            )
        
        return True


def validate_parameters(params_dict: Dict[str, Any], 
                       param_specs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Validate parameters against specifications.
    
    Args:
        params_dict: Dictionary of parameters to validate
        param_specs: Specifications for parameters
            Each spec is a dict with options like:
            - type: Required type or tuple of types
            - required: Whether parameter is required
            - default: Default value if not provided
            - min: Minimum value (for numbers)
            - max: Maximum value (for numbers)
            - options: List of valid values
            - validator: Custom validation function
            
    Returns:
        Dictionary with validated and defaulted parameters
        
    Raises:
        ValidationError: If validation fails
    """
    result = {}
    errors = []
    
    # Check for required parameters
    for param_name, spec in param_specs.items():
        if spec.get("required", False) and param_name not in params_dict:
            if "default" not in spec:
                errors.append(f"Missing required parameter: {param_name}")
    
    if errors:
        raise ValidationError(
            "; ".join(errors),
            {"errors": errors}
        )
    
    # Process each parameter
    for param_name, spec in param_specs.items():
        # If parameter not provided, use default if available
        if param_name not in params_dict:
            if "default" in spec:
                result[param_name] = spec["default"]
            continue
        
        value = params_dict[param_name]
        
        try:
            # Type validation
            if "type" in spec:
                ParameterValidator.validate_type(value, spec["type"], param_name)
            
            # Range validation for numbers
            if isinstance(value, (int, float)) and ("min" in spec or "max" in spec):
                ParameterValidator.validate_range(
                    value, 
                    spec.get("min"), 
                    spec.get("max"), 
                    param_name
                )
            
            # Options validation
            if "options" in spec:
                ParameterValidator.validate_in(value, spec["options"], param_name)
            
            # Pattern validation for strings
            if isinstance(value, str) and "pattern" in spec:
                ParameterValidator.validate_string_pattern(value, spec["pattern"], param_name)
            
            # Length validation
            if hasattr(value, "__len__") and ("min_length" in spec or "max_length" in spec):
                ParameterValidator.validate_length(
                    value, 
                    spec.get("min_length"), 
                    spec.get("max_length"), 
                    param_name
                )
            
            # Custom validation
            if "validator" in spec and callable(spec["validator"]):
                ParameterValidator.validate_custom(value, spec["validator"], param_name)
            
            # Add validated value to result
            result[param_name] = value
            
        except ValidationError as e:
            errors.append(str(e))
    
    if errors:
        raise ValidationError(
            "; ".join(errors),
            {"errors": errors}
        )
    
    return result


def validate_params(**param_specs):
    """Decorator for validating function parameters.
    
    Args:
        **param_specs: Specifications for parameters (see validate_parameters)
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)
            
            # Map positional args to parameter names
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Extract parameters to validate
            params_to_validate = {}
            for param_name, param_value in bound_args.arguments.items():
                if param_name in param_specs:
                    params_to_validate[param_name] = param_value
            
            # Add any kwargs that match specs but aren't in signature
            for param_name, param_value in kwargs.items():
                if param_name in param_specs and param_name not in params_to_validate:
                    params_to_validate[param_name] = param_value
            
            # Validate parameters
            validated_params = validate_parameters(params_to_validate, param_specs)
            
            # Update kwargs with validated values
            for param_name, param_value in validated_params.items():
                kwargs[param_name] = param_value
            
            # Call function with validated parameters
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator
