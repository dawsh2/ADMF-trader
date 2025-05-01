"""
Custom exception classes for the ADMF-Trader system.
Providing a structured approach to error handling across all modules.
"""


class ADMFTraderError(Exception):
    """Base exception class for all ADMF-Trader errors."""
    def __init__(self, message="An error occurred in the ADMF-Trader system"):
        self.message = message
        super().__init__(self.message)


class ConfigError(ADMFTraderError):
    """Exception raised for errors in the configuration system."""
    def __init__(self, message="Error in system configuration"):
        super().__init__(message)


class SchemaValidationError(ConfigError):
    """Exception raised when configuration fails schema validation."""
    def __init__(self, message="Configuration schema validation failed", errors=None):
        self.errors = errors or []
        full_message = f"{message}: {'; '.join(str(e) for e in self.errors)}"
        super().__init__(full_message)


class EventError(ADMFTraderError):
    """Exception raised for errors in the event system."""
    def __init__(self, message="Error in event processing"):
        super().__init__(message)


class EventHandlerError(EventError):
    """Exception raised when an event handler fails."""
    def __init__(self, event_type=None, handler_name=None, original_error=None):
        self.event_type = event_type
        self.handler_name = handler_name
        self.original_error = original_error
        
        message_parts = ["Event handler error"]
        if event_type:
            message_parts.append(f"for event type '{event_type}'")
        if handler_name:
            message_parts.append(f"in handler '{handler_name}'")
        if original_error:
            message_parts.append(f": {str(original_error)}")
        
        message = " ".join(message_parts)
        super().__init__(message)


class DataError(ADMFTraderError):
    """Exception raised for errors in data handling."""
    def __init__(self, message="Error in data processing"):
        super().__init__(message)


class DataSourceError(DataError):
    """Exception raised when a data source fails to load or provide data."""
    def __init__(self, source_name=None, symbol=None, message=None):
        self.source_name = source_name
        self.symbol = symbol
        
        message_parts = ["Data source error"]
        if source_name:
            message_parts.append(f"in source '{source_name}'")
        if symbol:
            message_parts.append(f"for symbol '{symbol}'")
        if message:
            message_parts.append(f": {message}")
        
        full_message = " ".join(message_parts)
        super().__init__(full_message)


class StrategyError(ADMFTraderError):
    """Exception raised for errors in strategy components."""
    def __init__(self, message="Error in strategy processing"):
        super().__init__(message)


class StrategyConfigError(StrategyError):
    """Exception raised when a strategy is incorrectly configured."""
    def __init__(self, strategy_name=None, parameter=None, message=None):
        self.strategy_name = strategy_name
        self.parameter = parameter
        
        message_parts = ["Strategy configuration error"]
        if strategy_name:
            message_parts.append(f"in strategy '{strategy_name}'")
        if parameter:
            message_parts.append(f"for parameter '{parameter}'")
        if message:
            message_parts.append(f": {message}")
        
        full_message = " ".join(message_parts)
        super().__init__(full_message)


class StrategyExecutionError(StrategyError):
    """Exception raised when a strategy fails during execution."""
    def __init__(self, strategy_name=None, method=None, original_error=None):
        self.strategy_name = strategy_name
        self.method = method
        self.original_error = original_error
        
        message_parts = ["Strategy execution error"]
        if strategy_name:
            message_parts.append(f"in strategy '{strategy_name}'")
        if method:
            message_parts.append(f"in method '{method}'")
        if original_error:
            message_parts.append(f": {str(original_error)}")
        
        full_message = " ".join(message_parts)
        super().__init__(full_message)


class RiskError(ADMFTraderError):
    """Exception raised for errors in risk management."""
    def __init__(self, message="Error in risk management"):
        super().__init__(message)


class PositionError(RiskError):
    """Exception raised for errors in position management."""
    def __init__(self, symbol=None, message=None):
        self.symbol = symbol
        
        message_parts = ["Position error"]
        if symbol:
            message_parts.append(f"for symbol '{symbol}'")
        if message:
            message_parts.append(f": {message}")
        
        full_message = " ".join(message_parts)
        super().__init__(full_message)


class OrderError(ADMFTraderError):
    """Exception raised for errors in order processing."""
    def __init__(self, message="Error in order processing"):
        super().__init__(message)


