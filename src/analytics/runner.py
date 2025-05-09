"""
Analytics module runner.

This module provides a function to run analytics on backtest results,
independent of the main application flow.
"""

import os
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from .analysis.performance import PerformanceAnalyzer
from .reporting.text_report import TextReportBuilder
from .reporting.html_report import HTMLReportBuilder

logger = logging.getLogger(__name__)


def run_analytics(config: Dict[str, Any], 
                 equity_file: Optional[str] = None,
                 trades_file: Optional[str] = None,
                 output_dir: Optional[str] = None) -> Tuple[bool, str]:
    """
    Run analytics on trading results.
    
    Args:
        config: Configuration dictionary
        equity_file: Path to equity curve CSV file (overrides config)
        trades_file: Path to trades CSV file (overrides config)
        output_dir: Output directory for reports (overrides config)
        
    Returns:
        Tuple[bool, str]: Success flag and message
    """
    try:
        # Get analytics configuration
        analytics_config = config.get('analytics', {})
        
        # Check for required files
        equity_file = equity_file or analytics_config.get('data', {}).get('equity_curve')
        trades_file = trades_file or analytics_config.get('data', {}).get('trades')
        
        if not equity_file:
            return False, "No equity curve file specified"
        
        if not os.path.exists(equity_file):
            return False, f"Equity curve file not found: {equity_file}"
        
        # Determine output directory
        output_dir = output_dir or analytics_config.get('reporting', {}).get('output_directory', './results/analytics')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Load equity curve
        logger.info(f"Loading equity curve from {equity_file}")
        equity_curve = pd.read_csv(equity_file)
        
        # Try to convert date column to datetime and set as index
        date_columns = ['date', 'timestamp', 'time', 'datetime']
        for col in date_columns:
            if col in equity_curve.columns:
                equity_curve[col] = pd.to_datetime(equity_curve[col])
                equity_curve.set_index(col, inplace=True)
                break
        
        # Load trades if available
        trades = []
        if trades_file and os.path.exists(trades_file):
            logger.info(f"Loading trades from {trades_file}")
            trades_df = pd.read_csv(trades_file)
            
            # Convert trades DataFrame to list of dictionaries
            for _, row in trades_df.iterrows():
                trade = row.to_dict()
                
                # Convert date fields to datetime
                date_fields = ['entry_time', 'exit_time', 'entry_date', 'exit_date']
                for field in date_fields:
                    if field in trade and trade[field]:
                        try:
                            trade[field] = pd.to_datetime(trade[field])
                        except:
                            pass
                
                trades.append(trade)
        
        # Create analyzer
        analyzer = PerformanceAnalyzer(
            equity_curve=equity_curve,
            trades=trades
        )
        
        # Run analysis
        analysis_config = analytics_config.get('analysis', {})
        risk_free_rate = analysis_config.get('risk_free_rate', 0.0)
        periods_per_year = analysis_config.get('periods_per_year', 252)
        
        logger.info("Running performance analysis...")
        metrics = analyzer.analyze_performance(
            risk_free_rate=risk_free_rate,
            periods_per_year=periods_per_year
        )
        
        # Log summary metrics
        logger.info(f"Total Return: {metrics.get('total_return', 0.0):.2%}")
        logger.info(f"Annualized Return: {metrics.get('annualized_return', 0.0):.2%}")
        logger.info(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0.0):.2f}")
        logger.info(f"Max Drawdown: {metrics.get('max_drawdown', 0.0):.2%}")
        
        if 'trade_metrics' in metrics:
            trade_metrics = metrics['trade_metrics']
            logger.info(f"Win Rate: {trade_metrics.get('win_rate', 0.0):.2%}")
            logger.info(f"Profit Factor: {trade_metrics.get('profit_factor', 0.0):.2f}")
        
        # Generate reports
        reporting_config = analytics_config.get('reporting', {})
        if reporting_config.get('enabled', True):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Get report formats
            formats = reporting_config.get('formats', ['text'])
            report_files = {}
            
            # Generate text report
            if 'text' in formats:
                text_config = reporting_config.get('text', {})
                width = text_config.get('width', 80)
                
                logger.info("Generating text report...")
                text_builder = TextReportBuilder(
                    analyzer=analyzer,
                    title=config.get('name', 'Analytics') + " - Performance Report",
                    width=width
                )
                
                text_file = os.path.join(output_dir, f"analytics_report_{timestamp}.txt")
                text_builder.save(text_file)
                report_files['text'] = text_file
                logger.info(f"Text report saved to: {text_file}")
            
            # Generate HTML report
            if 'html' in formats:
                html_config = reporting_config.get('html', {})
                
                logger.info("Generating HTML report...")
                html_builder = HTMLReportBuilder(
                    analyzer=analyzer,
                    title=html_config.get('title', config.get('name', 'Analytics') + " - Performance Report"),
                    description=html_config.get('description', "")
                )
                
                html_file = os.path.join(output_dir, f"analytics_report_{timestamp}.html")
                html_builder.save(html_file)
                report_files['html'] = html_file
                logger.info(f"HTML report saved to: {html_file}")
        
            # Build success message
            report_list = "\n".join([f"  - {f_type.upper()}: {f_path}" for f_type, f_path in report_files.items()])
            return True, f"Analytics completed successfully. Reports generated:\n{report_list}"
        
        return True, "Analytics completed successfully (no reports generated)"
        
    except Exception as e:
        logger.error(f"Error running analytics: {e}", exc_info=True)
        return False, f"Error running analytics: {str(e)}"