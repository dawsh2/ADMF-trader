# MA Crossover Signal Grouping Fix

## Overview

This fix addresses the issue where the MA Crossover strategy implementation was generating 54 trades while validation expected only 18 trades (a 3:1 ratio). The issue was identified in the rule_id format and signal deduplication mechanism.

## Root Causes

Three key issues were identified:

1. **Rule ID Format Mismatch**:
   - Current implementation uses: `ma_crossover_1`, `ma_crossover_2`, etc.
   - Expected format is: `ma_crossover_MINI_BUY_group_1`, etc.

2. **Event Bus Deduplication**:
   - The event bus has its own deduplication mechanism that wasn't being properly reset

3. **Risk Manager Reset**:
   - The risk manager reset also needed improvement in clearing processed_rule_ids

## Implemented Fixes

### 1. MA Crossover Strategy Rule ID Format

The critical change was to the `on_bar` method of `MACrossoverStrategy` to use the correct rule_id format:

```python
# Change from:
rule_id = f"{self.name}_{group_id}"

# To:
direction_name = "BUY" if signal_value == 1 else "SELL"
rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"
```

This ensures the rule_id format includes the symbol and direction information, which is critical for proper deduplication.

### 2. Risk Manager Reset Method

The `reset` method in `SimpleRiskManager` was enhanced to properly clear the processed_rule_ids:

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

### 3. Event Bus Reset

The `BacktestCoordinator.run` method was patched to explicitly reset the event bus before each run:

```python
def patched_run(self, symbols=None, start_date=None, end_date=None, 
               initial_capital=100000.0, timeframe=None):
    """Patched run method with explicit event bus reset."""
    # Reset the event bus first to clear processed rule_ids
    if hasattr(self, 'event_bus') and self.event_bus:
        logger.info("Explicitly resetting event bus before run")
        self.event_bus.reset()
        logger.info("Event bus reset complete")
    
    # Call the original run method
    return original_run(self, symbols, start_date, end_date, initial_capital, timeframe)
```

## Applying the Fix

The fix is applied through the script `ma_crossover_fix_complete.py` which implements all three fixes in a single execution.

To apply all fixes and run validation:

```bash
./run_and_validate_fix.sh
```

## Testing and Verification

After applying the fix, the following checks are performed:

1. Verify the MA Crossover rule_id format is correct
2. Verify the Risk Manager reset method properly clears processed_rule_ids
3. Verify the BacktestCoordinator run method resets the event bus
4. Run validation tests to ensure only 18 trades are generated

## Implementation Details

### Files Modified

1. `/src/strategy/implementations/ma_crossover.py`
2. `/src/risk/managers/simple.py`
3. `/src/execution/backtest/backtest.py` (via monkey patching)

### Added Files

1. `ma_crossover_fix_complete.py` - Main fix implementation
2. `run_and_validate_fix.sh` - Shell script to run and validate the fix
3. `MA_CROSSOVER_FIX_README.md` - This documentation file

## Expected Results

After applying the fix, the system should:

1. Generate exactly 18 trades (down from 54)
2. Have proper signal grouping behavior
3. Show alternating trade directions (BUY → SELL → BUY)

## Troubleshooting

If validation fails after applying the fix, check:

1. Log files for detailed error information
2. Rule ID format in the logs - should show the new format
3. Event tracking logs for proper event flow
4. If the correct implementation files are being used

## Further Recommendations

For future development:

1. Add unit tests for rule_id generation logic
2. Implement stronger validation for event processing
3. Consider adding automated integration tests for signal flow
4. Add runtime assertions to catch similar issues earlier
