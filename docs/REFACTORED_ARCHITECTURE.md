# Refactored Architecture Implementation

## Overview

The trading system has been refactored to properly separate signal generation from position management. This follows good software design principles, particularly the Single Responsibility Principle, by ensuring that:

1. Strategies focus solely on market analysis and signal generation
2. Risk managers handle position tracking and trading decisions

## Changes Made

### 1. System Bootstrap

The `system_bootstrap.py` file has been updated to:
- Support the enhanced risk manager
- Configure the risk manager based on the config type
- Skip signal interpreter when using the enhanced risk manager

### 2. Strategy Implementation

- Created a new strategy implementation: `simple_ma_crossover.py`
- This strategy only analyzes market data and emits directional signals
- No position tracking or rule ID generation in the strategy

### 3. Risk Manager

Added `enhanced_risk_manager.py` that:
- Queries the portfolio to determine current positions
- Compares signals against current positions
- Generates signal groups and rule IDs
- Creates orders only when direction changes

### 4. Configuration

The `mini_test.yaml` configuration has been updated to:
- Use the refactored strategy implementation
- Enable the enhanced risk manager
- Set appropriate parameters

## Running the System

Since the changes are now integrated directly into the system, you can run it with the standard command:

```bash
python main.py --config config/mini_test.yaml
```

This will:
1. Load the updated configuration
2. Use the refactored architecture components
3. Run a backtest with the simplified strategy and enhanced risk manager

## Verification

When the system runs, check the logs to verify:

1. **Strategy Logs**:
   - Only show signal generation based on market analysis
   - No position tracking or direction tracking
   - No rule ID generation

2. **Risk Manager Logs**:
   - Show position queries from the portfolio
   - Show position tracking and rule ID generation
   - Show order creation based on direction changes

## Additional Notes

- The old MA crossover implementations have been moved to a backup folder to avoid confusion
- The system bootstrap now checks the risk manager type in the configuration
- No temporary patches or scripts are needed as the changes are directly integrated

## Example Output

With the refactored architecture, the log output should now show:

```
2025-05-01 12:00:00 - simple_ma_crossover - INFO - BUY signal for MINI: fast MA crossed above slow MA
2025-05-01 12:00:00 - enhanced_risk_manager - INFO - Received signal: MINI direction=1 at 521.25
2025-05-01 12:00:00 - enhanced_risk_manager - INFO - Direction change for MINI: 0 -> 1, rule_id=MINI_BUY_group_1
2025-05-01 12:00:00 - enhanced_risk_manager - INFO - Creating order: BUY 100 MINI @ 521.25, rule_id=MINI_BUY_group_1
```

Note the clean separation between the strategy generating signals and the risk manager handling trading decisions.
