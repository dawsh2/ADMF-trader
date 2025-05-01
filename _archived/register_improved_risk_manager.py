#!/usr/bin/env python3
"""
Script to register the improved risk manager with the system.
Run this script before running the improved configuration.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

def register_risk_manager():
    """Register the improved risk manager with the system."""
    try:
        # Check if the file exists
        risk_manager_file = 'src/risk/managers/enhanced_risk_manager_improved.py'
        if not os.path.exists(risk_manager_file):
            logger.error(f"Risk manager file not found: {risk_manager_file}")
            return False
            
        # Import necessary modules
        sys.path.append('.')  # Add current directory to path
        
        from src.core.utils.discovery import register_component
        
        # Register the improved risk manager
        register_component('enhanced_improved', 'src.risk.managers.enhanced_risk_manager_improved', 'EnhancedRiskManager')
        logger.info("Successfully registered enhanced_improved risk manager")
        
        # Verify registration
        from src.core.utils.discovery import get_registered_components
        components = get_registered_components()
        if 'enhanced_improved' in components:
            logger.info("Verified registration of enhanced_improved risk manager")
            return True
        else:
            logger.error("Failed to verify registration")
            return False
    
    except Exception as e:
        logger.error(f"Error registering risk manager: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the registration."""
    logger.info("Registering improved risk manager...")
    success = register_risk_manager()
    if success:
        logger.info("Registration complete. You can now run:")
        logger.info("python main.py --config config/improved_mini_test.yaml")
    else:
        logger.error("Registration failed.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
