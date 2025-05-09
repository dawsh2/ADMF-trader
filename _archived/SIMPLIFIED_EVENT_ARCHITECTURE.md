# Simplified Event Architecture

This document outlines the architectural changes made to improve the trade tracking and event flow in the ADMF-trader platform. These changes fix issues with position and trade tracking in the portfolio module by implementing a cleaner event flow with clearer intent.

## Overview of Changes

### 1. Enhanced Order Events

Instead of adding new event types, we've enhanced the existing Order events with an "intent" field that clearly indicates the purpose of the order:

- `intent: "OPEN"`: Indicates an order intended to open a new position
- `intent: "CLOSE"`: Indicates an order intended to close an existing position

This is a more elegant solution that keeps the event flow simpler while still providing the necessary information.

### 2. Component Responsibilities

The updated architecture maintains clear component responsibilities:

- **Risk Manager**: 
  - Processes signals
  - Determines position intent (OPEN or CLOSE)
  - Creates orders with proper intent and rule_id metadata

- **Order Manager**: 
  - Handles orders with their intent metadata
  - Manages order execution
  - Emits TRADE_OPEN/TRADE_CLOSE events when fills occur

- **Portfolio Manager**:
  - Handles trade events
  - Updates positions and records trades
  - Maintains portfolio state

### 3. Event Flow

The simplified event flow is as follows:

1. Strategy issues a `SIGNAL` event
2. Risk Manager processes the signal and issues an `ORDER` event with intent=OPEN/CLOSE
3. Order Manager processes the order
4. Broker handles the order and generates a `FILL` event
5. Order Manager receives the fill and issues a `TRADE_OPEN` or `TRADE_CLOSE` event
6. Portfolio Manager processes trade events and updates portfolio state

## Implementation Details

### Order Creation

Modified the `create_order_event()` function to include intent:

```python
def create_order_event(direction, quantity, symbol, order_type, 
                    price=None, timestamp=None, order_id=None, intent=None, rule_id=None):
    # ...
    # Add intent if provided
    if intent:
        order.data['intent'] = intent
```

### Risk Manager

Enhanced the `SimpleRiskManager` to determine intent:

```python
# Determine intent based on position change
intent = None
if (final_size > 0 and current_quantity <= 0) or (final_size < 0 and current_quantity >= 0):
    # We're opening a new position or reversing direction
    intent = "OPEN"
else:
    # We're closing or reducing an existing position
    intent = "CLOSE"

# Create order with intent
order_params = {
    'symbol': symbol,
    'order_type': 'MARKET',
    'direction': direction,
    'quantity': abs(final_size),
    'price': price,
    'intent': intent,
    'rule_id': rule_id
}
```

### Order Manager

Updated the `handle_fill` method to check the intent field:

```python
# Check if we have an intent field in the order data
if 'intent' in order:
    is_opening_trade = order['intent'] == 'OPEN'
# Otherwise try to infer from rule_id or event history
elif rule_id and 'close' in rule_id.lower():
    is_opening_trade = False
```

### Benefits of This Approach

1. **Simpler Event Flow**: Uses fewer event types while maintaining the same functionality
2. **Clear Intent**: The intent field clearly communicates the purpose of the order
3. **Reduced Complexity**: Eliminates the need for position events and their handlers
4. **Improved Maintainability**: The code is more straightforward and easier to understand
5. **Better Performance**: Fewer events means less processing overhead

## Conclusion

This simplified approach achieves the same goals as the original architecture but with a cleaner design. By using metadata fields to convey intent rather than creating new event types, we've streamlined the event flow while still providing all the necessary information for proper trade tracking.