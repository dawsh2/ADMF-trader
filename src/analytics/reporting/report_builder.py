"""
Base class for building performance reports.

This module provides a foundation for creating various report formats
from performance analysis results.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
import json
import logging

# Import from analysis module
from ..analysis.performance import PerformanceAnalyzer

logger = logging.getLogger(__name__)


class ReportBuilder:
    """
    Base class for building performance reports.
    
    This class provides common functionality for creating reports from
    performance analysis results. Specific report formats should extend
    this class and implement the render_* methods.
    """
    
    def __init__(self, 
                analyzer: Optional[PerformanceAnalyzer] = None,
                title: str = "Performance Report",
                description: str = "",
                metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize the report builder.
        
        Args:
            analyzer: PerformanceAnalyzer instance with results
            title: Report title
            description: Report description
            metadata: Additional metadata for the report
        """
        self.analyzer = analyzer
        self.title = title
        self.description = description
        self.metadata = metadata or {}
        self.sections = []
        self.content = {}
    
    def set_analyzer(self, analyzer: PerformanceAnalyzer) -> None:
        """
        Set or update the performance analyzer.
        
        Args:
            analyzer: PerformanceAnalyzer instance
        """
        self.analyzer = analyzer
    
    def set_title(self, title: str) -> None:
        """
        Set or update the report title.
        
        Args:
            title: Report title
        """
        self.title = title
    
    def set_description(self, description: str) -> None:
        """
        Set or update the report description.
        
        Args:
            description: Report description
        """
        self.description = description
    
    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the report.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def add_section(self, section_id: str, title: str, order: int = None) -> None:
        """
        Add a report section.
        
        Args:
            section_id: Unique section identifier
            title: Section title
            order: Optional ordering priority (lower values come first)
        """
        section = {
            'id': section_id,
            'title': title,
            'order': order if order is not None else len(self.sections)
        }
        self.sections.append(section)
        
        # Sort sections by order
        self.sections = sorted(self.sections, key=lambda x: x['order'])
    
    def prepare_report_data(self) -> Dict[str, Any]:
        """
        Prepare data for the report from the analyzer.
        
        Returns:
            Dict containing organized report data
        """
        if self.analyzer is None:
            return {}
        
        from datetime import datetime
        
        data = {
            'title': self.title,
            'description': self.description,
            'metadata': self.metadata,
            'timestamp': datetime.now().isoformat(),
            'sections': {}
        }
        
        # Add basic metadata if available and equity curve has data
        if hasattr(self.analyzer, 'equity_curve') and self.analyzer.equity_curve is not None:
            if not self.analyzer.equity_curve.empty and len(self.analyzer.equity_curve.index) > 0:
                try:
                    data['metadata']['start_date'] = self.analyzer.equity_curve.index[0].strftime('%Y-%m-%d')
                    data['metadata']['end_date'] = self.analyzer.equity_curve.index[-1].strftime('%Y-%m-%d')
                    data['metadata']['days'] = (self.analyzer.equity_curve.index[-1] - self.analyzer.equity_curve.index[0]).days
                except (IndexError, AttributeError) as e:
                    # Handle the case of empty equity curve
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Could not extract dates from equity curve: {e}")
                    from datetime import datetime
                    today = datetime.now().strftime('%Y-%m-%d')
                    data['metadata']['start_date'] = today
                    data['metadata']['end_date'] = today
                    data['metadata']['days'] = 0
            else:
                # Empty equity curve
                from datetime import datetime
                today = datetime.now().strftime('%Y-%m-%d')
                data['metadata']['start_date'] = today
                data['metadata']['end_date'] = today
                data['metadata']['days'] = 0
        
        # Get performance metrics
        metrics = self.analyzer.metrics.copy() if hasattr(self.analyzer, 'metrics') else {}
        
        # Organize metrics into sections
        return_metrics = {k: v for k, v in metrics.items() if k not in ['trade_metrics', 'time_analysis', 'pnl_distribution']}
        trade_metrics = metrics.get('trade_metrics', {})
        
        # Populate sections
        data['sections']['summary'] = {
            'title': 'Performance Summary',
            'data': {
                'total_return': metrics.get('total_return', 0.0),
                'annualized_return': metrics.get('annualized_return', 0.0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0.0),
                'max_drawdown': metrics.get('max_drawdown', 0.0),
                'volatility': metrics.get('volatility', 0.0),
                'win_rate': trade_metrics.get('win_rate', 0.0) if trade_metrics else 0.0,
                'profit_factor': trade_metrics.get('profit_factor', 0.0) if trade_metrics else 0.0
            }
        }
        
        data['sections']['returns'] = {
            'title': 'Return Metrics',
            'data': return_metrics
        }
        
        if trade_metrics:
            data['sections']['trades'] = {
                'title': 'Trade Metrics',
                'data': trade_metrics
            }
        
        # Add additional sections from defined sections
        for section in self.sections:
            section_id = section['id']
            if section_id not in data['sections']:
                data['sections'][section_id] = {
                    'title': section['title'],
                    'data': self.content.get(section_id, {})
                }
        
        return data
    
    def add_content(self, section_id: str, content_id: str, content: Any) -> None:
        """
        Add content to a section.
        
        Args:
            section_id: Section identifier
            content_id: Content identifier
            content: Content to add
        """
        if section_id not in self.content:
            self.content[section_id] = {}
        
        self.content[section_id][content_id] = content
    
    def render_summary_section(self, data: Dict[str, Any]) -> str:
        """
        Render the summary section of the report.
        
        Args:
            data: Report data
            
        Returns:
            str: Rendered summary section
        """
        # This method should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement render_summary_section")
    
    def render_returns_section(self, data: Dict[str, Any]) -> str:
        """
        Render the returns section of the report.
        
        Args:
            data: Report data
            
        Returns:
            str: Rendered returns section
        """
        # This method should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement render_returns_section")
    
    def render_trades_section(self, data: Dict[str, Any]) -> str:
        """
        Render the trades section of the report.
        
        Args:
            data: Report data
            
        Returns:
            str: Rendered trades section
        """
        # This method should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement render_trades_section")
    
    def render_section(self, section_id: str, data: Dict[str, Any]) -> str:
        """
        Render a specific section of the report.
        
        Args:
            section_id: Section identifier
            data: Report data
            
        Returns:
            str: Rendered section
        """
        # This method should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement render_section")
    
    def render(self) -> Any:
        """
        Render the complete report.
        
        Returns:
            The rendered report (format depends on subclass implementation)
        """
        # This method should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement render")
    
    def save(self, filepath: str) -> None:
        """
        Save the rendered report to a file.
        
        Args:
            filepath: Path to save the report
        """
        # This method should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement save")