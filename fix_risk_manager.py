#!/usr/bin/env python
"""
Fix the risk manager and test signal-to-order conversion
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("risk_manager_fix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fix_risk')

def check_risk_manager():
    """Test the risk manager with correct initialization"""
    logger.info("Running risk manager check with fixed initialization...")
    
    try:
        # First, fix event_bus import
        event_bus_path = "src/core/event_bus.py"
        if not os.path.exists(event_bus_path):
            # Create a compatibility module
            os.makedirs(os.path.dirname(event_bus_path), exist_ok=True)
            with open(event_bus_path, 'w') as f:
                f.write("""\"\"\"
Compatibility module for event_bus imports.
\"\"\"

import logging
logging.getLogger(__name__).warning("Using compatibility event_bus import")

# Re-export from the correct module
from src.core.events.event_bus import EventBus, EventType, Event
""")
            logger.info(f"Created compatibility module: {event_bus_path}")
        
        # Import the necessary components
        from src.core.events.event_bus import EventBus, EventType
        from src.core.events.event_utils import create_signal_event
        from src.risk.position_manager import PositionManager
        
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
        
        # Create a position manager WITH CONFIG DICT
        position_manager = PositionManager(
            "test_pm", 
            config={
                'fixed_quantity': 10,
                'max_positions': 1,
                'enforce_single_position': True,
                'position_sizing_method': 'fixed',
                'allow_multiple_entries': False
            }
        )
        
        # Set the event bus
        position_manager.event_bus = event_bus
        
        # Initialize it properly with context
        position_manager.initialize({
            'event_bus': event_bus
        })
        
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
            if hasattr(position_manager, 'active_signals'):
                logger.info(f"Position manager active_signals: {position_manager.active_signals}")
            if hasattr(position_manager, 'active_positions'):
                logger.info(f"Position manager active_positions: {position_manager.active_positions}")
            
            # Fix the position manager and configuration
            logger.info("Checking for signal handling code in position_manager.py...")
            
            # Look for order generation logic
            with open("src/risk/position_manager.py", 'r') as f:
                content = f.read()
            
            if 'EventType.ORDER' not in content and 'Event(EventType.ORDER' not in content:
                logger.warning("ISSUE FOUND: Position manager does not generate order events!")
                
                # Let's add order generation logic
                logger.info("Adding order generation logic to position manager...")
                
                # Create a backup
                with open("src/risk/position_manager.py.bak", 'w') as f:
                    f.write(content)
                
                # Add order generation code
                modified_content = content.replace(
                    """        # Publish the modified signal
        self.event_bus.publish(Event(
            EventType.SIGNAL,
            modified_signal_data
        ))""", 
                    """        # Generate and publish an order event
        order_data = {
            'symbol': symbol,
            'quantity': adjusted_quantity,
            'direction': direction,
            'type': 'MARKET',  # Default to market orders
            'price': modified_signal_data.get('price', 0),
            'rule_id': rule_id,
            'timestamp': modified_signal_data.get('timestamp')
        }
        
        # Log the order generation
        self.logger.info(f"Generating order for {symbol}: direction={direction}, quantity={adjusted_quantity}")
        
        # Publish the order event
        self.event_bus.publish(Event(
            EventType.ORDER,
            order_data
        ))"""
                )
                
                # Write the modified content
                with open("src/risk/position_manager.py", 'w') as f:
                    f.write(modified_content)
                
                logger.info("Added order generation logic to position manager")
                return True
            
            # If not obvious what's wrong, check further
            logger.warning("Could not identify exact issue in position manager")
            return False
    
    except Exception as e:
        logger.error(f"Error fixing risk manager: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def fix_optimization_config():
    """Fix the MA crossover optimization config"""
    config_path = "config/ma_crossover_optimization.yaml"
    
    logger.info(f"Fixing optimization config: {config_path}")
    
    try:
        import yaml
        
        # Read current config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Fix risk section
        if 'risk' in config:
            # Check if we need to rename parameter fields
            if 'position_manager' in config['risk']:
                pm_config = config['risk']['position_manager']
                
                if 'position_sizing_method' not in pm_config:
                    pm_config['position_sizing_method'] = 'fixed'
                
                # Make sure the config is correctly structured as a config dict
                config['risk'] = {
                    'position_manager': {
                        'config': pm_config
                    }
                }
            
            # Create backup
            with open(f"{config_path}.bak", 'w') as f:
                yaml.dump(config, f)
            
            # Write fixed config
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            logger.info("Fixed optimization config risk section")
            return True
        else:
            logger.warning(f"Config does not have a risk section: {config}")
            return False
    
    except Exception as e:
        logger.error(f"Error fixing optimization config: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Run all fixes"""
    logger.info("Starting risk manager fixes...")
    
    # First fix the event_bus import issue
    logger.info("1. Fixing import paths...")
    
    try:
        import fix_import_paths
        fix_import_paths.main()
    except ImportError:
        logger.error("Could not import fix_import_paths.py - make sure it exists")
    
    # Fix the optimization config
    logger.info("2. Fixing optimization config...")
    
    if fix_optimization_config():
        logger.info("Optimization config fixed")
    else:
        logger.warning("Could not fix optimization config")
    
    # Check and fix the risk manager
    logger.info("3. Checking risk manager...")
    
    if check_risk_manager():
        logger.info("Risk manager fixed or working properly")
    else:
        logger.warning("Risk manager still not working properly - may need further fixes")
    
    logger.info("All risk manager fixes applied")
    logger.info("Now try running the optimization again with:")
    logger.info("python main.py optimize --config config/ma_crossover_optimization.yaml")

if __name__ == "__main__":
    main()
