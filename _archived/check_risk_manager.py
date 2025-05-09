#!/usr/bin/env python
"""
Check if the risk manager is correctly processing signals
"""

import os
import sys
import logging
import traceback
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("risk_manager_check.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('risk_check')

def check_risk_manager():
    """Test the risk manager with a simple signal"""
    logger.info("Running risk manager check...")
    
    try:
        # Import the necessary components
        # Import event bus first (after fix should work)
        from src.core.events.event_bus import EventBus, EventType
        from src.core.events.event_utils import create_signal_event
        
        # Find the risk manager class
        risk_manager_path = "src/risk/position_manager.py"
        if not os.path.exists(risk_manager_path):
            logger.error(f"Risk manager not found at: {risk_manager_path}")
            
            # Try to find it elsewhere
            for root, dirs, files in os.walk("src"):
                for file in files:
                    if file == "position_manager.py":
                        risk_manager_path = os.path.join(root, file)
                        logger.info(f"Found risk manager at: {risk_manager_path}")
                        break
            
            if not os.path.exists(risk_manager_path):
                logger.error("Could not find position_manager.py")
                return False
        
        # Import the position manager
        logger.info(f"Importing position manager from {risk_manager_path}")
        
        # Import position manager based on its location
        if risk_manager_path == "src/risk/position_manager.py":
            from src.risk.position_manager import PositionManager
        else:
            # Handle other locations if needed
            logger.error(f"Unsupported position manager location: {risk_manager_path}")
            return False
        
        # Create a test event bus
        event_bus = EventBus("test")
        
        # Add event listeners
        signals_received = []
        orders_received = []
        
        def signal_listener(event):
            logger.info(f"Signal received: {event}")
            signals_received.append(event)
        
        def order_listener(event):
            logger.info(f"Order received: {event}")
            orders_received.append(event)
        
        event_bus.subscribe(EventType.SIGNAL, signal_listener)
        event_bus.subscribe(EventType.ORDER, order_listener)
        
        # Create a position manager
        position_manager = PositionManager(
            "test_pm",
            fixed_quantity=10,
            max_positions=1,
            enforce_single_position=True,
            position_sizing_method="fixed",
            allow_multiple_entries=False
        )
        
        # Set the event bus
        position_manager.event_bus = event_bus
        
        # Create and send a test signal
        test_signal = create_signal_event(
            signal_value=1,  # Buy
            price=520.0,
            symbol="HEAD",
            timestamp=datetime.now(),
            rule_id="test_signal"
        )
        
        logger.info(f"Sending test signal: {test_signal}")
        event_bus.publish(test_signal)
        
        # Check if an order was generated
        logger.info(f"Signals received: {len(signals_received)}")
        logger.info(f"Orders received: {len(orders_received)}")
        
        if len(orders_received) > 0:
            logger.info("SUCCESS: Risk manager generated an order from the signal")
            return True
        else:
            logger.warning("FAILURE: Risk manager did not generate an order from the signal")
            
            # Check position manager's state
            if hasattr(position_manager, 'positions'):
                logger.info(f"Position manager positions: {position_manager.positions}")
            else:
                logger.warning("Position manager does not have a positions attribute")
            
            # Try to check other state variables
            for attr in ['max_positions', 'enforce_single_position', 'position_sizing_method', 'allow_multiple_entries']:
                if hasattr(position_manager, attr):
                    logger.info(f"Position manager {attr}: {getattr(position_manager, attr)}")
            
            return False
    
    except Exception as e:
        logger.error(f"Error checking risk manager: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Run the risk manager check"""
    # Run the check
    result = check_risk_manager()
    
    if result:
        logger.info("Risk manager check passed - signals are converted to orders")
    else:
        logger.warning("Risk manager check failed - signals are not converted to orders")
        logger.info("This might be why no trades are generated during optimization")

if __name__ == "__main__":
    main()
