# ADMF-Trader Unused Files

This document lists files that can be safely moved to the `_archived` directory or removed to clean up the repository's root directory. The goal is to maintain a clean root directory containing only essential files.

## Essential Root Files to Keep

- `main.py` - Main entry point for the application
- `setup.py` - Package installation script
- `README.md` - Main documentation file
- `IMPROVEMENTS.md` - System-wide improvement suggestions
- `REGIME_ENSEMBLE_README.md` - Documentation for regime ensemble strategies
- `REGIME_OPTIMIZATION_GUIDE.md` - Guide for optimizing regime strategies
- `.gitignore` - Git ignore file

## Temporary Files to Remove

Files with # characters or temporary backup files that should be deleted:
- `#README.md#`
- `#claudePromopt#`
- `.#claudePromopt`
- `claudePromopt~`
- `claudePromopt.html`

## Config/Test Files to Move to Appropriate Directories

These files should be moved to more appropriate directories:
- `debug_config.py` → `src/core/` or `tests/`
- `fix_config.py` → `src/core/` or `tests/`
- `fix_data_handler.py` → `src/data/` or `_archived/`
- `test_broker_eod_closing.py` → `tests/`
- `test_data_handler.py` → `tests/`
- `test_eod_closing.py` → `tests/`
- `test_eod_closing_simplified.py` → `tests/`

## Log Files to Remove or Move to logs/

These files should be cleaned up or moved to the logs directory:
- `backtest.log` → `logs/`
- `fix_data_handler.log` → `logs/`
- `main.log` → `logs/`
- `optimization.log` → `logs/`
- `test_runner.log` → `logs/`
- `trading.log` → `logs/`

## "Fix" READMEs to Consolidate

These README files should be consolidated into the main documentation or moved to docs/:
- `COMPLETE_FIX_README.md` → `docs/`
- `DIRECT_FIX_README.md` → `docs/`
- `PORTFOLIO_FIX_README.md` → `docs/`
- `SIMPLE_FIX_README.md` → `docs/`
- `IMPLEMENTATION_STATUS.md` → `docs/`

## Script Files to Move

These scripts should be moved to appropriate directories:
- `run_all_tests.py` → `tests/`
- `run_event_tests.py` → `tests/`
- `run_fixed_tests.py` → `tests/`
- `run_fixed_tests.sh` → `tests/`
- `run_integration_tests.py` → `tests/`
- `run_safe_tests.py` → `tests/`
- `run_tests.py` → `tests/`
- `run_tests.sh` → `tests/`
- `run_tests_comprehensive.py` → `tests/`
- `run_tests_with_output.py` → `tests/`
- `run_tests_with_timeout.py` → `tests/`
- `setup_and_run_tests.sh` → `tests/`

## Other Files to Archive

- `push` - Git push script or temp file
- `keep_files.txt` - No longer needed
- `optimization_plan.md` → `docs/`

## Cleanup Instructions

1. Create backup of all files if needed
2. Move test scripts to the `tests/` directory
3. Move documentation files to the `docs/` directory
4. Move log files to the `logs/` directory
5. Delete temporary files
6. Archive fix-related files in `_archived/` for reference
7. Create appropriate .gitignore entries for log files and temporary files

The goal is to have a clean root directory with minimal files:
```
ADMF-trader/
├── main.py
├── setup.py
├── README.md
├── IMPROVEMENTS.md
├── REGIME_ENSEMBLE_README.md
├── REGIME_OPTIMIZATION_GUIDE.md
├── .gitignore
├── config/                  # Configuration files
├── data/                    # Sample and test data
├── docs/                    # Documentation
├── results/                 # Backtest results
├── src/                     # Source code
├── tests/                   # Test suite
└── examples/                # Example scripts and notebooks
```