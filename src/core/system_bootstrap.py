"""
Bootstrap class for setting up the entire system.
"""
import logging
import importlib.util
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
        
        # Set up execution components
        self._setup_execution_components(container, config)
        
        # Set up risk components
        self._setup_risk_components(container, config)
        
        # Set up strategy components
        self._setup_strategy_components(container, config)
        
        # Set up analytics components
        self._setup_analytics_components(container, config)
        
        # Register components with event system in optimal order
        self._register_components_with_event_manager(container)
        
        logger.info("System bootstrap complete")
        return container, config
    
    def _setup_event_system(self, container, config):
        """Set up the event system components."""
        # Create the event bus - already has native deduplication
        event_bus = EventBus()
        event_manager = EventManager(event_bus)
        
        container.register_instance("event_bus", event_bus)
        container.register_instance("event_manager", event_manager)
        
        logger.info("Event system initialized with native deduplication")
    
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
    
    def _check_module_exists(self, module_path):
        """
        Check if a module exists without importing it.
        
        Args:
            module_path: Full path to the module
            
        Returns:
            bool: True if module exists, False otherwise
        """
        try:
            spec = importlib.util.find_spec(module_path)
            return spec is not None
        except ModuleNotFoundError:
            return False
    
    def _setup_execution_components(self, container, config):
        """Set up execution components."""
        from src.execution.order_manager import OrderManager
        from src.execution.broker.broker_simulator import SimulatedBroker
        from src.execution.backtest.backtest import BacktestCoordinator
        
        # Check risk manager type early to determine if we need signal interpreter
        risk_config = config.get_section("risk_manager")
        risk_manager_type = risk_config.get("type", "simple").lower() if risk_config else "simple"
        
        signal_interpreter_module_exists = self._check_module_exists("src.execution.signal_interpreter.standard_interpreter")
        
        # Get event bus
        event_bus = container.get("event_bus")
        
        # Create broker
        broker = SimulatedBroker(event_bus)
        broker_config = config.get_section("broker")
        broker.slippage = broker_config.get_float("slippage", 0.0)
        broker.commission = broker_config.get_float("commission", 0.0)
        container.register_instance("broker", broker)
        
        # Create order manager
        order_manager = OrderManager(event_bus, broker)
        container.register_instance("order_manager", order_manager)
        
        # Create signal interpreter placeholder - will be properly configured after portfolio and risk manager
        container.register_instance("signal_interpreter", None)
        
        # Create backtest coordinator
        backtest = BacktestCoordinator(container, config)
        container.register_instance("backtest", backtest)
        
        logger.info("Execution components initialized")
    
    def _setup_risk_components(self, container, config):
        """Set up risk management components."""
        from src.risk.portfolio.portfolio import PortfolioManager
        from src.risk.managers.simple import SimpleRiskManager
        from src.risk.managers.enhanced_risk_manager import EnhancedRiskManager
        
        # Check if signal interpreter module exists
        signal_interpreter_module_exists = self._check_module_exists("src.execution.signal_interpreter.standard_interpreter")
        
        # Get event bus
        event_bus = container.get("event_bus")
        order_manager = container.get("order_manager")
        
        # Create portfolio
        portfolio_config = config.get_section("portfolio")
        initial_cash = portfolio_config.get_float("initial_cash", 100000.0)
        
        portfolio = PortfolioManager(event_bus, initial_cash=initial_cash)
        container.register_instance("portfolio", portfolio)
        
        # Check for risk manager type in config
        risk_config = config.get_section("risk_manager")
        risk_manager_type = risk_config.get("type", "simple").lower()
        
        # Select appropriate risk manager based on type
        if risk_manager_type == "enhanced":
            logger.info("Using Enhanced Risk Manager (refactored architecture)")
            risk_manager = EnhancedRiskManager(event_bus, portfolio)
            
            # Configure the enhanced risk manager
            risk_manager.position_sizing_method = risk_config.get("position_sizing_method", "fixed")
            risk_manager.position_size = risk_config.get_int("position_size", 100)
            risk_manager.max_position_size = risk_config.get_int("max_position_size", 1000)
            risk_manager.equity_percent = risk_config.get_float("equity_percent", 5.0)
            risk_manager.risk_percent = risk_config.get_float("risk_percent", 2.0)
            
            # Log configuration
            logger.info(f"Enhanced risk manager configured with position_sizing_method={risk_manager.position_sizing_method}, "
                      f"position_size={risk_manager.position_size}, max_position_size={risk_manager.max_position_size}")
        else:
            # Use standard risk manager
            logger.info("Using standard Simple Risk Manager")
            risk_manager = SimpleRiskManager(event_bus, portfolio)
            risk_manager.position_size = risk_config.get_int("position_size", 100)
            risk_manager.max_position_pct = risk_config.get_float("max_position_pct", 0.1)
            
            # Log configuration
            logger.info(f"Simple risk manager configured with position_size={risk_manager.position_size}, "
                      f"max_position_pct={risk_manager.max_position_pct}")
        
        # Set order manager reference in risk manager if needed
        if hasattr(risk_manager, 'order_manager'):
            risk_manager.order_manager = order_manager
            
        container.register_instance("risk_manager", risk_manager)
        
        # Signal interpreter is only needed for the simple risk manager approach
        # With the enhanced risk manager, we handle signals directly
        if risk_manager_type != "enhanced" and signal_interpreter_module_exists:
            # Dynamically import the signal interpreter to avoid import errors
            try:
                import importlib
                StandardSignalInterpreter = importlib.import_module(
                    "src.execution.signal_interpreter.standard_interpreter"
                ).StandardSignalInterpreter
                
                signal_interpreter = StandardSignalInterpreter(
                    event_bus, 
                    portfolio,
                    risk_manager,
                    order_manager,
                    name="standard_interpreter",
                    parameters={
                        "position_size": risk_config.get_int("position_size", 100),
                        "max_position_pct": risk_config.get_float("max_position_pct", 0.1)
                    }
                )
                # Replace placeholder with actual interpreter
                container.register_instance("signal_interpreter", signal_interpreter)
                logger.info("Standard Signal Interpreter initialized")
            except ImportError as e:
                logger.warning(f"Could not initialize signal interpreter: {e}")
                # Keep the None placeholder
        else:
            # No signal interpreter needed with enhanced risk manager
            logger.info("No signal interpreter needed with enhanced risk manager")
            container.register_instance("signal_interpreter", None)
        
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
                
                # Get symbols from backtest configuration and add to strategy config
                backtest_config = config.get_section("backtest")
                symbols = backtest_config.get("symbols", [])
                
                # Create a merged config with symbols from backtest section
                if hasattr(strategy_config, "as_dict"):
                    merged_config = strategy_config.as_dict()
                else:
                    merged_config = dict(strategy_config)
                    
                # Add symbols if not already in strategy config
                if "symbols" not in merged_config and symbols:
                    merged_config["symbols"] = symbols
                    logger.debug(f"Added symbols from backtest config: {symbols}")
                    
                # Configure strategy with merged config
                strategy.configure(merged_config)
                
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
        
    def _register_components_with_event_manager(self, container):
        """Register components with event manager with correct priorities for proper event flow."""
        event_manager = container.get('event_manager')
        if not event_manager:
            logger.warning("No event manager available for component registration")
            return
        
        # Import event types
        from src.core.events.event_types import EventType
        
        # Register components in specific order to ensure proper event flow
        # The registration order is CRITICAL for event propagation
        
        # 1. Data handler (emits bars)
        data_handler = container.get('data_handler')
        if data_handler:
            event_manager.register_component('data_handler', data_handler, [EventType.BAR])
        
        # 2. Strategy (processes bars and emits signals)
        strategy = container.get('strategy')
        if strategy:
            event_manager.register_component('strategy', strategy, [EventType.BAR])
        
        # Get risk manager type to determine component registration
        risk_manager = container.get('risk_manager')
        risk_config = container.get('config').get_section("risk_manager")
        risk_manager_type = risk_config.get("type", "simple").lower() if risk_config else "simple"
        
        # 3. Register components based on risk manager type
        if risk_manager_type == "enhanced":
            # With enhanced risk manager, signals go directly to risk manager
            if risk_manager:
                event_manager.register_component('risk_manager', risk_manager, [EventType.SIGNAL])
                # Also unregister and re-register with event bus directly to ensure proper priority
                event_bus = container.get('event_bus')
                if event_bus:
                    # Unregister existing handler to avoid duplicates
                    event_bus.unregister(EventType.SIGNAL, risk_manager.on_signal)
                    # Re-register with high priority
                    event_bus.register(EventType.SIGNAL, risk_manager.on_signal, priority=100)
                    logger.info("Registered enhanced risk manager with high signal priority")
        else:
            # 3a. With standard risk manager, use signal interpreter
            signal_interpreter = container.get('signal_interpreter')
            if signal_interpreter:
                event_manager.register_component('signal_interpreter', signal_interpreter, [EventType.SIGNAL])
            
            # 3b. Standard risk manager processes interpreted signals
            if risk_manager and not signal_interpreter:
                event_manager.register_component('risk_manager', risk_manager, [EventType.SIGNAL])
        
        # 4. Order manager (processes orders and forwards to broker)
        order_manager = container.get('order_manager')
        if order_manager:
            event_manager.register_component('order_manager', order_manager, [EventType.ORDER])
        
        # 5. Broker (processes orders and emits fills)
        broker = container.get('broker')
        if broker:
            event_manager.register_component('broker', broker, [EventType.ORDER])
        
        # 6. Portfolio (processes fills)
        portfolio = container.get('portfolio')
        if portfolio:
            event_manager.register_component('portfolio', portfolio, [EventType.FILL, EventType.BAR])
        
        logger.info("All components registered with event manager in optimal order")
        
        # Also directly register event handlers for critical components with priority
        event_bus = container.get('event_bus')
        if event_bus and portfolio:
            # Unregister existing handler to avoid duplicates
            event_bus.unregister(EventType.FILL, portfolio.on_fill)
            
            # Re-register with higher priority to ensure it's called before other handlers
            event_bus.register(EventType.FILL, portfolio.on_fill, priority=200)
            logger.info("Re-registered portfolio fill handler with high priority")
        
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
