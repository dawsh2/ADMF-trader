# Position Management Fix for ADMF-Trader

## Problem

The backtest system is encountering issues with position management:

1. **Multiple Positions**: The system is creating multiple positions for the same symbol despite `max_positions: 1` setting
2. **Inconsistent PnL**: Large discrepancies between trade PnL and equity changes
3. **State Leakage**: Position state is leaking between optimization runs

## Solution

This fix directly modifies two key components:

1. **`SimpleMACrossoverStrategy`**: Improved signal generation with proper position tracking
2. **`OrderManager`**: Enhanced order tracking with single position enforcement

Rather than adding complex new components, this approach integrates position management directly into existing code for maximum compatibility.

## Key Improvements

1. **Active Signal Tracking**: The strategy now tracks active signals to prevent duplicates
2. **Order Tracking by Symbol**: The order manager tracks active orders by symbol
3. **Maximum Order Enforcement**: The system enforces a maximum of one order per symbol
4. **Enhanced Logging**: Detailed logging for better debugging

## How to Use

1. **Run the Fix**: Execute the shell script to run optimization with fixes:

```bash
chmod +x run_fix.sh
./run_fix.sh
```

2. **Check Results**: The script will create a log file with detailed output

## Configuration

The risk management settings are automatically applied:

```yaml
risk:
  position_manager:
    max_positions: 1
    fixed_quantity: 10
    enforce_single_position: true
    position_sizing_method: fixed
```

## Expected Results

After applying the fix, you should see:

1. Only one position per symbol
2. Consistent PnL and equity changes
3. Proper closing of all positions
4. No duplicate positions across optimization runs

If you encounter any issues, check the log file for detailed diagnostic information.
