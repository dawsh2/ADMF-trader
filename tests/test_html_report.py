"""
Test suite for the HTMLReportBuilder class.
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Ensure src directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analytics.analysis.performance import PerformanceAnalyzer
from src.analytics.reporting.html_report import HTMLReportBuilder


class TestHTMLReportBuilder(unittest.TestCase):
    """Test suite for HTMLReportBuilder."""
    
    def setUp(self):
        """Set up test data."""
        # Create sample equity curve
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        equity = [10000 * (1 + 0.001 * i + 0.001 * np.sin(i / 5)) for i in range(100)]
        
        self.equity_curve = pd.DataFrame({
            'date': dates,
            'equity': equity
        })
        self.equity_curve.set_index('date', inplace=True)
        
        # Create sample trades
        self.trades = []
        for i in range(20):
            trade_date = dates[i * 5]
            exit_date = trade_date + timedelta(days=3)
            
            is_win = i % 3 != 0  # 2/3 win rate
            pnl = 100 + i * 10 if is_win else -50 - i * 5
            
            self.trades.append({
                'entry_time': trade_date,
                'exit_time': exit_date,
                'symbol': f'STOCK{i % 5 + 1}',
                'direction': 'BUY' if i % 2 == 0 else 'SELL',
                'entry_price': 100 + i,
                'exit_price': 100 + i + (pnl / 10),
                'quantity': 10,
                'pnl': pnl,
                'status': 'CLOSED'
            })
        
        # Create analyzer
        self.analyzer = PerformanceAnalyzer(self.equity_curve, self.trades)
        self.analyzer.analyze_performance()
        
        # Create report builder
        self.report_builder = HTMLReportBuilder(
            analyzer=self.analyzer,
            title="Test Strategy Performance",
            description="This is a test strategy performance report."
        )
        
    def test_initialization(self):
        """Test initialization of HTMLReportBuilder."""
        self.assertEqual(self.report_builder.title, "Test Strategy Performance")
        self.assertEqual(self.report_builder.description, "This is a test strategy performance report.")
        
    def test_prepare_charts(self):
        """Test chart preparation."""
        charts = self.report_builder.prepare_charts()
        
        # Check that charts were created
        self.assertIsInstance(charts, dict)
        self.assertGreaterEqual(len(charts), 1, "At least one chart should be created")
        
        # Check for specific charts
        self.assertIn('equity_curve', charts, "Equity curve chart should be created")
        
        # Verify that charts are base64 encoded strings
        for chart_name, chart_data in charts.items():
            self.assertIsInstance(chart_data, str, f"Chart {chart_name} should be a string")
            self.assertTrue(chart_data.startswith('iVBOR') or chart_data.startswith('/9j/'),
                           f"Chart {chart_name} should be a base64 encoded image")
    
    def test_render(self):
        """Test HTML report rendering."""
        html = self.report_builder.render()
        
        # Check that HTML was created
        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 1000, "HTML report should have substantial content")
        
        # Check for key HTML elements
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('<html', html)
        self.assertIn('</html>', html)
        self.assertIn('Test Strategy Performance', html)
        
        # Check for sections
        self.assertIn('Performance Summary', html)
        self.assertIn('Return Metrics', html)
        self.assertIn('Trade Performance', html)
        
        # Check for chart images
        self.assertIn('data:image/png;base64,', html)
    
    def test_save_report(self):
        """Test saving HTML report to file."""
        test_file = "/tmp/test_report.html"
        
        try:
            self.report_builder.save(test_file)
            self.assertTrue(os.path.exists(test_file))
            
            # Check file contents
            with open(test_file, 'r') as f:
                content = f.read()
                self.assertIn('<!DOCTYPE html>', content)
                self.assertIn('Test Strategy Performance', content)
                
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file)


if __name__ == '__main__':
    unittest.main()