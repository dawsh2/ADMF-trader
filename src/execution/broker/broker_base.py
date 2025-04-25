# src/execution/broker/broker_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class BrokerBase(ABC):
    """Base interface for all brokers."""
    
    def __init__(self, name=None):
        """
        Initialize broker.
        
        Args:
            name: Optional broker name
        """
        self._name = name or self.__class__.__name__
        self.initialized = False
        self.stats = {
            'orders_processed': 0,
            'fills_generated': 0,
            'errors': 0
        }
    
    @abstractmethod
    def process_order(self, order_event):
        """
        Process an order event.
        
        Args:
            order_event: Order event to process
            
        Returns:
            Fill event or None
        """
        pass
    
    @abstractmethod
    def get_account_info(self):
        """
        Get account information.
        
        Returns:
            Dict with account info
        """
        pass
    
    def configure(self, config):
        """
        Configure broker with parameters.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        if hasattr(config, 'as_dict'):
            config = config.as_dict()
        
        # Default implementation does nothing
        self.initialized = True
    
    def reset_stats(self):
        """Reset broker statistics."""
        self.stats = {
            'orders_processed': 0,
            'fills_generated': 0,
            'errors': 0
        }
    
    def get_stats(self):
        """Get broker statistics."""
        return dict(self.stats)
    
    @property
    def name(self):
        """Get broker name."""
        return self._name
    
    @name.setter
    def name(self, value):
        """Set broker name."""
        self._name = value
