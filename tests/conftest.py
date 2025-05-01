"""
Global pytest fixtures and configuration.
Provides shared fixtures for all test modules.
"""

import os
import sys
import pytest
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Add src directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType, Event
from src.core.config.config import Config


@pytest.fixture
def event_bus():
    """Fixture to provide a clean event bus for each test."""
    bus = EventBus()
    yield bus
    bus.reset()  # Cleanup after test


@pytest.fixture
def empty_config():
    """Fixture to provide an empty configuration."""
    return Config()


@pytest.fixture
def sample_config():
    """Fixture to provide a sample configuration for testing."""
    config = Config()
    config_dict = {
        "backtest": {
            "initial_capital": 100000.0,
            "symbols": ["TEST"],
            "data_dir": "./test_data",
            "timeframe": "1min",
            "data_source": "csv",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        },
        "strategies": {
            "ma_crossover": {
                "enabled": True,
                "fast_window": 5,
                "slow_window": 15,
                "price_key": "close"
            }
        },
        "risk_manager": {
            "position_size": 100,
            "max_position_pct": 0.1
        }
    }
    config.from_dict(config_dict)
    return config


@pytest.fixture
def sample_bar_data():
    """Fixture to provide sample bar data for testing."""
    # Generate a week of minute data
    start_date = datetime(2024, 1, 1, 9, 30)
    dates = [start_date + timedelta(minutes=i) for i in range(5 * 390)]  # 5 days, 390 minutes per day
    
    # Generate random prices
    np.random.seed(42)  # For reproducibility
    closes = np.random.normal(100, 1, len(dates)).cumsum()
    opens = closes - np.random.normal(0, 0.1, len(dates))
    highs = np.maximum(opens, closes) + np.random.normal(0.1, 0.05, len(dates))
    lows = np.minimum(opens, closes) - np.random.normal(0.1, 0.05, len(dates))
    volumes = np.random.normal(10000, 2000, len(dates)).astype(int)
    
    # Create DataFrame
    df = pd.DataFrame({
        'datetime': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    return df


@pytest.fixture
def sample_bar_event(sample_bar_data):
    """Fixture to provide a sample bar event for testing."""
    row = sample_bar_data.iloc[0]
    event_data = {
        'symbol': 'TEST',
        'timestamp': row['datetime'].strftime('%Y-%m-%d %H:%M:%S'),
        'open': row['open'],
        'high': row['high'],
        'low': row['low'],
        'close': row['close'],
        'volume': row['volume']
    }
    return Event(EventType.BAR, event_data)


@pytest.fixture
def sample_signal_event():
    """Fixture to provide a sample signal event for testing."""
    event_data = {
        'symbol': 'TEST',
        'timestamp': '2024-01-01 09:30:00',
        'signal_value': 1,  # Buy signal
        'price': 100.0
    }
    return Event(EventType.SIGNAL, event_data)


@pytest.fixture
def sample_order_event():
    """Fixture to provide a sample order event for testing."""
    event_data = {
        'symbol': 'TEST',
        'timestamp': '2024-01-01 09:30:00',
        'direction': 'BUY',
        'quantity': 100,
        'order_type': 'MARKET',
        'price': 100.0,
        'order_id': 'test_order_1'
    }
    return Event(EventType.ORDER, event_data)


@pytest.fixture
def sample_fill_event():
    """Fixture to provide a sample fill event for testing."""
    event_data = {
        'symbol': 'TEST',
        'timestamp': '2024-01-01 09:30:01',  # Slightly after order
        'direction': 'BUY',
        'quantity': 100,
        'fill_price': 100.05,  # Slight slippage
        'commission': 0.5,
        'order_id': 'test_order_1'
    }
    return Event(EventType.FILL, event_data)
