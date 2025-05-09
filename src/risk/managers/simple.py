# src/risk/managers/simple.py
import logging
from typing import Dict, Any, Optional

from src.core.events.event_types import EventType
from src.core.events.event_utils import create_order_event
from src.risk.managers.risk_manager_base import RiskManagerBase

logger = logging.getLogger(__name__)

class SimpleRiskManager(RiskManagerBase):
    """Simple implementation of a risk manager with fixed position sizing and cash limits."""
    
    def __init__(self, event_bus, portfolio_manager, name=None):
        """Initialize simple risk manager."""
        super().__init__(event_bus, portfolio_manager, name)
        self.position_size = 100  # Default fixed position size
        self.max_position_pct = 0.1  # Maximum 10% of equity per position
        self.order_ids = set()  # Track created order IDs to avoid duplicates
        self.processed_signals = set()  # Track processed signal IDs
        self.processed_rule_ids = set()  # CRITICAL FIX: Track rule IDs separately
        self.events_in_progress = set()  # Track events currently being processed
        
        # BUGFIX: Order manager reference is needed for order creation
        self.order_manager = None
        
        # Create logger
        self.logger = logger
    
    def configure(self, config):
        """
        Configure the risk manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        super().configure(config)
        
        # Extract parameters from config
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
            
        # Set parameters if provided
        self.position_size = config_dict.get('position_size', 100)
        self.max_position_pct = config_dict.get('max_position_pct', 0.1)
        
        logger.info(f"Risk manager configured with position_size={self.position_size}, max_position_pct={self.max_position_pct}")
    
    def on_signal(self, signal_event):
        """
        Handle signal events and create orders with proper position sizing.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            Order event or None
        """
        # CRITICAL DEBUG: Log the incoming signal to help diagnose issues
        logger.info(f"Received signal event: {signal_event.get_id() if hasattr(signal_event, 'get_id') else 'unknown'}")
        
        # Get unique ID for deduplication
        signal_id = signal_event.get_id()
        
        # 1. Extract rule_id from signal event
        rule_id = None
        if hasattr(signal_event, 'data') and isinstance(signal_event.data, dict):
            rule_id = signal_event.data.get('rule_id')
            
            # Log what we found to help with debugging
            logger.info(f"Extracted rule_id from signal: {rule_id}")
        
        # CRITICAL FIX: Do the rule_id check first, before any other check
        # 2. MOST IMPORTANT CHECK: If rule_id exists and was already processed, reject immediately
        if rule_id and rule_id in self.processed_rule_ids:
            logger.info(f"REJECTING: Signal with rule_id {rule_id} already processed")
            # Print all processed rule_ids for debugging
            logger.info(f"All processed rule_ids: {sorted(list(self.processed_rule_ids))}")
            # Mark event as consumed to prevent other handlers from processing it
            if hasattr(signal_event, 'consumed'):
                signal_event.consumed = True
                logger.info(f"Signal with rule_id {rule_id} marked as consumed to stop propagation")
            # No need to process further
            return None
            
        # Debug log the rule_id more prominently 
        if rule_id:
            logger.info(f"PROCESSING NEW SIGNAL with rule_id: {rule_id}")
            # Check if rule_id contains 'group' to verify correct format
            if 'group' in rule_id:
                logger.info(f"CONFIRMED: Signal has proper group-based rule_id format")
            else:
                logger.warning(f"WARNING: Signal rule_id does not use group-based format: {rule_id}")
        
        # Additional diagnostic logging
        sym = signal_event.get_symbol() if hasattr(signal_event, 'get_symbol') else 'unknown'
        val = signal_event.get_signal_value() if hasattr(signal_event, 'get_signal_value') else 'unknown'
        logger.info(f"Signal details: symbol={sym}, value={val}, rule_id={rule_id}")
        
        # Skip if signal ID already processed (redundant safety check)
        if signal_id in self.processed_signals:
            logger.info(f"Skipping already processed signal ID: {signal_id}")
            if hasattr(signal_event, 'consumed'):
                signal_event.consumed = True
            return None
                    
        # Skip if in progress (redundant safety check)
        if signal_id in self.events_in_progress:
            logger.info(f"Skipping in-progress signal: {signal_id}")
            if hasattr(signal_event, 'consumed'):
                signal_event.consumed = True
            return None
            
        # Mark as in progress immediately
        self.events_in_progress.add(signal_id)
        
        # CRITICAL FIX: Add rule_id to processed set IMMEDIATELY to prevent race conditions
        # This must happen before we do any processing that could generate events
        if rule_id:
            logger.info(f"PROCESSING: Adding rule_id {rule_id} to processed set")
            self.processed_rule_ids.add(rule_id)
        
        # Standard signal processing logic
        try:
            # Increment stats
            self.stats['signals_processed'] += 1
            
            # Extract signal details
            symbol = signal_event.get_symbol()
            signal_value = signal_event.get_signal_value()
            price = signal_event.get_price()
            timestamp = signal_event.get_timestamp()
            
            # Skip neutral signals
            if signal_value == 0:
                self.stats['signals_filtered'] += 1
                logger.debug(f"Neutral signal for {symbol}, no order created")
                return None
            
            # Determine direction
            direction = 'BUY' if signal_value > 0 else 'SELL'
            
            # Calculate position size without checking rule_id again
            # This is important to make sure the first signal creates an order
            final_size = self._calculate_position_size(signal_event, symbol, signal_value, price)
            
            # Skip if size is zero
            if final_size == 0:
                self.stats['signals_filtered'] += 1
                logger.info(f"Signal for {symbol} resulted in zero size, skipping")
                return None
            
            # Create unique order ID
            import uuid
            order_id = str(uuid.uuid4())
            
            # Determine the intent of this order (OPEN or CLOSE)
            current_position = self.portfolio_manager.get_position(symbol)
            current_quantity = current_position.quantity if current_position else 0
            
            # Determine intent based on position change
            intent = None
            if (final_size > 0 and current_quantity <= 0) or (final_size < 0 and current_quantity >= 0):
                # We're opening a new position or reversing direction
                intent = "OPEN"
                logger.info(f"Setting order intent to OPEN for {symbol}: {direction} {abs(final_size)}")
            else:
                # We're closing or reducing an existing position
                intent = "CLOSE"
                logger.info(f"Setting order intent to CLOSE for {symbol}: {direction} {abs(final_size)}")
            
            # CRITICAL BUGFIX: Use order_manager directly if available
            if self.order_manager is not None:
                # This is more reliable than emitting events
                logger.info(f"Using order_manager to create order directly")
                
                # Create order parameters with position_action and rule_id
                order_params = {
                    'symbol': symbol,
                    'order_type': 'MARKET',
                    'direction': direction,
                    'quantity': abs(final_size),
                    'price': price,
                    'position_action': intent,  # Use 'position_action' instead of 'intent'
                    'rule_id': rule_id
                }
                
                logger.info(f"Creating order with intent: {intent} and rule_id: {rule_id}")
                
                # Create the order
                order_id = self.order_manager.create_order(**order_params)
                
                logger.info(f"Order created with ID: {order_id} for rule_id: {rule_id}")
                # Store signal as processed
                self.processed_signals.add(signal_id)
                self.stats['orders_generated'] += 1
                return order_id
            
            # Fallback approach using events if no order_manager
            else:
                # Create order event with explicit size field and position_action
                order_data = {
                    'symbol': symbol,
                    'order_type': 'MARKET',
                    'direction': direction,
                    'size': abs(final_size),  # Explicitly using 'size' as field name
                    'quantity': abs(final_size),  # Redundant but ensures compatibility
                    'price': price,
                    'timestamp': timestamp,
                    'order_id': order_id,
                    'status': 'PENDING',
                    'position_action': intent  # Use 'position_action' instead of 'intent'
                }
                
                # Add rule_id to order event if we have one
                if rule_id:
                    order_data['rule_id'] = rule_id
                
                from src.core.events.event_types import Event, EventType
                order_event = Event(EventType.ORDER, order_data, timestamp)
                
                # Mark signal as processed
                self.processed_signals.add(signal_id)
                
                # Emit order event
                if self.event_bus:
                    logger.info(f"Emitting order event with rule_id: {rule_id}")
                    self.event_bus.emit(order_event)
                    self.stats['orders_generated'] += 1
                    logger.info(f"Created order: {direction} {abs(final_size)} {symbol} @ {price:.2f} with rule_id: {rule_id}")
                
                return order_event
        except Exception as e:
            logger.error(f"Error creating order: {e}", exc_info=True)
            if 'errors' in self.stats:
                self.stats['errors'] += 1
            return None
        finally:
            # Always remove from in-progress set
            if signal_id in self.events_in_progress:
                self.events_in_progress.remove(signal_id)
                
            # Debug log for rule_id tracking
            if rule_id:
                logger.info(f"After processing, rule_id: {rule_id} in processed_rule_ids: {rule_id in self.processed_rule_ids}")
    
    def _calculate_position_size(self, signal_event, symbol, signal_value, price):
        """
        Internal method to calculate position size without rule_id check.
        This is used from on_signal to ensure the first signal creates an order.
        
        Args:
            signal_event: Signal event to size
            symbol: Instrument symbol
            signal_value: Signal value (+1, -1, etc)
            price: Price for calculations
            
        Returns:
            int: Position size (positive or negative)
        """
        # Get current position (if any)
        position = self.portfolio_manager.get_position(symbol)
        current_quantity = position.quantity if position else 0
        
        # For BUY signals
        if signal_value > 0:
            # If we already have a full position, skip
            if current_quantity >= self.position_size:
                logger.debug(f"Already have maximum long position for {symbol}, skipping")
                return 0
                
            # If we have a short position, close it first
            if current_quantity < 0:
                # Full position reversal (close short + open long)
                target_size = abs(current_quantity) + self.position_size
            else:
                # Just add to existing long position up to target
                target_size = self.position_size - current_quantity
                
            # Apply constraints
            # 1. Check cash limits
            available_cash = self.portfolio_manager.cash * 0.95  # Use 95% of available cash
            max_cash_size = int(available_cash / price) if price > 0 else 0
            
            # 2. Check position value limit (% of equity)
            max_position_value = self.portfolio_manager.equity * self.max_position_pct
            max_position_size = int(max_position_value / price) if price > 0 else 0
            
            # Use most restrictive limit
            limited_size = min(target_size, max_cash_size, max_position_size)
            
            # Log the adjustment if any limits were applied
            if limited_size < target_size:
                logger.info(f"Limited BUY size from {target_size} to {limited_size} for {symbol}")
            
            # Ensure minimum position size
            if 0 < limited_size < 10:
                logger.debug(f"Position size too small ({limited_size}), skipping")
                return 0
                
            return limited_size
            
        # For SELL signals
        else:
            # If we have a long position, close it first
            if current_quantity > 0:
                # Full position reversal: close long and open short
                target_size = current_quantity + self.position_size
            # If we already have a partial short position
            elif current_quantity < 0:
                # If we already have maximum short, skip
                if current_quantity <= -self.position_size:
                    logger.debug(f"Already have maximum short position for {symbol}, skipping")
                    return 0
                    
                # Add to existing short position up to target
                target_size = self.position_size + abs(current_quantity)
            else:
                # No position yet, full size
                target_size = self.position_size
            
            # Check position value limit for shorts (% of equity)
            max_position_value = self.portfolio_manager.equity * self.max_position_pct
            max_position_size = int(max_position_value / price) if price > 0 else 0
            
            # Use most restrictive limit
            limited_size = min(target_size, max_position_size)
            
            # Log if limits were applied
            if limited_size < target_size:
                logger.info(f"Limited SELL size from {target_size} to {limited_size} for {symbol}")
                
            # Ensure minimum position size
            if 0 < limited_size < 10:
                logger.debug(f"Short position size too small ({limited_size}), skipping")
                return 0
                
            return -limited_size  # Return negative value for SELL
    
    def size_position(self, signal_event):
        """
        Calculate position size based on signal and portfolio constraints.
        
        Args:
            signal_event: Signal event to size
            
        Returns:
            int: Position size (positive or negative)
        """
        # Extract signal details
        symbol = signal_event.get_symbol()
        signal_value = signal_event.get_signal_value()
        price = signal_event.get_price()
        
        # Redundant safety check #1: Check rule_id deduplication again
        rule_id = None
        if hasattr(signal_event, 'data') and isinstance(signal_event.data, dict):
            rule_id = signal_event.data.get('rule_id')
            
        # Double-check that rule_id hasn't been processed yet
        # This is a redundant safety check since the main check is in on_signal()
        if rule_id and rule_id in self.processed_rule_ids:
            logger.info(f"Signal for {symbol} with rule_id {rule_id} already processed, skipping")
            return 0  # Return zero size to prevent any trading
        
        # Delegate to internal method for actual size calculation
        return self._calculate_position_size(signal_event, symbol, signal_value, price)
    
    def reset(self):
        """Reset risk manager state."""
        # Call parent reset
        super().reset()
        
        # Clear order IDs and processed signals
        logger.info("Resetting risk manager state: clearing tracking collections")
        self.order_ids.clear()
        self.processed_signals.clear()
        
        # CRITICAL FIX: Ensure processed_rule_ids is emptied on reset
        # Explicitly log this action to verify it's being called
        rule_id_count = len(self.processed_rule_ids)
        logger.info(f"CLEARING {rule_id_count} PROCESSED RULE IDs")
        self.processed_rule_ids.clear()
        logger.info(f"After reset, processed_rule_ids size: {len(self.processed_rule_ids)}")
        
        # Clear events in progress
        self.events_in_progress.clear()
        
        logger.info(f"Risk manager {self.name} reset completed")
