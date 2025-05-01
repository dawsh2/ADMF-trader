# MA Crossover Signal Grouping Fix - Summary

## Issue Description

The MA Crossover strategy implementation was generating **54 trades** while validation expected **18 trades** (a 3:1 ratio). The root cause was identified in the rule_id format and deduplication mechanism across three key components.

## Root Causes

1. **Rule ID Format Mismatch**:
   - Current implementation used: `ma_crossover_1`, `ma_crossover_2`, etc.
   - Expected format is: `ma_crossover_MINI_BUY_group_1`, etc.

2. **Event Bus Deduplication**:
   - The event bus's deduplication mechanism wasn't being properly reset between runs

3. **Risk Manager Reset**:
   - The risk manager reset needed improvement in clearing processed_rule_ids

## Applied Fixes

### 1. MA Crossover Strategy Rule ID Format

The critical change was to the `on_bar` method of `MACrossoverStrategy` to use the correct rule_id format:

```python
# Change from:
rule_id = f"{self.name}_{group_id}"

# To:
direction_name = "BUY" if signal_value == 1 else "SELL"
rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"
```

This ensures the rule_id format includes the symbol and direction information, which is critical for proper deduplication. This fix was already implemented in the current version of the code.

### 2. Risk Manager Reset Method

The `reset` method in `SimpleRiskManager` was fixed to properly clear the processed_rule_ids:

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

This change ensures processed rule IDs are properly cleared during reset. This fix was already implemented in the current version of the code.

### 3. BacktestCoordinator Run Method Fix

The `BacktestCoordinator.run` method was modified to explicitly reset the event bus before each run:

```python
def run(self, symbols=None, start_date=None, end_date=None, initial_capital=100000.0, timeframe=None):
    """Run a backtest."""
    # CRITICAL FIX: Reset the event bus first to clear processed rule_ids
    if hasattr(self, 'event_bus') and self.event_bus:
        logger.info("Explicitly resetting event bus before run")
        self.event_bus.reset()
        logger.info("Event bus reset complete")
    
    # Use configuration if parameters not provided
    # ... rest of the method ...
```

This ensures the event bus is explicitly reset before each backtest run, clearing all processed rule IDs and preventing duplicate signals. This is crucial for proper deduplication.

## Verification

The fixes have been verified through:

1. Code inspection to confirm all three issues are addressed
2. A test script (`run_fixed_implementation.py`) that executes the MA Crossover strategy with the fixes in place
3. Checking that the number of trades is reduced from 54 to the expected 18

## Final Status

All three fixes have been successfully implemented and tested. The MA Crossover strategy now correctly generates 18 trades instead of 54, as expected by validation.

## Running the Verification

To test that the fix is working correctly:

1. Run the provided shell script: `./run_fixed_ma_crossover.sh`
2. Check that the output confirms the expected 18 trades were generated
3. Examine the log file for detailed information about the signal deduplication

This comprehensive fix ensures proper signal grouping and deduplication in the MA Crossover strategy implementation.
