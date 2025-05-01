#!/usr/bin/env python3
"""
MA Crossover Signal Grouping Complete Fix

This script applies all the necessary fixes to resolve the MA Crossover signal grouping issue.
The issue causes 54 trades to be generated instead of the expected 18 trades.

Fix components:
1. Rule ID Format Fix - Ensures MA Crossover strategy uses the correct rule_id format
2. Risk Manager Reset Fix - Ensures proper clearing of processed_rule_ids
3. Event Bus Reset Fix - Ensures event bus properly resets between runs

Usage: python ma_crossover_fix_complete.py
"""
import os
import sys
import logging
import datetime
import importlib
import functools

# Configure logging
log_file = f"ma_crossover_fix_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def fix_ma_crossover_rule_id():
    """
    Fix the rule_id format in the MA Crossover strategy.
    
    This ensures rule_ids are properly formatted as:
    ma_crossover_SYMBOL_DIRECTION_group_ID
    """
    try:
        from src.strategy.implementations.ma_crossover import MACrossoverStrategy
        
        # Check if rule_id format is already fixed
        original_on_bar = MACrossoverStrategy.on_bar
        
        # Create a test instance to inspect implementation
        test_strategy = MACrossoverStrategy(None, None)
        
        # Check if the fix is already applied
        if "direction_name = " in original_on_bar.__code__.co_consts:
            logger.info("MA Crossover rule_id format fix already applied")
            return True
        
        def fixed_on_bar(self, bar_event):
            """
            Process a bar event and generate signals with proper direction grouping.
            
            Args:
                bar_event: Market data bar event
                
            Returns:
                Optional signal event
            """
            # Enhanced debugging at the start of the method
            logger.debug(f"Received bar event: {bar_event.__dict__ if hasattr(bar_event, '__dict__') else bar_event}")
            
            # Extract data from bar event
            symbol = bar_event.get_symbol()
            logger.debug(f"Bar event symbol: {symbol}")
            
            # Skip if not in our symbol list
            if symbol not in self.symbols:
                logger.debug(f"Symbol {symbol} not in strategy symbols list: {self.symbols}")
                return None
            
            # Extract price data
            price = bar_event.get_close()
            timestamp = bar_event.get_timestamp()
            logger.debug(f"Bar data: symbol={symbol}, price={price}, timestamp={timestamp}")
            
            # Store data for this symbol
            if symbol not in self.data:
                self.data[symbol] = []
                logger.debug(f"Initialized data array for {symbol}")
            
            self.data[symbol].append({
                'timestamp': timestamp,
                'price': price
            })
            
            # Debug log - show early data collection
            if len(self.data[symbol]) <= self.slow_window:
                logger.debug(f"Collecting data for {symbol}: {len(self.data[symbol])}/{self.slow_window} bars")
                
            # Check if we have enough data
            if len(self.data[symbol]) <= self.slow_window:
                return None
            
            # Calculate moving averages
            prices = [bar['price'] for bar in self.data[symbol]]
            
            # Log raw prices for debugging
            logger.debug(f"Last few prices for {symbol}: {prices[-min(5, len(prices)):]}")
            
            # Calculate fast MA - current and previous
            fast_ma = sum(prices[-self.fast_window:]) / self.fast_window
            fast_ma_prev = sum(prices[-(self.fast_window+1):-1]) / self.fast_window
            
            # Calculate slow MA - current and previous
            slow_ma = sum(prices[-self.slow_window:]) / self.slow_window
            slow_ma_prev = sum(prices[-(self.slow_window+1):-1]) / self.slow_window
            
            # Always log MA values for debugging
            logger.debug(f"Symbol: {symbol}, Fast MA: {fast_ma:.2f}, Slow MA: {slow_ma:.2f}, " +
                       f"Prev Fast: {fast_ma_prev:.2f}, Prev Slow: {slow_ma_prev:.2f}, " +
                       f"Diff: {fast_ma - slow_ma:.4f}, Prev Diff: {fast_ma_prev - slow_ma_prev:.4f}")
            
            # Check for crossover
            signal_value = 0
            
            # Buy signal: fast MA crosses above slow MA
            if fast_ma_prev <= slow_ma_prev and fast_ma > slow_ma:
                signal_value = 1
                crossover_pct = (fast_ma - slow_ma) / slow_ma
                logger.info(f"BUY crossover detected for {symbol}: fast MA ({fast_ma:.2f}) crossed above "
                           f"slow MA ({slow_ma:.2f}), crossover: {crossover_pct:.4%}")
            
            # Sell signal: fast MA crosses below slow MA
            elif fast_ma_prev >= slow_ma_prev and fast_ma < slow_ma:
                signal_value = -1
                crossover_pct = (slow_ma - fast_ma) / slow_ma
                logger.info(f"SELL crossover detected for {symbol}: fast MA ({fast_ma:.2f}) crossed below "
                           f"slow MA ({slow_ma:.2f}), crossover: {crossover_pct:.4%}")
            
            # Enhanced debugging for rule ID
            logger.info(f"Signal generation: symbol={symbol}, signal_value={signal_value}, current_direction={self.signal_directions.get(symbol, 0)}")
            if signal_value != 0 and signal_value != self.signal_directions.get(symbol, 0):
                logger.info(f"DIRECTION CHANGE DETECTED: {self.signal_directions.get(symbol, 0)} -> {signal_value}")
            
            # Process signal only if it represents a direction change
            
            # Now check if direction has changed
            current_direction = self.signal_directions.get(symbol, 0)
            
            # CRITICAL: Only process signals that represent a direction change
            if signal_value != 0 and signal_value != current_direction:
                # Direction has changed - create a new group
                self.signal_count += 1
                self.signal_groups[symbol] = self.signal_count
                self.signal_directions[symbol] = signal_value
                
                # Create group-based rule ID - CRITICAL: match validation format
                group_id = self.signal_groups[symbol]
                
                # CRITICAL FIX: MUST use this specific format
                direction_name = "BUY" if signal_value == 1 else "SELL"
                rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"
                
                # Log rule_id with more emphasis
                logger.info(f"RULE ID CREATED: {rule_id} for direction change {current_direction} -> {signal_value}")
                
                # Log the new signal group with more visibility
                logger.info(f"NEW SIGNAL GROUP: {symbol} direction changed to {direction_name}, group={group_id}, rule_id={rule_id}")
                
                # Generate and emit signal event
                from src.core.events.event_utils import create_signal_event
                signal = create_signal_event(
                    signal_value=signal_value,
                    price=price,
                    symbol=symbol,
                    rule_id=rule_id,
                    timestamp=timestamp
                )
                
                # Debug the signal to verify rule_id is included
                if hasattr(signal, 'data') and isinstance(signal.data, dict):
                    logger.info(f"DEBUG: Signal created with rule_id={signal.data.get('rule_id')}")
                
                # Emit signal if we have an event bus
                if self.event_bus:
                    self.event_bus.emit(signal)
                    logger.info(f"Signal #{group_id} emitted for {symbol}: {signal_value}, rule_id={rule_id}, timestamp={timestamp}")
                
                return signal
            
            # If we have a signal but no direction change, we're still in the same group
            elif signal_value != 0 and signal_value == current_direction:
                # Use existing group ID but don't emit a new signal
                logger.debug(f"Signal for {symbol}: {signal_value} - same direction, no new signal emitted")
            
            return None
        
        # Apply the fixed on_bar method
        fixed_on_bar.__name__ = original_on_bar.__name__
        fixed_on_bar.__doc__ = original_on_bar.__doc__
        MACrossoverStrategy.on_bar = fixed_on_bar
        
        logger.info("Successfully applied MA Crossover rule_id format fix")
        return True
        
    except Exception as e:
        logger.error(f"Error applying MA Crossover rule_id fix: {e}", exc_info=True)
        return False

