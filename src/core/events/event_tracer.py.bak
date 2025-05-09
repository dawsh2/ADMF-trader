"""
Event tracer system for diagnostic and debugging purposes.
Provides an abstract base class and specialized implementations for tracking event flow.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict

from .event_types import Event, EventType

logger = logging.getLogger(__name__)

class EventTracerBase(ABC):
    """
    Abstract base class for event tracers.
    Provides standardized interface for tracking and analyzing event flow.
    """
    
    def __init__(self, event_bus, name=None):
        """
        Initialize the event tracer.
        
        Args:
            event_bus: Event bus to track events from
            name: Optional name for the tracer
        """
        self.event_bus = event_bus
        self.name = name or self.__class__.__name__
        self._register_handlers()
        logger.info(f"Initialized event tracer: {self.name}")
    
    @abstractmethod
    def _register_handlers(self):
        """Register handlers for events to be traced."""
        pass
    
    @abstractmethod
    def get_summary(self):
        """Get a summary of traced events."""
        pass
    
    @abstractmethod
    def reset(self):
        """Reset the tracer state."""
        pass
    
    def track_handler_call(self, event_type, component_name):
        """
        Track when a component handler is called.
        
        Args:
            event_type: Type of event being handled
            component_name: Name of component handling the event
        """
        # Must be implemented by concrete classes that use this feature
        pass

class SignalFlowTracer(EventTracerBase):
    """
    Specialized tracer for debugging signal flow.
    Tracks signals, orders, and fills through the system.
    """
    
    def __init__(self, event_bus, name=None):
        """Initialize the signal flow tracer."""
        self.bar_events = []
        self.signal_events = []
        self.order_events = []
        self.fill_events = []
        self.all_events = []
        self.handlers_called = defaultdict(int)
        super().__init__(event_bus, name)
    
    def _register_handlers(self):
        """Register handlers for relevant event types."""
        self.event_bus.register(EventType.BAR, self._on_bar)
        self.event_bus.register(EventType.SIGNAL, self._on_signal)
        self.event_bus.register(EventType.ORDER, self._on_order)
        self.event_bus.register(EventType.FILL, self._on_fill)
    
    def _on_bar(self, event):
        """Record bar event."""
        bar_data = {
            'id': id(event),
            'timestamp': event.get_timestamp(),
            'symbol': event.get_symbol(),
            'price': event.get_close()
        }
        self.bar_events.append(bar_data)
        self.all_events.append(('BAR', event.get_timestamp(), bar_data))
        logger.debug(f"TRACE: Bar event {event.get_symbol()} {event.get_close():.2f}")
    
    def _on_signal(self, event):
        """Record signal event."""
        signal_data = {
            'id': id(event),
            'timestamp': event.get_timestamp(),
            'symbol': event.get_symbol(),
            'signal_value': event.get_signal_value(),
            'price': event.get_price()
        }
        self.signal_events.append(signal_data)
        self.all_events.append(('SIGNAL', event.get_timestamp(), signal_data))
        logger.debug(f"TRACE: Signal event {event.get_symbol()} {event.get_signal_value()}")
    
    def _on_order(self, event):
        """Record order event."""
        order_data = {
            'id': id(event),
            'timestamp': event.get_timestamp(),
            'symbol': event.get_symbol(),
            'order_id': event.get_order_id(),
            'direction': event.get_direction(),
            'quantity': event.get_quantity(),
            'price': event.get_price()
        }
        self.order_events.append(order_data)
        self.all_events.append(('ORDER', event.get_timestamp(), order_data))
        logger.debug(f"TRACE: Order event {event.get_symbol()} {event.get_direction()}")
    
    def _on_fill(self, event):
        """Record fill event."""
        fill_data = {
            'id': id(event),
            'timestamp': event.get_timestamp(),
            'symbol': event.get_symbol(),
            'order_id': event.get_order_id(),
            'direction': event.get_direction(),
            'quantity': event.get_quantity(),
            'price': event.get_price()
        }
        self.fill_events.append(fill_data)
        self.all_events.append(('FILL', event.get_timestamp(), fill_data))
        logger.debug(f"TRACE: Fill event {event.get_symbol()} {event.get_direction()}")
    
    def track_handler_call(self, event_type, component_name):
        """Track when a component handler is called."""
        key = f"{event_type}:{component_name}"
        self.handlers_called[key] += 1
    
    def get_summary(self):
        """Get a summary of event flow."""
        summary = {
            'bar_events': len(self.bar_events),
            'signal_events': len(self.signal_events),
            'order_events': len(self.order_events),
            'fill_events': len(self.fill_events),
            'total_events': len(self.all_events),
            'handlers_called': dict(self.handlers_called)
        }
        
        # Add signal breakdown
        buy_signals = len([s for s in self.signal_events if s['signal_value'] > 0])
        sell_signals = len([s for s in self.signal_events if s['signal_value'] < 0])
        summary['buy_signals'] = buy_signals
        summary['sell_signals'] = sell_signals
        
        # Add ratios
        if len(self.signal_events) > 0:
            summary['orders_per_signal'] = len(self.order_events) / len(self.signal_events)
        if len(self.order_events) > 0:
            summary['fills_per_order'] = len(self.fill_events) / len(self.order_events)
            
        return summary
    
    def print_summary(self):
        """Print summary of event flow to console."""
        summary = self.get_summary()
        
        print("\nEvent Flow Summary:")
        print(f"  Bar events: {summary['bar_events']}")
        print(f"  Signal events: {summary['signal_events']}")
        print(f"  Order events: {summary['order_events']}")
        print(f"  Fill events: {summary['fill_events']}")
        
        # Print ratios
        print("\nSignal to Order to Fill Ratios:")
        if 'orders_per_signal' in summary:
            print(f"  Orders per signal: {summary['orders_per_signal']:.2f}")
        if 'fills_per_order' in summary:
            print(f"  Fills per order: {summary['fills_per_order']:.2f}")
        
        # Print signal breakdown
        print(f"\nSignal breakdown:")
        print(f"  BUY signals: {summary['buy_signals']}")
        print(f"  SELL signals: {summary['sell_signals']}")
        
        # Print handler calls
        print("\nHandler call counts:")
        for key, count in sorted(self.handlers_called.items()):
            print(f"  {key}: {count}")
    
    def analyze_duplicates(self):
        """
        Analyze event flow for duplicates.
        
        Returns:
            List of potential duplicate signals
        """
        # Check for duplicate signals
        symbols = set(s['symbol'] for s in self.signal_events)
        duplicates = []
        
        for symbol in symbols:
            symbol_signals = [s for s in self.signal_events if s['symbol'] == symbol]
            symbol_signals.sort(key=lambda x: x['timestamp'])
            
            # Check for signals close in time
            for i in range(len(symbol_signals) - 1):
                s1 = symbol_signals[i]
                s2 = symbol_signals[i + 1]
                
                # Check if signals are close in time and same direction
                time_diff = (s2['timestamp'] - s1['timestamp']).total_seconds()
                if time_diff < 0.01 and s1['signal_value'] == s2['signal_value']:
                    duplicates.append((s1, s2, time_diff))
        
        # Print summary of duplicates
        if duplicates:
            print(f"\nFound {len(duplicates)} potential duplicate signals:")
            for s1, s2, time_diff in duplicates[:5]:  # Show first 5
                print(f"  {s1['symbol']} value={s1['signal_value']}, time diff: {time_diff*1000:.2f}ms")
        else:
            print("\nNo duplicate signals found - FIX SUCCESSFUL!")
            
        return duplicates
    
    def reset(self):
        """Reset the tracer state."""
        self.bar_events.clear()
        self.signal_events.clear()
        self.order_events.clear()
        self.fill_events.clear()
        self.all_events.clear()
        self.handlers_called.clear()
        logger.info(f"Reset event tracer: {self.name}")

class PerformanceTracer(EventTracerBase):
    """
    Specialized tracer for performance monitoring.
    Tracks timing of events and handler execution.
    """
    
    def __init__(self, event_bus, name=None):
        """Initialize the performance tracer."""
        self.event_times = defaultdict(list)  # EventType -> list of processing times
        self.handler_times = defaultdict(list)  # handler name -> list of execution times
        self.event_counts = defaultdict(int)  # EventType -> count
        self.handler_counts = defaultdict(int)  # handler name -> count
        self.start_times = {}  # event_id -> start time
        super().__init__(event_bus, name)
    
    def _register_handlers(self):
        """Register handlers for all event types."""
        # Register for all event types with high priority
        for event_type in EventType:
            self.event_bus.register(event_type, self._on_event_start)
    
    def _on_event_start(self, event):
        """Record event start time."""
        import time
        event_id = event.get_id()
        self.start_times[event_id] = time.time()
        self.event_counts[event.get_type()] += 1
    
    def record_handler_execution(self, event_type, handler_name, execution_time):
        """
        Record handler execution time.
        
        Args:
            event_type: Type of event being handled
            handler_name: Name of handler
            execution_time: Time taken to execute handler in seconds
        """
        self.handler_times[handler_name].append(execution_time)
        self.handler_counts[handler_name] += 1
    
    def record_event_completion(self, event):
        """
        Record event completion time.
        
        Args:
            event: Event that completed processing
        """
        import time
        event_id = event.get_id()
        if event_id in self.start_times:
            end_time = time.time()
            execution_time = end_time - self.start_times[event_id]
            self.event_times[event.get_type()].append(execution_time)
            del self.start_times[event_id]
    
    def get_summary(self):
        """Get a summary of performance metrics."""
        import statistics
        
        summary = {
            'event_counts': dict(self.event_counts),
            'handler_counts': dict(self.handler_counts),
            'event_average_times': {},
            'handler_average_times': {}
        }
        
        # Calculate average event processing times
        for event_type, times in self.event_times.items():
            if times:
                summary['event_average_times'][event_type.name] = {
                    'avg': statistics.mean(times) * 1000,  # ms
                    'min': min(times) * 1000,  # ms
                    'max': max(times) * 1000,  # ms
                    'median': statistics.median(times) * 1000  # ms
                }
        
        # Calculate average handler execution times
        for handler_name, times in self.handler_times.items():
            if times:
                summary['handler_average_times'][handler_name] = {
                    'avg': statistics.mean(times) * 1000,  # ms
                    'min': min(times) * 1000,  # ms
                    'max': max(times) * 1000,  # ms
                    'median': statistics.median(times) * 1000  # ms
                }
                
        return summary
    
    def print_summary(self):
        """Print summary of performance metrics to console."""
        summary = self.get_summary()
        
        print("\nPerformance Summary:")
        print(f"  Total events processed: {sum(summary['event_counts'].values())}")
        
        print("\nEvent Counts:")
        for event_type, count in summary['event_counts'].items():
            print(f"  {event_type.name}: {count}")
        
        print("\nEvent Processing Times (ms):")
        for event_type, stats in summary['event_average_times'].items():
            print(f"  {event_type}: avg={stats['avg']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}")
        
        print("\nHandler Execution Times (ms):")
        for handler_name, stats in summary['handler_average_times'].items():
            print(f"  {handler_name}: avg={stats['avg']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}")
    
    def reset(self):
        """Reset the tracer state."""
        self.event_times.clear()
        self.handler_times.clear()
        self.event_counts.clear()
        self.handler_counts.clear()
        self.start_times.clear()
        logger.info(f"Reset performance tracer: {self.name}")

# Factory function to create appropriate tracer
def create_tracer(tracer_type, event_bus, name=None):
    """
    Create an event tracer of the specified type.
    
    Args:
        tracer_type: Type of tracer ("signal", "performance", etc.)
        event_bus: Event bus to track
        name: Optional name for the tracer
        
    Returns:
        EventTracerBase: The created tracer
    """
    tracer_types = {
        "signal": SignalFlowTracer,
        "performance": PerformanceTracer
    }
    
    if tracer_type not in tracer_types:
        raise ValueError(f"Unknown tracer type: {tracer_type}")
        
    return tracer_types[tracer_type](event_bus, name)
