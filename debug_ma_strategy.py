#!/usr/bin/env python3
"""
Debug the MA Crossover strategy implementation to verify rule_id format.

This script applies a direct fix to the MA Crossover strategy to ensure the
rule_id format includes symbol and direction as required.
"""

import sys
import os
import inspect
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("debug_ma_strategy")

def print_separator():
    """Print a separator line."""
    print("\n" + "=" * 70)

def debug_rule_id_format():
    """Debug and fix the rule_id format in the MA Crossover strategy."""
    print_separator()
    print("DEBUGGING MA CROSSOVER RULE ID FORMAT")
    print_separator()
    
    # Import the strategy class
    from src.strategy.implementations.ma_crossover import MACrossoverStrategy
    
    # Get the on_bar method source code
    on_bar_source = inspect.getsource(MACrossoverStrategy.on_bar)
    
    # Look for rule_id assignment
    rule_id_pattern = re.compile(r'rule_id\s*=\s*f["\']([^"\']*)["\']')
    matches = rule_id_pattern.findall(on_bar_source)
    
    print(f"Found {len(matches)} rule_id assignments in on_bar method:")
    for i, match in enumerate(matches):
        print(f"  {i+1}. rule_id = f\"{match}\"")
    
    # Check for direction_name assignment
    has_direction_name = "direction_name = " in on_bar_source
    print(f"Has direction_name assignment: {has_direction_name}")
    
    # Extract the actual rule_id format used
    if matches:
        rule_id_format = matches[0]
        print(f"\nCurrent rule_id format: f\"{rule_id_format}\"")
        
        # Check if it has the required components
        has_symbol = "{symbol}" in rule_id_format
        has_direction = "direction_name" in rule_id_format or "BUY" in rule_id_format or "SELL" in rule_id_format
        has_group = "group" in rule_id_format
        
        print("Format components check:")
        print(f"  - Has symbol reference: {has_symbol}")
        print(f"  - Has direction reference: {has_direction}")
        print(f"  - Has group reference: {has_group}")
        
        # Determine if format is correct
        format_correct = has_symbol and has_direction and has_group
        print(f"\nOverall format correct: {format_correct}")
        
        # If not correct, show what it should be
        if not format_correct:
            print("\nCorrect format should be:")
            print('direction_name = "BUY" if signal_value == 1 else "SELL"')
            print('rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"')
            
            # Create the fixed implementation
            print("\nApplying direct fix to the class implementation...")
            
            # Create a fixed on_bar method
            original_on_bar = MACrossoverStrategy.on_bar
            
            def fixed_on_bar(self, bar_event):
                """
                Process a bar event and generate signals with proper direction grouping.
                
                Args:
                    bar_event: Market data bar event
                    
                Returns:
                    Optional signal event
                """
                # Enhanced debugging at the start of the method
                self.logger.debug(f"Received bar event: {bar_event.__dict__ if hasattr(bar_event, '__dict__') else bar_event}")
                
                # Extract data from bar event
                symbol = bar_event.get_symbol()
                self.logger.debug(f"Bar event symbol: {symbol}")
                
                # Skip if not in our symbol list
                if symbol not in self.symbols:
                    self.logger.debug(f"Symbol {symbol} not in strategy symbols list: {self.symbols}")
                    return None
                
                # Extract price data
                price = bar_event.get_close()
                timestamp = bar_event.get_timestamp()
                self.logger.debug(f"Bar data: symbol={symbol}, price={price}, timestamp={timestamp}")
                
                # Store data for this symbol
                if symbol not in self.data:
                    self.data[symbol] = []
                    self.logger.debug(f"Initialized data array for {symbol}")
                
                self.data[symbol].append({
                    'timestamp': timestamp,
                    'price': price
                })
                
                # Debug log - show early data collection
                if len(self.data[symbol]) <= self.slow_window:
                    self.logger.debug(f"Collecting data for {symbol}: {len(self.data[symbol])}/{self.slow_window} bars")
                    
                # Check if we have enough data
                if len(self.data[symbol]) <= self.slow_window:
                    return None
                
                # Calculate moving averages
                prices = [bar['price'] for bar in self.data[symbol]]
                
                # Log raw prices for debugging
                self.logger.debug(f"Last few prices for {symbol}: {prices[-min(5, len(prices)):]}")
                
                # Calculate fast MA - current and previous
                fast_ma = sum(prices[-self.fast_window:]) / self.fast_window
                fast_ma_prev = sum(prices[-(self.fast_window+1):-1]) / self.fast_window
                
                # Calculate slow MA - current and previous
                slow_ma = sum(prices[-self.slow_window:]) / self.slow_window
                slow_ma_prev = sum(prices[-(self.slow_window+1):-1]) / self.slow_window
                
                # Always log MA values for debugging
                self.logger.debug(f"Symbol: {symbol}, Fast MA: {fast_ma:.2f}, Slow MA: {slow_ma:.2f}, " +
                               f"Prev Fast: {fast_ma_prev:.2f}, Prev Slow: {slow_ma_prev:.2f}, " +
                               f"Diff: {fast_ma - slow_ma:.4f}, Prev Diff: {fast_ma_prev - slow_ma_prev:.4f}")
                
                # Check for crossover
                signal_value = 0
                
                # Buy signal: fast MA crosses above slow MA
                if fast_ma_prev <= slow_ma_prev and fast_ma > slow_ma:
                    signal_value = 1
                    crossover_pct = (fast_ma - slow_ma) / slow_ma
                    self.logger.info(f"BUY crossover detected for {symbol}: fast MA ({fast_ma:.2f}) crossed above "
                                   f"slow MA ({slow_ma:.2f}), crossover: {crossover_pct:.4%}")
                
                # Sell signal: fast MA crosses below slow MA
                elif fast_ma_prev >= slow_ma_prev and fast_ma < slow_ma:
                    signal_value = -1
                    crossover_pct = (slow_ma - fast_ma) / slow_ma
                    self.logger.info(f"SELL crossover detected for {symbol}: fast MA ({fast_ma:.2f}) crossed below "
                                   f"slow MA ({slow_ma:.2f}), crossover: {crossover_pct:.4%}")
                
                # Enhanced debugging for rule ID
                self.logger.info(f"Signal generation: symbol={symbol}, signal_value={signal_value}, current_direction={self.signal_directions.get(symbol, 0)}")
                if signal_value != 0 and signal_value != self.signal_directions.get(symbol, 0):
                    self.logger.info(f"DIRECTION CHANGE DETECTED: {self.signal_directions.get(symbol, 0)} -> {signal_value}")
                
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
                    
                    # FIXED VERSION - Always use this format
                    direction_name = "BUY" if signal_value == 1 else "SELL"
                    rule_id = f"{self.name}_{symbol}_{direction_name}_group_{group_id}"
                    
                    # Add extra logging to debug rule_id format
                    self.logger.info(f"DEBUG: Creating rule_id with format: {{self.name}}_{{symbol}}_{{direction_name}}_group_{{group_id}}")
                    self.logger.info(f"DEBUG: Actual rule_id created: {rule_id}")
                    
                    # Log rule_id with more emphasis
                    self.logger.info(f"RULE ID CREATED: {rule_id} for direction change {current_direction} -> {signal_value}")
                    
                    # Log the new signal group with more visibility
                    self.logger.info(f"NEW SIGNAL GROUP: {symbol} direction changed to {direction_name}, group={group_id}, rule_id={rule_id}")
                    
                    # Generate and emit signal event
                    from src.core.events.event_utils import create_signal_event
                    signal = create_signal_event(
                        signal_value=signal_value,
                        price=price,
                        symbol=symbol,
                        rule_id=rule_id,
                        timestamp=timestamp
                    )
                    
                    # Log the signal event details
                    self.logger.info(f"DEBUG: Signal event created with rule_id: {signal.data.get('rule_id')}")
                    
                    # Emit signal if we have an event bus
                    if self.event_bus:
                        self.event_bus.emit(signal)
                        self.logger.info(f"Signal #{group_id} emitted for {symbol}: {signal_value}, rule_id={rule_id}, timestamp={timestamp}")
                    
                    return signal
                
                # If we have a signal but no direction change, we're still in the same group
                elif signal_value != 0 and signal_value == current_direction:
                    # Use existing group ID but don't emit a new signal
                    self.logger.debug(f"Signal for {symbol}: {signal_value} - same direction, no new signal emitted")
                
                return None
            
            # Apply the fix - replace the method
            MACrossoverStrategy.on_bar = fixed_on_bar
            print("✅ Fixed on_bar method with correct rule_id format")
        else:
            print("\nNo fix needed - rule_id format is already correct")
    else:
        print("\nCould not find rule_id assignment in the source code")
    
    # Apply other fixes to ensure proper deduplication
    from src.risk.managers.simple import SimpleRiskManager
    
    # Create a fixed reset method
    def fixed_reset(self):
        """Reset risk manager state with improved rule_id clearing."""
        # Call parent reset
        super(SimpleRiskManager, self).reset()
        
        # Clear tracking collections
        self.logger.info("Resetting risk manager state: clearing tracking collections")
        self.order_ids.clear()
        self.processed_signals.clear()
        
        # CRITICAL FIX: Ensure processed_rule_ids is emptied on reset
        rule_id_count = len(self.processed_rule_ids)
        self.logger.info(f"CLEARING {rule_id_count} PROCESSED RULE IDs")
        self.processed_rule_ids.clear()
        self.logger.info(f"After reset, processed_rule_ids size: {len(self.processed_rule_ids)}")
        
        # Clear events in progress
        self.events_in_progress.clear()
        
        self.logger.info(f"Risk manager {self.name} reset completed")
    
    # Apply the fixed reset method
    SimpleRiskManager.reset = fixed_reset
    print("\n✅ Applied improved reset method to SimpleRiskManager")
    
    print("\nDebug complete - run the implementation to check if the fix works")
    print_separator()
    
    return True

if __name__ == "__main__":
    debug_rule_id_format()
