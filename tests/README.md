# ADMF-Trader Testing Framework

This directory contains the comprehensive testing framework for the ADMF-Trader system, designed to ensure reliability, correctness, and maintainability of the codebase.

## Table of Contents

1. [Overview](#overview)
2. [Test Organization](#test-organization)
3. [Running Tests](#running-tests)
4. [Writing Tests](#writing-tests)
5. [Testing Best Practices](#testing-best-practices)
6. [Continuous Integration](#continuous-integration)

## Overview

The testing framework is built around pytest and includes:

- **Unit Tests**: For testing individual components in isolation
- **Integration Tests**: For testing how components work together
- **Parameterized Tests**: For testing components with multiple inputs
- **Test Fixtures**: For setting up common test environments
- **Coverage Reporting**: For measuring code coverage

## Test Organization

The tests are organized to mirror the source code structure:

```
tests/
├── conftest.py           # Shared fixtures and configuration
├── pytest.ini           # Pytest configuration
├── run_tests.py         # Test runner script
├── unit/               # Unit tests
│   ├── core/           # Tests for core module
│   ├── data/           # Tests for data module
│   ├── strategy/       # Tests for strategy module
│   ├── risk/           # Tests for risk module
│   ├── execution/      # Tests for execution module
│   └── analytics/      # Tests for analytics module
└── integration/        # Integration tests
```

## Running Tests

### Using the Test Runner

The easiest way to run tests is using the `run_tests.py` script:

```bash
# Run all tests
python run_tests.py --all

# Run only unit tests
python run_tests.py --unit

# Run only integration tests
python run_tests.py --integration

# Run tests for a specific module
python run_tests.py --module core

# Run a specific test file
python run_tests.py --file tests/unit/core/test_event_bus.py

# Generate coverage report
python run_tests.py --coverage

# Generate HTML coverage report
python run_tests.py --html-cov

# Run with increased verbosity
python run_tests.py -v

# Exit on first failure
python run_tests.py --xvs
```

### Using pytest Directly

You can also run pytest directly:

```bash
# Run all tests
pytest

# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration

# Run tests for a specific module
pytest -m core

# Run tests with coverage
pytest --cov=src tests/
```

## Writing Tests

### Test Structure

Tests are organized using pytest's class-based approach:

```python
import pytest

@pytest.mark.unit  # Mark as unit test
@pytest.mark.core  # Mark as testing core module
class TestEventBus:
    
    @pytest.fixture
    def event_bus(self):
        """Fixture to provide an event bus for each test."""
        from src.core.events.event_bus import EventBus
        return EventBus()
    
    def test_initialization(self):
        """Test EventBus initialization."""
        from src.core.events.event_bus import EventBus
        event_bus = EventBus()
        assert event_bus is not None
    
    def test_register_handler(self, event_bus):
        """Test registering an event handler."""
        # Test implementation
        pass
```

### Using Fixtures

Fixtures provide a way to set up test dependencies:

```python
# In conftest.py (shared fixtures)
@pytest.fixture
def sample_bar_data():
    """Fixture to provide sample bar data for testing."""
    # Create and return sample data
    pass

# In your test file
def test_strategy_signal(sample_bar_data):
    """Test strategy signal generation with sample data."""
    # Use sample_bar_data in the test
    pass
```

### Parameterized Tests

For testing with multiple inputs:

```python
@pytest.mark.parametrize("fast_window,slow_window,expected", [
    (5, 10, 1),   # Case 1: Fast crosses above slow
    (10, 5, -1),  # Case 2: Fast crosses below slow
    (5, 5, 0)     # Case 3: No crossing
])
def test_ma_crossover_signals(fast_window, slow_window, expected):
    """Test MA crossover with different window combinations."""
    # Test implementation using parameters
    pass
```

## Testing Best Practices

1. **Test One Thing Per Test**: Each test should verify a single behavior
2. **Use Descriptive Test Names**: Name tests to describe what they're testing
3. **Add Docstrings**: Explain what each test is validating
4. **Isolate Tests**: Tests should not depend on other tests
5. **Use Appropriate Fixtures**: Set up shared test data and dependencies
6. **Clean Up After Tests**: Reset state between tests
7. **Test Edge Cases**: Include tests for boundary conditions and error cases
8. **Aim for High Coverage**: Strive for at least 80% code coverage
9. **Avoid Test Duplication**: Use parameterized tests for similar cases
10. **Keep Tests Fast**: Tests should run quickly to encourage frequent testing

## Continuous Integration

The testing framework is designed to be used with continuous integration systems:

1. **Automated Test Runs**: Tests run automatically on code changes
2. **Coverage Reports**: Coverage reports are generated for each build
3. **Test Status**: Test status is reported in pull requests
4. **Failing Tests**: Pull requests with failing tests are blocked from merging

To set up continuous integration:

1. Configure your CI system to run `python run_tests.py --all --coverage`
2. Capture and publish test results and coverage reports
3. Set up required status checks for pull requests
