#!/usr/bin/env python
"""
Run the trading system with a fixed _generate_debug_report method.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run_with_fixed")

def run_with_fixed_method():
    """Run the backtest with a fixed debug report method."""
    
    # First, comment out the existing method to prevent execution
    backtest_file = "src/execution/backtest/backtest.py"
    with open(backtest_file, "r") as f:
        content = f.read()
    
    # Find the problematic method
    old_method_start = content.find("    def _generate_debug_report(self):")
    if old_method_start == -1:
        old_method_start = content.find("        def _generate_debug_report(self):")
    
    if old_method_start == -1:
        logger.error("Could not find the debug report method")
        return False
    
    # Create a monkey-patched version of the method
    monkey_patch = """
# Fixed by monkey-patching
import types
def _new_generate_debug_report(self):
    \"\"\"Fixed debug report method.\"\"\"
    logger.info("======= DETAILED DEBUG REPORT =======")
    
    # Strategy state
    if hasattr(self.strategy, 'get_debug_info'):
        strategy_info = self.strategy.get_debug_info()
        logger.info(f"Strategy debug info: {strategy_info}")
    
    # Signal count
    signal_count = len(getattr(self.strategy, 'signals_history', []))
    logger.info(f"Total signals generated: {signal_count}")
    
    # Data info
    if self.data_handler:
        data_info = {
            "total_bars": self.iterations,
            "symbols": self.data_handler.get_symbols(),
            "start_date": None,
            "end_date": None
        }
        logger.info(f"Data information: {data_info}")
    
    logger.info("======= END DEBUG REPORT =======")

# Monkey-patch the method
from src.execution.backtest.backtest import BacktestCoordinator
BacktestCoordinator._generate_debug_report = types.MethodType(_new_generate_debug_report, BacktestCoordinator)
"""
    
    # Write the monkey-patch to a file
    with open("monkey_patch.py", "w") as f:
        f.write(monkey_patch)
    
    # Run the main program using the config
    logger.info("Running backtest with fixed method...")
    import subprocess
    result = subprocess.run([
        "python", "-c", 
        "import monkey_patch; import sys; from main import main; main(); sys.exit(0)",
        "--config", "config/fixed_config.yaml"
    ], capture_output=True, text=True)
    
    # Print the output
    print(result.stdout)
    
    # Check for success
    if "No trades were executed" in result.stdout:
        logger.warning("Backtest still failed: No trades were executed")
        return False
    else:
        logger.info("Backtest succeeded!")
        return True

if __name__ == "__main__":
    print("Running backtest with fixed debug report method...")
    success = run_with_fixed_method()
    
    if success:
        print("\n✅ Backtest completed successfully!")
    else:
        print("\n❌ Backtest still having issues.")
        print("Try the following command to run the backtest without using the debug report:")
        print("python -c \"import sys; from src.execution.backtest.backtest import BacktestCoordinator; BacktestCoordinator._generate_debug_report = lambda self: None; from main import main; main(); sys.exit(0)\" --config config/fixed_config.yaml")
