"""
Bootstrap module for initializing the ADMF-Trader system.

This module handles the initialization of all components, dependency
injection, and configuration of the system.
"""

import os
import logging
import importlib.util
from typing import Dict, Any, Tuple, Optional, List

from src.core.configuration.config import Config
from src.core.dependency_injection.container import Container
from src.core.event_system.event_bus import EventBus

logger = logging.getLogger(__name__)

class Bootstrap:
    """
    System bootstrap to initialize all components.
    
    This class handles:
    - Loading configuration
    - Setting up dependency injection
    - Initializing core components
    - Connecting component dependencies
    """
    
    def __init__(self, config_files: Optional[List[str]] = None, 
                 env_prefix: str = "ADMF_", 
                 log_level: int = logging.INFO,
                 log_file: str = "main.log", 
                 debug: bool = False):
        """
        Initialize bootstrap.
        
        Args:
            config_files: List of configuration files to load
            env_prefix: Environment variable prefix
            log_level: Logging level
            log_file: Log file path
            debug: Enable debug mode
        """
        self.config_files = config_files or []
        self.env_prefix = env_prefix
        self.log_level = log_level
        self.log_file = log_file
        self.debug = debug
        
        # Context for additional options
        self.context: Dict[str, Any] = {}
        
    def set_context_value(self, key: str, value: Any) -> None:
        """
        Set a value in the bootstrap context.
        
        Args:
            key: Context key
            value: Context value
        """
        self.context[key] = value
        
    def setup(self) -> Tuple[Container, Config]:
        """
        Set up the system with standard components.
        
        Returns:
            Tuple of (container, config)
        """
        # Set up logging
        self._setup_logging()
        
        # Load configuration
        config = self._load_configuration()
        
        # Create container
        container = Container()
        container.register_instance("config", config)
        
        # Set up core components
        self._setup_core_components(container, config)
        
        # Set up data components
        self._setup_data_components(container, config)
        
        # Set up strategy components
        self._setup_strategy_components(container, config)
        
        # Set up risk components
        self._setup_risk_components(container, config)
        
        # Set up execution components
        self._setup_execution_components(container, config)
        
        # Set up backtesting components
        self._setup_backtesting_components(container, config)
        
        # Set up analytics components
        self._setup_analytics_components(container, config)
        
        logger.info("System bootstrap complete")
        return container, config
        
    def _setup_logging(self) -> None:
        """Set up logging system."""
        # Create handlers
        handlers = [
            logging.StreamHandler(),
            logging.FileHandler(self.log_file, mode='w')
        ]
        
        # Configure basic logging
        logging.basicConfig(
            level=self.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        
        # Set up root logger
        root_logger = logging.getLogger()
        
        # Enable debug mode if requested
        if self.debug:
            root_logger.setLevel(logging.DEBUG)
            logger.debug("Debug mode enabled")
            
        logger.info(f"Logging initialized at level {logging.getLevelName(root_logger.level)}")
        logger.info(f"Log file: {self.log_file}")
        
    def _load_configuration(self) -> Config:
        """
        Load configuration from files and environment.
        
        Returns:
            Config: Loaded configuration
        """
        config = Config()
        
        # Load config files
        for file_path in self.config_files:
            try:
                config_from_file = Config.from_file(file_path)
                config.update(config_from_file)
                logger.info(f"Loaded configuration from {file_path}")
            except Exception as e:
                logger.error(f"Error loading configuration from {file_path}: {e}")
        
        # TODO: Add environment variable loading
        
        return config
        
    def _setup_core_components(self, container: Container, config: Config) -> None:
        """
        Set up core components.
        
        Args:
            container: Dependency injection container
            config: Configuration
        """
        # Create event bus
        event_bus = EventBus()
        container.register_instance("event_bus", event_bus)
        
        logger.info("Core components initialized")
        
    def _setup_data_components(self, container: Container, config: Config) -> None:
        """
        Set up data components.
        
        Args:
            container: Dependency injection container
            config: Configuration
        """
        # Import data handler
        try:
            # Check for data sources in config
            data_config = config.get('data', {})
            data_sources = data_config.get('sources', [])
            
            if data_sources:
                # Import the concrete implementation
                from src.data.csv_data_handler import CSVDataHandler
                
                # Create a data directory if not exists
                data_dir = "./data"  # Default to data directory
                
                # Get date configuration from config
                date_column = data_config.get('date_column', 'timestamp')
                date_format = data_config.get('date_format', '%Y-%m-%d %H:%M:%S')
                
                # Create the CSV data handler
                data_handler = CSVDataHandler(
                    name="csv_data_handler", 
                    data_dir=data_dir,
                    filename_pattern="{symbol}.csv",  # Simple pattern that matches our data files
                    date_column=date_column,
                    date_format=date_format
                )
                
                # Register in container
                container.register_instance("data_handler", data_handler)
                
                # Prepare symbols for loading
                symbols = [source.get('symbol') for source in data_sources]
                logger.info(f"Data handler registered with {len(symbols)} symbols: {symbols}")
                
                # Store symbols in context for later use
                self.context['symbols'] = symbols
            else:
                logger.warning("No data sources configured")
                
        except ImportError as e:
            logger.error(f"Failed to import data components: {e}")
        except Exception as e:
            logger.error(f"Error setting up data components: {e}", exc_info=True)
            
        logger.info("Data components initialized")
        
    def _setup_strategy_components(self, container: Container, config: Config) -> None:
        """
        Set up strategy components.
        
        Args:
            container: Dependency injection container
            config: Configuration
        """
        try:
            # Check for strategy configuration
            strategy_config = config.get('strategy', {})
            strategy_name = strategy_config.get('name')
            
            if strategy_name:
                # Import strategy factory
                from src.strategy.strategy_factory import StrategyFactory
                
                # Get strategy params
                params = strategy_config.get('default_params', {})
                
                # Create strategy factory with the implementations directory
                import os
                strategy_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                          'src', 'strategy', 'implementations')
                
                logger.info(f"Looking for strategies in: {strategy_dir}")
                strategy_factory = StrategyFactory([strategy_dir])
                container.register_instance('strategy_factory', strategy_factory)
                
                # Print debug info
                strategy_factory.print_debug_info()
                
                # Create strategy with a name parameter
                logger.info(f"Creating strategy '{strategy_name}' with params: {params}")
                all_params = {
                    'name': strategy_name,  # Add required name parameter
                    **params  # Add the rest of the parameters
                }
                strategy = strategy_factory.create_strategy(strategy_name, **all_params)
                
                if strategy:
                    container.register_instance('strategy', strategy)
                    logger.info(f"Strategy '{strategy_name}' registered: {strategy.__class__.__name__}")
                else:
                    logger.warning(f"Failed to create strategy '{strategy_name}'")
            else:
                logger.warning("No strategy specified in configuration")
                
        except ImportError as e:
            logger.error(f"Failed to import strategy components: {e}")
        except Exception as e:
            logger.error(f"Error setting up strategy components: {e}", exc_info=True)
            
        logger.info("Strategy components initialized")
        
    def _setup_risk_components(self, container: Container, config: Config) -> None:
        """
        Set up risk components.
        
        Args:
            container: Dependency injection container
            config: Configuration
        """
        try:
            # Import portfolio and risk managers
            from src.risk.portfolio.portfolio_manager import PortfolioManager
            from src.risk.managers.standard_risk_manager import StandardRiskManager as RiskManager
            
            # Get initial capital from config
            initial_capital = config.get('initial_capital', 100000)
            
            # Get event bus from container
            event_bus = container.get('event_bus')
            
            # Create portfolio manager with the correct parameter order
            portfolio_manager = PortfolioManager(
                initial_cash=initial_capital,
                event_bus=event_bus,
                name="portfolio_manager"
            )
            container.register_instance("portfolio", portfolio_manager)
            
            # Create risk manager
            risk_config = config.get('risk', {})
            risk_manager = RiskManager(
                portfolio_manager=portfolio_manager,
                event_bus=event_bus,
                name="risk_manager"
            )
            # Configure risk manager if needed
            if risk_config:
                risk_manager.configure(risk_config)
            container.register_instance("risk_manager", risk_manager)
            
            logger.info(f"Portfolio manager initialized with ${initial_capital:.2f}")
            logger.info("Risk manager initialized")
            
        except ImportError as e:
            logger.error(f"Failed to import risk components: {e}")
            
        logger.info("Risk components initialized")
        
    def _setup_execution_components(self, container: Container, config: Config) -> None:
        """
        Set up execution components.
        
        Args:
            container: Dependency injection container
            config: Configuration
        """
        try:
            # Import broker components
            from src.execution.broker.simulated_broker import SimulatedBroker
            from src.execution.broker.market_simulator import MarketSimulator
            
            # Create market simulator
            market_simulator = MarketSimulator("market_simulator", config.get('broker', {}).get('market_simulator', {}))
            container.register_instance("market_simulator", market_simulator)
            
            # Create simulated broker
            broker = SimulatedBroker("simulated_broker", config.get('broker', {}))
            container.register_instance("broker", broker)
            
            logger.info("Market simulator initialized")
            logger.info("Simulated broker initialized")
            
        except ImportError as e:
            logger.error(f"Failed to import execution components: {e}")
            
        logger.info("Execution components initialized")
        
    def _setup_backtesting_components(self, container: Container, config: Config) -> None:
        """
        Set up backtesting components.
        
        Args:
            container: Dependency injection container
            config: Configuration
        """
        # Check if we're in backtest mode
        mode = config.get('mode', 'backtest')
        if mode == 'backtest':
            try:
                # Import the BacktestCoordinator
                from src.execution.backtest.backtest_coordinator import BacktestCoordinator
                
                # Create a trade repository
                from src.core.trade_repository import TradeRepository
                trade_repository = TradeRepository()
                container.register_instance("trade_repository", trade_repository)
                
                # Create the backtest coordinator
                backtest = BacktestCoordinator("backtest_coordinator", config)
                container.register_instance("backtest", backtest)
                
                # Set up shared context with key components
                event_bus = container.get("event_bus")
                shared_context = {
                    'event_bus': event_bus,
                    'trade_repository': trade_repository,
                    'config': config
                }
                
                # Add symbols to shared context if available in Bootstrap context
                if 'symbols' in self.context:
                    shared_context['symbols'] = self.context['symbols']
                
                # Initialize the backtest coordinator with the shared context
                backtest.initialize(shared_context)
                
                # Register key components with the backtest coordinator
                component_keys = ['data_handler', 'strategy', 'portfolio', 'risk_manager', 'broker', 'market_simulator']
                for key in component_keys:
                    if key in container.components:  # Use direct dictionary check 
                        component = container.get(key)
                        backtest.add_component(key, component)
                        logger.info(f"Registered {key} component with BacktestCoordinator")
                
                logger.info("Backtesting components initialized (BacktestCoordinator registered)")
            except ImportError as e:
                logger.error(f"Failed to import backtest components: {e}")
        else:
            logger.info("Backtesting components initialization skipped (not in backtest mode)")
        
    def _setup_analytics_components(self, container: Container, config: Config) -> None:
        """
        Set up analytics components.
        
        Args:
            container: Dependency injection container
            config: Configuration
        """
        # TODO: Initialize analytics components
        
        logger.info("Analytics components initialized")