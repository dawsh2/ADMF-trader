"""
Optimizing backtest coordinator with train/test validation.

This implementation adds train/test validation to the backtest process
for proper parameter optimization with complete isolation between runs.
"""

import logging
import gc
import hashlib
import random
import numpy as np
import pandas as pd
from src.core.component import Component
from src.core.events.event_bus import EventBus, EventType, Event
from src.core.trade_repository import TradeRepository
from src.core.backtest_state import BacktestState
from src.execution.backtest.backtest_coordinator import BacktestCoordinator
from src.strategy.strategy_adapters import StrategyAdapter

# Set up logging
logger = logging.getLogger(__name__)

class OptimizingBacktest(Component):
    """
    Manages the optimization process with train/test validation.
    
    This class coordinates the optimization process, ensuring proper
    train/test validation to prevent overfitting with complete isolation
    between train and test runs.
    """
    
    def __init__(self, name, config, parameter_space):
        """
        Initialize the optimizing backtest.
        
        Args:
            name (str): Component name
            config (dict): Base configuration
            parameter_space (ParameterSpace): Parameter space for optimization
        """
        super().__init__(name)
        self.config = config
        self.parameter_space = parameter_space
        self.best_parameters = None
        self.best_train_result = None
        self.best_test_result = None
        self.all_results = []
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
    def initialize(self, context):
        """
        Initialize with dependencies.
        
        Args:
            context (dict): Context containing dependencies
        """
        super().initialize(context)
        self.strategy_factory = context.get('strategy_factory')
        
        if not self.strategy_factory:
            raise ValueError("OptimizingBacktest requires strategy_factory in context")
            
    def optimize(self, strategy_name, objective_function, train_test_config=None):
        """
        Run optimization with train/test validation.
        
        Args:
            strategy_name (str): Name of the strategy to optimize
            objective_function (callable): Function to evaluate results
            train_test_config (dict, optional): Train/test configuration
            
        Returns:
            dict: Optimization results
        """
        # Default to using 70/30 train/test split if not specified
        if not train_test_config:
            train_test_config = {
                'method': 'ratio',
                'train_ratio': 0.7,
                'test_ratio': 0.3
            }

        # Ensure we have a valid train_test_split config
        if not isinstance(train_test_config, dict):
            logger.warning("Invalid train_test_config provided, using default 70/30 split")
            train_test_config = {
                'method': 'ratio',
                'train_ratio': 0.7,
                'test_ratio': 0.3
            }

        # Make sure the data config has train_test_split
        if 'data' in self.config and not self.config['data'].get('train_test_split'):
            logger.info("Adding train_test_split to data config for proper data separation")
            self.config['data']['train_test_split'] = train_test_config
            
        # Get parameter combinations to test
        parameter_combinations = self.parameter_space.get_combinations()
        
        if not parameter_combinations:
            raise ValueError("No parameter combinations to test")
            
        # Track results
        self.all_results = []
        best_train_score = float('-inf')
        
        # Test each parameter combination
        for params in parameter_combinations:
            # CRITICAL FIX: Add clear logging to separate train and test runs
            self.logger.info(f"{'=' * 30} TRAINING BACKTEST {'=' * 30}")

            # CRITICAL FIX: Force complete garbage collection before train run
            # This helps ensure that no state leaks between runs
            gc.collect()

            # Run backtest with training data
            train_result = self._run_backtest_with_params(
                strategy_name,
                params,
                'train',
                train_test_config
            )

            # Evaluate result
            train_score = objective_function(train_result)

            # CRITICAL FIX: Force complete garbage collection between train and test runs
            # This helps ensure that no state leaks between runs
            gc.collect()

            # Create separate diagnostic fingerprints for validation
            train_fingerprint = f"Training with params {params} produced {len(train_result.get('trades', []))} trades"
            self.logger.info(f"DIAGNOSTIC: {train_fingerprint}")

            # Run backtest with test data for current parameters
            self.logger.info(f"{'=' * 30} TESTING BACKTEST {'=' * 30}")
            
            # CRITICAL FIX: Force garbage collection before test run
            gc.collect()
            
            test_result = self._run_backtest_with_params(
                strategy_name,
                params,
                'test',
                train_test_config
            )

            # Create separate diagnostic fingerprints for validation
            test_fingerprint = f"Testing with params {params} produced {len(test_result.get('trades', []))} trades"
            self.logger.info(f"DIAGNOSTIC: {test_fingerprint}")

            # Verify if train and test actually differ
            if (train_result.get('statistics', {}).get('return_pct') ==
                test_result.get('statistics', {}).get('return_pct')):
                self.logger.error("CRITICAL DATA ISSUE: Train and test results are identical!")
                self.logger.error("This indicates that train/test split is not working correctly!")
            
            # Evaluate test result
            test_score = objective_function(test_result)
            
            # Print progress update
            train_stats = train_result.get('statistics', {})
            test_stats = test_result.get('statistics', {})
            
            # Format parameters as string
            params_str = ', '.join([f"{k}={v}" for k, v in params.items()])
            
            print(f"Parameters: {params_str} | "
                  f"Train Score: {train_score:.4f}, Return: {train_stats.get('return_pct', 0):.2f}%, "
                  f"Sharpe: {train_stats.get('sharpe_ratio', 0):.2f} | "
                  f"Test Score: {test_score:.4f}, Return: {test_stats.get('return_pct', 0):.2f}%, "
                  f"Sharpe: {test_stats.get('sharpe_ratio', 0):.2f}")
            
            # Store result
            result = {
                'parameters': params,
                'train_score': train_score,
                'test_score': test_score,
                'train_result': train_result,
                'test_result': test_result
            }
            
            self.all_results.append(result)
            
            # Update best result if this is better
            if train_score > best_train_score:
                best_train_score = train_score
                self.best_parameters = params
                self.best_train_result = train_result
                self.best_test_result = test_result
                
        # Sort results by train score
        self.all_results.sort(key=lambda x: x['train_score'], reverse=True)
        
        # Prepare final results
        optimization_results = {
            'best_parameters': self.best_parameters,
            'best_train_score': best_train_score,
            'best_test_score': objective_function(self.best_test_result),
            'all_results': self.all_results,
            'parameter_counts': len(parameter_combinations),
            'train_results': self.best_train_result,  # Add full train results
            'test_results': self.best_test_result     # Add full test results
        }
        
        return optimization_results
        
    def get_strategy_by_name(self, strategy_name):
        """
        Get a strategy by name using the strategy factory.
        
        Args:
            strategy_name (str): Name of the strategy to get
            
        Returns:
            object: Strategy class
            
        Raises:
            ValueError: If the strategy is not found
        """
        if not self.strategy_factory:
            raise ValueError("No strategy factory available")
            
        # Use the strategy factory to get the strategy
        try:
            strategy = self.strategy_factory.create_strategy(strategy_name, name='strategy')
            logger.info(f"Successfully created strategy: {strategy_name}")
            return strategy
        except Exception as e:
            logger.error(f"Error creating strategy '{strategy_name}': {e}")
            # Try to debug which strategies are available
            strategy_names = self.strategy_factory.get_strategy_names() if hasattr(self.strategy_factory, 'get_strategy_names') else []
            logger.info(f"Available strategies: {strategy_names}")
            raise ValueError(f"Failed to create strategy '{strategy_name}': {e}")
    
    def _run_backtest_with_params(self, strategy_name, params, data_split, train_test_config):
        """
        Run a backtest with specific parameters and data split.

        Args:
            strategy_name (str): Name of the strategy to use
            params (dict): Strategy parameters
            data_split (str): Data split to use ('train' or 'test')
            train_test_config (dict): Train/test configuration

        Returns:
            dict: Backtest results

        IMPORTANT: This method creates a completely isolated backtest environment
        for each parameter set and data split to ensure train/test isolation.
        """
        # CRITICAL FIX: Add clear logging to identify train vs test runs
        self.logger.info(f"{'=' * 30} RUNNING BACKTEST WITH {data_split.upper()} DATA {'=' * 30}")
        self.logger.info(f"Strategy: {strategy_name}, Parameters: {params}")
        
        # Use consistent initial capital for all backtests
        initial_capital = self.config.get('initial_capital', 100000)

        # CRITICAL FIX: Create completely new components for this backtest
        # Create new event bus for this backtest
        event_bus = EventBus()

        # Create fresh trade repository for each backtest to avoid state leakage
        trade_repository = TradeRepository()

        # Create backtest coordinator - with unique name for each run
        run_id = f"{data_split}_{hash(str(params))}"
        backtest = BacktestCoordinator(f"backtest_{run_id}", self.config.copy())

        # Initialize context with fresh components
        context = {
            'event_bus': event_bus,
            'trade_repository': trade_repository,
            'config': self.config.copy(),
            'strategy_factory': self.strategy_factory
        }

        # Set a deterministic seed based on parameter values to ensure reproducibility
        # But also make it unique for each train/test split
        import hashlib
        import random
        import numpy as np

        # Create a hash from parameters and split name for reproducible randomness
        params_str = str(sorted(params.items()))
        unique_seed = int(hashlib.md5(f"{params_str}_{data_split}".encode()).hexdigest(), 16) % (2**32)
        random.seed(unique_seed)
        np.random.seed(unique_seed)
        self.logger.info(f"Set random seed to {unique_seed} for {data_split} with params {params}")

        # Add data split info to the context
        context['data_split'] = data_split

        # Pass max_bars setting if available
        if 'max_bars' in self.config:
            context['max_bars'] = self.config['max_bars']
            self.logger.info(f"Using max_bars={self.config['max_bars']} in backtest context")
        
        # CRITICAL FIX: Create a data handler instance specific to this run
        # This ensures complete isolation between train and test data
        data_handler_class = self._get_data_handler_class()
        data_config = self.config.get('data', {}).copy()  # Create a copy to modify

        # Add max_bars to data_config if available in config
        if 'max_bars' in self.config:
            data_config['max_bars'] = self.config['max_bars']
            self.logger.info(f"Adding max_bars={self.config['max_bars']} to data_config")

        # Add unique identifier to data handler name to ensure isolation
        data_handler_name = f"data_handler_{run_id}"
        self.logger.info(f"Creating isolated data handler: {data_handler_name}")

        # Create a unique data handler for this run
        data_handler = data_handler_class(data_handler_name, data_config)
        data_handler.initialize(context)

        # Setup train/test split with logging to trace issues
        self.logger.info(f"Setting up train/test split with method: {train_test_config.get('method', 'ratio')}")
        data_handler.setup_train_test_split(
            method=train_test_config.get('method', 'ratio'),
            train_ratio=train_test_config.get('train_ratio', 0.7),
            test_ratio=train_test_config.get('test_ratio', 0.3),
            split_date=train_test_config.get('split_date'),
            train_periods=train_test_config.get('train_periods'),
            test_periods=train_test_config.get('test_periods')
        )

        # CRITICAL FIX: Make sure to activate the correct data split
        self.logger.info(f"Activating {data_split} split in data handler")
        data_handler.set_active_split(data_split)

        # Force garbage collection to ensure memory is freed
        gc.collect()
        
        # Log information about the split sizes
        if hasattr(data_handler, 'get_split_sizes'):
            split_sizes = data_handler.get_split_sizes()
            self.logger.info(f"Split data for {data_handler.get_current_symbol()}: "
                         f"train={split_sizes.get('train', 0)} rows, "
                         f"test={split_sizes.get('test', 0)} rows")
        
        # Activate the data split
        self.logger.info(f"Activated '{data_split}' data split")
        data_handler.set_active_split(data_split)

        # Add more thorough diagnostics for train/test splits
        try:
            # Create a function to generate a fingerprint for a DataFrame
            def get_data_fingerprint(df):
                """Create a unique fingerprint of a DataFrame for comparison"""
                if df is None or df.empty:
                    return "empty_dataframe"

                # Use first 5 and last 5 rows for fingerprinting
                sample_rows = pd.concat([df.head(5), df.tail(5)])
                # Convert to string and hash
                import hashlib
                hash_obj = hashlib.md5(pd.util.hash_pandas_object(sample_rows).values)
                return hash_obj.hexdigest()

            # Store fingerprints per symbol and split for comparison
            fingerprints = {}

            # Print DETAILED information about the data being used
            for symbol in data_handler.get_symbols():
                fingerprints[symbol] = {}
                if hasattr(data_handler, 'data_splits') and data_split in data_handler.data_splits.get(symbol, {}):
                    split_df = data_handler.data_splits[symbol][data_split]
                    # Generate fingerprint
                    fingerprint = get_data_fingerprint(split_df)
                    fingerprints[symbol][data_split] = fingerprint

                    # Log the first 3 and last 3 timestamps
                    if isinstance(split_df, pd.DataFrame) and len(split_df) > 6:
                        first_timestamps = split_df.iloc[0:3]['timestamp'].astype(str).tolist()
                        last_timestamps = split_df.iloc[-3:]['timestamp'].astype(str).tolist()
                        logger.info(f"DETAILED {data_split.upper()} DATA DIAGNOSTICS for {symbol}:")
                        logger.info(f"  First 3 timestamps: {first_timestamps}")
                        logger.info(f"  Last 3 timestamps: {last_timestamps}")
                        logger.info(f"  DataFrame fingerprint: {fingerprint}")

                        # If we have both train and test fingerprints, check for equality
                        # This would be a strong indication of data reuse
                        if 'train' in fingerprints[symbol] and 'test' in fingerprints[symbol]:
                            if fingerprints[symbol]['train'] == fingerprints[symbol]['test']:
                                logger.error(f"CRITICAL DATA ISSUE: Train and test datasets for {symbol} have identical fingerprints!")
                                logger.error(f"This indicates that the same data is being used for both training and testing!")
                    else:
                        logger.warning(f"Too few rows in {data_split} split for {symbol}")
        except Exception as e:
            logger.error(f"Error in detailed diagnostics: {e}")

        # IMPROVED: Verify data is available for this split
        if hasattr(data_handler, 'is_empty') and data_handler.is_empty(data_split):
            logger.warning(f"No data available for {data_split} split. Returning empty results.")
            return {
                'parameters': params,
                'data_split': data_split,
                'trades': [],
                'statistics': {
                    'return_pct': 0,
                    'sharpe_ratio': 0,
                    'profit_factor': 0,
                    'max_drawdown': 0,
                    'trades_executed': 0
                },
                'warning': f"No data available for {data_split} split"
            }
        
        # CRITICAL FIX: Create a completely new strategy instance for each backtest
        # This is essential to prevent state leakage between train and test runs
        try:
            # Generate a unique strategy name to ensure no shared state
            unique_strategy_name = f"strategy_{run_id}"
            self.logger.info(f"Creating fresh strategy instance: {unique_strategy_name}")
            
            # Create strategy with required dependencies
            strategy = self.strategy_factory.create_strategy(
                strategy_name, 
                event_bus=event_bus,
                data_handler=data_handler,
                name=unique_strategy_name
            )
            
            # Apply strategy parameters
            for key, value in params.items():
                if hasattr(strategy, key):
                    setattr(strategy, key, value)
                    self.logger.debug(f"Set strategy parameter {key}={value}")
                elif hasattr(strategy, 'parameters') and isinstance(strategy.parameters, dict):
                    strategy.parameters[key] = value
                    self.logger.debug(f"Set strategy parameter {key}={value} in parameters dict")
                    
            # Log strategy creation
            self.logger.info(f"Created strategy '{strategy_name}' with parameters {params}")
            
            # CRITICAL FIX: Explicitly reset the strategy state
            if hasattr(strategy, 'reset') and callable(getattr(strategy, 'reset')):
                self.logger.info(f"Explicitly resetting strategy state for {unique_strategy_name}")
                strategy.reset()
                
        except Exception as e:
            self.logger.error(f"Error creating strategy '{strategy_name}' with parameters {params}: {e}")
            # Fall back to simplified approach as a last resort
            try:
                # Try simplified approach with just required dependencies
                strategy = self.strategy_factory.create_strategy(
                    strategy_name, 
                    name=f"strategy_{run_id}"
                )
                
                # Initialize the strategy with context
                if hasattr(strategy, 'initialize') and callable(getattr(strategy, 'initialize')):
                    strategy.initialize({
                        'event_bus': event_bus,
                        'data_handler': data_handler
                    })
                
                # Apply parameters after creation
                for key, value in params.items():
                    try:
                        if hasattr(strategy, key):
                            setattr(strategy, key, value)
                        elif hasattr(strategy, 'parameters') and isinstance(strategy.parameters, dict):
                            strategy.parameters[key] = value
                    except Exception:
                        self.logger.warning(f"Could not set parameter {key}={value} on strategy")
                
                # CRITICAL FIX: Explicitly reset the strategy
                if hasattr(strategy, 'reset') and callable(getattr(strategy, 'reset')):
                    self.logger.info("Explicitly resetting fallback strategy state")
                    strategy.reset()
            except Exception as e2:
                raise ValueError(f"Failed to create strategy '{strategy_name}': {e2}")
        
        # Create other components with fresh state for each backtest
        from src.execution.portfolio import Portfolio
        from src.execution.broker.simulated_broker import SimulatedBroker
        from src.execution.order_manager import OrderManager
        
        # Create fresh portfolio for this backtest with consistent initial capital
        portfolio = Portfolio("portfolio", initial_capital)
        self.logger.info(f"Created new portfolio with initial capital: {initial_capital}")
        
        # Create fresh broker and order manager
        broker = SimulatedBroker("broker")
        order_manager = OrderManager("order_manager")
        
        # Add components to backtest
        backtest.add_component('data_handler', data_handler)
        
        # CRITICAL FIX: Wrap the strategy in a new adapter for each run
        strategy_adapter = StrategyAdapter(f'strategy_adapter_{run_id}', strategy)
        backtest.add_component('strategy', strategy_adapter)
        
        backtest.add_component('portfolio', portfolio)
        backtest.add_component('broker', broker)
        backtest.add_component('order_manager', order_manager)
        
        # Initialize backtest
        backtest.initialize(context)
        
        # Setup and run backtest
        backtest.setup()
        results = backtest.run()
        
        # Add parameters and split info to results
        results['parameters'] = params
        results['data_split'] = data_split
        
        # Add trade tracking debug info
        if 'trades' in results:
            # IMPROVED: Add detailed trade analysis
            trades = results['trades']
            closed_trades = [t for t in trades if t.get('closed', True)]
            open_trades = [t for t in trades if not t.get('closed', True)]
            winners = [t for t in closed_trades if t.get('pnl', 0) > 0]
            losers = [t for t in closed_trades if t.get('pnl', 0) < 0]
            break_even = [t for t in closed_trades if t.get('pnl', 0) == 0]
            
            logger.info(f"Backtest completed with {len(trades)} trades in {data_split} split")
            logger.info(f"  Closed trades: {len(closed_trades)}, Open trades: {len(open_trades)}")
            logger.info(f"  Winners: {len(winners)}, Losers: {len(losers)}, Break-even: {len(break_even)}")
            
            # Verify that all closed trades have a valid PnL value
            invalid_pnl = [i for i, t in enumerate(closed_trades) if 'pnl' not in t or t['pnl'] is None]
            if invalid_pnl:
                logger.warning(f"Found {len(invalid_pnl)} closed trades without valid PnL values")
                # Add diagnostics about these trades
                for idx in invalid_pnl[:5]:  # Show details for up to 5 invalid trades
                    trade = closed_trades[idx]
                    logger.warning(f"  Invalid trade #{idx}: {trade}")
                    
            # Calculate total PnL from trades
            total_pnl = sum(t.get('pnl', 0) for t in closed_trades if t.get('pnl') is not None)
            equity_change = results.get('final_capital', 0) - portfolio.initial_capital
            logger.info(f"  Total PnL from trades: {total_pnl:.2f}, Equity change: {equity_change:.2f}")
            
            # IMPROVED: Check for inconsistency between PnL and equity change
            if abs(total_pnl - equity_change) > 0.01 * abs(equity_change) and abs(equity_change) > 0.001:
                logger.warning(f"  Inconsistency between trade PnL ({total_pnl:.2f}) and equity change ({equity_change:.2f})")
                # Calculate unexplained difference for tracking
                unexplained_diff = equity_change - total_pnl
                percent_unexplained = (unexplained_diff / abs(equity_change)) * 100 if abs(equity_change) > 0.001 else 0
                
                logger.warning(f"  Unexplained difference: {unexplained_diff:.2f} ({percent_unexplained:.2f}% of equity change)")
                
                # Add consistency flag and diagnostics to results
                if 'statistics' in results:
                    results['statistics']['pnl_equity_consistent'] = False
                    results['statistics']['unexplained_pnl'] = unexplained_diff
                    results['statistics']['unexplained_pnl_percent'] = percent_unexplained
        else:
            logger.warning(f"No trades found in results for {data_split} split")
            # Add empty trades list to ensure consistent structure
            results['trades'] = []
        
        # IMPROVED: Always ensure statistics are present in results
        if 'statistics' not in results:
            results['statistics'] = {
                'return_pct': (results.get('final_capital', portfolio.initial_capital) - portfolio.initial_capital) / portfolio.initial_capital * 100,
                'sharpe_ratio': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0,
                'trades_executed': len(results.get('trades', []))
            }
        
        # CRITICAL FIX: Force garbage collection after backtest
        gc.collect()
        
        return results
        
    def _get_data_handler_class(self):
        """
        Get the data handler class for backtest.
        
        Returns:
            class: Data handler class
        """
        # Import here to avoid circular imports
        from src.data.historical_data_handler import HistoricalDataHandler
        return HistoricalDataHandler