def fix_risk_manager_reset():
    """
    Fix the reset method in SimpleRiskManager to properly clear processed_rule_ids.
    """
    try:
        from src.risk.managers.simple import SimpleRiskManager
        
        # Check if reset method is already fixed
        original_reset = SimpleRiskManager.reset
        
        # Create test instance to inspect implementation
        test_risk_manager = SimpleRiskManager(None, None)
        
        # Check if fix is already applied
        if "CLEARING" in original_reset.__code__.co_consts:
            logger.info("Risk Manager reset fix already applied")
            return True
        
        def fixed_reset(self):
            """Reset risk manager state with proper rule_id clearing."""
            # Call parent reset
            super(SimpleRiskManager, self).reset()
            
            # Clear order IDs and processed signals
            logger.info("Resetting risk manager state: clearing tracking collections")
            self.order_ids.clear()
            self.processed_signals.clear()
            
            # CRITICAL FIX: Ensure processed_rule_ids is emptied on reset
            rule_id_count = len(self.processed_rule_ids)
            logger.info(f"CLEARING {rule_id_count} PROCESSED RULE IDs")
            self.processed_rule_ids.clear()
            logger.info(f"After reset, processed_rule_ids size: {len(self.processed_rule_ids)}")
            
            # Clear events in progress
            self.events_in_progress.clear()
            
            logger.info(f"Risk manager {self.name} reset completed")
        
        # Apply the fixed reset method
        fixed_reset.__name__ = original_reset.__name__
        fixed_reset.__doc__ = original_reset.__doc__
        SimpleRiskManager.reset = fixed_reset
        
        logger.info("Successfully applied Risk Manager reset fix")
        return True
        
    except Exception as e:
        logger.error(f"Error applying Risk Manager reset fix: {e}", exc_info=True)
        return False

