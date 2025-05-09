"""
Runtime patch for ADMF-trader to fix optimization issues.

This script applies runtime patches to fix:
1. The rule_id/strategy_id handling in the order manager
2. The trade creation in the broker
"""

import logging
import traceback

# Set up logging
logger = logging.getLogger('runtime_patch')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def apply_patches():
    """Apply all runtime patches."""
    patch_order_manager()
    patch_broker()
    logger.info("All runtime patches applied successfully")

def patch_order_manager():
    """
    Patch the order manager to preserve the rule_id/strategy_id.
    """
    try:
        from src.execution import order_manager
        
        # Save original method
        original_create_order = order_manager.OrderManager._create_order_from_signal
        
        # Define patched method
        def patched_create_order(self, signal_data):
            # Call original method
            order = original_create_order(self, signal_data)
            
            # Fix rule_id if missing
            if order.get('rule_id') is None:
                if 'strategy_id' in signal_data:
                    order['rule_id'] = signal_data['strategy_id']
                    logger.info(f"Patched rule_id from strategy_id: {order['rule_id']}")
            
            return order
        
        # Apply patch
        order_manager.OrderManager._create_order_from_signal = patched_create_order
        logger.info("Successfully patched order_manager.OrderManager._create_order_from_signal")
    except Exception as e:
        logger.error(f"Failed to patch order manager: {e}")
        logger.error(traceback.format_exc())

def patch_broker():
    """
    Patch the broker to create trades.
    """
    try:
        from src.execution.broker import simulated_broker
        
        # Save original method
        original_create_fill = simulated_broker.SimulatedBroker._create_fill
        
        # Define patched method
        def patched_create_fill(self, order, fill_price, timestamp):
            # Call original method
            fill_data = original_create_fill(self, order, fill_price, timestamp)
            
            # Create and record trade
            try:
                from src.core.data_model import Trade
                
                # Create trade with order data
                trade_data = {
                    'id': f"trade_{order.get('id')}",
                    'symbol': order.get('symbol'),
                    'direction': order.get('direction'),
                    'quantity': order.get('quantity'),
                    'entry_price': fill_price,
                    'entry_time': timestamp,
                    'rule_id': order.get('rule_id')
                }
                
                # Apply standardized field names
                trade_data = Trade.from_dict(trade_data)
                
                # Add to portfolio if available
                if hasattr(self, 'portfolio') and self.portfolio is not None:
                    if hasattr(self.portfolio, 'add_trade'):
                        self.portfolio.add_trade(trade_data)
                        logger.info(f"Added trade to portfolio for order {order.get('id')}")
                    else:
                        logger.warning("Portfolio missing add_trade method")
                else:
                    logger.warning("No portfolio available to record trade")
                    
                    # Try to find the portfolio through the context
                    if hasattr(self, 'context') and self.context and 'portfolio' in self.context:
                        portfolio = self.context.get('portfolio')
                        if portfolio and hasattr(portfolio, 'add_trade'):
                            portfolio.add_trade(trade_data)
                            logger.info(f"Added trade to portfolio from context for order {order.get('id')}")
                        
            except Exception as e:
                logger.error(f"Error creating trade: {e}")
                logger.error(traceback.format_exc())
                
            return fill_data
        
        # Apply patch
        simulated_broker.SimulatedBroker._create_fill = patched_create_fill
        logger.info("Successfully patched simulated_broker.SimulatedBroker._create_fill")
    except Exception as e:
        logger.error(f"Failed to patch broker: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    apply_patches()
