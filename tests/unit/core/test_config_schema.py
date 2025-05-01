"""
Unit tests for the configuration schema validation.
"""

import pytest
from src.core.config.schema import (
    validate_config, validate_strategy_config, validate_parameters,
    CONFIG_SCHEMA, STRATEGY_SCHEMAS
)
from src.core.exceptions import SchemaValidationError


@pytest.mark.unit
@pytest.mark.core
class TestConfigSchema:
    
    @pytest.fixture
    def valid_config(self):
        """Fixture to provide a valid configuration."""
        return {
            "backtest": {
                "initial_capital": 100000.0,
                "symbols": ["AAPL", "MSFT"],
                "data_dir": "./data",
                "timeframe": "1d",
                "data_source": "csv",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31"
            },
            "strategies": {
                "ma_crossover": {
                    "enabled": True,
                    "fast_window": 5,
                    "slow_window": 15,
                    "price_key": "close"
                }
            },
            "risk_manager": {
                "position_size": 100,
                "max_position_pct": 0.1
            }
        }
    
    def test_valid_config(self, valid_config):
        """Test validation of a valid configuration."""
        # Should not raise any exceptions
        validate_config(valid_config)
    
    def test_missing_required_field(self, valid_config):
        """Test validation failure with missing required field."""
        # Remove required field
        del valid_config["backtest"]["symbols"]
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_config(valid_config)
        
        # Check error message
        error_str = str(excinfo.value)
        assert "symbols" in error_str
        assert "required" in error_str.lower()
    
    def test_invalid_type(self, valid_config):
        """Test validation failure with invalid type."""
        # Set integer field to string
        valid_config["backtest"]["initial_capital"] = "100000.0"
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_config(valid_config)
        
        # Check error message
        error_str = str(excinfo.value)
        assert "initial_capital" in error_str
        assert "number" in error_str.lower()
    
    def test_value_out_of_range(self, valid_config):
        """Test validation failure with value out of allowed range."""
        # Set max_position_pct > 1
        valid_config["risk_manager"]["max_position_pct"] = 1.5
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_config(valid_config)
        
        # Check error message
        error_str = str(excinfo.value)
        assert "max_position_pct" in error_str
        assert "maximum" in error_str.lower()
    
    def test_empty_array(self, valid_config):
        """Test validation failure with empty array where items are required."""
        # Set symbols to empty array
        valid_config["backtest"]["symbols"] = []
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_config(valid_config)
        
        # Check error message
        error_str = str(excinfo.value)
        assert "symbols" in error_str
        assert "empty" in error_str.lower() or "non-empty" in error_str.lower()


@pytest.mark.unit
@pytest.mark.core
class TestStrategySchema:
    
    @pytest.fixture
    def valid_ma_crossover_config(self):
        """Fixture to provide a valid MA Crossover strategy configuration."""
        return {
            "enabled": True,
            "fast_window": 5,
            "slow_window": 15,
            "price_key": "close"
        }
    
    @pytest.fixture
    def valid_regime_ensemble_config(self):
        """Fixture to provide a valid Regime Ensemble strategy configuration."""
        return {
            "enabled": True,
            "lookback_window": 50,
            "regime_indicators": ["volatility", "trend", "momentum"],
            "strategy_weights": {
                "regime_1": {
                    "ma_crossover": 0.7,
                    "momentum": 0.3
                },
                "regime_2": {
                    "ma_crossover": 0.3,
                    "momentum": 0.7
                }
            }
        }
    
    def test_valid_ma_crossover(self, valid_ma_crossover_config):
        """Test validation of a valid MA Crossover configuration."""
        # Should not raise any exceptions
        validate_strategy_config("ma_crossover", valid_ma_crossover_config)
    
    def test_valid_regime_ensemble(self, valid_regime_ensemble_config):
        """Test validation of a valid Regime Ensemble configuration."""
        # Should not raise any exceptions
        validate_strategy_config("regime_ensemble", valid_regime_ensemble_config)
    
    def test_ma_crossover_missing_window(self, valid_ma_crossover_config):
        """Test validation failure with missing window parameter."""
        # Remove required field
        del valid_ma_crossover_config["fast_window"]
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_strategy_config("ma_crossover", valid_ma_crossover_config)
        
        # Check error message
        error_str = str(excinfo.value)
        assert "fast_window" in error_str
        assert "required" in error_str.lower()
    
    def test_ma_crossover_invalid_window_values(self, valid_ma_crossover_config):
        """Test validation failure with invalid window values."""
        # Set invalid values
        valid_ma_crossover_config["fast_window"] = 0  # Minimum is 1
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_strategy_config("ma_crossover", valid_ma_crossover_config)
        
        # Check error message
        error_str = str(excinfo.value)
        assert "fast_window" in error_str
        assert "minimum" in error_str.lower()
    
    def test_ma_crossover_invalid_price_key(self, valid_ma_crossover_config):
        """Test validation failure with invalid price key."""
        # Set invalid value
        valid_ma_crossover_config["price_key"] = "adjusted_close"  # Not in enum
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_strategy_config("ma_crossover", valid_ma_crossover_config)
        
        # Check error message
        error_str = str(excinfo.value)
        assert "price_key" in error_str
        assert "enum" in error_str.lower() or "one of" in error_str.lower()
    
    def test_regime_ensemble_empty_indicators(self, valid_regime_ensemble_config):
        """Test validation failure with empty indicators array."""
        # Set empty array
        valid_regime_ensemble_config["regime_indicators"] = []
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_strategy_config("regime_ensemble", valid_regime_ensemble_config)
        
        # Check error message
        error_str = str(excinfo.value)
        assert "regime_indicators" in error_str
        assert "empty" in error_str.lower() or "non-empty" in error_str.lower()
    
    def test_unknown_strategy(self):
        """Test validation of an unknown strategy type."""
        # Basic config for unknown strategy
        unknown_config = {
            "enabled": True,
            "custom_param": 42
        }
        
        # Should not raise exceptions if basic structure is valid
        validate_strategy_config("unknown_strategy", unknown_config)
        
        # Test with invalid basic structure
        invalid_unknown = {
            "custom_param": 42
            # Missing 'enabled' field
        }
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_strategy_config("unknown_strategy", invalid_unknown)
        
        # Check error message
        error_str = str(excinfo.value)
        assert "enabled" in error_str
        assert "required" in error_str.lower()


