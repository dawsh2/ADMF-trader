"""
Bootstrap module for setting up the improved event flow architecture.

This module provides functions to initialize the event system with proper
signal deduplication and processing order.
"""
import logging
from typing import Dict, Any, Optional

from src.core.events.event_bus import EventBus
from src.core.events.event_manager import EventManager
from src.core.events.signal_preprocessor import SignalPreprocessor
from src.core.events.direct_signal_processor import DirectSignalProcessor
from src.core.events.signal_management_service import SignalManagementService
from src.risk.managers.enhanced_risk_manager import EnhancedRiskManager
from src.risk.portfolio.portfolio import PortfolioManager

logger = logging.getLogger(__name__)

def create_event_system(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create and bootstrap the event system with improved signal deduplication.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Dictionary with initialized components
    """
    # Create core components
    event_bus = EventBus()
    event_manager = EventManager(event_bus)
    
    # Create portfolio manager
    portfolio_manager = PortfolioManager(event_bus)
    if config and 'portfolio' in config:
        portfolio_manager.configure(config['portfolio'])
    
    # Create enhanced risk manager
    risk_manager = EnhancedRiskManager(event_bus, portfolio_manager)
    if config and 'risk' in config:
        risk_manager.configure(config['risk'])
    
    # Create signal preprocessor and direct processor
    signal_preprocessor = SignalPreprocessor(event_bus)
    direct_processor = DirectSignalProcessor(event_bus, risk_manager, signal_preprocessor)
    
    # Create signal management service as the central signal processing component
    signal_service = SignalManagementService(event_bus, risk_manager, signal_preprocessor)
    
    # Register components with event manager
    event_manager.register_component('portfolio_manager', portfolio_manager)
    event_manager.register_component('risk_manager', risk_manager)
    event_manager.register_component('signal_service', signal_service)
    
    logger.info("Event system bootstrapped with improved signal deduplication")
    
    # Return all components
    return {
        'event_bus': event_bus,
        'event_manager': event_manager,
        'portfolio_manager': portfolio_manager,
        'risk_manager': risk_manager,
        'signal_preprocessor': signal_preprocessor,
        'direct_processor': direct_processor,
        'signal_service': signal_service
    }

def get_signal_service(components: Dict[str, Any]) -> Optional[SignalManagementService]:
    """
    Get the signal management service from components dictionary.
    
    Args:
        components: Components dictionary from create_event_system
        
    Returns:
        SignalManagementService or None if not found
    """
    return components.get('signal_service')

def submit_signal(components: Dict[str, Any], signal_data: Dict[str, Any]):
    """
    Submit a signal through the signal management service.
    
    Args:
        components: Components dictionary from create_event_system
        signal_data: Signal data dictionary
        
    Returns:
        Result from signal submission
    """
    signal_service = get_signal_service(components)
    if not signal_service:
        logger.error("Signal management service not found in components")
        return None
    
    return signal_service.submit_signal(signal_data)

def reset_event_system(components: Dict[str, Any]):
    """
    Reset the event system to initial state.
    
    Args:
        components: Components dictionary from create_event_system
    """
    for name, component in components.items():
        if hasattr(component, 'reset'):
            component.reset()
            logger.debug(f"Reset component: {name}")
    
    logger.info("Event system reset to initial state")
