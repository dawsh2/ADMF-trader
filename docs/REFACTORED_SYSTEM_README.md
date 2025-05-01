# Testing the Refactored Architecture with the Complete System

This guide explains how to test the complete trading system with our refactored architecture that separates signal generation from position management.

## What Changed

The refactoring implementation includes:

1. **New Strategy Implementation**:
   - `SimpleMACrossoverStrategy` in `src/strategy/implementations/ma_crossover_pure.py`
   - Focuses only on generating signals based on market analysis
   - No position tracking or rule ID generation

2. **Enhanced Risk Manager**:
   - `EnhancedRiskManager` in `src/risk/managers/enhanced_risk_manager.py`
   - Handles position tracking and trading decisions
   - Generates rule IDs and manages signal groups

3. **System Integration**:
   - Created patched bootstrap to use our enhanced components
   - Added configuration to enable the refactored architecture

## Test Options

### Option 1: Run the Complete System

This option tests the refactored architecture using the complete trading system:

```bash
# Make the script executable
chmod +x chmod_run_script.sh
./chmod_run_script.sh

# Run the system with refactored architecture
./run_refactored_system.py
```

This will:
1. Apply patches to enable the enhanced risk manager
2. Load the refactored configuration (`config/refactored_test.yaml`)
3. Run the complete trading system with real data
4. Generate performance reports and logs

After running, check:
- `results/refactored_test/` for performance reports
- `refactored_system.log` for system logs

### Option 2: Run the Demo Script

For a simpler demonstration focusing just on the refactored components:

```bash
# Make the script executable
chmod +x chmod_test_script.sh
./chmod_test_script.sh

# Run the demo script
./test_refactored_architecture.py
```

This will:
1. Load data from `data/MINI_1min.csv`
2. Run a simplified version of the system with our refactored components
3. Generate visualization showing signals and positions
4. Log events to `refactoring_test.log`

After running, check:
- `refactoring_test_results.png` for visualization
- `refactoring_test.log` for event logs

## Verifying the Refactoring

When reviewing the system logs, look for these signs that the refactoring is working correctly:

1. **Strategy Logs**:
   - Should only show signal generation based on MA crossovers
   - No position tracking or rule ID related log entries

2. **Risk Manager Logs**:
   - Should show comparing signals against current positions
   - Should show rule ID generation and position tracking
   - Should show order creation based on direction changes

3. **System Performance**:
   - The system should trade correctly with the refactored architecture
   - Performance metrics should be comparable to the original implementation

## Troubleshooting

If you encounter issues:

1. **Check column case sensitivity**:
   - The MINI_1min.csv file has columns with capital letters (Open, High, Low, Close)
   - Our code handles this with case-insensitive matching

2. **Check logs for errors**:
   - Look at the main log file for error messages
   - Check bootstrap logs for component initialization issues

3. **Module not found errors**:
   - Make sure you're running from the project root directory

4. **Strategy not found**:
   - Check that the strategy name in the config matches the `name` attribute in the strategy class
