"""
Unit tests for the custom exception classes and error middleware.
"""

import pytest
import logging
from src.core.exceptions import (
    ADMFTraderError, ConfigError, SchemaValidationError, EventError,
    EventHandlerError, DataError, DataSourceError, StrategyError,
    StrategyConfigError, StrategyExecutionError, RiskError, PositionError,
    OrderError, OrderValidationError, OrderExecutionError, BacktestError,
    AnalyticsError, OptimizationError, ParameterSpaceError, ObjectiveFunctionError,
    OptimizationTimeoutError, ErrorMiddleware
)


@pytest.mark.unit
@pytest.mark.core
class TestExceptions:
    
    def test_basic_exception_hierarchy(self):
        """Test that exception hierarchy is correctly established."""
        # All custom exceptions should inherit from ADMFTraderError
        assert issubclass(ConfigError, ADMFTraderError)
        assert issubclass(EventError, ADMFTraderError)
        assert issubclass(DataError, ADMFTraderError)
        assert issubclass(StrategyError, ADMFTraderError)
        assert issubclass(RiskError, ADMFTraderError)
        assert issubclass(OrderError, ADMFTraderError)
        assert issubclass(BacktestError, ADMFTraderError)
        assert issubclass(AnalyticsError, ADMFTraderError)
        assert issubclass(OptimizationError, ADMFTraderError)
        
        # Test second level exceptions
        assert issubclass(SchemaValidationError, ConfigError)
        assert issubclass(EventHandlerError, EventError)
        assert issubclass(DataSourceError, DataError)
        assert issubclass(StrategyConfigError, StrategyError)
        assert issubclass(StrategyExecutionError, StrategyError)
        assert issubclass(PositionError, RiskError)
        assert issubclass(OrderValidationError, OrderError)
        assert issubclass(OrderExecutionError, OrderError)
        assert issubclass(ParameterSpaceError, OptimizationError)
        assert issubclass(ObjectiveFunctionError, OptimizationError)
        assert issubclass(OptimizationTimeoutError, OptimizationError)
    
    def test_base_exception_message(self):
        """Test base exception message."""
        # Default message
        error = ADMFTraderError()
        assert str(error) == "An error occurred in the ADMF-Trader system"
        
        # Custom message
        error = ADMFTraderError("Custom error message")
        assert str(error) == "Custom error message"
    
    def test_schema_validation_error(self):
        """Test SchemaValidationError with errors list."""
        errors = ["Field 'x' is required", "Value for field 'y' must be numeric"]
        error = SchemaValidationError(errors=errors)
        
        # Check error message contains all error details
        error_str = str(error)
        assert "Configuration schema validation failed" in error_str
        assert "Field 'x' is required" in error_str
        assert "Value for field 'y' must be numeric" in error_str
    
    def test_event_handler_error(self):
        """Test EventHandlerError with context details."""
        original_error = ValueError("Invalid value")
        error = EventHandlerError(
            event_type="BAR",
            handler_name="on_bar_handler",
            original_error=original_error
        )
        
        # Check error message contains context details
        error_str = str(error)
        assert "Event handler error" in error_str
        assert "for event type 'BAR'" in error_str
        assert "in handler 'on_bar_handler'" in error_str
        assert "Invalid value" in error_str
    
    def test_data_source_error(self):
        """Test DataSourceError with context details."""
        error = DataSourceError(
            source_name="CSVDataSource",
            symbol="AAPL",
            message="File not found"
        )
        
        # Check error message contains context details
        error_str = str(error)
        assert "Data source error" in error_str
        assert "in source 'CSVDataSource'" in error_str
        assert "for symbol 'AAPL'" in error_str
        assert "File not found" in error_str
    
    def test_strategy_config_error(self):
        """Test StrategyConfigError with context details."""
        error = StrategyConfigError(
            strategy_name="MACrossover",
            parameter="fast_window",
            message="Must be positive integer"
        )
        
        # Check error message contains context details
        error_str = str(error)
        assert "Strategy configuration error" in error_str
        assert "in strategy 'MACrossover'" in error_str
        assert "for parameter 'fast_window'" in error_str
        assert "Must be positive integer" in error_str
    
    def test_strategy_execution_error(self):
        """Test StrategyExecutionError with context details."""
        original_error = ZeroDivisionError("division by zero")
        error = StrategyExecutionError(
            strategy_name="MACrossover",
            method="calculate_signal",
            original_error=original_error
        )
        
        # Check error message contains context details
        error_str = str(error)
        assert "Strategy execution error" in error_str
        assert "in strategy 'MACrossover'" in error_str
        assert "in method 'calculate_signal'" in error_str
        assert "division by zero" in error_str
    
    def test_position_error(self):
        """Test PositionError with context details."""
        error = PositionError(
            symbol="AAPL",
            message="Insufficient shares for sell order"
        )
        
        # Check error message contains context details
        error_str = str(error)
        assert "Position error" in error_str
        assert "for symbol 'AAPL'" in error_str
        assert "Insufficient shares for sell order" in error_str
    
    def test_order_validation_error(self):
        """Test OrderValidationError with context details."""
        error = OrderValidationError(
            order_id="order_123",
            reason="Quantity must be positive"
        )
        
        # Check error message contains context details
        error_str = str(error)
        assert "Order validation error" in error_str
        assert "for order 'order_123'" in error_str
        assert "Quantity must be positive" in error_str
    
    def test_order_execution_error(self):
        """Test OrderExecutionError with context details."""
        error = OrderExecutionError(
            order_id="order_123",
            reason="Market closed",
            original_error=RuntimeError("API connection timeout")
        )
        
        # Check error message contains context details
        error_str = str(error)
        assert "Order execution error" in error_str
        assert "for order 'order_123'" in error_str
        assert "Market closed" in error_str
        # Original error not included since reason is provided
        assert "API connection timeout" not in error_str
        
        # Test with original error but no reason
        error = OrderExecutionError(
            order_id="order_123",
            original_error=RuntimeError("API connection timeout")
        )
        error_str = str(error)
        assert "API connection timeout" in error_str
    
    def test_optimization_timeout_error(self):
        """Test OptimizationTimeoutError with time details."""
        error = OptimizationTimeoutError(
            elapsed_time=120.5,
            max_time=60.0
        )
        
        # Check error message contains time details
        error_str = str(error)
        assert "Optimization timeout" in error_str
        assert "120.50s elapsed" in error_str
        assert "max: 60.00s" in error_str
    
    def test_objective_function_error(self):
        """Test ObjectiveFunctionError with parameters."""
        parameters = {
            "fast_window": 5,
            "slow_window": 15,
            "threshold": 0.01
        }
        error = ObjectiveFunctionError(
            message="Negative sharpe ratio",
            parameters=parameters
        )
        
        # Check error message contains parameters
        error_str = str(error)
        assert "Negative sharpe ratio" in error_str
        assert "parameters" in error_str
        assert "fast_window=5" in error_str
        assert "slow_window=15" in error_str
        assert "threshold=0.01" in error_str


