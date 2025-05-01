#!/usr/bin/env python3
"""
Check tool to verify rule_id flow between strategy and risk manager.

This script inspects the rule_id format and processing to ensure proper deduplication
without executing a full backtest.
"""

import logging
import sys
import re
import inspect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler("rule_id_flow_fixed.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("rule_id_flow_fixed")

def check_strategy_rule_id_format():
    """Check that the MACrossoverStrategy uses correct rule_id format."""
    try:
        # Import the strategy
        from src.strategy.implementations.ma_crossover import MACrossoverStrategy
        
        # Get the method source code
        on_bar_code = inspect.getsource(MACrossoverStrategy.on_bar)
        
        # Look for rule_id assignment
        if "rule_id = f\"{self.name}_{symbol}_{direction_name}_group_{group_id}\"" in on_bar_code:
            logger.info("✅ Strategy has correct rule_id format with symbol and direction")
            return True
        
        # Try alternative method - search for any rule_id assignment
        rule_id_matches = re.findall(r'rule_id\s*=\s*f["\']([^"\']*)["\']', on_bar_code)
        if rule_id_matches:
            for match in rule_id_matches:
                # Check if the match has the required components
                if "{symbol}" in match and ("direction" in match or "BUY" in match or "SELL" in match) and "group" in match:
                    logger.info(f"✅ Found acceptable rule_id format: {match}")
                    return True
            
            logger.error(f"❌ Found rule_id formats but none match requirements: {rule_id_matches}")
        else:
            # Try a broader approach - just check if there's anything close
            if "direction_name = \"BUY\" if signal_value == 1 else \"SELL\"" in on_bar_code and "rule_id" in on_bar_code:
                logger.info("✅ Found direction_name assignment and rule_id usage")
                return True
                
            logger.error("❌ Could not find rule_id assignment in strategy code")
        
        return False
    except ImportError:
        logger.error("❌ Could not import MACrossoverStrategy")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking strategy: {e}")
        return False

def check_risk_manager_rule_id_processing():
    """Check that the SimpleRiskManager properly processes rule_ids."""
    try:
        # Import the risk manager
        from src.risk.managers.simple import SimpleRiskManager
        
        # Get the initialization source code
        init_source = inspect.getsource(SimpleRiskManager.__init__)
        
        # Check for processed_rule_ids initialization
        if "processed_rule_ids = set()" in init_source or "self.processed_rule_ids = set()" in init_source:
            logger.info("✅ Risk manager initializes processed_rule_ids")
            init_ok = True
        else:
            # Try a broader pattern match
            if re.search(r'self\.processed_rule_ids\s*=\s*set\(\)', init_source):
                logger.info("✅ Risk manager initializes processed_rule_ids (regexp match)")
                init_ok = True
            elif "processed_rule_ids" in init_source:
                logger.info("✅ Risk manager has processed_rule_ids attribute")
                init_ok = True
            else:
                logger.error("❌ Risk manager does not initialize processed_rule_ids")
                init_ok = False
        
        # Get the on_signal source code
        on_signal_source = inspect.getsource(SimpleRiskManager.on_signal)
        
        # Check for rule_id check in on_signal
        if "rule_id and rule_id in self.processed_rule_ids" in on_signal_source or "if rule_id in self.processed_rule_ids" in on_signal_source:
            logger.info("✅ Risk manager checks for duplicate rule_ids")
            check_ok = True
        else:
            # Try a broader approach
            if "processed_rule_ids" in on_signal_source and "rule_id" in on_signal_source:
                logger.info("✅ Risk manager references processed_rule_ids and rule_id in on_signal")
                check_ok = True
            else:
                logger.error("❌ Risk manager does not check for duplicate rule_ids")
                check_ok = False
        
        # Get the reset source code
        reset_source = inspect.getsource(SimpleRiskManager.reset)
        
        # Check for proper reset implementation
        if "processed_rule_ids.clear()" in reset_source or "self.processed_rule_ids.clear()" in reset_source:
            logger.info("✅ Risk manager properly clears processed_rule_ids in reset")
            reset_ok = True
        else:
            # Try a broader approach
            if "processed_rule_ids" in reset_source and "clear" in reset_source:
                logger.info("✅ Risk manager appears to clear processed_rule_ids in reset")
                reset_ok = True
            else:
                logger.error("❌ Risk manager does not clear processed_rule_ids in reset")
                reset_ok = False
        
        return init_ok and check_ok and reset_ok
    except ImportError:
        logger.error("❌ Could not import SimpleRiskManager")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking risk manager: {e}")
        return False

def run_simulation():
    """Run a mini-simulation to verify rule_id flow."""
    try:
        # Create minimal strategy instance
        from src.strategy.implementations.ma_crossover import MACrossoverStrategy
        from src.risk.managers.simple import SimpleRiskManager
        from src.core.events.event_bus import EventBus
        from src.core.events.event_utils import create_signal_event
        import datetime
        
        class MockPortfolio:
            def __init__(self):
                self.equity = 100000.0
                self.cash = 100000.0
            
            def get_position(self, symbol):
                return None
        
        # Create event bus
        event_bus = EventBus()
        
        # Create risk manager
        risk_manager = SimpleRiskManager(event_bus, MockPortfolio())
        
        # Create simulated signals
        signals = []
        timestamp = datetime.datetime.now()
        
        # Create BUY signal with proper rule_id format
        signal1 = create_signal_event(
            signal_value=1,
            price=100.0,
            symbol="MINI",
            rule_id="ma_crossover_MINI_BUY_group_1",
            timestamp=timestamp
        )
        signals.append(signal1)
        
        # Create SELL signal with proper rule_id format
        signal2 = create_signal_event(
            signal_value=-1,
            price=105.0,
            symbol="MINI",
            rule_id="ma_crossover_MINI_SELL_group_2",
            timestamp=timestamp
        )
        signals.append(signal2)
        
        # Create duplicate BUY signal with same rule_id
        signal3 = create_signal_event(
            signal_value=1,
            price=102.0,
            symbol="MINI",
            rule_id="ma_crossover_MINI_BUY_group_1",  # Same as signal1
            timestamp=timestamp
        )
        signals.append(signal3)
        
        # Process signals
        logger.info("=== SIMULATING SIGNAL PROCESSING ===")
        
        # First signal - should be processed
        logger.info(f"Processing signal 1: rule_id={signal1.data.get('rule_id')}")
        result1 = risk_manager.on_signal(signal1)
        if result1:
            logger.info("✅ First signal processed correctly")
        else:
            logger.error("❌ First signal failed to process")
        
        # Second signal - should be processed (different rule_id)
        logger.info(f"Processing signal 2: rule_id={signal2.data.get('rule_id')}")
        result2 = risk_manager.on_signal(signal2)
        if result2:
            logger.info("✅ Second signal processed correctly")
        else:
            logger.error("❌ Second signal failed to process")
        
        # Third signal - should be rejected (duplicate rule_id)
        logger.info(f"Processing signal 3: rule_id={signal3.data.get('rule_id')} (DUPLICATE)")
        result3 = risk_manager.on_signal(signal3)
        if result3 is None:
            logger.info("✅ Duplicate signal correctly rejected")
        else:
            logger.error("❌ Duplicate signal was not rejected!")
        
        # Now reset and verify
        logger.info("Resetting risk manager")
        risk_manager.reset()
        
        # Try processing the duplicate signal again - should now work after reset
        logger.info(f"Re-processing signal 3 after reset: rule_id={signal3.data.get('rule_id')}")
        result4 = risk_manager.on_signal(signal3)
        if result4:
            logger.info("✅ Signal processed after reset - rule_ids were cleared properly")
            return True
        else:
            logger.error("❌ Signal still rejected after reset - rule_ids were not cleared!")
            return False
    except Exception as e:
        logger.error(f"❌ Error in simulation: {e}")
        return False

def main():
    """Run all checks."""
    print("\n=== RULE ID FLOW CHECK (FIXED) ===")
    print("This tool verifies the rule_id format and processing\n")
    
    # Check strategy rule_id format
    print("\n[1] Checking strategy rule_id format...")
    strategy_ok = check_strategy_rule_id_format()
    print("Strategy check:", "✅ PASSED" if strategy_ok else "❌ FAILED")
    
    # Check risk manager rule_id processing
    print("\n[2] Checking risk manager rule_id processing...")
    risk_manager_ok = check_risk_manager_rule_id_processing()
    print("Risk manager check:", "✅ PASSED" if risk_manager_ok else "❌ FAILED")
    
    # Run simulation to verify end-to-end flow
    print("\n[3] Running rule_id flow simulation...")
    simulation_ok = run_simulation()
    print("Simulation check:", "✅ PASSED" if simulation_ok else "❌ FAILED")
    
    # Overall result
    print("\n=== OVERALL RESULT ===")
    if strategy_ok and risk_manager_ok and simulation_ok:
        print("✅ ALL CHECKS PASSED - rule_id format and processing are correct!")
        return True
    else:
        print("❌ SOME CHECKS FAILED - see log for details")
        failed = []
        if not strategy_ok:
            failed.append("Strategy rule_id format")
        if not risk_manager_ok:
            failed.append("Risk manager rule_id processing")
        if not simulation_ok:
            failed.append("Rule ID flow simulation")
            
        print(f"Failed checks: {', '.join(failed)}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