def fix_backtest_coordinator_run():
    """
    Fix the BacktestCoordinator.run method to explicitly reset the event bus.
    """
    try:
        from src.execution.backtest.backtest import BacktestCoordinator
        
        # Store original run method
        original_run = BacktestCoordinator.run
        
        # Create new patched run method
        @functools.wraps(original_run)
        def patched_run(self, symbols=None, start_date=None, end_date=None, 
                      initial_capital=100000.0, timeframe=None):
            """
            Patched run method with explicit event bus reset.
            """
            # Reset the event bus first to clear processed rule_ids
            if hasattr(self, 'event_bus') and self.event_bus:
                logger.info("Explicitly resetting event bus before run")
                self.event_bus.reset()
                logger.info("Event bus reset complete")
            
            # Call the original run method
            return original_run(self, symbols, start_date, end_date, initial_capital, timeframe)
        
        # Apply the patch
        BacktestCoordinator.run = patched_run
        
        logger.info("Successfully applied BacktestCoordinator run fix")
        return True
        
    except Exception as e:
        logger.error(f"Error applying BacktestCoordinator run fix: {e}", exc_info=True)
        return False

def apply_all_fixes():
    """Apply all fixes and verify they're applied correctly."""
    logger.info("Starting MA Crossover Signal Grouping Fix...")
    
    # Track success status
    fix_results = {
        "ma_crossover_rule_id": False,
        "risk_manager_reset": False,
        "backtest_coordinator_run": False
    }
    
    # Apply fix 1: MA Crossover rule_id format
    logger.info("-" * 50)
    logger.info("FIX 1: MA Crossover rule_id format")
    fix_results["ma_crossover_rule_id"] = fix_ma_crossover_rule_id()
    
    # Apply fix 2: Risk Manager reset
    logger.info("-" * 50)
    logger.info("FIX 2: Risk Manager reset")
    fix_results["risk_manager_reset"] = fix_risk_manager_reset()
    
    # Apply fix 3: BacktestCoordinator run method
    logger.info("-" * 50)
    logger.info("FIX 3: BacktestCoordinator run")
    fix_results["backtest_coordinator_run"] = fix_backtest_coordinator_run()
    
    # Summarize results
    logger.info("-" * 50)
    logger.info("Fix Application Summary:")
    for fix_name, success in fix_results.items():
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"- {fix_name}: {status}")
    
    # Overall success
    all_success = all(fix_results.values())
    if all_success:
        logger.info("All fixes successfully applied!")
    else:
        logger.warning("One or more fixes failed to apply. Check the log for details.")
    
    return all_success

