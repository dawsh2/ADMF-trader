#!/usr/bin/env python3
"""
Fixed debug integration test for ADMF-Trader.

This script implements a minimal integration test with safety measures
to help diagnose and fix hanging tests in the ADMF-Trader system.
"""
import os
import sys
import logging
import time
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug_integration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("debug_integration")

# Import components with safety wrapper
def import_components():
    """Import components with better error messages."""
    try:
        from src.core.events.event_bus import EventBus
        logger.info("Successfully imported EventBus")
        
        from src.core.events.event_types import Event, EventType, BarEvent
        logger.info("Successfully imported Event, EventType, and BarEvent")
        
        from src.risk.portfolio.portfolio import PortfolioManager
        logger.info("Successfully imported PortfolioManager")
        
        from src.risk.managers.simple import SimpleRiskManager
        logger.info("Successfully imported SimpleRiskManager")
        
        from src.execution.broker.broker_simulator import SimulatedBroker
        logger.info("Successfully imported SimulatedBroker")
        
        from src.execution.order_manager import OrderManager
        logger.info("Successfully imported OrderManager")
        
        from src.strategy.implementations.ma_crossover import MACrossoverStrategy
        logger.info("Successfully imported MACrossoverStrategy")
        
        from tests.adapters import EventBusAdapter, EventTimeoutWrapper
        logger.info("Successfully imported adapter modules")
        
        return {
            'EventBus': EventBus,
            'Event': Event,
            'EventType': EventType,
            'BarEvent': BarEvent,
            'PortfolioManager': PortfolioManager,
            'SimpleRiskManager': SimpleRiskManager,
            'SimulatedBroker': SimulatedBroker,
            'OrderManager': OrderManager,
            'MACrossoverStrategy': MACrossoverStrategy,
            'EventBusAdapter': EventBusAdapter,
            'EventTimeoutWrapper': EventTimeoutWrapper
        }
    except Exception as e:
        logger.error(f"Error importing components: {e}")
        return None

def run_with_timeout(func, timeout=5, *args, **kwargs):
    """Run a function with timeout protection."""
    import threading
    
    result = {"completed": False, "result": None, "error": None}
    completed = threading.Event()
    
    def run_func():
        try:
            result["result"] = func(*args, **kwargs)
            result["completed"] = True
        except Exception as e:
            result["error"] = e
        finally:
            completed.set()
    
    thread = threading.Thread(target=run_func)
    thread.daemon = True
    thread.start()
    
    if not completed.wait(timeout):
        logger.error(f"Function timed out after {timeout} seconds")
        raise TimeoutError(f"Function timed out after {timeout} seconds")
    
    if result["error"]:
        logger.error(f"Function failed with error: {result['error']}")
        raise result["error"]
    
    return result["result"]

def create_event_bus():
    """Create event bus with safety features."""
    logger.info("Creating enhanced event bus...")
    components = import_components()
    
    if not components:
        logger.error("Failed to import components")
        return None
    
    event_bus = components['EventBus']()
    components['EventBusAdapter'].apply(event_bus)
    
    return event_bus

def create_components(event_bus):
    """Create test components."""
    logger.info("Creating test components...")
    components = import_components()
    
    if not components:
        logger.error("Failed to import components")
        return None
    
    # Create portfolio manager
    portfolio = components['PortfolioManager'](event_bus, initial_cash=100000.0)
    logger.info("Created portfolio")
    
    # Create risk manager
    risk_manager = components['SimpleRiskManager'](event_bus, portfolio)
    risk_manager.position_size = 100
    risk_manager.max_position_pct = 0.1
    logger.info("Created risk manager")
    
    # Create broker
    broker = components['SimulatedBroker'](event_bus)
    # Set properties directly to avoid potential issues with methods
    broker.slippage = 0.001
    broker.commission = 0.001
    logger.info("Created broker")
    
    # Create order manager
    order_manager = components['OrderManager'](event_bus, broker)
    logger.info("Created order manager")
    
    # Create strategy
    strategy_params = {
        'fast_window': 2,
        'slow_window': 5,
        'price_key': 'close',
        'symbols': ['TEST']
    }
    strategy = components['MACrossoverStrategy'](event_bus, None, parameters=strategy_params)
    logger.info("Created strategy")
    
    return {
        'event_bus': event_bus,
        'portfolio': portfolio,
        'risk_manager': risk_manager,
        'broker': broker,
        'order_manager': order_manager,
        'strategy': strategy
    }

