# Integration Proposal for Fixed Portfolio

## Current Issue

The fix we created for the portfolio module (FixedPortfolioManager) works correctly in isolation, but it's not being properly integrated with the rest of the system. The logs show that:

1. Fill events are being received by the original PortfolioManager
2. The action_type field is not being properly passed from the risk manager to the fill events
3. The portfolio is not tracking trades (Trade count: 0)

## Integration Steps

### 1. Update System Bootstrap to Use Fixed Portfolio

First, we need to modify the system bootstrap code to use our fixed portfolio manager:

```python
# In src/core/system_bootstrap.py
from src.risk.portfolio.fixed_portfolio import FixedPortfolioManager

# Replace portfolio creation code with:
portfolio = FixedPortfolioManager(event_bus, name="portfolio", initial_cash=initial_cash)
```

### 2. Fill Event Enhancement

The broker simulator needs to preserve the action_type field when creating fill events:

```python
# In src/execution/broker/broker_simulator.py

def process_order(self, order_event):
    # ...existing code...
    
    # Create fill data
    fill_data = order_data.copy()
    
    # Add action_type if present in the original order
    if 'action_type' in order_data:
        fill_data['action_type'] = order_data['action_type']
    
    # ...existing code...
```

### 3. Order Manager Enhancement

The order manager needs to preserve the action_type field from the risk manager:

```python
# In src/execution/order_manager.py

def handle_order(self, order_event):
    # ...existing code...
    
    # If converting trading decision to order, preserve action_type
    if order_id is None:
        # ...existing code to generate order_id...
        
        # Preserve action_type if present
        if 'action_type' in order_data:
            # Keep it in the order data
            pass  # It's already copied from order_data
    
    # ...existing code...
```

### 4. Fix Risk Manager to Include order_id

Update the risk manager to include an order_id in its trading decisions to avoid errors:

```python
# In src/risk/managers/enhanced_risk_manager.py

def _create_trading_decision(self, symbol, direction, size, price, timestamp, rule_id, action_type):
    # ...existing code...
    
    # Generate order ID for the trading decision
    import uuid
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    
    # Create order data with essential information
    order_data = {
        'symbol': symbol,
        'direction': direction,
        'quantity': abs(float(size)),
        'size': abs(float(size)),  # Explicitly set size field
        'price': price,
        'timestamp': timestamp,
        'rule_id': rule_id,
        'action_type': action_type,
        'order_id': order_id  # Add order_id
    }
    
    # ...existing code...
```

### 5. Event Priority Registration

Ensure the portfolio's event handlers are registered with the correct priority:

```python
# In src/core/system_bootstrap.py

# After creating the portfolio
event_bus.register(EventType.FILL, portfolio.on_fill, priority=90)  # High priority, but after order manager

# Or alternatively
event_manager.register_with_priority("portfolio", portfolio, {EventType.FILL: 90})
```

### 6. Debug Hooks

Add debug logging to track the flow of events and ensure the action_type is preserved:

```python
# In src/core/events/event_bus.py

def emit(self, event):
    # ...existing code...
    
    # Debug logging for important event types
    if event.get_type() in [EventType.ORDER, EventType.FILL]:
        event_data = event.data if hasattr(event, 'data') else {}
        action_type = event_data.get('action_type', 'None')
        logger.debug(f"Emitting {event.get_type()} event with action_type: {action_type}")
    
    # ...existing code...
```

## Testing the Integration

1. Create a test script that:
   - Initializes the system with the fixed portfolio
   - Runs a simple test sequence (signal → order → fill)
   - Verifies that trades are properly recorded

2. Add a command-line flag to switch between the original and fixed portfolio implementations for comparison.

## Verification

After implementing these changes, verify that:

1. All fill events have the appropriate action_type
2. The portfolio is correctly recording trades (both OPEN and CLOSE)
3. PnL calculations are accurate
4. The system produces the expected performance statistics

## Fall-Back Strategy

If the integration proves challenging, an alternative approach is to create a portfolio event listener that:

1. Listens for the same fill events that the portfolio receives
2. Maintains its own record of trades with proper action_type handling
3. Provides an alternative API for querying trade history and performance statistics

This would allow the system to continue functioning with the original portfolio while providing improved trade tracking.