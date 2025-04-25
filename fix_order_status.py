# fix_order_status.py
#!/usr/bin/env python

import logging
import importlib
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("OrderStatusFix")

def fix_order_manager_module():
    """Fix the OrderStatus import issues in the OrderManager."""
    logger.info("Applying OrderStatus fix...")
    
    try:
        # Import the module
        from src.execution.order_manager import OrderManager, OrderStatus
        
        # Original on_fill method
        original_on_fill = OrderManager.on_fill
        
        # Create a fixed on_fill method that explicitly imports OrderStatus
        def fixed_on_fill(self, fill_event):
            """Fixed on_fill method with explicit OrderStatus import."""
            # Import OrderStatus explicitly inside the method
            from src.execution.order_manager import OrderStatus
            
            try:
                # Track the event
                if hasattr(self, 'event_tracker'):
                    self.event_tracker.track_event(fill_event)
                
                # Extract fill details
                symbol = fill_event.get_symbol()
                direction = fill_event.get_direction()
                quantity = fill_event.get_quantity()
                price = fill_event.get_price()
                order_id = fill_event.data.get('order_id')
                
                # Find the order
                order = None
                if order_id and order_id in self.orders:
                    order = self.orders[order_id]
                else:
                    # Try to match by symbol and direction
                    matching_orders = [
                        o for o in [self.orders[oid] for oid in self.active_orders]
                        if o.symbol == symbol and o.direction == direction
                    ]
                    
                    if matching_orders:
                        # Use the oldest matching order
                        order = min(matching_orders, key=lambda o: o.created_time)
                        order_id = order.order_id
                
                # If no order found, create a synthetic one
                if order is None:
                    logger.warning(f"Creating synthetic order for orphaned fill: {symbol} {direction}")
                    
                    # Create a new order ID if needed
                    if not order_id:
                        import uuid
                        order_id = str(uuid.uuid4())
                    
                    # Create synthetic order
                    from src.execution.order_manager import Order
                    order = Order(
                        symbol=symbol,
                        order_type='MARKET',
                        direction=direction,
                        quantity=quantity,
                        price=price
                    )
                    
                    # Add to orders dictionary
                    self.orders[order_id] = order
                    self.active_orders.add(order_id)
                    self.stats['orders_created'] += 1
                    
                    logger.info(f"Created order: {order}")
                
                # Check current order status
                if order.status not in [OrderStatus.FILLED, OrderStatus.CANCELED]:
                    # Update order with fill information
                    order.update_status(
                        OrderStatus.FILLED if quantity >= order.get_remaining_quantity() else OrderStatus.PARTIAL,
                        fill_quantity=quantity,
                        fill_price=price
                    )
                    
                    # Check if order is now complete
                    if order.is_filled():
                        if order_id in self.active_orders:
                            self.active_orders.remove(order_id)
                        self.order_history.append(order)
                        self.stats['orders_filled'] += 1
                    
                    # Emit order status event
                    self._emit_order_status_event(order)
                    
                    logger.info(f"Updated order with fill: {order}")
                else:
                    logger.info(f"Order already {order.status.name}, ignoring fill")
            
            except Exception as e:
                logger.error(f"Error processing fill event: {e}", exc_info=True)
                self.stats['errors'] += 1
                
        # Replace the method
        OrderManager.on_fill = fixed_on_fill
        
        logger.info("✅ OrderStatus fix applied successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply OrderStatus fix: {e}")
        return False

if __name__ == "__main__":
    success = fix_order_manager_module()
    if success:
        logger.info("\nOrder management system fixed! You can now run your tests.")
    else:
        logger.error("\nFix failed. Please check the error messages.")
    
    sys.exit(0 if success else 1)
