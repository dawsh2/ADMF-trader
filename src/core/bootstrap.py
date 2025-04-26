"""
Bootstrap class for setting up the entire system.
"""
import logging
from typing import Dict, Any, Tuple

from src.core.config.config import Config
from src.core.di.container import Container
from src.core.events.event_bus import EventBus
from src.core.events.event_manager import EventManager
from src.core.utils.registry import Registry
from src.core.utils.discovery import discover_components

logger = logging.getLogger(__name__)

class Bootstrap:
    """System bootstrap that handles standard initialization."""
    
    def __init__(self, config_files=None, env_prefix="APP_", log_level=logging.INFO, log_file="backtest.log", debug=False):
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
        self.registries = {}
        
    def setup(self) -> Tuple[Container, Config]:
        """
        Set up the system with standard components.
        
        Returns:
            Tuple of (container, config)
        """
        # Set up logging with file and console output
        self._setup_logging()
        
        # Load configuration
        config = Config()
        
        # Load config files
        for file_path in self.config_files:
            try:
                config.load_file(file_path)
                logger.info(f"Loaded configuration from {file_path}")
            except Exception as e:
                logger.error(f"Error loading configuration from {file_path}: {e}")
        
        # Load environment variables
        config.load_env(prefix=self.env_prefix)
        
        # Create container and register config
        container = Container()
        container.register_instance("config", config)
        
        # Set up core event system
        self._setup_event_system(container, config)
        
        # Set up data components
        self._setup_data_components(container, config)
        
        # Set up order registry first (new component!)
        self._setup_order_registry(container, config)
        
        # Set up execution components
        self._setup_execution_components(container, config)
        
        # Set up risk components
        self._setup_risk_components(container, config)
        
        # Set up strategy components
        self._setup_strategy_components(container, config)
        
        # Set up analytics components
        self._setup_analytics_components(container, config)
        
        logger.info("System bootstrap complete")
        return container, config
    
    def _setup_event_system(self, container, config):
        """Set up the event system components."""
        event_bus = EventBus()
        event_manager = EventManager(event_bus)
        
        container.register_instance("event_bus", event_bus)
        container.register_instance("event_manager", event_manager)
        
        logger.info("Event system initialized")
    
    def _setup_order_registry(self, container, config):
        """Set up the order registry component."""
        from src.execution.order_registry import OrderRegistry
        
        # Get event bus
        event_bus = container.get("event_bus")
        
        # Create order registry
        order_registry = OrderRegistry(event_bus)
        container.register_instance("order_registry", order_registry)
        
        logger.info("Order registry initialized")
    
    def _setup_data_components(self, container, config):
        """Set up data handling components."""
        from src.core.events.event_emitters import BarEmitter
        from src.data.historical_data_handler import HistoricalDataHandler
        
        # Get event bus
        event_bus = container.get("event_bus")
        
        # Create bar emitter
        bar_emitter = BarEmitter("bar_emitter", event_bus)
        bar_emitter.start()
        container.register_instance("bar_emitter", bar_emitter)
        
        # Set up data source registry
        data_source_registry = Registry()
        self.registries["data_sources"] = data_source_registry
        
        # Discover data sources
        from src.data.data_source_base import DataSourceBase
        discover_components(
            package_name="src.data.sources",
            base_class=DataSourceBase,
            registry=data_source_registry,
            config=config
        )
        
        # Create data source
        data_config = config.get_section("data")
        source_type = data_config.get("source_type", "csv")
        
        if source_type == "csv":
            from src.data.sources.csv_handler import CSVDataSource
            data_dir = data_config.get("data_dir", "./data")
            data_source = CSVDataSource(data_dir)
        else:
            # Try to get from registry
            source_class = data_source_registry.get(source_type)
            if source_class:
                data_source = source_class()
            else:
                logger.warning(f"Unknown data source type: {source_type}, using CSV")
                from src.data.sources.csv_handler import CSVDataSource
                data_source = CSVDataSource("./data")
        
        container.register_instance("data_source", data_source)
        
        # Create data handler
        data_handler = HistoricalDataHandler(data_source, bar_emitter)
        container.register_instance("data_handler", data_handler)
        
        logger.info(f"Data components initialized with source type: {source_type}")
    
    def _setup_execution_components(self, container, config):
        """Set up execution components."""
        from src.execution.order_manager import OrderManager
        from src.execution.broker.broker_simulator import SimulatedBroker
        from src.execution.backtest.backtest import BacktestCoordinator
        
        # Get event bus and order registry
        event_bus = container.get("event_bus")
        order_registry = container.get("order_registry")
        
        # Create order manager with registry
        order_manager = OrderManager(event_bus, None, order_registry)
        container.register_instance("order_manager", order_manager)
        
        # Create broker with registry
        broker = SimulatedBroker(event_bus, order_registry)
        broker_config = config.get_section("broker")
        broker.slippage = broker_config.get_float("slippage", 0.0)
        broker.commission = broker_config.get_float("commission", 0.0)
        container.register_instance("broker", broker)
        
        # Connect order manager to broker
        order_manager.broker = broker
        
        # Create backtest coordinator
        backtest = BacktestCoordinator(container, config)
        container.register_instance("backtest", backtest)
        
        logger.info("Execution components initialized with order registry")
    
    def _setup_risk_components(self, container, config):
        """Set up risk management components."""
        from src.risk.portfolio.portfolio import PortfolioManager
        from src.risk.managers.simple import SimpleRiskManager
        
        # Get event bus
        event_bus = container.get("event_bus")
        
        # Create portfolio
        portfolio_config = config.get_section("portfolio")
        initial_cash = portfolio_config.get_float("initial_cash", 100000.0)
        
        portfolio = PortfolioManager(event_bus, initial_cash=initial_cash)
        container.register_instance("portfolio", portfolio)
        
        # Create risk manager
        risk_config = config.get_section("risk_manager")
        risk_manager = SimpleRiskManager(event_bus, portfolio)
        risk_manager.position_size = risk_config.get_int("position_size", 100)
        risk_manager.max_position_pct = risk_config.get_float("max_position_pct", 0.1)
        
        # Log risk manager config
        logger.info(f"Risk manager configured with position_size={risk_manager.position_size}, max_position_pct={risk_manager.max_position_pct}")
        
        container.register_instance("risk_manager", risk_manager)
        
        logger.info("Risk components initialized")
    
    def _setup_strategy_components(self, container, config):
        """Set up strategy components with improved discovery."""
        # Set up strategy registry
        strategy_registry = Registry()
        self.registries["strategies"] = strategy_registry
        
        # Discover strategies with detailed logging
        try:
            from src.strategy.strategy_base import Strategy
            
            logger.info("Discovering strategy implementations...")
            discovered = discover_components(
                package_name="src.strategy.implementations",
                base_class=Strategy,
                registry=strategy_registry,
                config=config
            )
            
            if discovered:
                logger.info(f"Discovered strategies: {', '.join(discovered.keys())}")
            else:
                logger.warning("No strategies discovered! Check implementations directory and class definitions.")
        except Exception as e:
            logger.error(f"Error during strategy discovery: {e}", exc_info=True)
            discovered = {}
        
        # Create strategy based on config
        strategy_name = config.get_section("backtest").get("strategy", "ma_crossover")
        logger.info(f"Requested strategy: {strategy_name}")
        
        # Log available strategies in registry
        logger.info(f"Available strategies in registry: {strategy_registry.list()}")
        
        # Get strategy class
        strategy_class = strategy_registry.get(strategy_name)
        
        if strategy_class:
            try:
                # Get dependencies
                event_bus = container.get("event_bus")
                data_handler = container.get("data_handler")
                
                # Create strategy instance
                strategy = strategy_class(event_bus, data_handler)
                
                # Configure strategy
                strategy_config = config.get_section("strategies").get_section(strategy_name)
                strategy.configure(strategy_config)
                
                container.register_instance("strategy", strategy)
                logger.info(f"Strategy '{strategy_name}' initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing strategy '{strategy_name}': {e}", exc_info=True)
                # Fall back to a placeholder strategy or default implementation if needed
        else:
            logger.error(f"Strategy '{strategy_name}' not found in registry. Available strategies: {strategy_registry.list()}")
    
    def _setup_analytics_components(self, container, config):
        """Set up analytics components."""
        from src.analytics.performance.calculator import PerformanceCalculator
        from src.analytics.reporting.report_generator import ReportGenerator
        
        # Create performance calculator
        calculator = PerformanceCalculator()
        container.register_instance("calculator", calculator)
        
        # Create report generator
        report_generator = ReportGenerator(calculator)
        container.register_instance("report_generator", report_generator)
        
        logger.info("Analytics components initialized")
        
    def _setup_logging(self):
        """Configure logging system with console and file handlers."""
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
            
        # Configure specific loggers
        logging.getLogger("matplotlib").setLevel(logging.WARNING)  # Reduce matplotlib noise
        logging.getLogger("urllib3").setLevel(logging.WARNING)    # Reduce urllib3 noise
        
        logger.info(f"Logging initialized at level {logging.getLevelName(root_logger.level)}")
        logger.info(f"Log file: {self.log_file}")
        
        # Return the root logger for convenience
        return root_logger
