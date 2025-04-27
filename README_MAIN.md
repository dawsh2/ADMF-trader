# ADMF-Trader: Unified Entry Point

This document explains how to use the unified entry point (`main.py`) for running backtests with different strategy configurations.

## Overview

The `main.py` script provides a single, consistent entry point for running any strategy backtest. It leverages the Bootstrap pattern to initialize the system with the appropriate configuration, runs the backtest, and generates reports.

## Usage

### Basic Usage

To run a backtest with a specific configuration:

```bash
python main.py --config config/my_strategy.yaml
```

### Common Options

- `--config`: Path to the configuration file (required)
- `--output-dir`: Directory to save results (default: `./results`)
- `--data-dir`: Directory containing market data (default: `./data`)
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Data Generation

For testing, you can generate synthetic data:

```bash
python main.py --config config/regime_ensemble.yaml --generate-data
```

Data generation options:
- `--generate-data`: Generate synthetic data before running backtest
- `--data-type`: Type of synthetic data (multi_regime, trend, mean_reversion, volatility, random)
- `--plot-data`: Plot the generated data

## Examples

### Running the Regime Ensemble Strategy

```bash
python main.py --config config/regime_ensemble.yaml --output-dir ./results --log-level INFO
```

### Running a Backtest with Synthetic Data

```bash
python main.py --config config/ma_crossover.yaml --generate-data --data-type multi_regime --plot-data
```

### Running with Debug Logging

```bash
python main.py --config config/volatility_strategy.yaml --log-level DEBUG
```

## Output

The system will:
1. Create an output directory based on the configuration name
2. Save log files and backtest results in this directory
3. Print a summary of the backtest results to the console
4. Provide a list of saved output files

## Benefits

- **Consistency**: All backtests are run using the same initialization process
- **Simplicity**: Minimal command-line interface focused on configuration
- **Modularity**: Clear separation of system initialization, backtest execution, and reporting
- **Maintainability**: Changes to the initialization process only need to be made in one place
