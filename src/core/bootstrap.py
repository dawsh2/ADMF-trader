# src/core/bootstrap.py

import os
import logging
import importlib
from typing import Dict, Any, List, Optional, Type, Tuple

from core.config.config import Config
from core.di.container import Container
from core.utils.discovery import discover_components

logger = logging.getLogger(__name__)

class BootstrapError(Exception):
    """Base exception for bootstrap errors."""
    pass

class ComponentError(BootstrapError):
    """Error during component initialization."""
    
    def __init__(self, component_name, original_error):
        self.component_name = component_name
        self.original_error = original_error
        super().__init__(f"Error initializing component '{component_name}': {original_error}")

class ConfigurationError(BootstrapError):
    """Error in configuration."""
    pass

class ModuleError(BootstrapError):
    """Error loading a module."""
    
    def __init__(self, module_name, original_error):
        self.module_name = module_name
        self.original_error = original_error
        super().__init__(f"Error loading module '{module_name}': {original_error}")

class Bootstrap:
    """Bootstrap the application."""
    
    def __init__(self, config_files=None, env_prefix='TRADING_'):
        """
        Initialize bootstrap process.
        
        Args:
            config_files: List of configuration files to load
            env_prefix: Prefix for environment variables
        """
        self.config_files = config_files or []
        self.env_prefix = env_prefix
        self.container = None
        self.config = None
        self._registries = {}
    
    def setup(self):
        """
        Set up the application.
        
        Returns:
            Tuple of (container, config)
            
        Raises:
            BootstrapError: If bootstrap process fails
        """
        try:
            # Initialize configuration
            self.config = Config()
            
            # Register defaults
            self._register_default_configs(self.config)
            
            # Load configuration files
            for file in self.config_files:
                try:
                    self.config.load_file(file)
                    logger.info(f"Loaded configuration from {file}")
                except Exception as e:
                    raise ConfigurationError(f"Error loading config file '{file}': {e}")
            
            # Load environment variables
            try:
                self.config.load_env(prefix=self.env_prefix)
                logger.info(f"Loaded configuration from environment variables with prefix {self.env_prefix}")
            except Exception as e:
                raise ConfigurationError(f"Error loading environment variables: {e}")
            
            # Initialize container
            self.container = Container()
            
            # Register config in container
            self.container.register_instance('config', self.config)
            
            # Register registries
            self._initialize_registries()
            
            # Register core components
            try:
                self._register_core_components()
            except Exception as e:
                logger.error(f"Error registering core components: {e}", exc_info=True)
                raise ComponentError("core", e)
            
            # Register module components
            try:
                self._register_modules()
            except ComponentError as e:
                # Re-raise component errors
                logger.error(f"Component error during bootstrap: {e}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Error registering modules: {e}", exc_info=True)
                raise BootstrapError(f"Error registering modules: {e}")
            
            logger.info("Bootstrap completed successfully")
            return self.container, self.config
        except Exception as e:
            logger.error(f"Bootstrap error: {e}", exc_info=True)
            # Re-raise to propagate the error
            raise
    
    def _register_default_configs(self, config):
        """Register default configurations."""
        config.register_defaults('core', {
            'log_level': 'INFO',
        })
        
        config.register_defaults('data', {
            'data_dir': './data',
            'date_format': '%Y-%m-%d',
            'source': 'csv'
        })
        
        config.register_defaults('strategies', {
            'enabled': True,
        })
        
        config.register_defaults('execution', {
            'broker': 'simulated',
            'slippage': 0.0,
            'commission': 0.0
        })
        
        config.register_defaults('risk', {
            'max_position_size': 100,
            'max_drawdown': 0.1,
            'max_exposure': 1.0
        })
    
    def _initialize_registries(self):
        """Initialize component registries."""
        # Import Registry class
        from core.utils.registry import Registry
        
        # Create registries for each module
        modules = ['data_sources', 'data_handlers', 'transformers', 
                  'strategies', 'indicators', 'risk_managers', 'brokers']
        
        for module in modules:
            registry_name = f"{module}_registry"
            self._registries[module] = Registry()
            self.container.register_instance(registry_name, self._registries[module])
            logger.debug(f"Initialized registry: {registry_name}")
    
    def _register_core_components(self):
        """Register core components."""
        # Register event bus
        try:
            from core.events.event_bus import EventBus
            self.container.register('event_bus', EventBus)
            logger.info("Registered event bus")
        except Exception as e:
            logger.error(f"Error registering event bus: {e}", exc_info=True)
            raise ComponentError("event_bus", e)
        
        # Register event manager
        try:
            from core.events.event_manager import EventManager
            self.container.register('event_manager', EventManager, {'event_bus': 'event_bus'})
            logger.info("Registered event manager")
        except Exception as e:
            logger.error(f"Error registering event manager: {e}", exc_info=True)
            raise ComponentError("event_manager", e)
        
        # Register factories for each module
        self._register_factories()
    
    def _register_factories(self):
        """Register component factories."""
        try:
            # Register data factory
            from data.factory import ComponentFactory as DataFactory
            self.container.register('data_factory', DataFactory, 
                                  {'registry': 'data_sources_registry'})
            logger.info("Registered data factory")
            
            # Register other factories as needed
        except Exception as e:
            logger.error(f"Error registering factories: {e}", exc_info=True)
            raise ComponentError("factories", e)
    
    def _register_modules(self):
        """Register module components."""
        self._register_data_module()
        self._register_strategy_module()
        self._register_execution_module()
        self._register_analytics_module()
    
    def _register_data_module(self):
        """Register data components."""
        # Get data config
        data_config = self.config.get_section('data')
        data_dir = data_config.get('data_dir', './data')
        
        # Discover data sources
        try:
            from data.data_source_base import DataSourceBase
            
            data_sources = discover_components(
                'data.sources',
                DataSourceBase,
                self._registries['data_sources'],
                enabled_only=False,
                config=self.config
            )
            
            logger.info(f"Discovered {len(data_sources)} data sources: {', '.join(data_sources.keys())}")
            
            # Register default data source based on config
            source_type = data_config.get('source', 'csv')
            
            if source_type in data_sources:
                source_class = data_sources[source_type]
                self.container.register(
                    'data_source',
                    source_class,
                    {'data_dir': data_dir}
                )
                logger.info(f"Registered {source_type} data source with data_dir={data_dir}")
            else:
                # Fallback to explicit import if discovery failed
                if source_type == 'csv':
                    from data.sources.csv_handler import CSVDataSource
                    self.container.register(
                        'data_source',
                        CSVDataSource,
                        {'data_dir': data_dir}
                    )
                    logger.info(f"Registered CSV data source (fallback) with data_dir={data_dir}")
                else:
                    raise ComponentError("data_source", ValueError(f"Unknown data source type: {source_type}"))
            
            # Discover and register data transformers
            from data.transformers.transformer_base import TransformerBase
            
            transformers = discover_components(
                'data.transformers',
                TransformerBase,
                self._registries['transformers'],
                enabled_only=False,
                config=self.config
            )
            
            logger.info(f"Discovered {len(transformers)} data transformers: {', '.join(transformers.keys())}")
            
            # Register data handler
            from data.data_handler_base import DataHandlerBase
            
            data_handlers = discover_components(
                'data',
                DataHandlerBase,
                self._registries['data_handlers'],
                enabled_only=False,
                config=self.config
            )
            
            logger.info(f"Discovered {len(data_handlers)} data handlers: {', '.join(data_handlers.keys())}")
            
            # Register historical data handler
            handler_type = data_config.get('handler', 'historical')
            
            if handler_type in data_handlers:
                handler_class = data_handlers[handler_type]
                self.container.register(
                    'data_handler',
                    handler_class,
                    {'data_source': 'data_source', 'bar_emitter': 'event_bus'}
                )
                logger.info(f"Registered {handler_type} data handler")
            else:
                # Fallback to explicit import
                from data.historical_data_handler import HistoricalDataHandler
                self.container.register(
                    'data_handler',
                    HistoricalDataHandler,
                    {'data_source': 'data_source', 'bar_emitter': 'event_bus'}
                )
                logger.info("Registered historical data handler (fallback)")
                
        except Exception as e:
            logger.error(f"Error registering data module: {e}", exc_info=True)
            raise ComponentError("data_module", e)
    
    def _register_strategy_module(self):
        """Register strategy components."""
        # Check if strategies are enabled
        strategy_config = self.config.get_section('strategies')
        if not strategy_config.get('enabled', True):
            logger.info("Strategies disabled in config, skipping")
            return
        
        try:
            # Import base class
            from strategies.strategy_base import StrategyBase
            
            # Discover strategy components
            strategies = discover_components(
                'strategies',
                StrategyBase,
                self._registries['strategies'],
                enabled_only=False,
                config=self.config
            )
            
            logger.info(f"Discovered {len(strategies)} strategies: {', '.join(strategies.keys())}")
            
            # Register discovered strategies that are enabled
            strategy_items = {k: v for k, v in strategy_config.as_dict().items() 
                             if isinstance(v, dict) and k != 'enabled'}
            
            for name, config in strategy_items.items():
                try:
                    # Check if strategy is enabled
                    if not config.get('enabled', False):
                        logger.info(f"Strategy {name} is disabled in config, skipping")
                        continue
                    
                    # Get strategy class
                    if name in strategies:
                        strategy_class = strategies[name]
                    else:
                        # Try to load from class path
                        class_path = config.get('class')
                        if not class_path:
                            logger.warning(f"No class defined for strategy {name}, skipping")
                            continue
                            
                        module_path, class_name = class_path.rsplit('.', 1)
                        try:
                            module = importlib.import_module(module_path)
                            strategy_class = getattr(module, class_name)
                        except ImportError as e:
                            logger.error(f"Error importing strategy module {module_path}: {e}")
                            raise ModuleError(module_path, e)
                        except AttributeError as e:
                            logger.error(f"Strategy class {class_name} not found in module {module_path}: {e}")
                            raise ModuleError(module_path, e)
                    
                    # Register strategy
                    strategy_id = f"strategy_{name}"
                    self.container.register(
                        strategy_id,
                        strategy_class,
                        {'event_bus': 'event_bus', 'data_handler': 'data_handler'}
                    )
                    
                    # Configure strategy
                    strategy = self.container.get(strategy_id)
                    if hasattr(strategy, 'configure'):
                        params = config.get('parameters', {})
                        strategy.configure(params)
                    
                    logger.info(f"Registered and configured strategy: {name}")
                except Exception as e:
                    logger.error(f"Error registering strategy {name}: {e}", exc_info=True)
                    raise ComponentError(f"strategy_{name}", e)
                
        except Exception as e:
            logger.error(f"Error registering strategy module: {e}", exc_info=True)
            raise ComponentError("strategy_module", e)
    
    def _register_execution_module(self):
        """Register execution components."""
        # Implementation similar to strategy module
        execution_config = self.config.get_section('execution')
        broker_type = execution_config.get('broker', 'simulated')
        
        try:
            # Register broker
            if broker_type == 'simulated':
                from execution.broker.simulated_broker import SimulatedBroker
                self.container.register(
                    'broker',
                    SimulatedBroker,
                    {'event_bus': 'event_bus'}
                )
                
                # Configure broker
                broker = self.container.get('broker')
                if hasattr(broker, 'configure'):
                    broker.configure(execution_config)
                
                logger.info(f"Registered and configured simulated broker")
            # Add other broker types as needed
        except Exception as e:
            logger.error(f"Error registering execution module: {e}", exc_info=True)
            raise ComponentError("execution_module", e)
    
    def _register_analytics_module(self):
        """Register analytics components."""
        # Implementation similar to other modules
        try:
            # Register performance calculator
            from analytics.performance.calculator import PerformanceCalculator
            self.container.register('performance_calculator', PerformanceCalculator)
            logger.info("Registered performance calculator")
        except Exception as e:
            logger.error(f"Error registering analytics module: {e}", exc_info=True)
            raise ComponentError("analytics_module", e)
