"""
Global error handler for ADMF-Trader system.

This module provides centralized error handling across all system components,
with context enrichment, logging, and callback support.
"""

import logging
import traceback
import threading
import functools
import time
from typing import Dict, Any, Callable, List, Optional, Type

from src.core.exceptions import ADMFTraderError

# Thread-local storage for context
_thread_context = threading.local()

class ErrorHandler:
    """Global error handler for ADMF-Trader system."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the error handler.
        
        Args:
            logger: Logger instance to use for logging errors
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_callbacks: List[Callable] = []
        
    def register_callback(self, callback: Callable) -> None:
        """Register a callback to be called on error.
        
        Args:
            callback: Function to be called with (exception, context) when an error occurs
        """
        if callable(callback) and callback not in self.error_callbacks:
            self.error_callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable) -> bool:
        """Unregister a previously registered callback.
        
        Args:
            callback: Callback to unregister
            
        Returns:
            True if the callback was removed, False if it wasn't registered
        """
        if callback in self.error_callbacks:
            self.error_callbacks.remove(callback)
            return True
        return False
    
    def handle(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> Exception:
        """Handle an exception with context.
        
        Args:
            exception: The exception to handle
            context: Additional context for the exception
            
        Returns:
            The exception (potentially enriched with context)
        """
        # Combine explicit context with thread-local context
        combined_context = {}
        if hasattr(_thread_context, 'context'):
            combined_context.update(_thread_context.context)
        if context:
            combined_context.update(context)
        
        # Add context to exception if it's our type
        if isinstance(exception, ADMFTraderError):
            # Use exception's specific context mechanism if available
            if hasattr(exception, 'add_context'):
                for key, value in combined_context.items():
                    exception.add_context(key, value)
        
        # Determine log level and format message
        if isinstance(exception, ADMFTraderError):
            self.logger.error(f"ADMF-Trader Error: {exception}")
        else:
            self.logger.error(f"Unexpected error: {exception}")
            if combined_context:
                context_str = ', '.join(f"{k}={v}" for k, v in combined_context.items())
                self.logger.error(f"Context: {context_str}")
            self.logger.debug(traceback.format_exc())
        
        # Call all registered callbacks
        for callback in self.error_callbacks:
            try:
                callback(exception, combined_context)
            except Exception as callback_error:
                self.logger.error(f"Error in error callback: {callback_error}")
        
        return exception
    
    def __call__(self, func: Callable) -> Callable:
        """Use as decorator for functions that should use error handling.
        
        Args:
            func: Function to wrap with error handling
            
        Returns:
            Wrapped function with error handling
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "args": repr(args),
                    "kwargs": repr(kwargs),
                    "timestamp": time.time()
                }
                self.handle(e, context)
                raise
        return wrapper

    @staticmethod
    def with_context(**context) -> Callable:
        """Context manager/decorator to add context to any errors that occur.
        
        Args:
            **context: Context values to include with any errors
            
        Returns:
            Context manager or decorator function
        """
        class ContextManager:
            def __enter__(self):
                # Create context attribute if it doesn't exist
                if not hasattr(_thread_context, 'context'):
                    _thread_context.context = {}
                
                # Store previous context values
                self.previous = dict(_thread_context.context)
                
                # Update with new context
                _thread_context.context.update(context)
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                # Restore previous context
                _thread_context.context = self.previous
                # Don't suppress exceptions
                return False
                
            def __call__(self, func):
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    with self:
                        return func(*args, **kwargs)
                return wrapper
                
        return ContextManager()
    
    @staticmethod
    def clear_context() -> None:
        """Clear all thread-local context data."""
        if hasattr(_thread_context, 'context'):
            _thread_context.context.clear()
    
    def safely(self, func: Callable, *args, default=None, **kwargs) -> Any:
        """Execute a function with error handling, returning a default value on error.
        
        Args:
            func: Function to execute safely
            *args: Positional arguments for func
            default: Value to return if an error occurs (default: None)
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func or default if an error occurs
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            context = {
                "function": func.__name__,
                "args": repr(args),
                "kwargs": repr(kwargs),
                "default_return": repr(default),
                "timestamp": time.time()
            }
            self.handle(e, context)
            return default
    
    def retry(self, max_attempts: int = 3, delay: float = 1.0, 
              backoff: float = 2.0, exceptions: List[Type[Exception]] = None) -> Callable:
        """Decorator for retrying functions on failure.
        
        Args:
            max_attempts: Maximum number of attempts (default: 3)
            delay: Initial delay between attempts in seconds (default: 1.0)
            backoff: Multiplicative factor for delay between attempts (default: 2.0)
            exceptions: List of exception types to retry on (default: all)
            
        Returns:
            Decorated function with retry logic
        """
        exceptions = exceptions or [Exception]
        
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                attempt = 1
                current_delay = delay
                
                while attempt <= max_attempts:
                    try:
                        return func(*args, **kwargs)
                    except tuple(exceptions) as e:
                        context = {
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay": current_delay
                        }
                        
                        # Last attempt failed - handle and raise
                        if attempt == max_attempts:
                            self.handle(e, context)
                            raise
                        
                        # Log retry attempt
                        self.logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.2f}s"
                        )
                        
                        # Wait before next attempt
                        time.sleep(current_delay)
                        current_delay *= backoff
                        attempt += 1
            
            return wrapper
        
        return decorator


# Global instance
global_error_handler = ErrorHandler()