@pytest.mark.unit
@pytest.mark.core
class TestParameterValidation:
    
    @pytest.fixture
    def meta_parameters(self):
        """Fixture to provide parameter metadata."""
        return {
            "window": {
                "type": "integer",
                "minimum": 1,
                "maximum": 200,
                "description": "Lookback window for calculation"
            },
            "threshold": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Threshold value for signal generation"
            },
            "method": {
                "type": "string",
                "enum": ["simple", "exponential", "weighted"],
                "description": "Method used for averaging"
            },
            "symbols": {
                "type": "array",
                "minItems": 1,
                "description": "List of symbols to trade"
            },
            "enabled": {
                "type": "boolean",
                "description": "Whether the component is enabled"
            }
        }
    
    def test_valid_parameters(self, meta_parameters):
        """Test validation of valid parameters."""
        parameters = {
            "window": 10,
            "threshold": 0.5,
            "method": "simple",
            "symbols": ["AAPL", "MSFT"],
            "enabled": True
        }
        
        # Should not raise any exceptions
        validate_parameters(parameters, meta_parameters)
    
    def test_type_validation(self, meta_parameters):
        """Test validation of parameter types."""
        # Test with wrong types
        parameters = {
            "window": "10",  # Should be integer
            "threshold": "0.5",  # Should be number
            "method": 123,  # Should be string
            "symbols": "AAPL",  # Should be array
            "enabled": "true"  # Should be boolean
        }
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_parameters(parameters, meta_parameters)
        
        # Check error messages
        error_str = str(excinfo.value)
        assert "window" in error_str and "integer" in error_str
        assert "threshold" in error_str and "number" in error_str
        assert "method" in error_str and "string" in error_str
        assert "symbols" in error_str and "array" in error_str
        assert "enabled" in error_str and "boolean" in error_str
    
    def test_range_validation(self, meta_parameters):
        """Test validation of numeric ranges."""
        # Test with out-of-range values
        parameters = {
            "window": 0,  # Below minimum
            "threshold": 1.5  # Above maximum
        }
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_parameters(parameters, meta_parameters)
        
        # Check error messages
        error_str = str(excinfo.value)
        assert "window" in error_str and "at least" in error_str
        assert "threshold" in error_str and "at most" in error_str
    
    def test_enum_validation(self, meta_parameters):
        """Test validation of enum values."""
        # Test with invalid enum value
        parameters = {
            "method": "advanced"  # Not in enum
        }
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_parameters(parameters, meta_parameters)
        
        # Check error message
        error_str = str(excinfo.value)
        assert "method" in error_str
        assert "one of" in error_str
        assert "simple" in error_str
        assert "exponential" in error_str
        assert "weighted" in error_str
    
    def test_array_validation(self, meta_parameters):
        """Test validation of array constraints."""
        # Test with empty array
        parameters = {
            "symbols": []  # Empty, minimum is 1
        }
        
        with pytest.raises(SchemaValidationError) as excinfo:
            validate_parameters(parameters, meta_parameters)
        
        # Check error message
        error_str = str(excinfo.value)
        assert "symbols" in error_str
        assert "at least" in error_str or "minItems" in error_str or "empty" in error_str
    
    def test_unknown_parameters(self, meta_parameters):
        """Test handling of unknown parameters."""
        # Parameters not in meta_parameters should be ignored
        parameters = {
            "window": 10,
            "unknown_param": "value"  # Not in meta_parameters
        }
        
        # Should not raise exceptions
        validate_parameters(parameters, meta_parameters)
    
    def test_partial_parameters(self, meta_parameters):
        """Test validation with subset of parameters."""
        # Only validate provided parameters
        parameters = {
            "window": 10,
            "threshold": 0.5
            # Other parameters not provided
        }
        
        # Should not raise exceptions
        validate_parameters(parameters, meta_parameters)
