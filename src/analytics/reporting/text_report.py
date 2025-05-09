"""
Text-based report generator for performance analysis.

This module provides a text report builder that formats performance analysis
results into a human-readable text format.
"""

from typing import Dict, List, Any, Optional, Union
import os
import textwrap
from datetime import datetime
import pandas as pd
import numpy as np

from ..analysis.performance import PerformanceAnalyzer
from .report_builder import ReportBuilder


class TextReportBuilder(ReportBuilder):
    """
    Generates text-based performance reports.
    
    This class extends the ReportBuilder base class to provide
    text formatting of performance analysis results.
    """
    
    def __init__(self, 
               analyzer: Optional[PerformanceAnalyzer] = None,
               title: str = "Performance Report",
               description: str = "",
               metadata: Optional[Dict[str, Any]] = None,
               width: int = 80):
        """
        Initialize the text report builder.
        
        Args:
            analyzer: PerformanceAnalyzer instance with results
            title: Report title
            description: Report description
            metadata: Additional metadata for the report
            width: Width of the text report in characters
        """
        super().__init__(analyzer, title, description, metadata)
        self.width = width
    
    def _format_header(self, text: str, char: str = '=') -> str:
        """Format a section header."""
        return f"\n{text}\n{char * len(text)}\n"
    
    def _format_subheader(self, text: str, char: str = '-') -> str:
        """Format a section subheader."""
        return f"\n{text}\n{char * len(text)}\n"
    
    def _format_value(self, value: Any) -> str:
        """Format a value for text display."""
        if isinstance(value, float):
            if abs(value) < 0.0001 and value != 0:
                return f"{value:.6e}"
            return f"{value:.4f}"
        if isinstance(value, (int, bool)):
            return str(value)
        if isinstance(value, (list, dict)):
            return str(value)
        return str(value)
    
    def _format_percentage(self, value: float) -> str:
        """Format a value as a percentage."""
        return f"{value * 100:.2f}%"
    
    def _format_key_value(self, key: str, value: Any, width: int = 25) -> str:
        """Format a key-value pair."""
        formatted_key = key.replace('_', ' ').title()
        formatted_value = self._format_value(value)
        
        # Add percentage for certain metrics
        if key in ['total_return', 'annualized_return', 'cagr', 'win_rate', 'max_drawdown', 
                  'volatility', 'avg_win_rate', 'avg_loss_rate']:
            if isinstance(value, (int, float)):
                formatted_value = self._format_percentage(value)
        
        return f"{formatted_key + ':':.<{width}} {formatted_value}"
    
    def _format_dict(self, data: Dict[str, Any], indent: int = 0) -> str:
        """Format a dictionary as text with indentation."""
        lines = []
        prefix = ' ' * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key.replace('_', ' ').title()}:")
                lines.append(self._format_dict(value, indent + 2))
            else:
                lines.append(f"{prefix}{self._format_key_value(key, value)}")
        
        return '\n'.join(lines)
    
    def render_summary_section(self, data: Dict[str, Any]) -> str:
        """
        Render the summary section of the report.
        
        Args:
            data: Report data
            
        Returns:
            str: Rendered summary section
        """
        if 'sections' not in data or 'summary' not in data['sections']:
            return "No summary data available."
        
        summary_data = data['sections']['summary']['data']
        if not summary_data:
            return "No summary data available."
        
        output = []
        output.append(self._format_header("Performance Summary"))
        
        # Strategy period info
        if 'metadata' in data and 'start_date' in data['metadata'] and 'end_date' in data['metadata']:
            period = (f"Period: {data['metadata']['start_date']} to {data['metadata']['end_date']} "
                     f"({data['metadata'].get('days', 0)} days)")
            output.append(period)
            output.append("")
        
        # Key metrics
        for key in ['total_return', 'annualized_return', 'max_drawdown', 
                   'sharpe_ratio', 'volatility', 'win_rate', 'profit_factor']:
            if key in summary_data:
                output.append(self._format_key_value(key, summary_data[key]))
        
        return '\n'.join(output)
    
    def render_returns_section(self, data: Dict[str, Any]) -> str:
        """
        Render the returns section of the report.
        
        Args:
            data: Report data
            
        Returns:
            str: Rendered returns section
        """
        if 'sections' not in data or 'returns' not in data['sections']:
            return "No returns data available."
        
        returns_data = data['sections']['returns']['data']
        if not returns_data:
            return "No returns data available."
        
        output = []
        output.append(self._format_header("Return Metrics"))
        
        # Group metrics
        return_metrics = {k: v for k, v in returns_data.items() 
                         if k in ['total_return', 'annualized_return', 'cagr']}
        
        risk_metrics = {k: v for k, v in returns_data.items() 
                       if k in ['volatility', 'max_drawdown', 'avg_drawdown', 'avg_drawdown_days']}
        
        ratio_metrics = {k: v for k, v in returns_data.items() 
                        if 'ratio' in k or k in ['alpha', 'beta']}
        
        # Add each group
        if return_metrics:
            output.append(self._format_subheader("Returns", "-"))
            for key, value in return_metrics.items():
                output.append(self._format_key_value(key, value))
            output.append("")
        
        if risk_metrics:
            output.append(self._format_subheader("Risk", "-"))
            for key, value in risk_metrics.items():
                output.append(self._format_key_value(key, value))
            output.append("")
        
        if ratio_metrics:
            output.append(self._format_subheader("Risk-Adjusted Metrics", "-"))
            for key, value in ratio_metrics.items():
                output.append(self._format_key_value(key, value))
        
        # Add other metrics that don't fit in the above categories
        other_metrics = {k: v for k, v in returns_data.items() 
                        if k not in return_metrics and k not in risk_metrics and k not in ratio_metrics}
        
        if other_metrics:
            output.append(self._format_subheader("Other Metrics", "-"))
            for key, value in other_metrics.items():
                output.append(self._format_key_value(key, value))
        
        return '\n'.join(output)
    
    def render_trades_section(self, data: Dict[str, Any]) -> str:
        """
        Render the trades section of the report.
        
        Args:
            data: Report data
            
        Returns:
            str: Rendered trades section
        """
        if 'sections' not in data or 'trades' not in data['sections']:
            return "No trade data available."
        
        trades_data = data['sections']['trades']['data']
        if not trades_data:
            return "No trade data available."
        
        output = []
        output.append(self._format_header("Trade Performance"))
        
        # Basic trade stats
        basic_stats = {k: v for k, v in trades_data.items() 
                      if k in ['num_trades', 'num_wins', 'num_losses', 
                              'win_rate', 'profit_factor', 'expectancy']}
        
        if basic_stats:
            output.append(self._format_subheader("Overall Statistics", "-"))
            for key, value in basic_stats.items():
                output.append(self._format_key_value(key, value))
            output.append("")
        
        # PnL stats
        pnl_stats = {k: v for k, v in trades_data.items() 
                    if k in ['total_pnl', 'avg_pnl', 'avg_win', 'avg_loss', 
                            'max_win', 'max_loss', 'avg_win_loss_ratio']}
        
        if pnl_stats:
            output.append(self._format_subheader("Profit/Loss Statistics", "-"))
            for key, value in pnl_stats.items():
                output.append(self._format_key_value(key, value))
            output.append("")
        
        # Consecutive stats
        if 'consecutive_stats' in trades_data and trades_data['consecutive_stats']:
            output.append(self._format_subheader("Streak Analysis", "-"))
            for key, value in trades_data['consecutive_stats'].items():
                output.append(self._format_key_value(key, value))
            output.append("")
        
        # Duration stats
        duration_stats = {k: v for k, v in trades_data.items() 
                         if k in ['avg_holding_period', 'avg_win_holding_period', 
                                 'avg_loss_holding_period']}
        
        if duration_stats:
            output.append(self._format_subheader("Trade Duration", "-"))
            for key, value in duration_stats.items():
                output.append(self._format_key_value(key, value))
        
        return '\n'.join(output)
    
    def render_section(self, section_id: str, data: Dict[str, Any]) -> str:
        """
        Render a specific section of the report.
        
        Args:
            section_id: Section identifier
            data: Report data
            
        Returns:
            str: Rendered section
        """
        if 'sections' not in data or section_id not in data['sections']:
            return f"No data available for section: {section_id}"
        
        section_data = data['sections'][section_id]
        section_title = section_data.get('title', section_id.replace('_', ' ').title())
        
        output = []
        output.append(self._format_header(section_title))
        
        # Format section data
        if 'data' in section_data and section_data['data']:
            content = section_data['data']
            if isinstance(content, dict):
                for key, value in content.items():
                    if isinstance(value, dict):
                        output.append(self._format_subheader(key.replace('_', ' ').title(), "-"))
                        output.append(self._format_dict(value))
                        output.append("")
                    else:
                        output.append(self._format_key_value(key, value))
            elif isinstance(content, str):
                output.append(content)
        
        return '\n'.join(output)
    
    def render(self) -> str:
        """
        Render the complete text report.
        
        Returns:
            str: Complete text report
        """
        data = self.prepare_report_data()
        if not data:
            return "No data available for report."
        
        output = []
        
        # Report header
        title_line = f"{data['title']}".center(self.width)
        output.append("=" * self.width)
        output.append(title_line)
        output.append("=" * self.width)
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output.append(f"Generated: {timestamp}".center(self.width))
        output.append("")
        
        # Description
        if data['description']:
            output.append(textwrap.fill(data['description'], width=self.width))
            output.append("")
        
        # Standard sections
        if 'summary' in data['sections']:
            output.append(self.render_summary_section(data))
        
        if 'returns' in data['sections']:
            output.append(self.render_returns_section(data))
        
        if 'trades' in data['sections']:
            output.append(self.render_trades_section(data))
        
        # Custom sections (excluding standard ones)
        for section_id in data['sections']:
            if section_id not in ['summary', 'returns', 'trades']:
                output.append(self.render_section(section_id, data))
        
        return '\n'.join(output)
    
    def save(self, filepath: str) -> None:
        """
        Save the rendered report to a text file.
        
        Args:
            filepath: Path to save the report
        """
        report_text = self.render()
        
        try:
            # Ensure directory exists
            directory = os.path.dirname(filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(filepath, 'w') as f:
                f.write(report_text)
        except Exception as e:
            raise IOError(f"Failed to save report to {filepath}: {e}")