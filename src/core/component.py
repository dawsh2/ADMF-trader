"""
Base component class with proper lifecycle management.

This provides a standard interface for all system components with
appropriate lifecycle methods for initialization, starting, stopping,
and resetting.
"""

import logging
from abc import ABC
from typing import Dict, Any, Optional

class Component(ABC):
    """
    Base class for all components with proper lifecycle management.
    
    Features:
    - Standard lifecycle methods (initialize, start, stop, reset)
    - Event bus integration
    - Logging support
    - Context-based dependency injection
    """
    
    def __init__(self, name: str):
        """
        Initialize the component.
        
        Args:
            name: Unique name for this component instance
        """
        self.name = name
        self.running = False
        self.context = None
        self.event_bus = None
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
    def initialize(self, context: Dict[str, Any]) -> None:
        """
        Set up dependencies using the provided context.
        
        Args:
            context: Dependencies and configuration needed by this component
        """
        self.context = context
        
        # Extract event bus from context
        if 'event_bus' in context:
            self.set_event_bus(context['event_bus'])
        
    def set_event_bus(self, event_bus) -> None:
        """
        Set the event bus for this component.
        
        Args:
            event_bus: Event bus instance
        """
        self.event_bus = event_bus
        
    def start(self) -> None:
        """Start the component's operation."""
        self.running = True
        self.logger.info(f"Component {self.name} started")
        
    def stop(self) -> None:
        """Stop the component's operation."""
        self.running = False
        self.logger.info(f"Component {self.name} stopped")
        
    def reset(self) -> None:
        """
        Reset the component's state.
        
        This method should clear all internal state while preserving
        configured dependencies.
        """
        self.running = False
        self.logger.info(f"Component {self.name} reset")
        # Child classes should override this method to reset their specific state
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get component statistics.
        
        Returns:
            Dict: Component statistics
        """
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'running': self.running
        }
        
    def __str__(self) -> str:
        """String representation of the component."""
        return f"{self.__class__.__name__}({self.name})"
        
    def __repr__(self) -> str:
        """Detailed string representation of the component."""
        return f"{self.__class__.__name__}(name='{self.name}', running={self.running})"
