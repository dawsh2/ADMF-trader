"""
Reporter for optimization results.

This module handles the formatting and saving of optimization results,
providing a standardized way to report optimization outcomes.
"""

import os
import json
import logging
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from tabulate import tabulate

# Set up logging
logger = logging.getLogger(__name__)

class OptimizationReporter:
    """
    Reporter for optimization results.
    
    This class handles the formatting and saving of optimization results.
    """
    
    def __init__(self, config):
        """
        Initialize the reporter.
        
        Args:
            config (dict): Optimization configuration
        """
        self.config = config
        self.output_dir = config.get('output_dir', './optimization_results')
        
        # Create output directory if it doesn't exist
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
    def generate_report(self, results):
        """
        Generate a report from optimization results.
        
        Args:
            results (dict): Optimization results
            
        Returns:
            str: Path to the generated report
        """
        # Check if results is None
        if results is None:
            logger.error("Cannot generate report: results is None")
            return None
            
        # Log start of report generation
        logger.info("Generating optimization report")
        
        # Get timestamp from results or generate new one
        timestamp = results.get('timestamp', 
                             datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        # Create report filename
        strategy_name = self.config['strategy']['name']
        report_filename = f"{strategy_name}_report_{timestamp}"
        
        # Generate appropriate reports based on config
        report_format = self.config.get('reporting', {}).get('format', 'all')
        
        # Generate reports
        if report_format in ['all', 'text']:
            self._generate_text_report(results, f"{report_filename}.txt")
            
        if report_format in ['all', 'csv']:
            self._generate_csv_report(results, f"{report_filename}.csv")
            
        if report_format in ['all', 'html']:
            self._generate_html_report(results, f"{report_filename}.html")
            
        if report_format in ['all', 'visualization']:
            self._generate_visualizations(results, report_filename)
            
        logger.info(f"Report generation completed for {strategy_name}")
        
        return os.path.join(self.output_dir, f"{report_filename}.txt")
        
    def _generate_text_report(self, results, filename):
        """
        Generate a text report from optimization results.
        
        Args:
            results (dict): Optimization results
            filename (str): Name of the output file
        """
        # Create file path
        filepath = os.path.join(self.output_dir, filename)
        
        # Create report content
        report = []
        
        # Add header
        strategy_name = self.config['strategy']['name']
        timestamp = results.get('timestamp', 'Not available')
        
        report.append('=' * 80)
        report.append(f"OPTIMIZATION REPORT: {strategy_name}")
        report.append(f"Timestamp: {timestamp}")
        report.append('=' * 80)
        report.append('')
        
        # Add configuration summary
        report.append('CONFIGURATION')
        report.append('-' * 80)
        
        # Get optimization method
        optimization_method = self.config.get('optimization', {}).get('method', 'grid')
        report.append(f"Optimization Method: {optimization_method}")
        
        # Get objective function
        objective = self.config.get('optimization', {}).get('objective', 'sharpe_ratio')
        report.append(f"Objective Function: {objective}")
        
        # Add data information
        data_config = self.config.get('data', {})
        symbols = data_config.get('symbols', [])
        if isinstance(symbols, list):
            symbols_str = ', '.join(symbols)
        else:
            symbols_str = symbols
            
        report.append(f"Symbols: {symbols_str}")
        
        # Add train/test split information
        train_test_config = data_config.get('train_test_split', {})
        split_method = train_test_config.get('method', 'ratio')
        
        if split_method == 'ratio':
            train_ratio = train_test_config.get('train_ratio', 0.7)
            test_ratio = train_test_config.get('test_ratio', 0.3)
            report.append(f"Train/Test Split: {split_method} (Train: {train_ratio:.2f}, Test: {test_ratio:.2f})")
        elif split_method == 'date':
            train_start = train_test_config.get('train_start', 'Not specified')
            train_end = train_test_config.get('train_end', 'Not specified')
            test_start = train_test_config.get('test_start', 'Not specified')
            test_end = train_test_config.get('test_end', 'Not specified')
            report.append(f"Train/Test Split: {split_method}")
            report.append(f"  Train Period: {train_start} to {train_end}")
            report.append(f"  Test Period: {test_start} to {test_end}")
        else:
            report.append(f"Train/Test Split: {split_method}")
            
        report.append('')
        
        # Add parameter space summary
        parameter_space = results.get('parameter_space', {})
        report.append('PARAMETER SPACE')
        report.append('-' * 80)

        # Check if parameter_space is a dictionary
        if isinstance(parameter_space, dict):
            for param_name, param_info in parameter_space.items():
                param_type = param_info.get('type', 'Not specified')

                if param_type == 'integer' or param_type == 'float':
                    param_min = param_info.get('min', 'Not specified')
                    param_max = param_info.get('max', 'Not specified')
                    param_step = param_info.get('step', 'Not specified')
                    report.append(f"{param_name}: {param_type} (min: {param_min}, max: {param_max}, step: {param_step})")
                elif param_type == 'categorical':
                    categories = param_info.get('categories', [])
                    categories_str = ', '.join(str(c) for c in categories)
                    report.append(f"{param_name}: {param_type} (categories: {categories_str})")
                elif param_type == 'boolean':
                    report.append(f"{param_name}: {param_type}")
                else:
                    report.append(f"{param_name}: {param_type}")
        elif isinstance(parameter_space, str):
            # Just output the parameter space as a string
            report.append(parameter_space)
            report.append('')
            # Skip the detailed parameter parsing
                
        report.append('')
        
        # Add best parameters
        best_parameters = results.get('best_parameters', {})
        report.append('BEST PARAMETERS')
        report.append('-' * 80)
        
        # Check if best_parameters is None or empty
        if best_parameters is None:
            report.append("No valid parameters found. Optimization may have failed to produce results.")
        elif not best_parameters:
            report.append("No parameters found. Optimization completed but did not find a viable solution.")
        else:
            for param_name, param_value in best_parameters.items():
                report.append(f"{param_name}: {param_value}")
            
        report.append('')
        
        # Add performance metrics
        report.append('PERFORMANCE METRICS')
        report.append('-' * 80)
        
        # Add training metrics if available
        train_results = results.get('train_results', {})
        if train_results:
            report.append('Training Performance:')
            train_stats = train_results.get('statistics', {})
            
            # List all available metrics in train_stats
            for key, value in sorted(train_stats.items()):
                if isinstance(value, (int, float)):
                    if 'pct' in key or 'rate' in key or 'ratio' in key or 'drawdown' in key:
                        report.append(f"  {key}: {value:.4f}")
                    else:
                        report.append(f"  {key}: {value}")
            report.append('')
            
        # Add testing metrics if available
        test_results = results.get('test_results', {})
        if test_results:
            report.append('Testing Performance:')
            test_stats = test_results.get('statistics', {})

            # CRITICAL FIX: Debug logging to verify test_stats is unique from train_stats
            train_stats = train_results.get('statistics', {})
            if test_stats == train_stats:
                logger.error("TEST DATA ISSUE: Test statistics are identical to train statistics!")
                logger.error("This indicates potential data leakage or reporting issue")

                # Add warning to report
                report.append("  WARNING: Test results appear identical to train results!")
                report.append("  This could indicate an issue with the train/test split implementation.")

            # List all available metrics in test_stats
            for key, value in sorted(test_stats.items()):
                if isinstance(value, (int, float)):
                    if 'pct' in key or 'rate' in key or 'ratio' in key or 'drawdown' in key:
                        report.append(f"  {key}: {value:.4f}")
                    else:
                        report.append(f"  {key}: {value}")
            report.append('')
            
        # Add combined metrics if available
        combined_stats = results.get('statistics', {})
        if combined_stats:
            report.append('Overall Performance:')
            
            # List all available metrics in combined_stats
            for key, value in sorted(combined_stats.items()):
                if isinstance(value, (int, float)):
                    if 'pct' in key or 'rate' in key or 'ratio' in key or 'drawdown' in key:
                        report.append(f"  {key}: {value:.4f}")
                    else:
                        report.append(f"  {key}: {value}")
            report.append('')
            
        # Add overfitting analysis if train and test results are available
        if train_results and test_results:
            report.append('OVERFITTING ANALYSIS')
            report.append('-' * 80)

            train_stats = train_results.get('statistics', {})
            test_stats = test_results.get('statistics', {})

            # CRITICAL FIX: Check if train and test stats are identical
            if train_stats == test_stats:
                report.append("CRITICAL WARNING: Train and test statistics are identical!")
                report.append("This indicates a potential data leakage issue or train/test isolation failure.")
                report.append("Overfitting analysis cannot be performed with identical datasets.")
                report.append("")

                # Add diagnostic information on trades
                train_trades = train_results.get('trades', [])
                test_trades = test_results.get('trades', [])

                if train_trades and test_trades:
                    # Compare first few trades between train and test
                    report.append("Trade Comparison (First 3 trades):")

                    for i in range(min(3, len(train_trades), len(test_trades))):
                        train_trade = train_trades[i]
                        test_trade = test_trades[i]

                        train_entry = train_trade.get('entry_time', 'N/A')
                        test_entry = test_trade.get('entry_time', 'N/A')

                        if train_entry == test_entry:
                            report.append(f"  Trade {i+1}: Same entry time in both datasets: {train_entry}")
                        else:
                            report.append(f"  Trade {i+1}: Train entry: {train_entry}, Test entry: {test_entry}")

                    report.append("")

            # Display consistency metrics
            train_metrics_consistent = train_results.get('metrics_consistent', True)
            test_metrics_consistent = test_results.get('metrics_consistent', True)
            train_trades_consistent = train_results.get('trades_equity_consistent', True)
            test_trades_consistent = test_results.get('trades_equity_consistent', True)

            report.append("Data Consistency Check:")
            report.append(f"  Train metrics consistent: {train_metrics_consistent}")
            report.append(f"  Test metrics consistent: {test_metrics_consistent}")
            report.append(f"  Train trades/equity consistent: {train_trades_consistent}")
            report.append(f"  Test trades/equity consistent: {test_trades_consistent}")
            report.append("")

            # Calculate performance differences
            return_diff = train_stats.get('return_pct', 0) - test_stats.get('return_pct', 0)
            sharpe_diff = train_stats.get('sharpe_ratio', 0) - test_stats.get('sharpe_ratio', 0)
            pf_diff = train_stats.get('profit_factor', 0) - test_stats.get('profit_factor', 0)

            report.append(f"Return Difference (Train - Test): {return_diff:.2f}%")
            report.append(f"Sharpe Ratio Difference: {sharpe_diff:.2f}")
            report.append(f"Profit Factor Difference: {pf_diff:.2f}")

            # Add overfitting assessment
            overfitting_score = (abs(return_diff) / 100 + abs(sharpe_diff) + abs(pf_diff)) / 3

            if return_diff == 0 and sharpe_diff == 0 and pf_diff == 0:
                assessment = "INVALID - Train and test datasets are identical"
                logger.error("CRITICAL ERROR: Zero differences detected between train and test results!")
            elif overfitting_score < 0.2:
                assessment = "Low risk of overfitting"
            elif overfitting_score < 0.5:
                assessment = "Moderate risk of overfitting"
            else:
                assessment = "High risk of overfitting"

            report.append(f"Overfitting Assessment: {assessment} (Score: {overfitting_score:.2f})")

            # Add warning about inconsistent metrics
            if not (train_metrics_consistent and test_metrics_consistent and
                   train_trades_consistent and test_trades_consistent):
                report.append("")
                report.append("WARNING: Metric inconsistencies detected.")
                report.append("This may indicate issues with trade tracking or equity calculation.")
                report.append("Consider reviewing the implementation or running debug diagnostics.")

            report.append('')
            
        # Add parameter importance if available
        parameter_importance = results.get('parameter_importance', {})
        if parameter_importance:
            report.append('PARAMETER IMPORTANCE')
            report.append('-' * 80)
            
            for param_name, importance in parameter_importance.items():
                report.append(f"{param_name}: {importance:.4f}")
                
            report.append('')
            
        # Write report to file
        try:
            with open(filepath, 'w') as f:
                f.write('\n'.join(report))
            logger.info(f"Text report saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving text report: {e}")
            
    def _generate_csv_report(self, results, filename):
        """
        Generate a CSV report from optimization results.
        
        Args:
            results (dict): Optimization results
            filename (str): Name of the output file
        """
        # Create file path
        filepath = os.path.join(self.output_dir, filename)
        
        # Extract results grid if available
        results_grid = results.get('results_grid', [])
        
        if not results_grid:
            logger.warning("No results grid available for CSV report")
            return
            
        try:
            # Convert to DataFrame
            df = pd.DataFrame(results_grid)
            
            # Save to CSV
            df.to_csv(filepath, index=False)
            logger.info(f"CSV report saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving CSV report: {e}")
            
    def _generate_html_report(self, results, filename):
        """
        Generate an HTML report from optimization results.
        
        Args:
            results (dict): Optimization results
            filename (str): Name of the output file
        """
        # Create file path
        filepath = os.path.join(self.output_dir, filename)
        
        # Create report content
        strategy_name = self.config['strategy']['name']
        timestamp = results.get('timestamp', 'Not available')
        
        # Create HTML content
        html = []
        
        # Add header
        html.append('<!DOCTYPE html>')
        html.append('<html lang="en">')
        html.append('<head>')
        html.append('<meta charset="UTF-8">')
        html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        html.append(f'<title>Optimization Report: {strategy_name}</title>')
        html.append('<style>')
        html.append('body { font-family: Arial, sans-serif; margin: 20px; }')
        html.append('h1, h2 { color: #333; }')
        html.append('table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }')
        html.append('th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }')
        html.append('th { background-color: #f2f2f2; }')
        html.append('tr:nth-child(even) { background-color: #f9f9f9; }')
        html.append('.card { border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 20px; }')
        html.append('.metric { display: inline-block; width: 32%; margin-bottom: 10px; }')
        html.append('.warning { color: #f44336; }')
        html.append('</style>')
        html.append('</head>')
        html.append('<body>')
        
        # Add title
        html.append(f'<h1>Optimization Report: {strategy_name}</h1>')
        html.append(f'<p>Generated on: {timestamp}</p>')
        
        # Add configuration summary
        html.append('<div class="card">')
        html.append('<h2>Configuration</h2>')
        
        # Get optimization method
        optimization_method = self.config.get('optimization', {}).get('method', 'grid')
        objective = self.config.get('optimization', {}).get('objective', 'sharpe_ratio')
        
        html.append('<table>')
        html.append('<tr><th>Setting</th><th>Value</th></tr>')
        html.append(f'<tr><td>Optimization Method</td><td>{optimization_method}</td></tr>')
        html.append(f'<tr><td>Objective Function</td><td>{objective}</td></tr>')
        
        # Add data information
        data_config = self.config.get('data', {})
        symbols = data_config.get('symbols', [])
        if isinstance(symbols, list):
            symbols_str = ', '.join(symbols)
        else:
            symbols_str = symbols
            
        html.append(f'<tr><td>Symbols</td><td>{symbols_str}</td></tr>')
        
        # Add train/test split information
        train_test_config = data_config.get('train_test_split', {})
        split_method = train_test_config.get('method', 'ratio')
        
        if split_method == 'ratio':
            train_ratio = train_test_config.get('train_ratio', 0.7)
            test_ratio = train_test_config.get('test_ratio', 0.3)
            html.append(f'<tr><td>Train/Test Split</td><td>{split_method} (Train: {train_ratio:.2f}, Test: {test_ratio:.2f})</td></tr>')
        elif split_method == 'date':
            train_start = train_test_config.get('train_start', 'Not specified')
            train_end = train_test_config.get('train_end', 'Not specified')
            test_start = train_test_config.get('test_start', 'Not specified')
            test_end = train_test_config.get('test_end', 'Not specified')
            html.append(f'<tr><td>Train/Test Split</td><td>{split_method}</td></tr>')
            html.append(f'<tr><td>Train Period</td><td>{train_start} to {train_end}</td></tr>')
            html.append(f'<tr><td>Test Period</td><td>{test_start} to {test_end}</td></tr>')
        else:
            html.append(f'<tr><td>Train/Test Split</td><td>{split_method}</td></tr>')
            
        html.append('</table>')
        html.append('</div>')
        
        # Add best parameters
        best_parameters = results.get('best_parameters', {})
        
        html.append('<div class="card">')
        html.append('<h2>Best Parameters</h2>')
        
        if best_parameters is None:
            html.append('<p class="warning">No valid parameters found. Optimization may have failed to produce results.</p>')
        elif not best_parameters:
            html.append('<p class="warning">No parameters found. Optimization completed but did not find a viable solution.</p>')
        else:
            html.append('<table>')
            html.append('<tr><th>Parameter</th><th>Value</th></tr>')
            
            for param_name, param_value in best_parameters.items():
                html.append(f'<tr><td>{param_name}</td><td>{param_value}</td></tr>')
                
            html.append('</table>')
            
        html.append('</div>')
        
        # Add performance metrics
        html.append('<div class="card">')
        html.append('<h2>Performance Metrics</h2>')
        
        # Add training metrics if available
        train_results = results.get('train_results', {})
        test_results = results.get('test_results', {})

        # CRITICAL FIX: Add diagnostic to check for identical train/test stats
        train_stats = train_results.get('statistics', {})
        test_stats = test_results.get('statistics', {})

        if train_stats and test_stats and train_stats == test_stats:
            logger.error("CRITICAL HTML REPORT ISSUE: Train and test statistics are identical!")
            # Add warning box to HTML report
            html.append('<div style="background-color: #ffcccc; border: 1px solid #ff0000; padding: 10px; margin: 10px 0; border-radius: 5px;">')
            html.append('<strong>WARNING: Train and test statistics are identical!</strong>')
            html.append('<p>This may indicate an issue with the train/test split implementation or data isolation.</p>')
            html.append('</div>')

        if train_results or test_results:
            html.append('<table>')
            html.append('<tr><th>Metric</th><th>Training</th><th>Testing</th></tr>')

            # Define metrics to display
            metrics = [
                ('Total Return (%)', 'return_pct', ':.2f'),
                ('Sharpe Ratio', 'sharpe_ratio', ':.2f'),
                ('Profit Factor', 'profit_factor', ':.2f'),
                ('Max Drawdown (%)', 'max_drawdown', ':.2f'),
                ('Win Rate', 'win_rate', ':.2f'),
                ('Trades Executed', 'trades_executed', '')
            ]

            for label, key, format_str in metrics:
                train_value = train_stats.get(key, 'N/A')
                test_value = test_stats.get(key, 'N/A')

                # Add row highlighting if values are identical (for non-N/A values)
                row_style = ""
                if train_value != 'N/A' and test_value != 'N/A' and train_value == test_value:
                    row_style = ' style="background-color: #ffffcc;"'

                if train_value != 'N/A' and format_str and isinstance(train_value, (int, float)):
                    # Safe alternative to f-string formatting
                    try:
                        train_value = format(train_value, format_str)
                    except (ValueError, TypeError):
                        train_value = str(train_value)

                if test_value != 'N/A' and format_str and isinstance(test_value, (int, float)):
                    # Safe alternative to f-string formatting
                    try:
                        test_value = format(test_value, format_str)
                    except (ValueError, TypeError):
                        test_value = str(test_value)

                html.append(f'<tr{row_style}><td>{label}</td><td>{train_value}</td><td>{test_value}</td></tr>')

            html.append('</table>')
        else:
            html.append('<p>No performance metrics available</p>')
            
        html.append('</div>')
        
        # Add overfitting analysis if train and test results are available
        if train_results and test_results:
            html.append('<div class="card">')
            html.append('<h2>Overfitting Analysis</h2>')

            train_stats = train_results.get('statistics', {})
            test_stats = test_results.get('statistics', {})

            # CRITICAL FIX: Add warning if train and test stats are identical
            if train_stats == test_stats:
                html.append('<div style="background-color: #ffcccc; border: 1px solid #ff0000; padding: 10px; margin: 10px 0; border-radius: 5px;">')
                html.append('<strong>CRITICAL WARNING: Train and test statistics are identical!</strong>')
                html.append('<p>This indicates that train and test datasets contain the same data or there is a data isolation issue. Overfitting analysis is not valid with identical datasets.</p>')
                html.append('</div>')

                # Add detailed trade comparison
                train_trades = train_results.get('trades', [])
                test_trades = test_results.get('trades', [])

                if train_trades and test_trades:
                    html.append('<h3>Trade Comparison</h3>')
                    html.append('<table>')
                    html.append('<tr><th>#</th><th>Train Entry Time</th><th>Test Entry Time</th><th>Same?</th></tr>')

                    for i in range(min(5, len(train_trades), len(test_trades))):
                        train_trade = train_trades[i]
                        test_trade = test_trades[i]

                        train_entry = train_trade.get('entry_time', 'N/A')
                        test_entry = test_trade.get('entry_time', 'N/A')

                        is_same = train_entry == test_entry
                        same_text = "IDENTICAL" if is_same else "Different"
                        same_color = "#ffcccc" if is_same else "#ccffcc"

                        html.append(f'<tr style="background-color: {same_color}"><td>{i+1}</td><td>{train_entry}</td><td>{test_entry}</td><td>{same_text}</td></tr>')

                    html.append('</table>')

            # Calculate performance differences
            return_diff = train_stats.get('return_pct', 0) - test_stats.get('return_pct', 0)
            sharpe_diff = train_stats.get('sharpe_ratio', 0) - test_stats.get('sharpe_ratio', 0)
            pf_diff = train_stats.get('profit_factor', 0) - test_stats.get('profit_factor', 0)

            html.append('<h3>Performance Differences</h3>')
            html.append('<table>')
            html.append('<tr><th>Metric</th><th>Difference (Train - Test)</th></tr>')

            # Highlight rows with zero difference
            return_style = ' style="background-color: #ffffcc;"' if return_diff == 0 else ''
            sharpe_style = ' style="background-color: #ffffcc;"' if sharpe_diff == 0 else ''
            pf_style = ' style="background-color: #ffffcc;"' if pf_diff == 0 else ''

            html.append(f'<tr{return_style}><td>Return (%)</td><td>{return_diff:.2f}%</td></tr>')
            html.append(f'<tr{sharpe_style}><td>Sharpe Ratio</td><td>{sharpe_diff:.2f}</td></tr>')
            html.append(f'<tr{pf_style}><td>Profit Factor</td><td>{pf_diff:.2f}</td></tr>')
            html.append('</table>')

            # Add overfitting assessment
            overfitting_score = (abs(return_diff) / 100 + abs(sharpe_diff) + abs(pf_diff)) / 3

            if return_diff == 0 and sharpe_diff == 0 and pf_diff == 0:
                assessment = "INVALID - Train and test datasets are identical"
                color = "red"
                logger.error("CRITICAL ERROR: Zero differences detected between train and test results in HTML report!")
            elif overfitting_score < 0.2:
                assessment = "Low risk of overfitting"
                color = "green"
            elif overfitting_score < 0.5:
                assessment = "Moderate risk of overfitting"
                color = "orange"
            else:
                assessment = "High risk of overfitting"
                color = "red"

            html.append(f'<p><strong>Overfitting Assessment:</strong> <span style="color: {color}">{assessment}</span> (Score: {overfitting_score:.2f})</p>')
            html.append('</div>')
            
        # Add parameter importance if available
        parameter_importance = results.get('parameter_importance', {})
        if parameter_importance:
            html.append('<div class="card">')
            html.append('<h2>Parameter Importance</h2>')
            
            html.append('<table>')
            html.append('<tr><th>Parameter</th><th>Importance</th></tr>')
            
            # Sort by importance
            sorted_params = sorted(parameter_importance.items(), key=lambda x: x[1], reverse=True)
            
            for param_name, importance in sorted_params:
                html.append(f'<tr><td>{param_name}</td><td>{importance:.4f}</td></tr>')
                
            html.append('</table>')
            html.append('</div>')
            
        # Add results grid if available (top N results)
        results_grid = results.get('results_grid', [])
        if results_grid:
            html.append('<div class="card">')
            html.append('<h2>Top Results</h2>')
            
            # Limit to top 10 results
            top_results = results_grid[:10] if len(results_grid) > 10 else results_grid
            
            if top_results:
                # Get column names
                columns = list(top_results[0].keys())
                
                html.append('<table>')
                
                # Add header
                html.append('<tr>')
                for col in columns:
                    html.append(f'<th>{col}</th>')
                html.append('</tr>')
                
                # Add data rows
                for row in top_results:
                    html.append('<tr>')
                    for col in columns:
                        value = row.get(col, '')
                        if isinstance(value, float):
                            html.append(f'<td>{value:.4f}</td>')
                        else:
                            html.append(f'<td>{value}</td>')
                    html.append('</tr>')
                    
                html.append('</table>')
            else:
                html.append('<p>No results available</p>')
                
            html.append('</div>')
            
        # Add footer
        html.append('<p><small>Generated by ADMF-Trader Optimization Framework</small></p>')
        html.append('</body>')
        html.append('</html>')
        
        # Write HTML to file
        try:
            with open(filepath, 'w') as f:
                f.write('\n'.join(html))
            logger.info(f"HTML report saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving HTML report: {e}")
            
    def _generate_visualizations(self, results, base_filename):
        """
        Generate visualizations from optimization results.
        
        Args:
            results (dict): Optimization results
            base_filename (str): Base name for output files
        """
        # Check if matplotlib is available
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
        except ImportError:
            logger.warning("Matplotlib not available, skipping visualizations")
            return
            
        try:
            # Create directory for visualizations
            viz_dir = os.path.join(self.output_dir, 'visualizations')
            Path(viz_dir).mkdir(parents=True, exist_ok=True)
            
            # 1. Generate parameter heatmap for grid search
            self._generate_parameter_heatmap(results, os.path.join(viz_dir, f"{base_filename}_heatmap.png"))
            
            # 2. Generate equity curve comparison for train/test
            self._generate_equity_curve_comparison(results, os.path.join(viz_dir, f"{base_filename}_equity.png"))
            
            # 3. Generate parameter importance visualization
            self._generate_parameter_importance(results, os.path.join(viz_dir, f"{base_filename}_importance.png"))
            
            # 4. Generate overfitting analysis visualization
            self._generate_overfitting_analysis(results, os.path.join(viz_dir, f"{base_filename}_overfitting.png"))
            
            logger.info(f"Visualizations generated in {viz_dir}")
        except Exception as e:
            logger.error(f"Error generating visualizations: {e}")
            
    def _generate_parameter_heatmap(self, results, filepath):
        """
        Generate a heatmap of parameter combinations.
        
        Args:
            results (dict): Optimization results
            filepath (str): Path to save the visualization
        """
        # Skip if not grid search or no results grid
        optimization_method = self.config.get('optimization', {}).get('method', 'grid')
        if optimization_method != 'grid':
            return
            
        results_grid = results.get('results_grid', [])
        if not results_grid:
            return
            
        # Try to generate heatmap for two parameters
        parameter_space = results.get('parameter_space', {})
        if len(parameter_space) < 2:
            return
            
        # Get the first two parameters
        param_names = list(parameter_space.keys())[:2]
        param1, param2 = param_names
        
        # Extract parameter values and scores
        param1_values = []
        param2_values = []
        scores = []
        
        for result in results_grid:
            if param1 in result and param2 in result and 'score' in result:
                param1_values.append(result[param1])
                param2_values.append(result[param2])
                scores.append(result['score'])
                
        # Skip if insufficient data
        if len(param1_values) < 4:
            return
            
        # Create unique parameter values for grid
        unique_param1 = sorted(set(param1_values))
        unique_param2 = sorted(set(param2_values))
        
        # Create score grid
        score_grid = np.zeros((len(unique_param2), len(unique_param1)))
        
        for i, p1 in enumerate(param1_values):
            p2 = param2_values[i]
            score = scores[i]
            
            i1 = unique_param1.index(p1)
            i2 = unique_param2.index(p2)
            
            score_grid[i2, i1] = score
            
        # Create plot
        plt.figure(figsize=(10, 8))
        plt.imshow(score_grid, interpolation='nearest', cmap='viridis')
        plt.colorbar(label='Score')
        
        # Set ticks and labels
        plt.xticks(np.arange(len(unique_param1)), unique_param1, rotation=45)
        plt.yticks(np.arange(len(unique_param2)), unique_param2)
        
        plt.xlabel(param1)
        plt.ylabel(param2)
        plt.title(f"Parameter Optimization Heatmap")
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(filepath)
        plt.close()
        
    def _generate_equity_curve_comparison(self, results, filepath):
        """
        Generate equity curve comparison visualization.
        
        Args:
            results (dict): Optimization results
            filepath (str): Path to save the visualization
        """
        # Check if train and test equity curves are available
        train_results = results.get('train_results', {})
        test_results = results.get('test_results', {})
        
        if not train_results or not test_results:
            return
            
        train_equity = train_results.get('equity_curve', [])
        test_equity = test_results.get('equity_curve', [])
        
        if not train_equity or not test_equity:
            return
            
        # Extract equity values
        train_dates = [entry.get('timestamp') for entry in train_equity]
        train_values = [entry.get('equity') for entry in train_equity]
        
        test_dates = [entry.get('timestamp') for entry in test_equity]
        test_values = [entry.get('equity') for entry in test_equity]
        
        # Create plot
        plt.figure(figsize=(12, 6))
        
        plt.plot(train_dates, train_values, label='Training', color='blue')
        plt.plot(test_dates, test_values, label='Testing', color='green')
        
        plt.xlabel('Date')
        plt.ylabel('Equity')
        plt.title('Equity Curve Comparison: Training vs Testing')
        plt.legend()
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(filepath)
        plt.close()
        
    def _generate_parameter_importance(self, results, filepath):
        """
        Generate parameter importance visualization.
        
        Args:
            results (dict): Optimization results
            filepath (str): Path to save the visualization
        """
        parameter_importance = results.get('parameter_importance', {})
        if not parameter_importance:
            return
            
        # Sort by importance
        sorted_params = sorted(parameter_importance.items(), key=lambda x: x[1], reverse=True)
        
        param_names = [p[0] for p in sorted_params]
        importance_values = [p[1] for p in sorted_params]
        
        # Create plot
        plt.figure(figsize=(10, 6))
        
        plt.barh(param_names, importance_values, color='skyblue')
        
        plt.xlabel('Importance')
        plt.ylabel('Parameter')
        plt.title('Parameter Importance Analysis')
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(filepath)
        plt.close()
        
    def _generate_overfitting_analysis(self, results, filepath):
        """
        Generate overfitting analysis visualization.
        
        Args:
            results (dict): Optimization results
            filepath (str): Path to save the visualization
        """
        # Check if train and test results are available
        train_results = results.get('train_results', {})
        test_results = results.get('test_results', {})
        
        if not train_results or not test_results:
            return
            
        # Extract metrics for comparison
        metrics = [
            ('Return (%)', 'return_pct'),
            ('Sharpe Ratio', 'sharpe_ratio'),
            ('Profit Factor', 'profit_factor'),
            ('Win Rate', 'win_rate')
        ]
        
        metric_names = [m[0] for m in metrics]
        train_values = []
        test_values = []
        
        for _, key in metrics:
            train_values.append(train_results.get('statistics', {}).get(key, 0))
            test_values.append(test_results.get('statistics', {}).get(key, 0))
            
        # Create plot
        plt.figure(figsize=(10, 6))
        
        x = range(len(metric_names))
        width = 0.35
        
        plt.bar([i - width/2 for i in x], train_values, width, label='Training', color='blue')
        plt.bar([i + width/2 for i in x], test_values, width, label='Testing', color='green')
        
        plt.xlabel('Metric')
        plt.ylabel('Value')
        plt.title('Training vs Testing Performance Comparison')
        plt.xticks(x, metric_names)
        plt.legend()
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(filepath)
        plt.close()
        
    def print_summary(self, results):
        """
        Print a summary of the optimization results to the console.

        Args:
            results (dict): Optimization results
        """
        # Check if results is None
        if results is None:
            print("Cannot generate summary: results is None")
            return

        # Get strategy name and timestamp
        strategy_name = self.config['strategy']['name']
        timestamp = results.get('timestamp', 'Not available')

        # Print header
        print('=' * 80)
        print(f"OPTIMIZATION SUMMARY: {strategy_name}")
        print(f"Timestamp: {timestamp}")
        print('=' * 80)

        # Print best parameters
        best_parameters = results.get('best_parameters', {})
        print("\nBEST PARAMETERS:")
        print('-' * 40)

        if best_parameters is None:
            print("No valid parameters found. Optimization may have failed to produce results.")
        elif not best_parameters:
            print("No parameters found. Optimization completed but did not find a viable solution.")
        else:
            for param_name, param_value in best_parameters.items():
                print(f"{param_name}: {param_value}")

        # Print performance metrics
        print("\nPERFORMANCE METRICS:")
        print('-' * 40)

        # Add training metrics if available
        train_results = results.get('train_results', {})
        test_results = results.get('test_results', {})

        # CRITICAL FIX: Check for identical train/test statistics
        train_stats = train_results.get('statistics', {}) if train_results else {}
        test_stats = test_results.get('statistics', {}) if test_results else {}

        if train_stats and test_stats and train_stats == test_stats:
            print("\n*** WARNING: TRAIN AND TEST STATISTICS ARE IDENTICAL! ***")
            print("*** This indicates a problem with train/test split isolation! ***")
            print("*** Optimization results may not be reliable! ***\n")

        if train_results:
            print('Training Performance:')

            print(f"  Total Return: {train_stats.get('return_pct', 0):.2f}%")
            print(f"  Sharpe Ratio: {train_stats.get('sharpe_ratio', 0):.2f}")
            print(f"  Profit Factor: {train_stats.get('profit_factor', 0):.2f}")
            print(f"  Max Drawdown: {train_stats.get('max_drawdown', 0):.2f}%")
            print(f"  Trades: {train_stats.get('trades_executed', 0)}")
            print()

        # Add testing metrics if available
        if test_results:
            print('Testing Performance:')

            print(f"  Total Return: {test_stats.get('return_pct', 0):.2f}%")
            print(f"  Sharpe Ratio: {test_stats.get('sharpe_ratio', 0):.2f}")
            print(f"  Profit Factor: {test_stats.get('profit_factor', 0):.2f}")
            print(f"  Max Drawdown: {test_stats.get('max_drawdown', 0):.2f}%")
            print(f"  Trades: {test_stats.get('trades_executed', 0)}")
            print()

        # If train and test results are available, show comparison
        if train_stats and test_stats and train_stats != test_stats:
            print('Performance Comparison (Train vs Test):')
            print(f"  Return: {train_stats.get('return_pct', 0):.2f}% vs {test_stats.get('return_pct', 0):.2f}%")
            print(f"  Sharpe: {train_stats.get('sharpe_ratio', 0):.2f} vs {test_stats.get('sharpe_ratio', 0):.2f}")
            print(f"  Profit Factor: {train_stats.get('profit_factor', 0):.2f} vs {test_stats.get('profit_factor', 0):.2f}")
            print(f"  Trades: {train_stats.get('trades_executed', 0)} vs {test_stats.get('trades_executed', 0)}")
            print()

        # Print report location
        print(f"\nDetailed reports saved to: {self.output_dir}")
        print('=' * 80)
