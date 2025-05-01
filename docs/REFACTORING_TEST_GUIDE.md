# Testing the Refactored Architecture

This guide explains how to test and verify the architectural changes made to separate signal generation from position management.

## Overview of Changes

1. **Strategy Module**: Now focused solely on analyzing market data and generating directional signals
2. **Risk Manager**: Centralized position tracking and trading decision logic
3. **Clear Separation**: Cleaner architecture with single responsibility for each component

## Running the Test

We've created a demonstration script that shows these architectural changes in action using real market data.

### Option 1: Using the run script

```bash
# Make the script executable
chmod +x run_test.sh

# Run the test
./run_test.sh
```

### Option 2: Running directly

```bash
python test_refactored_architecture.py
```

## What the Test Does

1. **Loads real market data** from `data/MINI_1min.csv`
2. **Creates strategy and risk manager** components with the new architecture
3. **Processes market data** through the strategy to generate signals
4. **Routes signals** to the risk manager to make trading decisions
5. **Tracks positions** in the mock portfolio manager
6. **Visualizes results** showing prices, moving averages, signals, and positions

## Reviewing Test Results

After running the test, you can examine the following outputs:

1. **Console Output**: Shows a summary of the test run

2. **Log File**: `refactoring_test.log` contains detailed event logs showing:
   - Signal generation by the strategy
   - Order creation by the risk manager
   - Position updates

3. **Visualization**: `refactoring_test_results.png` shows:
   - Price chart with moving averages
   - Buy signals (green triangles) and sell signals (red triangles)
   - Position size changes over time
   - Price performance

## Verifying the Architectural Changes

When reviewing the test results, confirm that:

1. **Strategy Only Generates Signals**:
   - Strategies are not tracking positions
   - Signals are based purely on market analysis (MA crossovers)
   - No rule IDs or position tracking in strategy code

2. **Risk Manager Handles Trading Decisions**:
   - Compares signals against current positions
   - Generates rule IDs for tracking
   - Creates orders only when direction changes
   - Maintains position state

3. **Clean Flow of Information**:
   - Strategy generates signals based on market data
   - Risk manager receives signals and makes trading decisions
   - Portfolio manager tracks positions

## Next Steps

After verifying that the refactoring works correctly:

1. Continue migrating remaining strategies to the new pattern
2. Update system bootstrap code to use the enhanced risk manager
3. Run comparative tests with the original implementation to ensure behavior is consistent