def create_and_emit_bar_event(event_bus):
    """Create and emit a bar event."""
    logger.info("Creating and emitting bar event...")
    components = import_components()
    
    if not components:
        logger.error("Failed to import components")
        return False
    
    # Use the proper BarEvent class if available
    timestamp = datetime.now()
    
    try:
        # Create a proper bar event using the BarEvent class
        event = components['BarEvent'](
            symbol='TEST',
            timestamp=timestamp,
            open_price=100.0,
            high_price=102.0,
            low_price=99.0,
            close_price=101.0,
            volume=1000
        )
        logger.info("Created BarEvent successfully")
    except Exception as e:
        logger.error(f"Failed to create BarEvent: {e}")
        # Fallback to custom implementation
        class EnhancedBarEvent(components['Event']):
            def get_symbol(self):
                return self.data.get('symbol')
            
            def get_open(self):
                return self.data.get('open')
                
            def get_high(self):
                return self.data.get('high')
                
            def get_low(self):
                return self.data.get('low')
                
            def get_close(self):
                return self.data.get('close')
                
            def get_volume(self):
                return self.data.get('volume')
        
        bar_data = {
            'symbol': 'TEST',
            'timestamp': timestamp.isoformat(),
            'open': 100.0,
            'high': 102.0,
            'low': 99.0,
            'close': 101.0,
            'volume': 1000
        }
        
        event = EnhancedBarEvent(components['EventType'].BAR, bar_data, timestamp)
        logger.info("Created custom EnhancedBarEvent as fallback")
    
    # Emit event
    logger.info("Emitting bar event...")
    handlers_called = event_bus.emit(event)
    logger.info(f"Bar event emitted, {handlers_called} handlers called")
    
    return handlers_called > 0

def track_events(event_bus):
    """Track events with a simple handler."""
    logger.info("Setting up event tracking...")
    components = import_components()
    
    if not components:
        logger.error("Failed to import components")
        return None
    
    events = []
    
    # Create handler for all event types
    def track_handler(event):
        events.append({
            'type': event.get_type(),
            'id': event.get_id(),
            'timestamp': event.get_timestamp()
        })
        logger.info(f"Tracked event: {event.get_type()}")
        return True
    
    # Register handler for all event types
    for event_type in components['EventType']:
        event_bus.register(event_type, track_handler)
    
    logger.info("Event tracking set up")
    return events

def main():
    """Main function."""
    logger.info("Starting debug integration test")
    
    # Wrap everything in try-except to catch all errors
    success = False
    try:
        # Create event bus
        event_bus = run_with_timeout(create_event_bus, 5)
        if not event_bus:
            logger.error("Failed to create event bus")
            return False
        
        # Set up event tracking
        tracked_events = run_with_timeout(track_events, 5, event_bus)
        if tracked_events is None:
            logger.error("Failed to set up event tracking")
            return False
        
        # Create components
        components = run_with_timeout(create_components, 10, event_bus)
        if not components:
            logger.error("Failed to create components")
            return False
        
        # Emit bar event
        success = run_with_timeout(create_and_emit_bar_event, 5, event_bus)
        if not success:
            logger.error("Failed to emit bar event")
            return False
        
        # Wait for event processing
        logger.info("Waiting for event processing...")
        time.sleep(1)
        
        # Check events
        logger.info(f"Tracked {len(tracked_events)} events")
        for i, event in enumerate(tracked_events):
            logger.info(f"Event {i+1}: {event['type']}")
        
        # Check portfolio
        try:
            portfolio = components['portfolio']
            
            # Try different ways to get positions
            try:
                # First try positions property
                if hasattr(portfolio, 'positions'):
                    positions = portfolio.positions
                    logger.info(f"Portfolio positions (from property): {positions}")
                # Try get_positions method
                elif hasattr(portfolio, 'get_positions'):
                    positions = portfolio.get_positions()
                    logger.info(f"Portfolio positions (from get_positions): {positions}")
                # Try listing all position objects
                else:
                    # Try to get all positions by symbol
                    positions = {}
                    for symbol in ['TEST']:
                        pos = portfolio.get_position(symbol)
                        if pos:
                            positions[symbol] = pos
                    logger.info(f"Portfolio positions (from get_position): {positions}")
            except Exception as e:
                logger.error(f"Error accessing positions: {e}")
                
            # Check portfolio cash
            logger.info(f"Portfolio cash: {portfolio.cash}")
        except Exception as e:
            logger.error(f"Error checking portfolio: {e}")
        
        # Mark as success if we got this far
        success = True
        logger.info("Debug integration test completed successfully")
        
    except Exception as e:
        logger.error(f"Debug integration test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
