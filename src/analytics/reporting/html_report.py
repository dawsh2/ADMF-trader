"""
HTML-based report generator for performance analysis.

This module provides an HTML report builder that formats performance analysis
results into a rich, interactive HTML format with charts and tables.
"""

from typing import Dict, List, Any, Optional, Union
import os
import json
from datetime import datetime
import pandas as pd
import numpy as np
from jinja2 import Template
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import base64
from io import BytesIO

from ..analysis.performance import PerformanceAnalyzer
from .report_builder import ReportBuilder


class HTMLReportBuilder(ReportBuilder):
    """
    Generates HTML-based performance reports with charts.
    
    This class extends the ReportBuilder base class to provide
    HTML formatting of performance analysis results with interactive
    charts and tables.
    """
    
    def __init__(self, 
               analyzer: Optional[PerformanceAnalyzer] = None,
               title: str = "Performance Report",
               description: str = "",
               metadata: Optional[Dict[str, Any]] = None,
               template_path: Optional[str] = None):
        """
        Initialize the HTML report builder.
        
        Args:
            analyzer: PerformanceAnalyzer instance with results
            title: Report title
            description: Report description
            metadata: Additional metadata for the report
            template_path: Optional custom HTML template path
        """
        super().__init__(analyzer, title, description, metadata)
        self.template_path = template_path
        self.charts = {}
        
    def _format_percentage(self, value: float) -> str:
        """Format a value as a percentage."""
        if isinstance(value, (int, float)):
            return f"{value * 100:.2f}%"
        return str(value)
    
    def _prepare_chart_equity_curve(self) -> str:
        """Prepare equity curve chart and return base64 encoded image."""
        if not hasattr(self.analyzer, 'equity_curve') or self.analyzer.equity_curve is None:
            return ""
            
        if self.analyzer.equity_curve.empty or 'equity' not in self.analyzer.equity_curve.columns:
            return ""
        
        try:
            plt.figure(figsize=(10, 6))
            ax = plt.gca()
            
            # Plot equity curve
            self.analyzer.equity_curve['equity'].plot(
                ax=ax, 
                color='#1f77b4', 
                linewidth=2, 
                label='Equity'
            )
            
            # Calculate drawdowns
            if hasattr(self.analyzer, 'metrics') and 'drawdowns' in self.analyzer.metrics:
                drawdowns = pd.Series(
                    self.analyzer.metrics['drawdowns'], 
                    index=self.analyzer.equity_curve.index
                )
                
                # Plot drawdowns on secondary axis
                ax2 = ax.twinx()
                drawdowns.plot(
                    ax=ax2, 
                    color='#d62728', 
                    alpha=0.3, 
                    label='Drawdown'
                )
                ax2.set_ylabel('Drawdown', color='#d62728')
                ax2.tick_params(axis='y', colors='#d62728')
                ax2.fill_between(
                    drawdowns.index, 
                    0, 
                    drawdowns.values, 
                    color='#d62728', 
                    alpha=0.1
                )
                
                # Set y-limits for drawdown to be positive
                ax2.set_ylim(max(0, drawdowns.min() * 1.2), 0)
            
            # Add grid
            ax.grid(True, alpha=0.3)
            
            # Format axes
            ax.set_xlabel('Date')
            ax.set_ylabel('Equity ($)')
            ax.set_title('Equity Curve and Drawdowns')
            
            # Add legend
            lines, labels = ax.get_legend_handles_labels()
            if hasattr(ax, 'right_ax'):
                lines2, labels2 = ax.right_ax.get_legend_handles_labels()
                lines += lines2
                labels += labels2
            ax.legend(lines, labels, loc='best')
            
            # Save to bytesIO
            buffer = BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            
            # Encode to base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
            
            return image_base64
            
        except Exception as e:
            import logging
            logging.error(f"Error creating equity curve chart: {str(e)}")
            plt.close()
            return ""
    
    def _prepare_chart_returns_distribution(self) -> str:
        """Prepare returns distribution chart and return base64 encoded image."""
        if not hasattr(self.analyzer, 'return_series') or self.analyzer.return_series is None:
            return ""
            
        if self.analyzer.return_series.empty:
            return ""
        
        try:
            plt.figure(figsize=(10, 6))
            
            # Plot return distribution
            self.analyzer.return_series.hist(
                bins=50, 
                alpha=0.6, 
                color='#1f77b4'
            )
            
            # Add normal distribution curve
            mean = self.analyzer.return_series.mean()
            std = self.analyzer.return_series.std()
            
            x = np.linspace(mean - 3*std, mean + 3*std, 100)
            y = np.exp(-(x - mean)**2 / (2 * std**2)) / (std * np.sqrt(2 * np.pi))
            y = y * len(self.analyzer.return_series) * (self.analyzer.return_series.max() - self.analyzer.return_series.min()) / 50
            
            plt.plot(x, y, 'r--', linewidth=2)
            
            # Add mean and zero lines
            plt.axvline(mean, color='#ff7f0e', linestyle='--', linewidth=2, label=f'Mean: {mean:.6f}')
            plt.axvline(0, color='black', linestyle='-', linewidth=1, label='Zero')
            
            # Format chart
            plt.grid(True, alpha=0.3)
            plt.title('Returns Distribution')
            plt.xlabel('Return')
            plt.ylabel('Frequency')
            plt.legend()
            
            # Save to bytesIO
            buffer = BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            
            # Encode to base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
            
            return image_base64
            
        except Exception as e:
            import logging
            logging.error(f"Error creating returns distribution chart: {str(e)}")
            plt.close()
            return ""
    
    def _prepare_chart_monthly_returns(self) -> str:
        """Prepare monthly returns heatmap chart and return base64 encoded image."""
        if not hasattr(self.analyzer, 'equity_curve') or self.analyzer.equity_curve is None:
            return ""
            
        if self.analyzer.equity_curve.empty:
            return ""
        
        try:
            # Resample equity curve to get monthly returns
            monthly_returns = self.analyzer.equity_curve['equity'].resample('M').last().pct_change().dropna()
            
            # Create a pivot table with years as rows and months as columns
            returns_pivot = pd.DataFrame({
                'Year': monthly_returns.index.year,
                'Month': monthly_returns.index.month,
                'Return': monthly_returns.values
            })
            returns_pivot = returns_pivot.pivot(index='Year', columns='Month', values='Return')
            
            # Plot as a heatmap
            plt.figure(figsize=(12, len(returns_pivot) * 0.5 + 2))
            
            cmap = plt.cm.RdYlGn  # Red for negative, yellow for neutral, green for positive
            
            # Create heatmap
            plt.pcolormesh(
                returns_pivot.columns, 
                returns_pivot.index, 
                returns_pivot.values, 
                cmap=cmap,
                vmin=-0.1,  # Set min/max to have consistent colors
                vmax=0.1
            )
            
            # Add color bar
            cbar = plt.colorbar(label='Return')
            cbar.set_label('Monthly Return')
            
            # Add text annotations with return values
            for i in range(len(returns_pivot.index)):
                for j in range(len(returns_pivot.columns)):
                    if not np.isnan(returns_pivot.iloc[i, j]):
                        return_value = returns_pivot.iloc[i, j]
                        color = 'white' if abs(return_value) > 0.05 else 'black'
                        plt.text(
                            j + 0.5, 
                            i + 0.5, 
                            f'{return_value:.2%}', 
                            ha='center', 
                            va='center',
                            color=color
                        )
            
            # Format chart
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            plt.xticks(np.arange(1, 13) + 0.5, month_names)
            plt.yticks(np.arange(len(returns_pivot.index)) + 0.5, returns_pivot.index)
            
            plt.title('Monthly Returns Heatmap')
            plt.grid(False)
            
            # Save to bytesIO
            buffer = BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            
            # Encode to base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
            
            return image_base64
            
        except Exception as e:
            import logging
            logging.error(f"Error creating monthly returns chart: {str(e)}")
            plt.close()
            return ""
    
    def _prepare_chart_trade_pnl(self) -> str:
        """Prepare trade P&L distribution chart and return base64 encoded image."""
        if not hasattr(self.analyzer, 'trades') or not self.analyzer.trades:
            return ""
        
        try:
            # Extract trade P&Ls
            pnls = [trade.get('pnl', 0) for trade in self.analyzer.trades if 'pnl' in trade]
            
            if not pnls:
                return ""
            
            plt.figure(figsize=(10, 6))
            
            # Plot P&L distribution
            plt.hist(
                pnls, 
                bins=min(50, len(pnls) // 2 + 1), 
                alpha=0.6, 
                color='#1f77b4'
            )
            
            # Add mean line
            mean_pnl = np.mean(pnls)
            plt.axvline(mean_pnl, color='#ff7f0e', linestyle='--', linewidth=2, label=f'Mean: {mean_pnl:.2f}')
            
            # Add zero line
            plt.axvline(0, color='black', linestyle='-', linewidth=1, label='Zero')
            
            # Format chart
            plt.grid(True, alpha=0.3)
            plt.title('Trade P&L Distribution')
            plt.xlabel('P&L')
            plt.ylabel('Frequency')
            plt.legend()
            
            # Save to bytesIO
            buffer = BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            
            # Encode to base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
            
            return image_base64
            
        except Exception as e:
            import logging
            logging.error(f"Error creating trade P&L chart: {str(e)}")
            plt.close()
            return ""
    
    def prepare_charts(self) -> Dict[str, str]:
        """Prepare all charts and return as dict of base64 encoded images."""
        self.charts = {}
        
        # Add equity curve chart
        equity_curve_chart = self._prepare_chart_equity_curve()
        if equity_curve_chart:
            self.charts['equity_curve'] = equity_curve_chart
        
        # Add returns distribution chart
        returns_dist_chart = self._prepare_chart_returns_distribution()
        if returns_dist_chart:
            self.charts['returns_distribution'] = returns_dist_chart
        
        # Add monthly returns chart
        monthly_returns_chart = self._prepare_chart_monthly_returns()
        if monthly_returns_chart:
            self.charts['monthly_returns'] = monthly_returns_chart
        
        # Add trade P&L chart
        trade_pnl_chart = self._prepare_chart_trade_pnl()
        if trade_pnl_chart:
            self.charts['trade_pnl'] = trade_pnl_chart
        
        return self.charts
    
    def _default_template(self) -> str:
        """Return the default HTML template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #2980b9;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }
        h3 {
            color: #3498db;
        }
        .header-info {
            text-align: center;
            margin-bottom: 30px;
            color: #7f8c8d;
        }
        .section {
            margin-bottom: 40px;
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .metric-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        .metric-table th {
            text-align: left;
            padding: 10px;
            background-color: #2980b9;
            color: white;
        }
        .metric-table td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        .metric-table tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .metric-table tr:hover {
            background-color: #e0f7fa;
        }
        .chart-container {
            margin: 20px 0;
            text-align: center;
        }
        .chart {
            max-width: 100%;
            height: auto;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            border-radius: 5px;
        }
        .positive {
            color: green;
        }
        .negative {
            color: red;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            color: #7f8c8d;
            font-size: 0.9em;
        }
        .summary-box {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .summary-item {
            flex-basis: 30%;
            background-color: #fff;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 15px;
        }
        .summary-item h4 {
            margin-top: 0;
            color: #7f8c8d;
            font-size: 0.9em;
            text-transform: uppercase;
        }
        .summary-item p {
            margin-bottom: 0;
            font-size: 1.4em;
            font-weight: bold;
        }
        @media (max-width: 768px) {
            .summary-item {
                flex-basis: 48%;
            }
        }
        @media (max-width: 480px) {
            .summary-item {
                flex-basis: 100%;
            }
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    
    <div class="header-info">
        <p>Generated: {{ timestamp }}</p>
        {% if metadata.start_date and metadata.end_date %}
        <p>Period: {{ metadata.start_date }} to {{ metadata.end_date }} ({{ metadata.days }} days)</p>
        {% endif %}
        {% if description %}
        <p>{{ description }}</p>
        {% endif %}
    </div>
    
    <!-- Performance Summary Section -->
    <div class="section">
        <h2>Performance Summary</h2>
        
        <div class="summary-box">
            {% if sections.summary.data.total_return is defined %}
            <div class="summary-item">
                <h4>Total Return</h4>
                <p class="{% if sections.summary.data.total_return > 0 %}positive{% else %}negative{% endif %}">
                    {{ (sections.summary.data.total_return * 100)|round(2) }}%
                </p>
            </div>
            {% endif %}
            
            {% if sections.summary.data.annualized_return is defined %}
            <div class="summary-item">
                <h4>Annualized Return</h4>
                <p class="{% if sections.summary.data.annualized_return > 0 %}positive{% else %}negative{% endif %}">
                    {{ (sections.summary.data.annualized_return * 100)|round(2) }}%
                </p>
            </div>
            {% endif %}
            
            {% if sections.summary.data.sharpe_ratio is defined %}
            <div class="summary-item">
                <h4>Sharpe Ratio</h4>
                <p class="{% if sections.summary.data.sharpe_ratio > 1 %}positive{% else %}negative{% endif %}">
                    {{ sections.summary.data.sharpe_ratio|round(2) }}
                </p>
            </div>
            {% endif %}
            
            {% if sections.summary.data.max_drawdown is defined %}
            <div class="summary-item">
                <h4>Max Drawdown</h4>
                <p class="negative">
                    {{ (sections.summary.data.max_drawdown * 100)|round(2) }}%
                </p>
            </div>
            {% endif %}
            
            {% if sections.summary.data.win_rate is defined %}
            <div class="summary-item">
                <h4>Win Rate</h4>
                <p>
                    {{ (sections.summary.data.win_rate * 100)|round(2) }}%
                </p>
            </div>
            {% endif %}
            
            {% if sections.summary.data.profit_factor is defined %}
            <div class="summary-item">
                <h4>Profit Factor</h4>
                <p class="{% if sections.summary.data.profit_factor > 1 %}positive{% else %}negative{% endif %}">
                    {{ sections.summary.data.profit_factor|round(2) }}
                </p>
            </div>
            {% endif %}
        </div>
        
        {% if charts.equity_curve %}
        <div class="chart-container">
            <h3>Equity Curve</h3>
            <img class="chart" src="data:image/png;base64,{{ charts.equity_curve }}" alt="Equity Curve">
        </div>
        {% endif %}
    </div>
    
    <!-- Return Metrics Section -->
    {% if sections.returns %}
    <div class="section">
        <h2>Return Metrics</h2>
        
        <table class="metric-table">
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            {% for key, value in sections.returns.data.items() %}
            {% if value is number and key not in ['drawdowns'] %}
            <tr>
                <td>{{ key|replace('_', ' ')|title }}</td>
                <td>
                    {% if key in ['total_return', 'annualized_return', 'cagr', 'win_rate', 'max_drawdown', 'volatility'] %}
                    {{ (value * 100)|round(2) }}%
                    {% else %}
                    {{ value|round(4) }}
                    {% endif %}
                </td>
            </tr>
            {% endif %}
            {% endfor %}
        </table>
        
        {% if charts.returns_distribution %}
        <div class="chart-container">
            <h3>Returns Distribution</h3>
            <img class="chart" src="data:image/png;base64,{{ charts.returns_distribution }}" alt="Returns Distribution">
        </div>
        {% endif %}
        
        {% if charts.monthly_returns %}
        <div class="chart-container">
            <h3>Monthly Returns</h3>
            <img class="chart" src="data:image/png;base64,{{ charts.monthly_returns }}" alt="Monthly Returns">
        </div>
        {% endif %}
    </div>
    {% endif %}
    
    <!-- Trade Metrics Section -->
    {% if sections.trades %}
    <div class="section">
        <h2>Trade Performance</h2>
        
        <h3>Trade Statistics</h3>
        <table class="metric-table">
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            {% for key, value in sections.trades.data.items() %}
            {% if value is not mapping and key not in ['consecutive_stats', 'time_analysis', 'pnl_distribution'] %}
            <tr>
                <td>{{ key|replace('_', ' ')|title }}</td>
                <td>
                    {% if key in ['win_rate'] %}
                    {{ (value * 100)|round(2) }}%
                    {% elif value is number %}
                    {{ value|round(4) }}
                    {% else %}
                    {{ value }}
                    {% endif %}
                </td>
            </tr>
            {% endif %}
            {% endfor %}
        </table>
        
        {% if sections.trades.data.consecutive_stats %}
        <h3>Streak Analysis</h3>
        <table class="metric-table">
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            {% for key, value in sections.trades.data.consecutive_stats.items() %}
            <tr>
                <td>{{ key|replace('_', ' ')|title }}</td>
                <td>{{ value }}</td>
            </tr>
            {% endfor %}
        </table>
        {% endif %}
        
        {% if charts.trade_pnl %}
        <div class="chart-container">
            <h3>Trade P&L Distribution</h3>
            <img class="chart" src="data:image/png;base64,{{ charts.trade_pnl }}" alt="Trade P&L Distribution">
        </div>
        {% endif %}
    </div>
    {% endif %}
    
    <!-- Custom Sections -->
    {% for section_id, section in sections.items() %}
    {% if section_id not in ['summary', 'returns', 'trades'] %}
    <div class="section">
        <h2>{{ section.title }}</h2>
        
        {% if section.data is mapping %}
        <table class="metric-table">
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            {% for key, value in section.data.items() %}
            {% if value is not mapping %}
            <tr>
                <td>{{ key|replace('_', ' ')|title }}</td>
                <td>
                    {% if value is number %}
                    {{ value|round(4) }}
                    {% else %}
                    {{ value }}
                    {% endif %}
                </td>
            </tr>
            {% endif %}
            {% endfor %}
        </table>
        {% endif %}
    </div>
    {% endif %}
    {% endfor %}
    
    <div class="footer">
        <p>Generated with ADMF-Trader Analytics Engine</p>
    </div>
</body>
</html>"""
    
    def render_summary_section(self, data: Dict[str, Any]) -> str:
        """
        Render the summary section of the HTML report.
        This is not directly used in the HTML report but is implemented
        for consistency with the base class.
        
        Args:
            data: Report data
            
        Returns:
            str: Rendered summary section HTML
        """
        # For HTML reports, rendering happens in the complete template
        return ""
    
    def render_returns_section(self, data: Dict[str, Any]) -> str:
        """
        Render the returns section of the HTML report.
        This is not directly used in the HTML report but is implemented
        for consistency with the base class.
        
        Args:
            data: Report data
            
        Returns:
            str: Rendered returns section HTML
        """
        # For HTML reports, rendering happens in the complete template
        return ""
    
    def render_trades_section(self, data: Dict[str, Any]) -> str:
        """
        Render the trades section of the HTML report.
        This is not directly used in the HTML report but is implemented
        for consistency with the base class.
        
        Args:
            data: Report data
            
        Returns:
            str: Rendered trades section HTML
        """
        # For HTML reports, rendering happens in the complete template
        return ""
    
    def render_section(self, section_id: str, data: Dict[str, Any]) -> str:
        """
        Render a specific section of the HTML report.
        This is not directly used in the HTML report but is implemented
        for consistency with the base class.
        
        Args:
            section_id: Section identifier
            data: Report data
            
        Returns:
            str: Rendered section HTML
        """
        # For HTML reports, rendering happens in the complete template
        return ""
    
    def render(self) -> str:
        """
        Render the complete HTML report.
        
        Returns:
            str: Complete HTML report
        """
        # Prepare data for the report
        data = self.prepare_report_data()
        if not data:
            return "<html><body><h1>No data available for report.</h1></body></html>"
        
        # Prepare charts
        charts = self.prepare_charts()
        
        # Get template
        if self.template_path and os.path.exists(self.template_path):
            with open(self.template_path, 'r') as f:
                template_str = f.read()
        else:
            template_str = self._default_template()
        
        # Create template
        template = Template(template_str)
        
        # Render template with data
        context = {
            **data,
            'charts': charts,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return template.render(**context)
    
    def save(self, filepath: str) -> None:
        """
        Save the rendered HTML report to a file.
        
        Args:
            filepath: Path to save the report
        """
        html_content = self.render()
        
        try:
            # Ensure directory exists
            directory = os.path.dirname(filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            raise IOError(f"Failed to save HTML report to {filepath}: {e}")