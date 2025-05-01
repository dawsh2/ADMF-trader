# MA Crossover Signal Grouping Fix - Final Solution

## Problem Summary

The MA Crossover strategy was generating **54 trades** while validation expected **18 trades** (3:1 ratio). This was due to an issue with the rule_id format and event bus deduplication.

## Root Cause Analysis

After examining the code, we identified three critical issues:

1. **Rule ID Format Mismatch**: The system used a simple rule_id format, while validation expected format including symbol and direction
2. **Risk Manager Reset**: The Risk Manager's reset method needed to properly clear processed_rule_ids
3. **Event Bus Deduplication**: The event bus had its own deduplication mechanism that wasn't being reset properly

## Fix Implementation

We've implemented a comprehensive fix addressing all three issues:

### 1. Strategy Rule ID Format

The MA Crossover strategy needed to use the correct rule_id format:

```python
# Correct format:
direction_name = "BUY" if signal_value == 1 else "SELL"
rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"
```

This was already implemented correctly in the code.

### 2. Risk Manager Reset Method

The Risk Manager needed to properly clear processed_rule_ids during reset:

```python
def reset(self):
    # Call parent reset
    super().reset()
    
    # Clear order IDs and processed signals
    logger.info("Resetting risk manager state: clearing tracking collections")
    self.order_ids.clear()
    self.processed_signals.clear()
    
    # CRITICAL FIX: Ensure processed_rule_ids is emptied on reset
    rule_id_count = len(self.processed_rule_ids)
    logger.info(f"CLEARING {rule_id_count} PROCESSED RULE IDs")
    self.processed_rule_ids.clear()
    logger.info(f"After reset, processed_rule_ids size: {len(self.processed_rule_ids)}")
    
    # Clear events in progress
    self.events_in_progress.clear()
    
    logger.info(f"Risk manager {self.name} reset completed")
```

This was also already implemented correctly.

### 3. Event Bus Reset Fix

The critical missing piece was ensuring the event bus itself is reset properly. We've patched the BacktestCoordinator to explicitly reset the event bus before each run:

```python
def patched_run(self):
    """Patched run method with explicit event bus reset."""
    # Reset the event bus first to clear processed rule_ids
    if hasattr(self, 'event_bus') and self.event_bus:
        logger.info("Explicitly resetting event bus before run")
        self.event_bus.reset()
        logger.info("Event bus reset complete")
    
    # Call the original run method
    return original_run(self)
```

This ensures that all deduplication keys (including rule_ids) are cleared between runs.

## Running the Fixed Implementation

To apply and test the fix:

1. First apply the event bus reset fix:
   ```bash
   python reset_event_bus.py
   ```

2. Then run the fixed implementation:
   ```bash
   python run_fixed_ma_crossover_v2.py
   ```

Or use the combined script:
```bash
./run_and_validate_fixed.sh
```

## Verification

After applying the fixes, the system should:
1. Generate exactly 18 trades (one per signal group)
2. Show proper rule_id format with symbol and direction
3. Maintain proper deduplication of signals
4. Show correct alternating trade directions (BUY → SELL → BUY)

## Why This Works

The solution addresses the complete signal flow:

1. **MA Crossover Strategy**: Creates signals with correct rule_id format
2. **Risk Manager**: Deduplicates signals based on rule_id and properly resets
3. **Event Bus**: Now properly resets its deduplication tracking between runs

The event bus fix was the missing piece - while both the strategy and risk manager were correctly implemented, the event bus's own deduplication was keeping track of rule_ids across runs, causing duplicate signals to be rejected.

By ensuring the event bus is properly reset before each run, we allow new signals with the same rule_id pattern to be processed correctly in subsequent runs.
