# ADMF-Trader Position Management Fix

This package contains fixes for the position management issues in the ADMF-Trader backtesting system, addressing the problems with multiple open positions and state leakage.

## The Problem

The current implementation has several issues:
1. Multiple positions being opened for the same symbol
2. Position state leakage between optimization runs
3. Inconsistencies between trade PnL and equity changes

## The Solution

The fix adds two new components:
1. **PositionManager** - Enforces position limits and ensures consistent position management
2. **BacktestState** - Ensures proper state isolation between optimization runs

## How to Use

### Apply the Fixes

Run the fix script to implement the position management improvements:

```bash
./run_fix.sh
```

This will:
1. Create the necessary directories and files
2. Update the existing code to integrate with the new components
3. Update your configuration with proper risk management settings
4. Run the optimization to verify the fix

### Debug Position Management

If you want to analyze position management in detail:

```bash
./run_debug.sh
```

This will:
1. Set up debug hooks in key components
2. Run a backtest with detailed position logging
3. Write the debug output to `debug_positions.log`

## Configuration

The fix adds the following configuration section to your YAML files:

```yaml
risk:
  position_manager:
    fixed_quantity: 10
    max_positions: 1
    enforce_single_position: true
    position_sizing_method: fixed
    allow_multiple_entries: false
```

You can adjust these settings as needed:
- `max_positions`: Maximum number of simultaneous positions allowed
- `fixed_quantity`: Fixed position size in shares/contracts
- `enforce_single_position`: Prevents multiple entries in the same direction

## Implementation Details

The fix implements:
1. A new `PositionManager` class that enforces position limits
2. A new `BacktestState` class that ensures proper state isolation
3. Integration with existing components to use these new components
4. Debug tools to help identify position management issues

The key improvements are:
- Consistent tracking of active positions
- Prevention of duplicate signals
- Proper state reset between optimization runs
- Improved diagnostic logging

## Next Steps

After applying the fix, you should:
1. Review your strategy implementations to ensure they're compatible with the new components
2. Update your optimization configurations for other strategies
3. Run comprehensive tests to verify the fix resolves the issues
