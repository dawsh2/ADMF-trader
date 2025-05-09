# Analytics Module Documentation

## Overview

The Analytics module provides comprehensive tools for analyzing trading strategy performance. It includes metrics calculation, performance analysis, reporting, and visualization capabilities.

## Components

The module is organized into several submodules:

### Metrics

The metrics submodule contains functions for calculating various performance metrics:

- **Core Metrics** (`metrics/core.py`): Fundamental performance metrics like returns, volatility, and drawdowns.
- **Ratio Metrics** (`metrics/ratios.py`): Risk-adjusted performance ratios like Sharpe, Sortino, and Calmar.
- **Trade Metrics** (`metrics/trade.py`): Trade-specific metrics like win rate, profit factor, and expectancy.

### Analysis

The analysis submodule contains components for comprehensive performance analysis:

- **Performance Analyzer** (`analysis/performance.py`): Combines various metrics into a complete performance analysis.

### Reporting

The reporting submodule contains tools for generating reports in different formats:

- **Report Builder** (`reporting/report_builder.py`): Base class for report generation with a flexible section-based structure.
- **Text Report** (`reporting/text_report.py`): Generates plain text reports for console output or text files.
- **HTML Report** (`reporting/html_report.py`): Generates rich HTML reports with interactive elements and charts.

## Usage Examples

### Basic Usage

```python
from src.analytics.analysis.performance import PerformanceAnalyzer
from src.analytics.reporting.text_report import TextReportBuilder
from src.analytics.reporting.html_report import HTMLReportBuilder

# Create analyzer with equity curve and trades
analyzer = PerformanceAnalyzer(equity_curve, trades)

# Run analysis
metrics = analyzer.analyze_performance()

# Generate text report
text_builder = TextReportBuilder(analyzer=analyzer, title="Strategy Report")
text_report = text_builder.render()
text_builder.save("strategy_report.txt")

# Generate HTML report with charts
html_builder = HTMLReportBuilder(analyzer=analyzer, title="Strategy Report")
html_report = html_builder.render()
html_builder.save("strategy_report.html")
```

### Using Individual Metrics

```python
from src.analytics.metrics.core import total_return, max_drawdown, volatility
from src.analytics.metrics.ratios import sharpe_ratio, sortino_ratio
from src.analytics.metrics.trade import win_rate, profit_factor

# Calculate individual metrics
total_ret = total_return(equity_curve)
max_dd = max_drawdown(equity_curve)
vol = volatility(returns)
sharpe = sharpe_ratio(returns)
sortino = sortino_ratio(returns)
win_rt = win_rate(trades)
pf = profit_factor(trades)

print(f"Total Return: {total_ret:.2%}")
print(f"Max Drawdown: {max_dd:.2%}")
print(f"Volatility: {vol:.2%}")
print(f"Sharpe Ratio: {sharpe:.2f}")
print(f"Sortino Ratio: {sortino:.2f}")
print(f"Win Rate: {win_rt:.2%}")
print(f"Profit Factor: {pf:.2f}")
```

## Metrics Explained

### Return Metrics

- **Total Return**: The overall percentage return over the entire period.
- **Annualized Return**: The return normalized to an annual basis.
- **CAGR**: Compound Annual Growth Rate.

### Risk Metrics

- **Volatility**: Standard deviation of returns, a measure of risk.
- **Maximum Drawdown**: The largest peak-to-trough decline.
- **Average Drawdown**: The mean of all drawdowns.
- **Drawdown Duration**: How long drawdowns typically last.

### Risk-Adjusted Metrics

- **Sharpe Ratio**: Return per unit of risk (using standard deviation).
- **Sortino Ratio**: Return per unit of downside risk (using downside deviation).
- **Calmar Ratio**: Return per unit of maximum drawdown risk.
- **Omega Ratio**: Probability-weighted ratio of gains versus losses.

### Trade Metrics

- **Win Rate**: Percentage of trades that are profitable.
- **Profit Factor**: Gross profits divided by gross losses.
- **Expectancy**: Average amount you can expect to win or lose per trade.
- **Average Trade**: Mean P&L across all trades.
- **Average Win/Loss**: Mean P&L of winning/losing trades.

## Report Types

### Text Reports

Text reports provide a clean, well-formatted representation of performance metrics suitable for console output or text files. They include:

- Performance summary
- Detailed return metrics
- Risk metrics
- Trade statistics

### HTML Reports

HTML reports offer a rich, interactive presentation of performance results with visualizations:

- Summary dashboard with key metrics
- Interactive equity curve chart
- Returns distribution analysis
- Monthly returns heatmap
- Trade P&L distribution
- Detailed metrics tables

## Customization

### Adding Custom Metrics

You can extend the metrics modules with your own custom metrics:

```python
def my_custom_metric(equity_curve: pd.DataFrame, column: str = 'equity') -> float:
    """Calculate my custom performance metric."""
    # Implementation here
    return result
```

### Creating Custom Reports

You can create custom report formats by extending the `ReportBuilder` base class:

```python
class MyCustomReportBuilder(ReportBuilder):
    """Custom report builder implementation."""
    
    def render(self) -> str:
        """Implement custom rendering logic."""
        data = self.prepare_report_data()
        # Custom rendering logic
        return rendered_output
```

## Integration with Backtest System

The analytics module is designed to integrate seamlessly with the backtest system:

```python
from src.backtest.coordinator import BacktestCoordinator
from src.analytics.analysis.performance import PerformanceAnalyzer
from src.analytics.reporting.html_report import HTMLReportBuilder

# Run backtest
coordinator = BacktestCoordinator(config)
results = coordinator.run()

# Analyze results
analyzer = PerformanceAnalyzer(
    equity_curve=results.equity_curve,
    trades=results.trades
)
analyzer.analyze_performance()

# Generate report
report = HTMLReportBuilder(analyzer)
report.save("backtest_report.html")
```