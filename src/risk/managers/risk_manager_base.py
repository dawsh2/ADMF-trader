"""
Base class for risk managers.
"""
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Union

from core.events.event_types import EventType
from core.events.event_utils import EventTracker

logger = logging.getLogger(__name__)

class RiskManagerBase(ABC):
    """
    Abstract base class for all risk managers.
    
    Risk managers are responsible for:
    - Processing signals and generating orders
    - Applying risk limits and constraints
    - Position sizing
    - Managing overall risk exposure
    - Providing risk analytics
    """
    
    def __init__(self, event_bus, portfolio_manager, name=None):
        """
        Initialize risk manager.
        
        Args:
            event_bus: Event bus for communication
            portfolio_manager: Portfolio for position information
            name: Optional risk manager name
        """
        self._name = name or f"risk_manager_{uuid.uuid4().hex[:8]}"
        self.event_bus = event_bus
        self.portfolio_manager = portfolio_manager
        self.configured = False
        
        # Statistics tracking
        self.stats = {
            'signals_processed': 0,
            'orders_generated': 0,
            'signals_filtered': 0,
            'total_risk_exposure': 0.0,
        }
        
        # Event tracker for analysis
        self.event_tracker = EventTracker(f"{self._name}_tracker")
        
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.SIGNAL, self.on_signal)
    
    def configure(self, config):
        """
        Configure the risk manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        # Basic configuration - subclasses should call super().configure()
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
            
        self._name = config_dict.get('name', self._name)
        self.configured = True
    
    def set_event_bus(self, event_bus):
        """
        Set the event bus.
        
        Args:
            event_bus: Event bus instance
        """
        self.event_bus = event_bus
        # Register for events
        if self.event_bus:
            self.event_bus.register(EventType.SIGNAL, self.on_signal)
    
    @abstractmethod
    def on_signal(self, signal_event):
        """
        Handle signal events and create orders.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            Order event or None
        """
        pass
    
    @abstractmethod
    def size_position(self, signal_event):
        """
        Calculate position size for a signal.
        
        Args:
            signal_event: Signal event to size
            
        Returns:
            int: Position size (positive or negative)
        """
        pass
    
    def evaluate_trade(self, symbol, direction, quantity, price):
        """
        Evaluate if a trade complies with risk rules.
        
        Args:
            symbol: Instrument symbol
            direction: Trade direction
            quantity: Trade quantity
            price: Trade price
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        # Default implementation - subclasses should override
        return True, ""
    
    def get_stats(self):
        """
        Get risk manager statistics.
        
        Returns:
            Dict with statistics
        """
        # Calculate metrics for stats
        if hasattr(self.portfolio_manager, 'get_positions_summary'):
            positions = self.portfolio_manager.get_positions_summary()
            total_exposure = sum(abs(pos.get('market_value', 0)) for pos in positions)
            self.stats['total_risk_exposure'] = total_exposure
            
            if self.portfolio_manager.equity > 0:
                self.stats['exposure_ratio'] = total_exposure / self.portfolio_manager.equity
            else:
                self.stats['exposure_ratio'] = 0.0
        
        return dict(self.stats)
    
    def reset(self):
        """Reset risk manager state."""
        # Reset statistics
        self.stats = {
            'signals_processed': 0,
            'orders_generated': 0,
            'signals_filtered': 0,
            'total_risk_exposure': 0.0,
        }
        
        # Reset event tracker
        self.event_tracker.reset()
    
    @property
    def name(self):
        """Get risk manager name."""
        return self._name
    
    @name.setter
    def name(self, value):
        """Set risk manager name."""
        self._name = value
