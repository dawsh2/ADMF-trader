"""
Structured logging implementation for ADMF-Trader.

This module provides enhanced logging with context, correlation IDs,
and performance tracking capabilities.
"""

import os
import sys
import time
import json
import uuid
import logging
import inspect
import threading
import functools
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Union

# Thread-local storage for context
_thread_local = threading.local()


class StructuredLogger:
    """Logger with structured logging capabilities and context tracking."""
    
    def __init__(self, name: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """Initialize structured logger.
        
        Args:
            name: Logger name (default: module name of caller)
            logger: Existing logger to wrap (default: None)
        """
        if name is None:
            # Get caller's module name
            frame = inspect.currentframe()
            if frame:
                try:
                    frame = frame.f_back
                    if frame:
                        module = inspect.getmodule(frame)
                        if module:
                            name = module.__name__
                except:
                    pass
            
            # Default if we couldn't get caller's module
            if name is None:
                name = "admf_trader"
        
        self.logger = logger or logging.getLogger(name)
        self.context = {}
    
    def with_context(self, **context) -> 'StructuredLogger':
        """Create a new logger with additional context.
        
        Args:
            **context: Context values to add
            
        Returns:
            New StructuredLogger instance with combined context
        """
        new_logger = StructuredLogger(logger=self.logger)
        new_logger.context = {**self.context, **context}
        return new_logger
    
    def _get_context(self, additional_context=None) -> Dict[str, Any]:
        """Get combined context from all sources.
        
        Args:
            additional_context: Additional context to include
            
        Returns:
            Combined context dictionary
        """
        # Start with thread-local context
        combined_context = {}
        if hasattr(_thread_local, 'context'):
            combined_context.update(_thread_local.context)
        
        # Add instance context
        combined_context.update(self.context)
        
        # Add additional context
        if additional_context:
            combined_context.update(additional_context)
        
        return combined_context
    
    def _format_log_message(self, msg: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format message with context as a dictionary for structured logging.
        
        Args:
            msg: Log message
            context: Additional context
            
        Returns:
            Structured log entry as dictionary
        """
        combined_context = self._get_context(context)
        
        log_entry = {
            "message": msg,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Add context if present
        if combined_context:
            log_entry["context"] = combined_context
        
        return log_entry
    
    def debug(self, msg: str, *args, **kwargs):
        """Log a debug message with context.
        
        Args:
            msg: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional options including:
                - context: Additional context dictionary
                - exc_info: Exception info
                - stack_info: Stack info
                - extra: Extra info for logger
        """
        context = kwargs.pop('context', None)
        
        if self.logger.isEnabledFor(logging.DEBUG):
            log_entry = self._format_log_message(msg, context)
            
            # Format message with args if provided
            if args:
                formatted_msg = msg % args
            else:
                formatted_msg = msg
            
            # Convert to JSON if needed, otherwise just use formatted message
            if hasattr(_thread_local, 'use_json') and _thread_local.use_json:
                formatted_msg = json.dumps(log_entry)
            
            self.logger.debug(formatted_msg, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """Log an info message with context.
        
        Args:
            msg: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional options including:
                - context: Additional context dictionary
                - exc_info: Exception info
                - stack_info: Stack info
                - extra: Extra info for logger
        """
        context = kwargs.pop('context', None)
        
        if self.logger.isEnabledFor(logging.INFO):
            log_entry = self._format_log_message(msg, context)
            
            # Format message with args if provided
            if args:
                formatted_msg = msg % args
            else:
                formatted_msg = msg
            
            # Convert to JSON if needed, otherwise just use formatted message
            if hasattr(_thread_local, 'use_json') and _thread_local.use_json:
                formatted_msg = json.dumps(log_entry)
            
            self.logger.info(formatted_msg, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Log a warning message with context.
        
        Args:
            msg: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional options including:
                - context: Additional context dictionary
                - exc_info: Exception info
                - stack_info: Stack info
                - extra: Extra info for logger
        """
        context = kwargs.pop('context', None)
        
        if self.logger.isEnabledFor(logging.WARNING):
            log_entry = self._format_log_message(msg, context)
            
            # Format message with args if provided
            if args:
                formatted_msg = msg % args
            else:
                formatted_msg = msg
            
            # Convert to JSON if needed, otherwise just use formatted message
            if hasattr(_thread_local, 'use_json') and _thread_local.use_json:
                formatted_msg = json.dumps(log_entry)
            
            self.logger.warning(formatted_msg, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Log an error message with context.
        
        Args:
            msg: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional options including:
                - context: Additional context dictionary
                - exc_info: Exception info
                - stack_info: Stack info
                - extra: Extra info for logger
        """
        context = kwargs.pop('context', None)
        
        if self.logger.isEnabledFor(logging.ERROR):
            log_entry = self._format_log_message(msg, context)
            
            # Format message with args if provided
            if args:
                formatted_msg = msg % args
            else:
                formatted_msg = msg
            
            # Convert to JSON if needed, otherwise just use formatted message
            if hasattr(_thread_local, 'use_json') and _thread_local.use_json:
                formatted_msg = json.dumps(log_entry)
            
            self.logger.error(formatted_msg, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """Log a critical message with context.
        
        Args:
            msg: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional options including:
                - context: Additional context dictionary
                - exc_info: Exception info
                - stack_info: Stack info
                - extra: Extra info for logger
        """
        context = kwargs.pop('context', None)
        
        if self.logger.isEnabledFor(logging.CRITICAL):
            log_entry = self._format_log_message(msg, context)
            
            # Format message with args if provided
            if args:
                formatted_msg = msg % args
            else:
                formatted_msg = msg
            
            # Convert to JSON if needed, otherwise just use formatted message
            if hasattr(_thread_local, 'use_json') and _thread_local.use_json:
                formatted_msg = json.dumps(log_entry)
            
            self.logger.critical(formatted_msg, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        """Log an exception message with context.
        
        Args:
            msg: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional options including:
                - context: Additional context dictionary
                - exc_info: Exception info (default: True)
                - stack_info: Stack info
                - extra: Extra info for logger
        """
        context = kwargs.pop('context', None)
        
        # Ensure exc_info is True if not provided
        if 'exc_info' not in kwargs:
            kwargs['exc_info'] = True
        
        # Extract exception details for context
        if kwargs['exc_info'] is True:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if exc_value:
                if context is None:
                    context = {}
                context.update({
                    "exception_type": exc_type.__name__ if exc_type else "Unknown",
                    "exception_message": str(exc_value)
                })
        
        self.error(msg, *args, context=context, **kwargs)
    
    @staticmethod
    def context_scope(**context):
        """Context manager to add context to all logs within scope.
        
        Args:
            **context: Context values to include
            
        Returns:
            Context manager
        """
        class ContextScope:
            def __enter__(self):
                # Store previous context
                self.previous_context = getattr(_thread_local, 'context', {})
                
                # Set new context (merged with previous)
                if not hasattr(_thread_local, 'context'):
                    _thread_local.context = {}
                
                _thread_local.context = {**self.previous_context, **context}
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                # Restore previous context
                _thread_local.context = self.previous_context
        
        return ContextScope()
    
    @staticmethod
    def use_json(enabled=True):
        """Context manager to enable/disable JSON logging.
        
        Args:
            enabled: Whether to enable JSON logging
            
        Returns:
            Context manager
        """
        class JsonLogScope:
            def __enter__(self):
                # Store previous setting
                self.previous = getattr(_thread_local, 'use_json', False)
                
                # Set new setting
                _thread_local.use_json = enabled
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                # Restore previous setting
                _thread_local.use_json = self.previous
        
        return JsonLogScope()
    
    @staticmethod
    def with_correlation_id(correlation_id=None):
        """Context manager to add correlation ID to logs.
        
        Args:
            correlation_id: ID to use (default: generated UUID)
            
        Returns:
            Context manager
        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        return StructuredLogger.context_scope(correlation_id=correlation_id)
    
    @staticmethod
    def log_execution_time(logger=None, level=logging.INFO):
        """Decorator to log function execution time.
        
        Args:
            logger: Logger to use (default: create new logger)
            level: Log level to use
            
        Returns:
            Decorator function
        """
        def decorator(func):
            # Get logger to use
            log = logger
            if log is None:
                log = StructuredLogger(func.__module__)
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                
                # Log the execution time
                log.log(
                    level,
                    f"Function {func.__name__} executed in {duration:.6f} seconds",
                    context={"duration": duration, "function": func.__name__}
                )
                
                return result
            
            return wrapper
        
        return decorator


# Global function to get a logger
def get_logger(name=None) -> StructuredLogger:
    """Get a structured logger.
    
    Args:
        name: Logger name (default: caller's module name)
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


# Configure logging system
def configure_logging(
    level=logging.INFO,
    log_file=None,
    json_format=False,
    include_timestamp=True,
    include_level=True,
    include_name=True,
    console=True
):
    """Configure the logging system.
    
    Args:
        level: Logging level
        log_file: File to log to (default: None)
        json_format: Whether to use JSON format
        include_timestamp: Whether to include timestamp in log format
        include_level: Whether to include level in log format
        include_name: Whether to include logger name in log format
        console: Whether to log to console
    """
    # Create formatter
    format_parts = []
    if include_timestamp:
        format_parts.append("%(asctime)s")
    if include_level:
        format_parts.append("%(levelname)s")
    if include_name:
        format_parts.append("%(name)s")
    format_parts.append("%(message)s")
    
    log_format = " - ".join(format_parts)
    formatter = logging.Formatter(log_format)
    
    # Set global logging level
    logging.root.setLevel(level)
    
    # Configure handlers
    handlers = []
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # File handler
    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Apply handlers to root logger
    for handler in handlers:
        logging.root.addHandler(handler)
    
    # Set default setting for JSON format
    _thread_local.use_json = json_format


class PerformanceMetrics:
    """Track and log performance metrics."""
    
    def __init__(self, name, logger=None):
        """Initialize performance metrics.
        
        Args:
            name: Metrics name
            logger: Logger to use (default: create new logger)
        """
        self.name = name
        self.logger = logger or get_logger(f"metrics.{name}")
        self.metrics = {}
        self.lock = threading.Lock()
    
    def record(self, metric_name, value):
        """Record a metric value.
        
        Args:
            metric_name: Name of the metric
            value: Value to record
        """
        with self.lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = []
            
            self.metrics[metric_name].append(value)
            
            # Log the value
            self.logger.debug(
                f"Recorded {metric_name}: {value}",
                context={"metric": metric_name, "value": value}
            )
    
    def record_time(self, metric_name):
        """Context manager to record execution time.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Context manager
        """
        class TimeRecorder:
            def __init__(self, metrics, name):
                self.metrics = metrics
                self.name = name
                self.start_time = None
            
            def __enter__(self):
                self.start_time = time.time()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                self.metrics.record(self.name, duration)
        
        return TimeRecorder(self, metric_name)
    
    def time_function(self, metric_name):
        """Decorator to record function execution time.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self.record_time(metric_name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_stats(self, metric_name):
        """Get statistics for a metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Dictionary of statistics or None if no data
        """
        import statistics  # Import here to avoid dependency for basic logging
        
        with self.lock:
            values = self.metrics.get(metric_name, [])
            
            if not values:
                return None
            
            stats = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'mean': statistics.mean(values),
                'median': statistics.median(values)
            }
            
            # Add standard deviation if we have at least 2 values
            if len(values) > 1:
                stats['stdev'] = statistics.stdev(values)
            
            return stats
    
    def log_stats(self, level=logging.INFO):
        """Log statistics for all metrics.
        
        Args:
            level: Log level to use
        """
        with self.lock:
            for metric_name in sorted(self.metrics.keys()):
                stats = self.get_stats(metric_name)
                if stats:
                    self.logger.log(
                        level,
                        f"{metric_name}: count={stats['count']}, "
                        f"min={stats['min']:.6f}, max={stats['max']:.6f}, "
                        f"mean={stats['mean']:.6f}, median={stats['median']:.6f}",
                        context={"metric": metric_name, "stats": stats}
                    )
    
    def reset(self):
        """Reset all metrics."""
        with self.lock:
            self.metrics.clear()
