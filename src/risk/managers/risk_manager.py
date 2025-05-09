# src/risk/risk_manager_base.py
from abc import ABC, abstractmethod
from src.core.events.event_types import EventType
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class RiskManagerBase(ABC):
    """Base abstract class for all risk managers."""
    
    def __init__(self, event_bus, portfolio):
        """
        Initialize risk manager.
        
        Args:
            event_bus: Event bus for communication
            portfolio: Portfolio for position information
        """
        self.event_bus = event_bus
        self.portfolio = portfolio
        self.configured = False
        
        # Register for events
        self.event_bus.register(EventType.SIGNAL, self.on_signal)
    
    def configure(self, config):
        """
        Configure the risk manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        # Basic configuration - subclasses should call super().configure()
        if hasattr(config, 'as_dict'):
            config = config.as_dict()
            
        self.configured = True
    
    @abstractmethod
    def on_signal(self, signal_event):
        """
        Handle signal events and create orders.
        
        Args:
            signal_event: Signal event to process
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
    
    def reset(self):
        """Reset risk manager state."""
        pass




class StandardRiskManager(RiskManagerBase):
    """Standard risk manager with fixed or percentage-based sizing."""
    
    def __init__(self, event_bus, portfolio):
        """
        Initialize risk manager.
        
        Args:
            event_bus: Event bus for communication
            portfolio: Portfolio for position information
        """
        super().__init__(event_bus, portfolio)
        
        # Default parameters
        self.max_position_size = 100
        self.position_sizing = 'fixed'  # 'fixed', 'percent_equity', 'percent_risk'
        self.sizing_value = 100  # 100 shares, 10% equity, or 2% risk
        self.max_risk_per_trade = 0.02  # 2% maximum risk per trade
    
    def configure(self, config):
        """
        Configure the risk manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        super().configure(config)
        
        if hasattr(config, 'as_dict'):
            config = config.as_dict()
            
        self.max_position_size = config.get('max_position_size', 100)
        self.position_sizing = config.get('position_sizing', 'fixed')
        self.sizing_value = config.get('sizing_value', 100)
        self.max_risk_per_trade = config.get('max_risk_per_trade', 0.02)
    
    def on_signal(self, signal_event):
        """
        Handle signal events and create orders.
        
        Args:
            signal_event: Signal event to process
        """
        # Calculate position size
        size = self.size_position(signal_event)
        
        # Create order event if size is non-zero
        if size != 0:
            symbol = signal_event.get_symbol()
            price = signal_event.get_price()
            signal_value = signal_event.get_signal_value()
            
            # Determine direction
            direction = 'BUY' if signal_value > 0 else 'SELL'
            
            # Create order
            order = create_order_event(symbol, 'MARKET', direction, abs(size), price)
            
            # Emit order event
            self.event_bus.emit(order)
            logger.info(f"Created order: {direction} {abs(size)} {symbol} @ {price:.2f}")
    
    def size_position(self, signal_event):
        """
        Calculate position size for a signal.
        
        Args:
            signal_event: Signal event to size
            
        Returns:
            int: Position size (positive or negative)
        """
        symbol = signal_event.get_symbol()
        price = signal_event.get_price()
        signal_value = signal_event.get_signal_value()
        
        # Get current position
        position = self.portfolio.get_position(symbol)
        current_quantity = position.quantity if position else 0
        
        # Calculate target size based on sizing method
        if self.position_sizing == 'fixed':
            target_size = self.sizing_value
        elif self.position_sizing == 'percent_equity':
            equity_pct = self.sizing_value / 100.0
            target_size = int((self.portfolio.equity * equity_pct) / price)
        elif self.position_sizing == 'percent_risk':
            # Calculate stop loss price (simplified approach)
            stop_loss_pct = 0.02  # 2% stop loss
            risk_amount = self.portfolio.equity * self.max_risk_per_trade
            price_risk = price * stop_loss_pct
            target_size = int(risk_amount / price_risk)
        else:
            target_size = 0
        
        # Apply maximum position size
        target_size = min(target_size, self.max_position_size)
        
        # Apply signal direction
        if signal_value < 0:
            target_size = -target_size
        
        # Calculate order size (difference between target and current)
        order_size = target_size - current_quantity
        
        return order_size    
