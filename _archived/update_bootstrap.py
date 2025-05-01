#!/usr/bin/env python
"""
Update Bootstrap to Use Refactored Architecture

This script patches the system bootstrap to use our enhanced risk manager
when specified in the configuration.
"""
import logging
import sys
from src.core.system_bootstrap import Bootstrap
from src.risk.managers.enhanced_risk_manager import EnhancedRiskManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('update_bootstrap.log')
    ]
)

logger = logging.getLogger('update_bootstrap')

# Store original method reference
original_setup_risk = Bootstrap._setup_risk_components

# Create a patched method that can use our enhanced risk manager
def patched_setup_risk_components(self, container, config):
    """Patched version of risk component setup that supports the enhanced risk manager."""
    
    from src.risk.portfolio.portfolio import PortfolioManager
    from src.risk.managers.simple import SimpleRiskManager
    from src.execution.signal_interpreter.standard_interpreter import StandardSignalInterpreter
    
    # Get event bus
    event_bus = container.get("event_bus")
    order_manager = container.get("order_manager")
    
    # Create portfolio
    portfolio_config = config.get_section("portfolio")
    initial_cash = portfolio_config.get_float("initial_cash", 100000.0)
    
    portfolio = PortfolioManager(event_bus, initial_cash=initial_cash)
    container.register_instance("portfolio", portfolio)
    
    # Get risk manager type from config
    risk_config = config.get_section("risk_manager")
    risk_manager_type = risk_config.get("type", "simple").lower()
    
    # Create appropriate risk manager based on type
    if risk_manager_type == "enhanced":
        logger.info("Using Enhanced Risk Manager from refactored architecture")
        risk_manager = EnhancedRiskManager(event_bus, portfolio)
        
        # Configure the enhanced risk manager
        risk_manager.position_sizing_method = risk_config.get("position_sizing_method", "fixed")
        risk_manager.position_size = risk_config.get_int("position_size", 100)
        risk_manager.max_position_size = risk_config.get_int("max_position_size", 1000)
        risk_manager.equity_percent = risk_config.get_float("equity_percent", 5.0)
        risk_manager.risk_percent = risk_config.get_float("risk_percent", 2.0)
    else:
        # Use the original SimpleRiskManager as fallback
        logger.info("Using standard SimpleRiskManager")
        risk_manager = SimpleRiskManager(event_bus, portfolio)
        risk_manager.position_size = risk_config.get_int("position_size", 100)
        risk_manager.max_position_pct = risk_config.get_float("max_position_pct", 0.1)
    
    # Set order manager reference in risk manager
    if hasattr(risk_manager, 'order_manager'):
        risk_manager.order_manager = order_manager
    
    # Log risk manager config
    logger.info(f"Risk manager '{risk_manager_type}' configured: {risk_manager.__dict__}")
    container.register_instance("risk_manager", risk_manager)
    
    # Now create signal interpreter using portfolio and risk manager
    # Only use this if not using the enhanced risk manager
    if risk_manager_type != "enhanced":
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
        container.register_instance("signal_interpreter", signal_interpreter)
    else:
        # When using enhanced risk manager, we don't need the signal interpreter
        container.register_instance("signal_interpreter", None)
    
    logger.info("Risk components initialized with patched bootstrap")

def apply_patches():
    """Apply all patches to the system."""
    # Patch the bootstrap's risk component setup
    Bootstrap._setup_risk_components = patched_setup_risk_components
    
    logger.info("Applied patches to Bootstrap: Enhanced risk manager support enabled")
    
if __name__ == "__main__":
    # Apply the patches
    apply_patches()
    logger.info("Bootstrap patched with enhanced risk manager support")
    print("Done! Now run 'python main.py --config config/refactored_test.yaml'")