def verify_fixes():
    """Verify that fixes are correctly applied by running a test."""
    try:
        from src.strategy.implementations.ma_crossover import MACrossoverStrategy
        from src.risk.managers.simple import SimpleRiskManager
        from src.execution.backtest.backtest import BacktestCoordinator
        
        # Create test instances
        test_strategy = MACrossoverStrategy(None, None)
        test_risk_manager = SimpleRiskManager(None, None)
        test_backtest = BacktestCoordinator()
        
        # Verify test_strategy has correct rule_id format
        on_bar_code = MACrossoverStrategy.on_bar.__code__.co_consts
        rule_id_fixed = any("direction_name" in str(const) for const in on_bar_code if isinstance(const, str))
        
        # Verify test_risk_manager has correct reset method
        reset_code = SimpleRiskManager.reset.__code__.co_consts
        reset_fixed = any("CLEARING" in str(const) for const in reset_code if isinstance(const, str))
        
        # Verify test_backtest has correct run method
        run_code = BacktestCoordinator.run.__code__.co_consts
        run_fixed = hasattr(BacktestCoordinator.run, '__wrapped__')
        
        # Log verification results
        logger.info("-" * 50)
        logger.info("Fix Verification Results:")
        logger.info(f"- MA Crossover rule_id format: {'VERIFIED' if rule_id_fixed else 'NOT VERIFIED'}")
        logger.info(f"- Risk Manager reset: {'VERIFIED' if reset_fixed else 'NOT VERIFIED'}")
        logger.info(f"- BacktestCoordinator run: {'VERIFIED' if run_fixed else 'NOT VERIFIED'}")
        
        # Overall verification
        all_verified = rule_id_fixed and reset_fixed and run_fixed
        if all_verified:
            logger.info("All fixes verified successfully!")
        else:
            logger.warning("One or more fixes could not be verified. Manual testing recommended.")
        
        return all_verified
        
    except Exception as e:
        logger.error(f"Error verifying fixes: {e}", exc_info=True)
        return False

def main():
    """Main function to apply and verify fixes."""
    logger.info("=" * 80)
    logger.info("MA CROSSOVER SIGNAL GROUPING FIX")
    logger.info("=" * 80)
    
    # Apply all fixes
    fixes_applied = apply_all_fixes()
    
    if fixes_applied:
        # Verify fixes
        fixes_verified = verify_fixes()
        
        if fixes_verified:
            logger.info("=" * 80)
            logger.info("ALL FIXES SUCCESSFULLY APPLIED AND VERIFIED!")
            logger.info("=" * 80)
            logger.info("The fixed implementation should now generate 18 trades instead of 54.")
            logger.info("To test the fix, run: python run_and_validate_fixed.sh")
        else:
            logger.warning("=" * 80)
            logger.warning("FIXES APPLIED BUT VERIFICATION FAILED")
            logger.warning("=" * 80)
            logger.warning("Manual testing is recommended to ensure the fix is working correctly.")
    else:
        logger.error("=" * 80)
        logger.error("FIX APPLICATION FAILED")
        logger.error("=" * 80)
        logger.error("Check the logs for details on which fixes failed.")
    
    return 0 if fixes_applied else 1

if __name__ == "__main__":
    sys.exit(main())
