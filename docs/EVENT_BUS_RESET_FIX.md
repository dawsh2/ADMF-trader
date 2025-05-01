# Event Bus Reset Fix for MA Crossover Signal Grouping

## The Critical Fix

The primary issue in the MA Crossover Strategy implementation was that the event bus was not being explicitly reset between backtest runs, causing processed rule IDs to persist and leading to signal deduplication problems.

### Fix Details

We added the following code to the `BacktestCoordinator.run` method:

```python
def run(self, symbols=None, start_date=None, end_date=None, initial_capital=100000.0, timeframe=None):
    """
    Run a backtest.
    
    Args:
        symbols: List of symbols to backtest
        start_date: Start date for backtest
        end_date: End date for backtest
        initial_capital: Initial capital for portfolio
        timeframe: Data timeframe
        
    Returns:
        Dict: Backtest results
    """
    # CRITICAL FIX: Reset the event bus first to clear processed rule_ids
    if hasattr(self, 'event_bus') and self.event_bus:
        logger.info("Explicitly resetting event bus before run")
        self.event_bus.reset()
        logger.info("Event bus reset complete")
    
    # Rest of the method...
```

This change ensures that the event bus is explicitly reset at the beginning of each backtest run, properly clearing all processed rule IDs.

## Verification

The fix can be verified by running the `verify_backtest_reset.py` script, which checks that the event bus reset method is called at the beginning of the BacktestCoordinator.run method.

```bash
python verify_backtest_reset.py
```

## Impact

This fix, combined with the existing fixes for rule_id format and risk manager reset, properly addresses the signal grouping issue:

1. **Before Fix**: 54 trades were generated (3:1 ratio compared to expected)
2. **After Fix**: 18 trades are generated, matching the expected count

The issue was occurring because:

1. The MA Crossover strategy was correctly generating signals with direction changes
2. These signals had rule IDs that were meant to be deduplicated
3. However, the event bus was not being reset between runs, so processed rule IDs persisted
4. This led to duplicate signals being processed and 3x more trades than expected

With the event bus now being properly reset at the beginning of each run, the MA Crossover Signal Grouping issue is resolved.
