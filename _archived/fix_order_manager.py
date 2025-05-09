#!/usr/bin/env python3
"""
Fix the order manager to properly implement strategy-driven trading.

This script completely rewrites the trade handling in the OrderManager to:
1. Remove artificial trade generation
2. Implement proper separation of TRADE_OPEN and TRADE_CLOSE events
3. Let the strategy determine entry and exit points based on market data

The current implementation artificially creates winning trades with fixed price adjustments,
rather than letting the strategy determine trade outcomes based on actual market conditions.
"""
import os
import re
import sys
import shutil
from datetime import datetime

def backup_file(file_path):
    """Create a backup of the file."""
    backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_order_manager():
    """Fix the core issue in the order manager."""
    file_path = 'src/execution/order_manager.py'
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return False
        
    # Create a backup
    backup_file(file_path)
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # The core issue is that the order manager is automatically creating TRADE_CLOSE events
    # immediately after TRADE_OPEN events, with artificially adjusted prices
    
    # Find the pattern where it creates TRADE_OPEN event
    trade_open_pattern = r"""            # CRITICAL FIX: Always emit both a trade open AND a trade close event for each order
            # First emit TRADE_OPEN event
            logger\.info\(f"Emitting TRADE_OPEN event for \{symbol\}: \{direction\} \{quantity\} @ \{price:\.2f\}"\)
            open_transaction_id = str\(uuid\.uuid4\(\)\) 
            trade_open_event = create_trade_open_event\(
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                price=price,
                commission=commission/2\.0,  # Split commission between open/close
                timestamp=timestamp,
                rule_id=rule_id,
                order_id=order_id,
                transaction_id=open_transaction_id
            \)
            
            # Emit the trade open event
            if self\.event_bus:
                self\.event_bus\.emit\(trade_open_event\)"""
                
    # Find the pattern that artificially generates TRADE_CLOSE event with fixed prices
    artificial_close_pattern = r"""            # Then immediately emit a TRADE_CLOSE event to ensure we have complete trades
            # Create slightly different exit price to ensure non-zero PnL
            exit_price = price \* 1\.001 if direction == "BUY" else price \* 0\.999
            
            # Calculate PnL - small but non-zero
            if direction == "BUY":
                pnl = \(exit_price - price\) \* quantity
            else:
                pnl = \(price - exit_price\) \* quantity
                
            # Add small time difference
            from datetime import datetime, timedelta
            exit_time = timestamp \+ timedelta\(minutes=5\) if timestamp else datetime\.now\(\)
            
            # Create a unique transaction ID for close
            close_transaction_id = str\(uuid\.uuid4\(\)\)
            
            # Create and emit close event
            logger\.info\(f"Emitting TRADE_CLOSE event for \{symbol\}: \{direction\} \{quantity\} @ \{exit_price:\.2f\}, PnL: \{pnl:\.2f\}"\)
            trade_close_event = create_trade_close_event\(
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                entry_price=price,
                exit_price=exit_price,
                entry_time=timestamp,
                exit_time=exit_time,
                pnl=pnl,
                commission=commission/2\.0,
                rule_id=rule_id,
                order_id=order_id,
                transaction_id=close_transaction_id
            \)
            
            # Emit the trade close event
            if self\.event_bus:
                self\.event_bus\.emit\(trade_close_event\)"""
    
    # Replacement for trade open - keep this part
    trade_open_replacement = """            # Emit a trade open event when an order is filled
            # This allows the strategy to determine when to close the trade based on market conditions
            logger.info(f"Emitting TRADE_OPEN event for {symbol}: {direction} {quantity} @ {price:.2f}")
            open_transaction_id = str(uuid.uuid4()) 
            trade_open_event = create_trade_open_event(
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                price=price,
                commission=commission,  # Assign full commission to open trade
                timestamp=timestamp,
                rule_id=rule_id,
                order_id=order_id,
                transaction_id=open_transaction_id
            )
            
            # Emit the trade open event
            if self.event_bus:
                self.event_bus.emit(trade_open_event)
                
            # DO NOT automatically emit a TRADE_CLOSE event here
            # The strategy should determine when to close trades based on market conditions
            # This ensures realistic backtesting with proper trade timing"""
    
    # Check if the pattern exists in the content
    if re.search(artificial_close_pattern, content, re.MULTILINE):
        # Replace the artificial close generation
        modified_content = re.sub(
            artificial_close_pattern,
            "", 
            content, 
            flags=re.MULTILINE
        )
        
        # Also replace the trade open event to match the new pattern
        if re.search(trade_open_pattern, modified_content, re.MULTILINE):
            modified_content = re.sub(
                trade_open_pattern,
                trade_open_replacement,
                modified_content,
                flags=re.MULTILINE
            )
            
        # If we made changes, write them back
        if modified_content != content:
            with open(file_path, 'w') as f:
                f.write(modified_content)
                
            print(f"Successfully modified {file_path}")
            print("Removed automatic trade close generation with artificial prices")
            print("Now trades will only be closed when the strategy explicitly signals to close them")
            return True
        else:
            print("No changes were made. The file may have already been modified.")
            return False
    else:
        print("Could not find the artificial trade close pattern in the file.")
        print("The file may have already been fixed or has a different structure.")
        return False

def main():
    """Main function."""
    print("Fixing order manager to implement proper strategy-driven trading...")
    print("\nThis script will remove artificial trade generation and implement proper strategy-driven trading.")
    print("After this fix, trades will only be closed when your strategy explicitly signals to close them,")
    print("rather than automatically generating artificial close events with fixed price adjustments.\n")
    
    success = fix_order_manager()
    
    if success:
        print("\n✓ Order manager fixed successfully.")
        print("\nIMPORTANT: You will need to update your strategy to properly generate TRADE_CLOSE signals")
        print("when your strategy determines it's time to exit a position. Without this, trades may remain")
        print("open and not be reflected in performance metrics.")
    else:
        print("\n✗ Order manager fix was not successful. Please check the error messages above.")
        
    print("\nIf this fix causes issues, you can restore from the backup created by this script.")

if __name__ == "__main__":
    main()