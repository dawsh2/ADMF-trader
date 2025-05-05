# Event-Driven Architecture Improvements

This document outlines the architectural changes made to improve the trade tracking and event flow in the ADMF-trader platform. These changes fix issues with position and trade tracking in the portfolio module by implementing a more clear and structured event-driven approach.

## Overview of Changes

### 1. New Event Types

Added these new event types to replace the previous approach of using the `action_type` field:

- `POSITION_OPEN`: Indicates intent to open a new position
- `POSITION_CLOSE`: Indicates intent to close an existing position
- `TRADE_OPEN`: Records the opening of a trade
- `TRADE_CLOSE`: Records the closing of a trade with complete entry/exit information

### 2. Component Responsibilities

The new event architecture clearly defines component responsibilities:

- **Risk Manager**: Emits `POSITION_OPEN` and `POSITION_CLOSE` events based on signals
- **Order Manager**: Handles position events, creates orders, and emits `TRADE_OPEN` events when fills occur
- **Portfolio Manager**: Handles `TRADE_OPEN` and `TRADE_CLOSE` events to track positions and record trades

### 3. Event Flow

The improved event flow is as follows:

1. Strategy issues a `SIGNAL` event
2. Risk Manager processes the signal and issues a `POSITION_OPEN` or `POSITION_CLOSE` event
3. Order Manager processes position events and creates orders
4. Broker processes orders and generates `FILL` events
5. Order Manager receives fill events and issues `TRADE_OPEN` or `TRADE_CLOSE` events
6. Portfolio Manager processes trade events and updates portfolio state

## Implementation Details

### Event Utility Functions

Added new utility functions in `event_utils.py` to create the new event types:

- `create_position_open_event()`: Creates a position open event
- `create_position_close_event()`: Creates a position close event
- `create_trade_open_event()`: Creates a trade open event
- `create_trade_close_event()`: Creates a trade close event

Also updated the `dict_to_event()` function to deserialize these new event types.

### SimpleRiskManager

Modified the `SimpleRiskManager` to emit position events based on signal events:

- When processing a signal, it determines if it would open a new position or close an existing one
- Emits the appropriate `POSITION_OPEN` or `POSITION_CLOSE` event
- The position event includes all necessary information such as symbol, direction, quantity, price

### OrderManager

Enhanced the `OrderManager` to handle position events and generate trade events:

- Added handlers for `POSITION_OPEN` and `POSITION_CLOSE` events
- These handlers create orders with a `position_action` field marking them as open or close orders
- Modified the `handle_fill` method to emit `TRADE_OPEN` events when fills occur
- Improved event tracking for position and trade lifecycle

### PortfolioManager

Updated the `PortfolioManager` to handle trade events:

- Added handlers for `TRADE_OPEN` and `TRADE_CLOSE` events
- These handlers create trade records and update portfolio state
- Improved trade record format to include all necessary information

## Benefits

1. **Clear Intent**: The event types clearly express intent (open position, close position) rather than relying on the generic `action_type` field
2. **Complete Tracking**: Fills and trades are properly linked with their originating orders and positions
3. **Improved Debugging**: Event flow is clearer and easier to debug due to explicit event types
4. **System Resilience**: Components are less tightly coupled, making the system more robust to errors

## Future Improvements

1. Implement the full trade lifecycle with position tracking for nested and partial fills
2. Add support for multiple legs/complex orders through position event groups
3. Enhance risk management with position sizing based on existing positions
4. Improve trade analytics with complete trade records