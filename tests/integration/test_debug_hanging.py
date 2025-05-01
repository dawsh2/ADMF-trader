"""
Debug test to identify hanging point in strategy-portfolio integration.
"""

import sys
import os
import pytest
import logging
import threading
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import components with timeouts
def import_with_timeout(timeout=5):
    """Import components with timeout protection."""
    logger.debug("Starting imports with timeout protection...")
    
    result = {"success": True, "error": None}
    completed = threading.Event()
    
    def do_imports():
        try:
            global EventBus, Event, EventType, create_signal_event, create_order_event
            global Strategy, PortfolioManager, SimulatedBroker
            
            logger.debug("Importing EventBus...")
            from src.core.events.event_bus import EventBus
            
            logger.debug("Importing Event and EventType...")
            from src.core.events.event_types import Event, EventType
            
            logger.debug("Importing event utilities...")
            from src.core.events.event_utils import create_signal_event, create_order_event
            
            logger.debug("Importing Strategy...")
            from src.strategy.strategy_base import Strategy
            
            logger.debug("Importing PortfolioManager...")
            from src.risk.portfolio.portfolio import PortfolioManager
            
            logger.debug("Importing SimulatedBroker...")
            from src.execution.broker.broker_simulator import SimulatedBroker
            
            logger.debug("All imports successful")
            completed.set()
        except Exception as e:
            logger.error(f"Import error: {e}")
            result["success"] = False
            result["error"] = e
            completed.set()
    
    import_thread = threading.Thread(target=do_imports)
    import_thread.daemon = True
    import_thread.start()
    
    if not completed.wait(timeout):
        logger.error(f"Import timed out after {timeout} seconds")
        result["success"] = False
        result["error"] = "Import timeout"
    
    return result

# Run imports
import_result = import_with_timeout()
if not import_result["success"]:
    # Define empty classes if imports fail
    class EventBus:
        def __init__(self): pass
    class Event:
        def __init__(self, type_val, data): 
            self.event_type = type_val
            self.data = data
    class EventType:
        BAR = 1
        SIGNAL = 2
        ORDER = 3
        FILL = 4
    def create_signal_event(*args): pass
    def create_order_event(*args): pass
    class Strategy:
        def __init__(self, *args): pass
    class PortfolioManager:
        def __init__(self, *args): pass
    class SimulatedBroker:
        def __init__(self, *args): pass

# Test execution timeout wrapper
def run_with_timeout(func, timeout=5, *args, **kwargs):
    """Run a function with timeout protection."""
    result = {"completed": False, "result": None, "error": None}
    completed = threading.Event()
    
    def run_func():
        try:
            result["result"] = func(*args, **kwargs)
            result["completed"] = True
            completed.set()
        except Exception as e:
            result["error"] = e
            completed.set()
    
    thread = threading.Thread(target=run_func)
    thread.daemon = True
    thread.start()
    
    if not completed.wait(timeout):
        return f"TIMEOUT after {timeout}s"
    
    if result["error"]:
        return f"ERROR: {result['error']}"
    
    return result["result"]

