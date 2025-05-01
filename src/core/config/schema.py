"""
Configuration schema validation for ADMF-Trader.
Provides schema definitions and validation functions for configuration files.
"""

import jsonschema
from src.core.exceptions import SchemaValidationError


# Base schema for the entire configuration
CONFIG_SCHEMA = {
    "type": "object",
    "required": ["backtest"],
    "properties": {
        "backtest": {
            "type": "object",
            "required": ["initial_capital", "symbols", "data_dir", "timeframe", "data_source"],
            "properties": {
                "initial_capital": {"type": "number", "minimum": 0},
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1
                },
                "data_dir": {"type": "string"},
                "timeframe": {"type": "string"},
                "data_source": {"type": "string"},
                "start_date": {"type": "string", "format": "date"},
                "end_date": {"type": "string", "format": "date"}
            }
        },
        "strategies": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["enabled"],
                "properties": {
                    "enabled": {"type": "boolean"}
                }
            }
        },
        "risk_manager": {
            "type": "object",
            "properties": {
                "position_size": {"type": "number", "minimum": 0},
                "max_position_pct": {"type": "number", "minimum": 0, "maximum": 1},
                "stop_loss_pct": {"type": "number", "minimum": 0, "maximum": 1},
                "take_profit_pct": {"type": "number", "minimum": 0}
            }
        },
        "broker": {
            "type": "object",
            "properties": {
                "commission": {"type": "number", "minimum": 0},
                "slippage": {"type": "number", "minimum": 0},
                "latency_ms": {"type": "integer", "minimum": 0}
            }
        },
        "output": {
            "type": "object",
            "properties": {
                "save_results": {"type": "boolean"},
                "save_trades": {"type": "boolean"},
                "save_portfolio": {"type": "boolean"},
                "output_dir": {"type": "string"},
                "plot_results": {"type": "boolean"}
            }
        },
        "logging": {
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                "file": {"type": "string"},
                "console": {"type": "boolean"}
            }
        }
    }
}


# Strategy-specific schemas
STRATEGY_SCHEMAS = {
    "ma_crossover": {
        "type": "object",
        "required": ["enabled", "fast_window", "slow_window"],
        "properties": {
            "enabled": {"type": "boolean"},
            "fast_window": {"type": "integer", "minimum": 1},
            "slow_window": {"type": "integer", "minimum": 2},
            "price_key": {"type": "string", "enum": ["open", "high", "low", "close"]}
        },
        "dependencies": {
            "enabled": {
                "oneOf": [
                    {"properties": {"enabled": {"enum": [False]}}},
                    {
                        "properties": {"enabled": {"enum": [True]}},
                        "required": ["fast_window", "slow_window"]
                    }
                ]
            }
        }
    },
    "regime_ensemble": {
        "type": "object",
        "required": ["enabled", "lookback_window", "regime_indicators"],
        "properties": {
            "enabled": {"type": "boolean"},
            "lookback_window": {"type": "integer", "minimum": 10},
            "regime_indicators": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1
            },
            "strategy_weights": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": {"type": "number"}
                }
            }
        }
    }
}


def validate_config(config, schema=CONFIG_SCHEMA):
    """Validate a configuration dictionary against a schema.
    
    Args:
        config (dict): Configuration dictionary to validate
        schema (dict, optional): Schema to validate against. Defaults to CONFIG_SCHEMA.
        
    Raises:
        SchemaValidationError: If validation fails
    """
    try:
        jsonschema.validate(instance=config, schema=schema)
    except jsonschema.exceptions.ValidationError as e:
        # Extract error details for better messaging
        errors = _extract_validation_errors(e)
        raise SchemaValidationError(errors=errors)