class OrderValidationError(OrderError):
    """Exception raised when an order fails validation."""
    def __init__(self, order_id=None, reason=None):
        self.order_id = order_id
        self.reason = reason
        
        message_parts = ["Order validation error"]
        if order_id:
            message_parts.append(f"for order '{order_id}'")
        if reason:
            message_parts.append(f": {reason}")
        
        full_message = " ".join(message_parts)
        super().__init__(full_message)


class OrderExecutionError(OrderError):
    """Exception raised when an order execution fails."""
    def __init__(self, order_id=None, reason=None, original_error=None):
        self.order_id = order_id
        self.reason = reason
        self.original_error = original_error
        
        message_parts = ["Order execution error"]
        if order_id:
            message_parts.append(f"for order '{order_id}'")
        if reason:
            message_parts.append(f": {reason}")
        if original_error and not reason:
            message_parts.append(f": {str(original_error)}")
        
        full_message = " ".join(message_parts)
        super().__init__(full_message)


class BacktestError(ADMFTraderError):
    """Exception raised for errors in backtesting."""
    def __init__(self, message="Error in backtest execution"):
        super().__init__(message)


class AnalyticsError(ADMFTraderError):
    """Exception raised for errors in analytics processing."""
    def __init__(self, message="Error in analytics processing"):
        super().__init__(message)


class OptimizationError(ADMFTraderError):
    """Base class for optimization-related errors."""
    def __init__(self, message="Error in optimization process"):
        super().__init__(message)


class ParameterSpaceError(OptimizationError):
    """Exception raised for errors in parameter space definition."""
    def __init__(self, parameter=None, message=None):
        self.parameter = parameter
        
        message_parts = ["Parameter space error"]
        if parameter:
            message_parts.append(f"for parameter '{parameter}'")
        if message:
            message_parts.append(f": {message}")
        
        full_message = " ".join(message_parts)
        super().__init__(full_message)


class ObjectiveFunctionError(OptimizationError):
    """Exception raised for errors in objective function evaluation."""
    def __init__(self, message="Error in objective function evaluation", parameters=None):
        self.parameters = parameters
        
        message_parts = [message]
        if parameters:
            param_str = ", ".join(f"{k}={v}" for k, v in parameters.items())
            message_parts.append(f" with parameters: {param_str}")
        
        full_message = "".join(message_parts)
        super().__init__(full_message)


class OptimizationTimeoutError(OptimizationError):
    """Exception raised when optimization exceeds time limit."""
    def __init__(self, elapsed_time=None, max_time=None):
        self.elapsed_time = elapsed_time
        self.max_time = max_time
        
        message_parts = ["Optimization timeout"]
        if elapsed_time and max_time:
            message_parts.append(f": {elapsed_time:.2f}s elapsed (max: {max_time:.2f}s)")
        
        full_message = " ".join(message_parts)
        super().__init__(full_message)


# Custom error middleware for graceful handling of exceptions
class ErrorMiddleware:
    """Middleware for handling exceptions in a consistent way across the system."""
    
    def __init__(self, logger=None):
        """Initialize the error middleware.
        
        Args:
            logger: Optional logger instance for logging errors
        """
        self.logger = logger
    
    def handle(self, func, *args, **kwargs):
        """Execute a function with error handling.
        
        Args:
            func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function or None if an error occurs
            
        Raises:
            ADMFTraderError: Raised for known error types
        """
        try:
            return func(*args, **kwargs)
        except ADMFTraderError as e:
            # Known error types - log and re-raise
            if self.logger:
                self.logger.error(f"ADMF-Trader Error: {e}")
            raise
        except Exception as e:
            # Unknown errors - wrap in ADMFTraderError
            if self.logger:
                self.logger.exception(f"Unexpected error: {e}")
            raise ADMFTraderError(f"Unexpected error: {str(e)}")
    
    def handle_safely(self, func, *args, default_return=None, **kwargs):
        """Execute a function with error handling, returning a default value on error.
        
        Args:
            func: The function to execute
            args: Positional arguments for the function
            default_return: Value to return if an error occurs
            kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function or default_return if an error occurs
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log all errors
            if self.logger:
                self.logger.exception(f"Error handled safely: {e}")
            return default_return
