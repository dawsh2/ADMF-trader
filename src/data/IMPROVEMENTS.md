# Data Module Improvements

This document outlines recommended improvements to the `src/data` module to address duplication, standardize interfaces, and enhance maintainability.

## Current Issues

### 1. Redundant Implementations

The data module contains overlapping implementations with duplicated functionality:

- **Data Handlers**
  - `historical_data_handler.py` and `csv_data_handler.py` have significant overlap
  - Both implement similar CSV loading and column mapping logic
  - `historical_data_handler.py` has both current and backup (.bak) versions

- **Data Models**
  - Dual use of `src.core.data_model.Bar` and `src.data.data_types.Bar`
  - Redundant conversion between different Bar representations

### 2. Inconsistent Inheritance

- **Interface Divergence**
  - `historical_data_handler.py` extends `DataHandler` but implements methods from `DataHandlerBase`
  - `historical_data_handler.py.bak` extends `Component` directly instead of a data-specific class
  - `csv_data_handler.py` extends `DataHandler`

- **Inheritance vs. Composition**
  - Limited use of composition for reusing functionality
  - CSV loading repeated across multiple classes instead of being extracted

### 3. Other Architecture Issues

- **Configuration Complexity**: CSV handler configuration options scattered across implementations
- **Exception Handling**: Inconsistent error handling approaches
- **Registry Duplication**: Module has its own registry similar to core registry

## Recommended Improvements

### 1. Consolidate Data Handling Components

#### Phase 1: Extract Common Functionality
- Create a shared `CSVLoader` utility class that handles:
  - Finding and reading CSV files
  - Column mapping
  - Date parsing
  - Standardization of data formats

#### Phase 2: Simplify Handler Hierarchy
- Select `DataHandler` as the canonical interface
- Create a clean `BaseDataHandler` implementation
- Build specialized handlers through composition:
  ```python
  class HistoricalDataHandler(DataHandler):
      def __init__(self, name, data_config):
          super().__init__(name)
          self.csv_loader = CSVLoader(data_config)
          self.time_splitter = TimeSeriesSplitter()
  ```

#### Phase 3: Remove Redundancy
- Delete backup (.bak) files after migration
- Remove duplicate implementations
- Update import statements throughout the codebase

### 2. Standardize Data Models

#### Bar Implementation
- Select `src.data.data_types.Bar` dataclass as the canonical implementation
- Add conversion utilities for backward compatibility
- Update all code to use the canonical model

#### Timeframe Standardization
- Consolidate timeframe normalization logic into one place
- Add proper docstrings with examples

### 3. Improve Interface Contracts

#### Well-Defined Responsibilities
- `DataSourceBase`: Responsible only for raw data access
- `DataHandler`: Responsible for managing data flow with clear lifecycle:
  - Loading data
  - Splitting data (train/test)
  - Serving bars
  - Emitting events

#### Consistent Method Signatures
- Standardize parameter types and return values
- Add comprehensive type hints
- Document method contracts clearly

### 4. Advanced Features

#### Caching Layer
- Implement data caching for better performance
- Support memory-mapped files for large datasets

#### Asynchronous Loading
- Add support for asynchronous data loading
- Implement progressive loading for large datasets

#### Data Quality Checks
- Add validation for data completeness
- Implement detection of gaps, outliers, etc.

## Implementation Priority

1. **High Priority**
   - Extract common CSV handling logic
   - Select canonical Bar model
   - Standardize interfaces

2. **Medium Priority**
   - Implement proper caching
   - Improve error handling
   - Add data quality validation

3. **Lower Priority**
   - Add advanced features
   - Improve test coverage
   - Optimize performance

## Migration Guide

The migration should proceed in these steps:

1. Create the common `CSVLoader` utility class
2. Update existing handlers to use this class
3. Standardize on `DataHandler` interface
4. Remove deprecated and duplicate code
5. Update documentation and examples

This approach ensures backward compatibility while reducing code duplication and improving maintainability.