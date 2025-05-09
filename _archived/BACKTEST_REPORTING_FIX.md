# Backtest Reporting Fix

## Problem Summary

The backtest reports were incorrectly showing "0 trades executed" despite equity changes and other statistics showing that trading occurred. This discrepancy was causing confusion and making it difficult to evaluate trading strategies.

## Root Cause Analysis

After thorough investigation, I found that the root cause involves several interrelated issues:

1. **Trade Status Filtering**: The `get_recent_trades()` method in the `PortfolioManager` class was filtering out trades with `status='OPEN'` by default, but keeping only those with `status='CLOSED'`.

2. **Position Action Field**: The system correctly tracks both opening and closing trades, with each assigned a status:
   - Opening trades (position_action='OPEN') are assigned status='OPEN'
   - Closing trades (position_action='CLOSE') are assigned status='CLOSED'

3. **Reporting System**: The backtest reporting system uses `get_recent_trades()` with default parameters, which filters out OPEN trades, leading to the misleading "0 trades executed" report.

The verification script (`verify_portfolio_trades.py`) confirmed this behavior by showing that:
- The portfolio correctly records both OPEN and CLOSED trades
- But `get_recent_trades()` returns only CLOSED trades

## Solution

I've created two Python scripts to address this issue:

1. **trade_report_fix.py**: This script patches three key methods:
   - `PortfolioManager.get_recent_trades()`: Modified to include OPEN trades by default (filter_open=False)
   - `BacktestReportGenerator.generate_report()`: Enhanced to include all trades in the metrics calculation
   - `PerformanceCalculator.calculate_metrics()`: Updated to count all trades regardless of status

2. **run_fixed_backtest.py**: This script:
   - Applies the patches from trade_report_fix.py
   - Runs a backtest with the mini_test configuration
   - Generates backtest reports showing all trades
   - Shows a summary of trade statistics

## How to Use

1. First, apply the fix to the reporting system:
   ```
   ./trade_report_fix.py
   ```

2. Then run a backtest with the fix applied:
   ```
   ./run_fixed_backtest.py
   ```

The backtest report will now correctly show all trades (both OPEN and CLOSED), providing accurate metrics and statistics.

## Technical Details

### Trade Lifecycle

1. When a signal is received:
   - The risk manager creates an order with a `position_action` field (either 'OPEN' or 'CLOSE')
   - This field determines how the trade will be recorded in the portfolio

2. When an order is filled:
   - The order manager emits either a TRADE_OPEN or TRADE_CLOSE event, depending on the position_action
   - TRADE_OPEN events create new position entries with status='OPEN'
   - TRADE_CLOSE events create closing position entries with status='CLOSED'

3. Portfolio reporting:
   - `get_recent_trades()` was filtering out OPEN trades by default
   - This made reports show only closed trades, potentially none if all positions remained open

### Key Code Changes

The key change is in the `get_recent_trades()` method:

```python
# Original behavior - filters out OPEN trades by default
def get_recent_trades(self, n=None, filter_open=True):
    # ...
    # CRITICAL FIX: Only filter out open trades, INCLUDE zero-PnL trades
    if filter_open:
        # Skip trades with status='OPEN' but keep zero PnL trades
        if t.get('status') == 'OPEN':
            continue
        # Include zero PnL trades, they matter for transaction costs
```

Our patch changes the default parameter:

```python
# Patched version - includes OPEN trades by default
def patched_get_recent_trades(self, n=None, filter_open=False):
    # ...same implementation but different default parameter
```

With this change, the backtest report now correctly shows all trades, giving a more accurate picture of the strategy's performance.

## Future Recommendations

1. **Documentation**: Add more detailed documentation about the trade lifecycle, status tracking, and reporting options

2. **Configuration Option**: Add a configuration option for backtest reports to control whether to include OPEN trades

3. **Trade Status Clarity**: Consider adding more explicit trade status transitions and logging

4. **Consistent Terminology**: Ensure consistent terminology across the codebase (e.g., consistently use position_action for lifecycle stages)

5. **Unit Tests**: Add unit tests specifically for trade counting and reporting to catch similar issues early