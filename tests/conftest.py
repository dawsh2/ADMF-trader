"""
Pytest configuration file for ADMF-Trader tests.
"""

import pytest
import os
import sys
import logging
import datetime

# Add project root to sys.path for proper imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Core fixtures
@pytest.fixture
def event_bus():
    """Create a clean event bus for each test."""
    from src.core.events.event_bus import EventBus
    bus = EventBus()
    yield bus
    # Clean up
    bus.reset()

@pytest.fixture
def event_type_enum():
    """Get the EventType enum."""
    from src.core.events.event_types import EventType
    return EventType

@pytest.fixture
def sample_bar_data():
    """Get sample bar data for testing."""
    return {
        'symbol': 'TEST',
        'open': 100.0,
        'high': 101.0,
        'low': 99.0,
        'close': 100.5,
        'volume': 1000,
        'timestamp': datetime.datetime.now().isoformat()
    }

@pytest.fixture
def position():
    """Create a position for testing."""
    from src.risk.portfolio.position import Position
    return Position('TEST', 100, 50.0)

@pytest.fixture
def portfolio(event_bus):
    """Create a portfolio for testing."""
    from src.risk.portfolio.portfolio import PortfolioManager
    portfolio = PortfolioManager(event_bus, initial_cash=10000.0)
    yield portfolio
    # Clean up
    portfolio.reset()

@pytest.fixture
def broker(event_bus):
    """Create a broker for testing."""
    from src.execution.broker.broker_simulator import SimulatedBroker
    return SimulatedBroker(event_bus)

@pytest.fixture
def test_strategy(event_bus):
    """Create a test strategy for testing."""
    from src.strategy.strategy_base import Strategy
    
    class TestStrategy(Strategy):
        def __init__(self, event_bus, data_handler=None):
            super().__init__(event_bus, data_handler, "test_strategy")
            self.signals_emitted = []
        
        def emit_signal(self, signal_value, price, symbol):
            from src.core.events.event_utils import create_signal_event
            signal = create_signal_event(signal_value, price, symbol)
            self.signals_emitted.append(signal)
            if self.event_bus:
                self.event_bus.emit(signal)
            return signal
    
    return TestStrategy(event_bus)

# Configure logging for tests
@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for tests."""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(project_root, 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configure root logger
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_file = os.path.join(logs_dir, 'test.log')
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Set lower log level for noisy modules
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    # Return logger for tests
    return logging.getLogger('tests')