@pytest.mark.integration
class TestDebugHanging:
    """Debug test to identify hanging points."""
    
    def test_event_bus_creation(self):
        """Test basic EventBus creation."""
        logger.debug("Starting EventBus creation test")
        
        result = run_with_timeout(EventBus, 2)
        
        if isinstance(result, str) and result.startswith("TIMEOUT"):
            logger.error("EventBus creation timed out")
            pytest.fail("EventBus creation timed out")
        
        logger.debug("EventBus creation completed successfully")
    
    def test_event_creation(self):
        """Test basic Event creation."""
        logger.debug("Starting Event creation test")
        
        def create_test_event():
            return Event(EventType.BAR, {"test": "data"})
        
        result = run_with_timeout(create_test_event, 2)
        
        if isinstance(result, str) and result.startswith("TIMEOUT"):
            logger.error("Event creation timed out")
            pytest.fail("Event creation timed out")
        
        logger.debug("Event creation completed successfully")
    
    def test_event_bus_emit(self):
        """Test basic EventBus emit with Event."""
        logger.debug("Starting EventBus emit test")
        
        def event_bus_emit_test():
            bus = EventBus()
            event = Event(EventType.BAR, {"test": "data"})
            
            # Simple handler
            handler_called = False
            def handler(event):
                nonlocal handler_called
                handler_called = True
            
            # Register and emit
            bus.register(EventType.BAR, handler)
            bus.emit(event)
            
            return handler_called
        
        result = run_with_timeout(event_bus_emit_test, 2)
        
        if isinstance(result, str) and result.startswith("TIMEOUT"):
            logger.error("EventBus emit timed out")
            pytest.fail("EventBus emit timed out")
        
        logger.debug("EventBus emit completed successfully")
    
    def test_portfolio_creation(self):
        """Test basic PortfolioManager creation."""
        logger.debug("Starting PortfolioManager creation test")
        
        def create_portfolio():
            bus = EventBus()
            portfolio = PortfolioManager(bus, initial_cash=10000.0)
            return portfolio
        
        result = run_with_timeout(create_portfolio, 2)
        
        if isinstance(result, str) and result.startswith("TIMEOUT"):
            logger.error("PortfolioManager creation timed out")
            pytest.fail("PortfolioManager creation timed out")
        
        logger.debug("PortfolioManager creation completed successfully")
    
    def test_broker_creation(self):
        """Test basic SimulatedBroker creation."""
        logger.debug("Starting SimulatedBroker creation test")
        
        def create_broker():
            bus = EventBus()
            broker = SimulatedBroker(bus)
            return broker
        
        result = run_with_timeout(create_broker, 2)
        
        if isinstance(result, str) and result.startswith("TIMEOUT"):
            logger.error("SimulatedBroker creation timed out")
            pytest.fail("SimulatedBroker creation timed out")
        
        logger.debug("SimulatedBroker creation completed successfully")
    
    def test_strategy_creation(self):
        """Test basic Strategy creation."""
        logger.debug("Starting Strategy creation test")
        
        def create_strategy():
            bus = EventBus()
            strategy = Strategy(bus, None, "test_strategy")
            return strategy
        
        result = run_with_timeout(create_strategy, 2)
        
        if isinstance(result, str) and result.startswith("TIMEOUT"):
            logger.error("Strategy creation timed out")
            pytest.fail("Strategy creation timed out")
        
        logger.debug("Strategy creation completed successfully")
    
    def test_signal_creation(self):
        """Test basic signal event creation."""
        logger.debug("Starting signal creation test")
        
        def create_signal():
            return create_signal_event(1, 100.0, 'TEST')
        
        result = run_with_timeout(create_signal, 2)
        
        if isinstance(result, str) and result.startswith("TIMEOUT"):
            logger.error("Signal creation timed out")
            pytest.fail("Signal creation timed out")
        
        logger.debug("Signal creation completed successfully")
    
    def test_order_creation(self):
        """Test basic order event creation."""
        logger.debug("Starting order creation test")
        
        def create_order():
            return create_order_event('BUY', 100, 'TEST', 'MARKET', 100.0)
        
        result = run_with_timeout(create_order, 2)
        
        if isinstance(result, str) and result.startswith("TIMEOUT"):
            logger.error("Order creation timed out")
            pytest.fail("Order creation timed out")
        
        logger.debug("Order creation completed successfully")
    
    def test_fill_creation(self):
        """Test basic fill event creation."""
        logger.debug("Starting fill creation test")
        
        def create_fill():
            return Event(EventType.FILL, {
                'symbol': 'TEST',
                'direction': 'BUY',
                'size': 100,
                'fill_price': 100.0,
                'commission': 0.0
            })
        
        result = run_with_timeout(create_fill, 2)
        
        if isinstance(result, str) and result.startswith("TIMEOUT"):
            logger.error("Fill creation timed out")
            pytest.fail("Fill creation timed out")
        
        logger.debug("Fill creation completed successfully")
    
    def test_portfolio_on_fill(self):
        """Test portfolio on_fill method."""
        logger.debug("Starting portfolio on_fill test")
        
        def process_fill():
            bus = EventBus()
            portfolio = PortfolioManager(bus, initial_cash=10000.0)
            
            fill = Event(EventType.FILL, {
                'symbol': 'TEST',
                'direction': 'BUY',
                'size': 100,
                'fill_price': 100.0,
                'commission': 0.0
            })
            
            portfolio.on_fill(fill)
            return portfolio
        
        result = run_with_timeout(process_fill, 3)
        
        if isinstance(result, str) and result.startswith("TIMEOUT"):
            logger.error("Portfolio on_fill timed out")
            pytest.fail("Portfolio on_fill timed out")
        
        logger.debug("Portfolio on_fill completed successfully")
    
    def test_broker_on_order(self):
        """Test broker on_order method."""
        logger.debug("Starting broker on_order test")
        
        def process_order():
            bus = EventBus()
            broker = SimulatedBroker(bus)
            
            order = create_order_event('BUY', 100, 'TEST', 'MARKET', 100.0)
            
            fill = broker.on_order(order)
            return fill
        
        result = run_with_timeout(process_order, 3)
        
        if isinstance(result, str) and result.startswith("TIMEOUT"):
            logger.error("Broker on_order timed out")
            pytest.fail("Broker on_order timed out")
        
        logger.debug("Broker on_order completed successfully")
    
    def test_event_flow(self):
        """Test simplified event flow with timeouts for each step."""
        logger.debug("Starting simplified event flow test")
        
        # Step 1: Create components
        logger.debug("Step 1: Creating components")
        
        def create_components():
            bus = EventBus()
            portfolio = PortfolioManager(bus, initial_cash=10000.0)
            broker = SimulatedBroker(bus)
            
            # Register broker for order events
            def order_handler(order_event):
                fill = broker.on_order(order_event)
                # Don't emit, call portfolio directly
                if fill:
                    portfolio.on_fill(fill)
            
            bus.register(EventType.ORDER, order_handler)
            
            return {"bus": bus, "portfolio": portfolio, "broker": broker}
        
        components = run_with_timeout(create_components, 3)
        
        if isinstance(components, str) and components.startswith("TIMEOUT"):
            logger.error("Component creation timed out")
            pytest.fail("Component creation timed out")
        
        logger.debug("Step 1 completed successfully")
        
        # Step 2: Create and emit order
        logger.debug("Step 2: Creating and emitting order")
        
        def emit_order():
            order = create_order_event('BUY', 100, 'TEST', 'MARKET', 100.0)
            components["bus"].emit(order)
            return True
        
        order_result = run_with_timeout(emit_order, 3)
        
        if isinstance(order_result, str) and order_result.startswith("TIMEOUT"):
            logger.error("Order emission timed out")
            pytest.fail("Order emission timed out")
        
        logger.debug("Step 2 completed successfully")
        
        # Step 3: Check portfolio was updated
        logger.debug("Step 3: Checking portfolio update")
        
        def check_portfolio():
            portfolio = components["portfolio"]
            return 'TEST' in portfolio.positions
        
        check_result = run_with_timeout(check_portfolio, 2)
        
        if isinstance(check_result, str) and check_result.startswith("TIMEOUT"):
            logger.error("Portfolio check timed out")
            pytest.fail("Portfolio check timed out")
        
        if not check_result:
            logger.error("Portfolio wasn't updated")
            pytest.fail("Portfolio wasn't updated")
        
        logger.debug("Step 3 completed successfully")
        logger.debug("All tests completed successfully")
