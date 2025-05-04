"""
Enhanced pytest fixtures with safety measures for test stability.

This conftest file adds safety measures to prevent test hangs and
timeouts in the ADMF-Trader test suite.

Usage:
    Import these fixtures into your conftest.py:
    
    from tests.conftest_safe import safe_event_bus, test_timeout, event_monitor
    
    Or use the pytest --import option:
    pytest --import=tests.conftest_safe
"""

import pytest
import signal
import logging
import threading
import time

from src.core.events.event_bus import EventBus
from tests.adapters import EventBusAdapter
from tests.utils.event_monitor import EventMonitor

logger = logging.getLogger(__name__)

@pytest.fixture
def safe_event_bus():
    """
    Create a safety-enhanced event bus for testing.
    
    This event bus includes protections against:
    - Infinite recursion
    - Cyclic event processing
    - Too many events of same type
    - Weak reference errors
    
    Returns:
        An enhanced EventBus instance
    """
    # Create a new event bus
    event_bus = EventBus()
    
    # Apply safety enhancements
    EventBusAdapter.apply(event_bus)
    
    yield event_bus
    
    # Clean up
    event_bus.reset()

@pytest.fixture
def event_monitor(safe_event_bus):
    """
    Create an event monitor for tracking events during tests.
    
    Args:
        safe_event_bus: Enhanced event bus fixture
        
    Returns:
        EventMonitor instance
    """
    monitor = EventMonitor(safe_event_bus)
    monitor.start()
    
    yield monitor
    
    # Clean up
    monitor.stop()

@pytest.fixture(scope="function", autouse=False)
def test_timeout():
    """
    Apply a timeout to a test function.
    
    This fixture uses the SIGALRM signal to implement timeouts.
    After the timeout expires, it raises an exception to fail the test.
    
    Note: Only works on Unix-like systems.
    
    Args:
        timeout: Timeout in seconds (default: 30)
    """
    # Define handler for timeout
    def timeout_handler(signum, frame):
        pytest.fail(f"Test timed out after 30 seconds")
    
    # Set the handler and alarm
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    old_alarm = signal.alarm(30)
    
    yield
    
    # Restore previous alarm and handler
    signal.alarm(old_alarm)
    signal.signal(signal.SIGALRM, old_handler)

def pytest_addoption(parser):
    """Add command line options."""
    parser.addoption(
        "--apply-adapters",
        action="store_true",
        default=False,
        help="Apply safety adapters to event system"
    )

@pytest.fixture(scope="session", autouse=True)
def configure_enhanced_logging():
    """Configure enhanced logging for tests."""
    # Set up logging format with thread information
    log_format = '%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler("test_safe.log"),
            logging.StreamHandler()
        ]
    )
    
    # Log the start of the test session
    logger.info("Starting test session with safety enhancements")
    
    yield
    
    # Log the end of the test session
    logger.info("Test session complete")