def validate_strategy_config(strategy_name, strategy_config):
    """Validate strategy-specific configuration.
    
    Args:
        strategy_name (str): Name of the strategy
        strategy_config (dict): Strategy configuration to validate
        
    Raises:
        SchemaValidationError: If validation fails
    """
    if strategy_name not in STRATEGY_SCHEMAS:
        # For unknown strategies, only check basic structure
        basic_schema = {
            "type": "object",
            "required": ["enabled"],
            "properties": {
                "enabled": {"type": "boolean"}
            }
        }
        try:
            jsonschema.validate(instance=strategy_config, schema=basic_schema)
        except jsonschema.exceptions.ValidationError as e:
            errors = _extract_validation_errors(e)
            raise SchemaValidationError(errors=errors)
        return
    
    # Validate against strategy-specific schema
    schema = STRATEGY_SCHEMAS[strategy_name]
    try:
        jsonschema.validate(instance=strategy_config, schema=schema)
    except jsonschema.exceptions.ValidationError as e:
        errors = _extract_validation_errors(e)
        raise SchemaValidationError(errors=errors)


def validate_parameters(parameters, meta_parameters):
    """Validate parameters against their metadata definitions.
    
    Args:
        parameters (dict): Parameter values to validate
        meta_parameters (dict): Metadata for parameters, including constraints
        
    Raises:
        SchemaValidationError: If validation fails
    """
    errors = []
    
    for name, value in parameters.items():
        if name not in meta_parameters:
            continue  # Skip unknown parameters
        
        meta = meta_parameters[name]
        
        # Type validation
        if "type" in meta:
            expected_type = meta["type"]
            if expected_type == "integer" and not isinstance(value, int):
                errors.append(f"Parameter '{name}' must be an integer, got {type(value).__name__}")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Parameter '{name}' must be a number, got {type(value).__name__}")
            elif expected_type == "string" and not isinstance(value, str):
                errors.append(f"Parameter '{name}' must be a string, got {type(value).__name__}")
            elif expected_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Parameter '{name}' must be a boolean, got {type(value).__name__}")
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(f"Parameter '{name}' must be an array, got {type(value).__name__}")
            elif expected_type == "object" and not isinstance(value, dict):
                errors.append(f"Parameter '{name}' must be an object, got {type(value).__name__}")
        
        # Numeric constraints
        if isinstance(value, (int, float)):
            if "minimum" in meta and value < meta["minimum"]:
                errors.append(f"Parameter '{name}' must be at least {meta['minimum']}, got {value}")
            if "maximum" in meta and value > meta["maximum"]:
                errors.append(f"Parameter '{name}' must be at most {meta['maximum']}, got {value}")
        
        # String enum validation
        if isinstance(value, str) and "enum" in meta:
            if value not in meta["enum"]:
                enum_values = ", ".join(str(v) for v in meta["enum"])
                errors.append(f"Parameter '{name}' must be one of: {enum_values}, got '{value}'")
        
        # Array constraints
        if isinstance(value, list):
            if "minItems" in meta and len(value) < meta["minItems"]:
                errors.append(f"Parameter '{name}' must have at least {meta['minItems']} items, got {len(value)}")
            if "maxItems" in meta and len(value) > meta["maxItems"]:
                errors.append(f"Parameter '{name}' must have at most {meta['maxItems']} items, got {len(value)}")
    
    if errors:
        raise SchemaValidationError(errors=errors)


def _extract_validation_errors(validation_error):
    """Extract error details from a ValidationError.
    
    Args:
        validation_error (ValidationError): Validation error to extract details from
        
    Returns:
        list: List of error messages
    """
    errors = []
    
    def _extract_error(error, path=""):
        # Build path string
        if path and error.path:
            path = f"{path}.{error.path[-1]}" if error.path else path
        elif error.path:
            path = error.path[-1]
        
        # Add error message
        if path:
            errors.append(f"Error at '{path}': {error.message}")
        else:
            errors.append(f"Error: {error.message}")
        
        # Process nested errors
        for suberror in getattr(error, "context", []):
            _extract_error(suberror, path)
    
    _extract_error(validation_error)
    return errors
