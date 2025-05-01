#!/usr/bin/env python3
"""
Verify MA Crossover Signal Grouping Fixes

This script verifies that all three fixes have been applied correctly:
1. Rule ID Format in MA Crossover Strategy
2. Risk Manager Reset
3. BacktestCoordinator Run
"""
import logging
import sys
import importlib
import inspect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("verify_fixes.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def verify_ma_crossover_rule_id():
    """Verify MA Crossover rule_id format fix."""
    try:
        from src.strategy.implementations.ma_crossover import MACrossoverStrategy
        
        # Create test instance
        test_strategy = MACrossoverStrategy(None, None)
        
        # Check on_bar method source code
        on_bar_source = inspect.getsource(MACrossoverStrategy.on_bar)
        
        # Check for key parts of the fix
        has_direction_name = "direction_name" in on_bar_source
        has_correct_format = "rule_id = f\"{self.name}_{symbol}_{direction_name}_group_{group_id}\"" in on_bar_source
        
        logger.info(f"Rule ID format fix verification:")
        logger.info(f"Has direction_name: {has_direction_name}")
        logger.info(f"Has correct format: {has_correct_format}")
        
        return has_direction_name and has_correct_format
    except Exception as e:
        logger.error(f"Error verifying MA Crossover rule_id fix: {e}", exc_info=True)
        return False

def verify_risk_manager_reset():
    """Verify Risk Manager reset fix."""
    try:
        from src.risk.managers.simple import SimpleRiskManager
        
        # Create test instance
        test_risk_manager = SimpleRiskManager(None, None)
        
        # Check reset method source code
        reset_source = inspect.getsource(SimpleRiskManager.reset)
        
        # Check for key parts of the fix
        has_clearing_log = "CLEARING" in reset_source
        has_rule_id_clear = "self.processed_rule_ids.clear()" in reset_source
        
        logger.info(f"Risk Manager reset fix verification:")
        logger.info(f"Has clearing log: {has_clearing_log}")
        logger.info(f"Has rule_id clear: {has_rule_id_clear}")
        
        return has_clearing_log and has_rule_id_clear
    except Exception as e:
        logger.error(f"Error verifying Risk Manager reset fix: {e}", exc_info=True)
        return False

def verify_backtest_coordinator_run():
    """Verify BacktestCoordinator run fix."""
    try:
        from src.execution.backtest.backtest import BacktestCoordinator
        
        # Check run method source code
        run_source = inspect.getsource(BacktestCoordinator.run)
        
        # Check for key parts of the fix
        has_explicit_reset = "Explicitly resetting event bus before run" in run_source
        has_reset_call = "self.event_bus.reset()" in run_source
        
        logger.info(f"BacktestCoordinator run fix verification:")
        logger.info(f"Has explicit reset log: {has_explicit_reset}")
        logger.info(f"Has reset call: {has_reset_call}")
        
        return has_explicit_reset and has_reset_call
    except Exception as e:
        logger.error(f"Error verifying BacktestCoordinator run fix: {e}", exc_info=True)
        return False

def main():
    """Main verification function."""
    logger.info("=" * 60)
    logger.info("VERIFYING MA CROSSOVER SIGNAL GROUPING FIXES")
    logger.info("=" * 60)
    
    # Verify all fixes
    ma_crossover_fixed = verify_ma_crossover_rule_id()
    risk_manager_fixed = verify_risk_manager_reset()
    backtest_coordinator_fixed = verify_backtest_coordinator_run()
    
    # Print summary
    logger.info("=" * 60)
    logger.info("VERIFICATION SUMMARY:")
    logger.info(f"MA Crossover rule_id format: {'FIXED' if ma_crossover_fixed else 'NOT FIXED'}")
    logger.info(f"Risk Manager reset: {'FIXED' if risk_manager_fixed else 'NOT FIXED'}")
    logger.info(f"BacktestCoordinator run: {'FIXED' if backtest_coordinator_fixed else 'NOT FIXED'}")
    logger.info("=" * 60)
    
    # Overall status
    all_fixed = ma_crossover_fixed and risk_manager_fixed and backtest_coordinator_fixed
    if all_fixed:
        logger.info("ALL FIXES VERIFIED SUCCESSFULLY!")
        logger.info("The fixes should reduce trades from 54 to the expected 18.")
    else:
        logger.warning("ONE OR MORE FIXES COULD NOT BE VERIFIED!")
        logger.warning("Further investigation needed.")
    
    return 0 if all_fixed else 1

if __name__ == "__main__":
    sys.exit(main())
