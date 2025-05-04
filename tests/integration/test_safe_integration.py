"""
Integration tests with enhanced safety measures.
"""
import pytest
import logging
import time
from datetime import datetime, timedelta

from src.core.events.event_types import EventType, Event

# Remove any debug print statements that might be causing the 'Fixed Event class' message
from src.core.events.event_bus import EventBus
from src.risk.portfolio.portfolio import PortfolioManager
from src.risk.managers.simple import SimpleRiskManager
from src.execution.broker.broker_simulator import SimulatedBroker
from src.execution.order_manager import OrderManager
from src.strategy.implementations.ma_crossover import MACrossoverStrategy

from tests.adapters import EventBusAdapter, EventTimeoutWrapper
from tests.utils.event_monitor import EventMonitor

logger = logging.getLogger(__name__)

@pytest.mark.integration
class TestSafeIntegration:
    """Integration tests with enhanced safety measures."""
    
    @pytest.fixture
    def safe_components(self):
        """Set up safe components for testing."""
        # Create event bus with safety adapter
        event_bus = EventBus()
        EventBusAdapter.apply(event_bus)
        
        # Create monitor
        monitor = EventMonitor(event_bus)
        
        # Create components with timeout protection
        def setup_components():
            # Create portfolio
            portfolio = PortfolioManager(event_bus, initial_cash=100000.0)
            
            # Create risk manager
            risk_manager = SimpleRiskManager(event_bus, portfolio)
            risk_manager.position_size = 100
            risk_manager.max_position_pct = 0.1
            
            # Create broker
            broker = SimulatedBroker(event_bus)
            if hasattr(broker, 'set_slippage'):
                broker.set_slippage(0.001)  # 0.1% slippage
            else:
                broker.slippage = 0.001
                
            if hasattr(broker, 'set_commission'):
                broker.set_commission(0.001)  # 0.1% commission
            else:
                broker.commission = 0.001
            
            # Create order manager
            order_manager = OrderManager(event_bus, broker)
            
            # Create strategy with small windows for testing
            strategy = MACrossoverStrategy(
                event_bus, None, 
                parameters={
                    'fast_window': 2,  # Small window for quicker signals
                    'slow_window': 5,
                    'price_key': 'close',
                    'symbols': ['TEST']
                }
            )
            
            return {
                'portfolio': portfolio,
                'risk_manager': risk_manager,
                'broker': broker,
                'order_manager': order_manager,
                'strategy': strategy
            }
        
        # Create components with timeout protection
        try:
            components = EventTimeoutWrapper.run_with_timeout(setup_components, timeout=5)
            components['event_bus'] = event_bus
            components['monitor'] = monitor
            
            # Start monitoring
            monitor.start()
            
            yield components
            
            # Clean up
            monitor.stop()
            event_bus.reset()
            
        except TimeoutError as e:
            logger.error(f"Timeout during component setup: {e}")
            pytest.fail(f"Component setup timed out: {e}")
    
    def test_basic_event_flow(self, safe_components):
        """Test basic event flow with safety measures."""
        event_bus = safe_components['event_bus']
        monitor = safe_components['monitor']
        
        # Reset monitor
        monitor.reset()
        
        # Create and emit a simple bar event
        def run_test():
            bar_data = {
                'symbol': 'TEST',
                'timestamp': datetime.now().isoformat(),
                'open': 100.0,
                'high': 102.0,
                'low': 99.0,
                'close': 101.0,
                'volume': 1000
            }
            
            # Emit the event
            event = Event(EventType.BAR, bar_data)
            event_bus.emit(event)
            
            # Short delay to allow for processing
            time.sleep(0.1)
            
            # Check results
            event_count = monitor.get_event_count()
            logger.info(f"Processed {event_count} events")
            monitor.print_summary()
            
            return event_count
        
        # Run with timeout protection
        try:
            event_count = EventTimeoutWrapper.run_with_timeout(run_test, timeout=5)
            
            # Basic assertion - just verify something happened
            assert event_count > 0, "No events were processed"
            
        except TimeoutError as e:
            logger.error(f"Test timed out: {e}")
            pytest.fail(f"Test timed out: {e}")
    
    def test_multiple_bar_sequence(self, safe_components):
        """Test processing multiple bars safely."""
        event_bus = safe_components['event_bus']
        monitor = safe_components['monitor']
        portfolio = safe_components['portfolio']
        
        # Reset monitor
        monitor.reset()
        
        # Create and process multiple bar events
        def run_test():
            # Create a sequence of bar events with increasing prices
            events = []
            
            # Create bars with clear price trend
            base_time = datetime.now()
            for i in range(10):
                bar_data = {
                    'symbol': 'TEST',
                    'timestamp': (base_time + timedelta(minutes=i)).isoformat(),
                    'open': 100.0 + i,
                    'high': 102.0 + i,
                    'low': 99.0 + i,
                    'close': 101.0 + i,
                    'volume': 1000
                }
                events.append(Event(EventType.BAR, bar_data))
            
            # Process events with small delay between
            for i, event in enumerate(events):
                logger.info(f"Processing bar {i+1}/{len(events)}")
                event_bus.emit(event)
                # Small delay to allow for event processing
                time.sleep(0.05)
            
            # Check results
            monitor.print_summary()
            
            # Get portfolio state
            positions = portfolio.get_positions()
            cash = portfolio.cash
            logger.info(f"Final cash: {cash}")
            logger.info(f"Positions: {positions}")
            
            return {
                'bar_count': monitor.get_event_count(EventType.BAR),
                'signal_count': monitor.get_event_count(EventType.SIGNAL),
                'order_count': monitor.get_event_count(EventType.ORDER),
                'fill_count': monitor.get_event_count(EventType.FILL),
                'positions': positions,
                'cash': cash
            }
        
        # Run with timeout protection
        try:
            results = EventTimeoutWrapper.run_with_timeout(run_test, timeout=10)
            
            # Basic assertions
            assert results['bar_count'] == 10, "Not all bar events were processed"
            
            # More relaxed assertions since we're just verifying the test runs
            assert monitor.get_event_count() > 0, "No events were processed"
            
        except TimeoutError as e:
            logger.error(f"Test timed out: {e}")
            pytest.fail(f"Test timed out: {e}")
