"""
Base component class with proper lifecycle management.

This provides a standard interface for all system components with
appropriate lifecycle methods for initialization, starting, stopping,
and resetting.
"""

class Component:
    """Base class for all components with proper lifecycle management."""
    
    def __init__(self, name):
        """
        Initialize the component.
        
        Args:
            name (str): Unique name for this component instance
        """
        self.name = name
        self.running = False
        self.context = None
        
    def initialize(self, context):
        """
        Set up dependencies using the provided context.
        
        Args:
            context (dict): Dependencies and configuration needed by this component
        """
        self.context = context
        
    def start(self):
        """Start the component's operation."""
        self.running = True
        
    def stop(self):
        """Stop the component's operation."""
        self.running = False
        
    def reset(self):
        """
        Reset the component's state.
        
        This method should clear all internal state while preserving
        configured dependencies.
        """
        self.running = False
        # Child classes should override this method to reset their specific state
        
    def __str__(self):
        """String representation of the component."""
        return f"{self.__class__.__name__}({self.name})"
