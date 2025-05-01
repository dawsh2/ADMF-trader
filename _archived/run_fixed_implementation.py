#!/usr/bin/env python3
"""
Run MA Crossover Strategy with Fixed Implementation

This script runs the MA Crossover strategy with all fixes applied
and compares the number of trades generated.
"""
import os
import sys
import logging
import datetime
import pandas as pd
import types

# Set up logging
log_file = f"ma_crossover_fixed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_backtest():
    """Run backtest using fixed implementations."""
    try:
        # Import components
        from src.core.events.event_bus import EventBus
        from src.core.events.event_manager import EventManager
        from src.data.historical_data_handler import HistoricalDataHandler
        from src.risk.portfolio.portfolio import PortfolioManager
        from src.risk.managers.simple import SimpleRiskManager
        from src.execution.broker.broker_simulator import SimulatedBroker
        from src.execution.order_manager import OrderManager
        from src.strategy.implementations.ma_crossover import MACrossoverStrategy
        from src.execution.backtest.backtest import BacktestCoordinator
        
        # Create event system
        event_bus = EventBus()
        event_manager = EventManager(event_bus)
        
        # Create a mock data source for HistoricalDataHandler
        from src.data.data_source_base import DataSourceBase
        class MockDataSource(DataSourceBase):
            def get_data(self, symbol, start_date, end_date, timeframe):
                # Create a simple DataFrame with OHLCV data
                dates = pd.date_range(start=start_date, end=end_date, freq='1min')
                data = {
                    'open': [100 + i * 0.1 for i in range(len(dates))],
                    'high': [100 + i * 0.1 + 0.5 for i in range(len(dates))],
                    'low': [100 + i * 0.1 - 0.5 for i in range(len(dates))],
                    'close': [100 + i * 0.1 + 0.2 for i in range(len(dates))],
                    'volume': [1000 for _ in range(len(dates))]
                }
                df = pd.DataFrame(data, index=dates)
                return df
                
            def is_available(self, symbol: str, start_date=None, end_date=None, timeframe: str = '1d') -> bool:
                # This is the required abstract method implementation
                return True
        
        # Create data handler with the mock data source
        data_source = MockDataSource()
        data_handler = HistoricalDataHandler(data_source, event_bus)
        
        # Create portfolio
        portfolio = PortfolioManager(event_bus)
        
        # Create risk manager
        risk_manager = SimpleRiskManager(event_bus, portfolio)
        
        # Create broker and order manager
        broker = SimulatedBroker(event_bus)
        order_manager = OrderManager(event_bus, broker)
        
        # Connect risk manager and order manager
        risk_manager.order_manager = order_manager
        
        # Create strategy
        strategy_params = {
            'fast_window': 5,
            'slow_window': 15
        }
        strategy = MACrossoverStrategy(event_bus, data_handler, parameters=strategy_params)
        
        # Set symbols
        symbols = ['MINI']
        strategy.symbols = symbols
        
        # Create backtest coordinator
        coordinator = BacktestCoordinator()
        
        # Register components with the coordinator
        coordinator.event_bus = event_bus
        coordinator.event_manager = event_manager
        coordinator.data_handler = data_handler
        coordinator.portfolio = portfolio
        coordinator.risk_manager = risk_manager
        coordinator.broker = broker
        coordinator.order_manager = order_manager
        coordinator.strategy = strategy
        
        # Configure data handler directly for this test
        # No need to use data paths - MockDataSource will generate data
        
        # Create a simple test to demonstrate the fix
        # Use a very short time period to avoid infinite loop
        symbols = ['MINI']
        start_date = '2020-01-01'
        end_date = '2020-01-03'  # Just 3 days of data
        initial_capital = 100000.0
        
        # Add a maximum iteration count to prevent infinite loops
        max_iterations = 1000
        
        # Create a patched version of _run_backtest method to avoid infinite loops
        original_run_backtest = coordinator._run_backtest
        
        def patched_run_backtest(self):
            """Modified _run_backtest to limit iterations."""
            symbols = self.data_handler.get_symbols()
            if not symbols:
                logger.warning("No symbols available in data handler")
                return
            
            iteration = 0
            continue_backtest = True
            
            while continue_backtest and iteration < max_iterations:
                continue_backtest = False
                iteration += 1
                
                for symbol in symbols:
                    # Get next bar for this symbol
                    bar = self.data_handler.get_next_bar(symbol)
                    
                    # If we have a bar, process it
                    if bar:
                        continue_backtest = True
                
                # Log progress periodically
                if iteration % 100 == 0:
                    logger.info(f"Processed {iteration} iterations")
                    
            if iteration >= max_iterations:
                logger.warning(f"Reached maximum iterations ({max_iterations}), stopping backtest")
            
            logger.info(f"Backtest completed after {iteration} iterations")
        
        # Apply the patch
        coordinator._run_backtest = types.MethodType(patched_run_backtest, coordinator)
        
        # Run backtest
        logger.info(f"Running backtest with MA Crossover strategy (fixed implementation)")
        logger.info(f"Parameters: fast_window={strategy_params['fast_window']}, slow_window={strategy_params['slow_window']}")
        logger.info(f"Date range: {start_date} to {end_date}")
        
        results = coordinator.run(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital
        )
        
        # Analyze results
        trades = results.get('trades', [])
        trade_count = len(trades)
        
        logger.info(f"Backtest complete. Generated {trade_count} trades.")
        logger.info(f"Expected trade count: 18")
        
        # Check if fix was successful
        if trade_count == 18:
            logger.info("✅ FIX SUCCESSFUL! Generated exactly 18 trades as expected.")
        else:
            logger.warning(f"❌ FIX INCOMPLETE. Generated {trade_count} trades instead of 18.")
            
        # Save trades to CSV for analysis
        trades_df = pd.DataFrame(trades)
        if not trades_df.empty:
            trades_df.to_csv('backtest_trades_fixed.csv', index=False)
            logger.info("Trades saved to 'backtest_trades_fixed.csv'")
            
        return trade_count == 18
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        return False

def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("RUNNING MA CROSSOVER FIXED IMPLEMENTATION")
    logger.info("=" * 60)
    
    success = run_backtest()
    
    logger.info("=" * 60)
    if success:
        logger.info("MA CROSSOVER FIX VALIDATED SUCCESSFULLY!")
    else:
        logger.info("MA CROSSOVER FIX VALIDATION FAILED!")
    logger.info("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
