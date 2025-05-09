# examples/run_backtest.py
import logging
import os
import datetime

from core.events.event_bus import EventBus
from core.events.event_types import EventType
from data.sources.csv_handler import CSVDataSource
from data.historical_data_handler import HistoricalDataHandler
from portfolio.portfolio import Portfolio
from risk.risk_manager import RiskManager
from execution.broker.simulated_broker import SimulatedBroker
from strategies.ma_crossover import MovingAverageCrossover
from backtesting.backtest import Backtest
from core.analytics.performance.calculator import PerformanceCalculator
from core.analytics.reporting.report_generator import ReportGenerator

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    # Setup logging
    setup_logging()
    
    # Create event bus
    event_bus = EventBus()
    
    # Create data components
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    data_source = CSVDataSource(data_dir=data_dir)
    data_handler = HistoricalDataHandler(data_source=data_source, bar_emitter=event_bus)
    
    # Create portfolio and risk components
    portfolio = Portfolio(event_bus=event_bus, initial_cash=10000.0)
    risk_manager = RiskManager(event_bus=event_bus, portfolio=portfolio)
    
    # Create broker
    broker = SimulatedBroker(event_bus=event_bus)
    broker.configure({
        'slippage': 0.001,  # 0.1% slippage
        'commission': 0.001  # 0.1% commission
    })
    
    # Create strategy
    strategy = MovingAverageCrossover(event_bus=event_bus, data_handler=data_handler)
    strategy.configure({
        'symbols': ['AAPL', 'MSFT'],
        'fast_window': 10,
        'slow_window': 30,
        'price_key': 'close'
    })
    
    # Create performance calculator and report generator
    calculator = PerformanceCalculator()
    report_generator = ReportGenerator(calculator=calculator)
    
    # Create and configure backtest
    backtest = Backtest()
    backtest.set_event_bus(event_bus)
    backtest.set_data_handler(data_handler)
    backtest.set_portfolio(portfolio)
    backtest.set_risk_manager(risk_manager)
    backtest.set_broker(broker)
    backtest.add_strategy(strategy)
    backtest.set_performance_calculator(calculator)
    
    # Run backtest
    start_date = datetime.datetime(2020, 1, 1)
    end_date = datetime.datetime(2020, 12, 31)
    symbols = ['AAPL', 'MSFT']
    
    result = backtest.run(start_date, end_date, symbols)
    
    # Print results
    print("\nBacktest Results:")
    for key, value in result.stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")
    
    # Generate report
    report = report_generator.generate_detailed_report()
    report_path = os.path.join(os.path.dirname(__file__), 'backtest_report.txt')
    report_generator.save_report(report, report_path)
    print(f"\nDetailed report saved to: {report_path}")

if __name__ == "__main__":
    main()
