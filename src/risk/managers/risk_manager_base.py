"""
Base class for risk managers.

This module provides the abstract base class for risk managers, which are responsible
for processing signals, applying risk limits, and generating orders.
"""
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple

from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType

logger = logging.getLogger(__name__)

class RiskManagerBase(ABC):
    """
    Abstract base class for risk managers.
    
    Risk managers are responsible for:
    - Processing signals and generating orders
    - Applying risk limits and constraints
    - Position sizing
    - Managing overall risk exposure
    """
    
    def __init__(self, portfolio_manager, event_bus=None, name=None):
        """
        Initialize risk manager.
        
        Args:
            portfolio_manager: Portfolio manager instance
            event_bus: Optional event bus for communication
            name: Optional risk manager name
        """
        self._name = name or f"risk_manager_{uuid.uuid4().hex[:8]}"
        self.portfolio_manager = portfolio_manager
        self.event_bus = event_bus
        self.configured = False
        
        # Statistics tracking
        self.stats = {
            'signals_processed': 0,
            'orders_generated': 0,
            'signals_filtered': 0,
            'total_risk_exposure': 0.0,
        }
        
        # Register for events
        if self.event_bus:
            self.event_bus.subscribe(EventType.SIGNAL, self.on_signal)
    
    def initialize(self, context):
        """
        Initialize with dependencies from context.
        
        Args:
            context (dict): Shared context with dependencies
        """
        # Replace event bus if provided in context
        if 'event_bus' in context and not self.event_bus:
            self.event_bus = context['event_bus']
            self.event_bus.subscribe(EventType.SIGNAL, self.on_signal)
            logger.info(f"RiskManager {self._name} initialized with event bus from context")
            
        # Get portfolio manager from context if not already set
        if self.portfolio_manager is None and 'portfolio' in context:
            self.portfolio_manager = context['portfolio']
            logger.info(f"RiskManager {self._name} initialized with portfolio from context")
            
    def start(self):
        """Start the risk manager operations."""
        logger.info(f"RiskManager {self._name} started")
        
    def stop(self):
        """Stop the risk manager operations."""
        logger.info(f"RiskManager {self._name} stopped")
        
    def reset(self):
        """Reset the risk manager state."""
        # Reset statistics
        self.stats = {
            'signals_processed': 0,
            'orders_generated': 0,
            'signals_filtered': 0,
            'total_risk_exposure': 0.0,
        }
        logger.info(f"RiskManager {self._name} reset")
        
    def set_event_bus(self, event_bus):
        """
        Set the event bus.
        
        Args:
            event_bus: Event bus instance
        """
        self.event_bus = event_bus
        
        # Register for events
        if self.event_bus:
            self.event_bus.subscribe(EventType.SIGNAL, self.on_signal)
    
    @abstractmethod
    def on_signal(self, signal_event):
        """
        Process a signal event and generate an order if appropriate.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            Generated order event or None
        """
        pass
    
    @abstractmethod
    def size_position(self, signal_event):
        """
        Calculate position size for a signal.
        
        Args:
            signal_event: Signal event to size
            
        Returns:
            float: Calculated position size
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
    
    def generate_order(self, signal_data, quantity):
        """
        Generate an order from signal data.
        
        Args:
            signal_data: Signal data dictionary
            quantity: Order quantity
            
        Returns:
            Order event
        """
        if quantity == 0:
            return None
            
        order_data = {
            'symbol': signal_data.get('symbol'),
            'direction': signal_data.get('direction'),
            'quantity': abs(quantity),  # Ensure quantity is positive
            'price': signal_data.get('price', 0.0),
            'order_type': 'MARKET',  # Default to market orders
            'rule_id': signal_data.get('rule_id'),
            'timestamp': signal_data.get('timestamp')
        }
        
        # Add optional fields if present
        for field in ['stop_price', 'limit_price', 'time_in_force', 'account_id']:
            if field in signal_data:
                order_data[field] = signal_data[field]
        
        # Create order event
        order_event = Event(
            EventType.ORDER,
            order_data
        )
        
        # Update statistics
        self.stats['orders_generated'] += 1
        
        return order_event
    
    def configure(self, config):
        """
        Configure the risk manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        # Default implementation - subclasses should extend
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
            
        self._name = config_dict.get('name', self._name)
        self.configured = True
        
        logger.info(f"Configured risk manager: {self._name}")
    
    def get_stats(self):
        """
        Get risk manager statistics.
        
        Returns:
            Dict with statistics
        """
        # Calculate metrics for stats
        positions = self.portfolio_manager.get_positions_summary()
        total_exposure = sum(abs(float(pos.get('market_value', 0))) for pos in positions)
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
    
    @property
    def name(self):
        """Get risk manager name."""
        return self._name