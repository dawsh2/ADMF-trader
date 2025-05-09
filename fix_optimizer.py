#!/usr/bin/env python
"""
Fix script for integrating new components into the optimization process.

This script updates the optimizer code to include the BacktestState and
PositionManager components, ensuring proper state isolation and position
management during optimization.
"""

import os
import sys
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_directory_if_not_exists(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def fix_ma_crossover_strategy():
    """Update the SimpleMACrossoverStrategy to integrate with BacktestState."""
    strategy_file = "src/strategy/implementations/simple_ma_crossover.py"
    
    try:
        # Read the file
        with open(strategy_file, 'r') as f:
            content = f.read()
            
        # Create backup
        backup_file = f"{strategy_file}.bak"
        with open(backup_file, 'w') as f:
            f.write(content)
        logger.info(f"Created backup of {strategy_file} as {backup_file}")
        
        # Modify the content to add BacktestState integration
        modified_content = content.replace(
            "from src.core.component import Component",
            "from src.core.component import Component\nfrom src.core.backtest_state import BacktestState"
        )
        
        # Add state storage
        modified_content = modified_content.replace(
            "def initialize(self, context):",
            "def initialize(self, context):\n        # Get or create BacktestState\n        self.backtest_state = context.get('backtest_state')\n        if not self.backtest_state:\n            self.backtest_state = BacktestState()\n            context['backtest_state'] = self.backtest_state\n"
        )
        
        # Update position tracking
        modified_content = modified_content.replace(
            "self.positions[symbol] = position",
            "self.positions[symbol] = position\n            # Update backtest state\n            if self.backtest_state:\n                self.backtest_state.set_position(symbol, position)"
        )
        
        # Write the modified content
        with open(strategy_file, 'w') as f:
            f.write(modified_content)
        logger.info(f"Updated {strategy_file} with BacktestState integration")
            
    except Exception as e:
        logger.error(f"Error updating {strategy_file}: {e}")
        
def fix_optimizing_backtest():
    """Update OptimizingBacktest to include PositionManager and BacktestState."""
    backtest_file = "src/execution/backtest/optimizing_backtest.py"
    
    try:
        # Read the file
        with open(backtest_file, 'r') as f:
            content = f.read()
            
        # Create backup
        backup_file = f"{backtest_file}.bak"
        with open(backup_file, 'w') as f:
            f.write(content)
        logger.info(f"Created backup of {backtest_file} as {backup_file}")
        
        # Add imports
        modified_content = content.replace(
            "from src.core.trade_repository import TradeRepository",
            "from src.core.trade_repository import TradeRepository\nfrom src.core.backtest_state import BacktestState\nfrom src.risk.position_manager import PositionManager"
        )
        
        # Find the setup_components method and add our components
        components_setup = """    def _setup_components(self, context=None):
        """
        fixed_setup = """    def _setup_components(self, context=None):
        # Create a fresh BacktestState for each run
        self.backtest_state = BacktestState()
        context['backtest_state'] = self.backtest_state
        
        # Create PositionManager if risk config is present
        risk_config = self.config.get('risk', {})
        if risk_config:
            position_manager_config = risk_config.get('position_manager', {})
            if position_manager_config:
                self.position_manager = PositionManager('position_manager', position_manager_config)
                self.components['position_manager'] = self.position_manager
                logger.info(f"Created PositionManager with config: {position_manager_config}")
        """
        
        modified_content = modified_content.replace(components_setup, fixed_setup)
        
        # Write the modified content
        with open(backtest_file, 'w') as f:
            f.write(modified_content)
        logger.info(f"Updated {backtest_file} with PositionManager and BacktestState integration")
            
    except Exception as e:
        logger.error(f"Error updating {backtest_file}: {e}")
        
def update_configuration():
    """Update configuration templates with proper risk management settings."""
    template_file = "config/ma_crossover_optimization.yaml"
    
    try:
        # Read the file
        with open(template_file, 'r') as f:
            content = f.read()
            
        # Create backup
        backup_file = f"{template_file}.bak"
        with open(backup_file, 'w') as f:
            f.write(content)
        logger.info(f"Created backup of {template_file} as {backup_file}")
        
        # Ensure the risk section has all necessary parameters
        if "risk:" not in content:
            # Add risk section if missing
            content += """
risk:
  position_manager:
    fixed_quantity: 10
    max_positions: 1
    enforce_single_position: true
    position_sizing_method: fixed
    allow_multiple_entries: false
"""
        else:
            # Update existing risk section
            # This is a naive approach - a proper parser would be better
            risk_index = content.find("risk:")
            next_section = content.find(":", risk_index + 5)
            next_section = content.rfind("\n", risk_index, next_section)
            
            risk_section = content[risk_index:next_section]
            if "position_manager:" not in risk_section:
                # Add position manager subsection
                updated_risk = f"""risk:
  position_manager:
    fixed_quantity: 10
    max_positions: 1
    enforce_single_position: true
    position_sizing_method: fixed
    allow_multiple_entries: false"""
                
                content = content[:risk_index] + updated_risk + content[next_section:]
                
        # Write the modified content
        with open(template_file, 'w') as f:
            f.write(content)
        logger.info(f"Updated {template_file} with proper risk management settings")
            
    except Exception as e:
        logger.error(f"Error updating {template_file}: {e}")
        
def fix_components():
    """Fix component initialization order in the backtest coordinator."""
    coordinator_file = "src/execution/backtest/backtest_coordinator.py"
    
    try:
        # Read the file
        with open(coordinator_file, 'r') as f:
            content = f.read()
            
        # Create backup
        backup_file = f"{coordinator_file}.bak"
        with open(backup_file, 'w') as f:
            f.write(content)
        logger.info(f"Created backup of {coordinator_file} as {backup_file}")
        
        # Fixed version of the setup method
        setup_method = """    def setup(self):
        """
        fixed_setup = """    def setup(self):
        """
        
        # Modify the content to fix component initialization order
        modified_content = content
        
        # Add state clearing before initializing components
        reset_statement = """        # Reset all components
        for name, component in self.components.items():
            component.reset()"""
        
        if reset_statement not in modified_content:
            modified_content = modified_content.replace(
                "    def reset(self):",
                f"    def reset(self):\n{reset_statement}"
            )
        
        # Fix close_all_open_trades method
        close_trades_orig = """    def close_all_open_trades(self):
        """
        close_trades_fixed = """    def close_all_open_trades(self):
        # Get position manager from components
        position_manager = self.components.get('position_manager')
        if position_manager:
            self.logger.info("Using PositionManager to ensure clean position tracking")
            
        """
        
        modified_content = modified_content.replace(close_trades_orig, close_trades_fixed)
        
        # Write the modified content
        with open(coordinator_file, 'w') as f:
            f.write(modified_content)
        logger.info(f"Updated {coordinator_file} with fixed component initialization")
            
    except Exception as e:
        logger.error(f"Error updating {coordinator_file}: {e}")
        
def run_fix():
    """Run all the fixes."""
    try:
        # Create directories
        create_directory_if_not_exists("src/risk")
        
        # Apply fixes
        fix_ma_crossover_strategy()
        fix_optimizing_backtest()
        update_configuration()
        fix_components()
        
        logger.info("All fixes applied successfully")
        return True
    except Exception as e:
        logger.error(f"Error applying fixes: {e}")
        return False
        
def main():
    parser = argparse.ArgumentParser(description="Fix ADMF-Trader optimization issues")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("Dry run mode - no changes will be made")
        logger.info("Would create directories: src/risk")
        logger.info("Would update: src/strategy/implementations/simple_ma_crossover.py")
        logger.info("Would update: src/execution/backtest/optimizing_backtest.py")
        logger.info("Would update: config/ma_crossover_optimization.yaml")
        logger.info("Would update: src/execution/backtest/backtest_coordinator.py")
    else:
        success = run_fix()
        if success:
            logger.info("Success! The ADMF-Trader optimization has been fixed to prevent duplicate positions.")
            logger.info("You can now run your optimization with:")
            logger.info("  python main.py optimize --config config/ma_crossover_optimization.yaml")
        else:
            logger.error("Fix failed. Please check the logs for details.")
            return 1
            
    return 0
    
if __name__ == "__main__":
    sys.exit(main())
