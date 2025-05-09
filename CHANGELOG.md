# Changelog

## 2025-05-08 - Position Management Fix

### Added
- New `PositionManager` class for enforcing position limits and consistent position management
- New `BacktestState` class for proper state isolation between optimization runs
- Debug tools for analyzing position management
- Shell scripts for applying fixes and running debug tools

### Fixed
- Issue with multiple positions being opened for the same symbol
- Position state leakage between optimization runs
- Inconsistencies between trade PnL and equity changes
- Missing risk management parameters in configuration files

### Changed
- Updated SimpleMACrossoverStrategy to integrate with BacktestState
- Updated OptimizingBacktest to include PositionManager and BacktestState
- Improved component initialization order in BacktestCoordinator
- Enhanced configuration template with proper risk management settings
