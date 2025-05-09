"""
Test suite for the TextReportBuilder class.
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
from src.analytics.reporting.text_report import TextReportBuilder


class TestTextReportBuilder(unittest.TestCase):
    """Test suite for TextReportBuilder."""
    
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
        self.report_builder = TextReportBuilder(
            analyzer=self.analyzer,
            title="Test Strategy Performance",
            description="This is a test strategy performance report."
        )
        
    def test_initialization(self):
        """Test initialization of TextReportBuilder."""
        self.assertEqual(self.report_builder.title, "Test Strategy Performance")
        self.assertEqual(self.report_builder.description, "This is a test strategy performance report.")
        self.assertEqual(self.report_builder.width, 80)
        
    def test_render_summary_section(self):
        """Test rendering of summary section."""
        data = self.report_builder.prepare_report_data()
        summary = self.report_builder.render_summary_section(data)
        
        self.assertIn("Performance Summary", summary)
        self.assertIn("Total Return", summary)
        self.assertIn("Sharpe Ratio", summary)
        
    def test_render_returns_section(self):
        """Test rendering of returns section."""
        data = self.report_builder.prepare_report_data()
        returns = self.report_builder.render_returns_section(data)
        
        self.assertIn("Return Metrics", returns)
        self.assertIn("Returns", returns)
        self.assertIn("Risk", returns)
        
    def test_render_trades_section(self):
        """Test rendering of trades section."""
        data = self.report_builder.prepare_report_data()
        trades = self.report_builder.render_trades_section(data)
        
        self.assertIn("Trade Performance", trades)
        self.assertIn("Win Rate", trades)
        self.assertIn("Profit Factor", trades)
        
    def test_complete_render(self):
        """Test complete report rendering."""
        report = self.report_builder.render()
        
        # Check that each major section is present
        self.assertIn("Test Strategy Performance", report)
        self.assertIn("Performance Summary", report)
        self.assertIn("Return Metrics", report)
        self.assertIn("Trade Performance", report)
        
    def test_save_report(self):
        """Test saving report to file."""
        test_file = "/tmp/test_report.txt"
        
        try:
            self.report_builder.save(test_file)
            self.assertTrue(os.path.exists(test_file))
            
            # Check file contents
            with open(test_file, 'r') as f:
                content = f.read()
                self.assertIn("Test Strategy Performance", content)
                self.assertIn("Performance Summary", content)
                
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file)


if __name__ == '__main__':
    unittest.main()