@pytest.mark.unit
@pytest.mark.core
class TestErrorMiddleware:
    
    @pytest.fixture
    def error_middleware(self):
        """Create an error middleware instance."""
        # Setup a logger that doesn't actually log to avoid test output
        logger = logging.getLogger("null")
        logger.addHandler(logging.NullHandler())
        return ErrorMiddleware(logger)
    
    def test_handle_success(self, error_middleware):
        """Test successful function execution."""
        def success_func(a, b):
            return a + b
        
        result = error_middleware.handle(success_func, 1, 2)
        assert result == 3
    
    def test_handle_known_error(self, error_middleware):
        """Test handling of known error types."""
        def error_func():
            raise ConfigError("Bad config")
        
        with pytest.raises(ConfigError):
            error_middleware.handle(error_func)
    
    def test_handle_unknown_error(self, error_middleware):
        """Test handling of unknown error types."""
        def error_func():
            raise ValueError("Bad value")
        
        with pytest.raises(ADMFTraderError) as excinfo:
            error_middleware.handle(error_func)
        
        # Unknown errors should be wrapped in ADMFTraderError
        assert "Unexpected error" in str(excinfo.value)
        assert "Bad value" in str(excinfo.value)
    
    def test_handle_safely_success(self, error_middleware):
        """Test safe handling with successful function."""
        def success_func(a, b):
            return a + b
        
        result = error_middleware.handle_safely(success_func, 1, 2)
        assert result == 3
    
    def test_handle_safely_error(self, error_middleware):
        """Test safe handling with error function."""
        def error_func():
            raise ValueError("Bad value")
        
        # Should return default value on error
        result = error_middleware.handle_safely(error_func, default_return="default")
        assert result == "default"
    
    def test_handle_safely_custom_default(self, error_middleware):
        """Test safe handling with custom default value."""
        def error_func():
            raise ZeroDivisionError("division by zero")
        
        # Test different default values
        assert error_middleware.handle_safely(error_func, default_return=None) is None
        assert error_middleware.handle_safely(error_func, default_return=42) == 42
        assert error_middleware.handle_safely(error_func, default_return=[]) == []
        
        # Test with no default (should return None)
        assert error_middleware.handle_safely(error_func) is None
    
    def test_handle_with_args_kwargs(self, error_middleware):
        """Test handling with various argument patterns."""
        def complex_func(a, b=2, *args, **kwargs):
            return a + b + sum(args) + sum(kwargs.values())
        
        # Test with positional args
        result = error_middleware.handle(complex_func, 1, 2)
        assert result == 3
        
        # Test with keyword args
        result = error_middleware.handle(complex_func, a=1, b=3)
        assert result == 4
        
        # Test with *args
        result = error_middleware.handle(complex_func, 1, 2, 3, 4)
        assert result == 10
        
        # Test with **kwargs
        result = error_middleware.handle(complex_func, 1, c=3, d=4)
        assert result == 10
        
        # Test with mixed args
        result = error_middleware.handle(complex_func, 1, 2, 3, c=4, d=5)
        assert result == 15
