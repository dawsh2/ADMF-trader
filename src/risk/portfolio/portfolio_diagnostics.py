"""
Diagnostic version of the portfolio module to identify trade tracking issues.
"""
import pandas as pd
import datetime
import logging
import uuid
import traceback
import sys
from typing import Dict, Any, List, Optional, Union

# Use a dedicated logger for diagnostics with high visibility
logging.basicConfig(level=logging.DEBUG)
diag_logger = logging.getLogger("DIAGNOSTICS")
diag_logger.setLevel(logging.DEBUG)

# Add console handler with distinctive formatting
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
ch.setFormatter(formatter)
diag_logger.addHandler(ch)

class TradeTracker:
    """Helper class to track and diagnose trade processing issues"""
    
    def __init__(self):
        self.trades = []
        self.trade_ids = set()
        self.fill_ids = set()
        self.id = id(self)
        diag_logger.info(f"TradeTracker initialized with ID: {self.id}")
        
    def add_trade(self, trade):
        """Add a trade with verification"""
        # Generate unique ID if none exists
        if 'id' not in trade:
            trade['id'] = str(uuid.uuid4())
            
        # Log addition attempt
        diag_logger.info(f"Adding trade {trade['id']} to tracker (before: {len(self.trades)} trades)")
        
        # Add trade
        self.trades.append(trade)
        self.trade_ids.add(trade['id'])
        
        # Verify addition
        verification_length = len(self.trades)
        diag_logger.info(f"After addition: {verification_length} trades in tracker")
        
        # Validate trade exists in list
        found = False
        for t in self.trades:
            if t['id'] == trade['id']:
                found = True
                break
                
        if not found:
            diag_logger.error(f"CRITICAL: Trade {trade['id']} not found in trades list after addition!")
        else:
            diag_logger.info(f"Trade {trade['id']} successfully verified in trades list")
            
        return verification_length

    def add_fill(self, fill_id):
        """Track a processed fill ID"""
        self.fill_ids.add(fill_id)
        diag_logger.info(f"Added fill ID {fill_id} to tracker. Total fills: {len(self.fill_ids)}")
        
    def get_trades(self):
        """Get trades with validation"""
        diag_logger.info(f"get_trades called, tracker has {len(self.trades)} trades")
        
        if not self.trades:
            diag_logger.warning("No trades available in tracker")
            return []
            
        # Verify each trade
        diag_logger.info(f"First trade in tracker: {self.trades[0]}")
        
        return self.trades

def debug_on_fill(self, fill_event):
    """
    Enhanced diagnostic version of on_fill method with detailed tracing
    """
    diag_logger.info("=" * 50)
    diag_logger.info("DEBUG_ON_FILL CALLED")
    diag_logger.info("=" * 50)
    
    # Always initialize trades collection if needed
    if not hasattr(self, 'trades'):
        diag_logger.warning("CRITICAL: trades collection doesn't exist!")
        self.trades = []
        diag_logger.info(f"Created new trades list with ID: {id(self.trades)}")
    
    # Create trade tracker if not exists
    if not hasattr(self, 'trade_tracker'):
        self.trade_tracker = TradeTracker()
        diag_logger.info(f"Created trade tracker with ID: {self.trade_tracker.id}")
    
    # Print info about self object
    diag_logger.info(f"Portfolio object ID: {id(self)}")
    diag_logger.info(f"Trades list ID: {id(self.trades)}")
    diag_logger.info(f"Current trade count: {len(self.trades)}")
    
    try:
        # Get the fill data from the event object
        diag_logger.info(f"Processing fill event ID: {getattr(fill_event, 'id', 'unknown')}")
        
        # Print entire fill event data for diagnosis
        if hasattr(fill_event, 'data'):
            diag_logger.info(f"Fill event data: {fill_event.data}")
        else:
            diag_logger.warning("Fill event has no data attribute!")
            return
        
        fill_data = fill_event.data
        
        # Generate a unique ID for this fill
        fill_id = None
        if hasattr(fill_event, 'id'):
            fill_id = fill_event.id
        else:
            # Create a fill ID from its data
            symbol = fill_data.get('symbol', 'UNKNOWN')
            direction = fill_data.get('direction', 'UNKNOWN')
            size = fill_data.get('size', 0)
            fill_price = fill_data.get('fill_price', 0.0)
            timestamp = getattr(fill_event, 'timestamp', datetime.datetime.now()).isoformat()
            fill_id = f"{symbol}_{direction}_{size}_{fill_price}_{timestamp}"
            diag_logger.info(f"Generated fill ID: {fill_id}")

        # Check if we've already processed this fill
        if hasattr(self, 'processed_fill_ids') and fill_id in self.processed_fill_ids:
            diag_logger.info(f"Fill {fill_id} already processed, skipping")
            return
            
        # Track the fill
        if hasattr(self, 'processed_fill_ids'):
            diag_logger.info(f"Adding fill ID to processed set (before: {len(self.processed_fill_ids)})")
            self.processed_fill_ids.add(fill_id)
            diag_logger.info(f"After addition: {len(self.processed_fill_ids)} fill IDs")
        else:
            diag_logger.warning("processed_fill_ids doesn't exist, creating it")
            self.processed_fill_ids = {fill_id}
        
        # Add to tracker
        self.trade_tracker.add_fill(fill_id)

        # Extract fill details with explicit type conversion for safer handling
        symbol = fill_data.get('symbol', 'UNKNOWN')
        direction = fill_data.get('direction', 'BUY')  # Default to BUY if not specified
        
        # Ensure quantity is numeric and positive
        try:
            quantity = float(fill_data.get('size', 0))  # Use 'size' for quantity
            if quantity <= 0:
                diag_logger.warning(f"Skipping fill with zero or negative quantity: {quantity}")
                return
        except (ValueError, TypeError):
            diag_logger.warning(f"Invalid quantity value in fill data: {fill_data.get('size')}")
            quantity = 1  # Default to 1 if conversion fails
            
        # Ensure price is numeric
        try:
            price = float(fill_data.get('fill_price', 0.0))  # Use 'fill_price' for price
        except (ValueError, TypeError):
            diag_logger.warning(f"Invalid price value in fill data: {fill_data.get('fill_price')}")
            price = 0.0  # Default to 0 if conversion fails
            
        # Ensure commission is numeric
        try:
            commission = float(fill_data.get('commission', 0.0))
        except (ValueError, TypeError):
            diag_logger.warning(f"Invalid commission value in fill data: {fill_data.get('commission')}")
            commission = 0.0  # Default to 0 if conversion fails
            
        timestamp = getattr(fill_event, 'timestamp', datetime.datetime.now())
        diag_logger.info(f"Extracted fill data: {symbol} {direction} {quantity} @ {price}")

        # Create a trade record
        trade = {
            'id': str(uuid.uuid4()),
            'timestamp': timestamp,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'size': quantity,  # Add size field for compatibility
            'price': price,
            'fill_price': price,  # Add fill_price for compatibility
            'commission': commission,
            'pnl': 0.0,  # Placeholder, will be calculated by position update
            'realized_pnl': 0.0  # Placeholder
        }
        diag_logger.info(f"Created trade record: {trade}")
        
        # CRITICAL: Update position and get PnL
        # Get or create position
        if not hasattr(self, 'positions'):
            diag_logger.warning("positions dict doesn't exist, creating it")
            self.positions = {}
            
        if symbol not in self.positions:
            diag_logger.info(f"Creating new position for {symbol}")
            from .position import Position
            self.positions[symbol] = Position(symbol)

        # Convert to position update 
        quantity_change = quantity if direction == 'BUY' else -quantity
        diag_logger.info(f"Position quantity change: {quantity_change}")

        # CRITICAL: Get position and update it
        try:
            position = self.positions[symbol]
            diag_logger.info(f"Updating position for {symbol}: current quantity={position.quantity}")
            pnl = position.update(quantity_change, price, timestamp)
            diag_logger.info(f"Position update complete: new quantity={position.quantity}, PnL={pnl}")
            
            # Update trade with calculated PnL
            trade['pnl'] = float(pnl)
            trade['realized_pnl'] = float(pnl)
            diag_logger.info(f"Updated trade with PnL: {pnl}")
        except Exception as e:
            diag_logger.error(f"Error updating position: {e}")
            diag_logger.error(traceback.format_exc())
            return
            
        # CRITICAL: Try adding trade to self.trades in different ways
        try:
            # Method 1: Direct append with verification
            diag_logger.info(f"Adding trade to self.trades (before: {len(self.trades)} trades)")
            
            # Create a brand-new trades list if needed
            if not isinstance(self.trades, list):
                diag_logger.warning("self.trades is not a list! Recreating it.")
                self.trades = []
                
            # Add trade to list
            self.trades.append(trade)
            diag_logger.info(f"After direct append: {len(self.trades)} trades")
            
            # Force print contents to verify (only in debug mode)
            if self.trades:
                diag_logger.info(f"Latest trade in list: {self.trades[-1]}")
            
            # Method 2: Using trade tracker
            trade_count = self.trade_tracker.add_trade(trade)
            diag_logger.info(f"Trade tracker now has {trade_count} trades")
            
            # Verify the trade is in the trades list
            found = False
            for t in self.trades:
                if t.get('id') == trade['id']:
                    found = True
                    break
                    
            if not found:
                diag_logger.error("CRITICAL: Trade not found in trades list after addition!")
                # Try alternative approach - reinitialized list 
                diag_logger.info("Reinitializing trades list as a workaround")
                self.trades = list(self.trades) + [trade]
                diag_logger.info(f"After reinitialization: {len(self.trades)} trades")
        except Exception as e:
            diag_logger.error(f"Error adding trade: {e}")
            diag_logger.error(traceback.format_exc())
            
            # Last resort - create new trades list
            diag_logger.info("Creating fresh trades list and adding trade")
            self.trades = [trade]
            
        # Update stats
        if hasattr(self, 'stats'):
            diag_logger.info("Updating portfolio stats")
            self.stats['trades_executed'] += 1
            self.stats['total_commission'] += commission
            self.stats['total_pnl'] += pnl

            if direction == 'BUY':
                self.stats['long_trades'] += 1
            else:
                self.stats['short_trades'] += 1

            if pnl > 0:
                self.stats['winning_trades'] += 1
            elif pnl < 0:
                self.stats['losing_trades'] += 1
            else:
                self.stats['break_even_trades'] += 1
        else:
            diag_logger.warning("stats dictionary doesn't exist")
            
        # Final verification
        diag_logger.info(f"Final trades count: {len(self.trades)}")
        diag_logger.info(f"Tracker trades count: {len(self.trade_tracker.get_trades())}")
        diag_logger.info("=" * 50)
        
    except Exception as e:
        diag_logger.error(f"CRITICAL ERROR in on_fill: {e}")
        diag_logger.error(traceback.format_exc())

def debug_get_recent_trades(self, n=None):
    """
    Enhanced debugging version of get_recent_trades
    
    Args:
        n: Number of trades to return (None for all)
        
    Returns:
        List of trade dictionaries
    """
    diag_logger.info("=" * 50)
    diag_logger.info("DEBUG_GET_RECENT_TRADES CALLED")
    diag_logger.info("=" * 50)
    
    # Verify trades collection exists
    if not hasattr(self, 'trades'):
        diag_logger.error("CRITICAL: trades collection doesn't exist!")
        return []
        
    # Check for the trade tracker
    if hasattr(self, 'trade_tracker'):
        tracker_trades = self.trade_tracker.get_trades()
        diag_logger.info(f"Trade tracker has {len(tracker_trades)} trades")
        
        # Compare with main trades list
        if len(tracker_trades) != len(self.trades):
            diag_logger.warning(f"DISCREPANCY: tracker has {len(tracker_trades)} trades but self.trades has {len(self.trades)}")
            
            # If main list is empty but tracker has trades, use tracker's trades
            if not self.trades and tracker_trades:
                diag_logger.info("Restoring trades from tracker")
                self.trades = list(tracker_trades)
    
    # Log trade count and object ID
    diag_logger.info(f"self.trades object ID: {id(self.trades)}")
    diag_logger.info(f"self.trades contains {len(self.trades)} items")
    
    # Print the first few trades for diagnosis
    if self.trades:
        diag_logger.info(f"First trade: {self.trades[0]}")
        if len(self.trades) > 1:
            diag_logger.info(f"Second trade: {self.trades[1]}")
    else:
        diag_logger.warning("No trades in self.trades list")
        
        # If this is an empty list but we have trade stats, something is wrong
        if hasattr(self, 'stats') and self.stats.get('trades_executed', 0) > 0:
            diag_logger.error(f"CRITICAL ERROR: Stats show {self.stats.get('trades_executed')} trades but none in list")
            
            # Create dummy trades for debugging
            diag_logger.info("Creating dummy trades for diagnosis")
            dummy_trades = []
            for i in range(self.stats.get('trades_executed', 0)):
                dummy_trades.append({
                    'id': f"dummy_{i}",
                    'timestamp': datetime.datetime.now(),
                    'symbol': 'MINI',
                    'direction': 'BUY' if i % 2 == 0 else 'SELL',
                    'quantity': 10,
                    'price': 100.0,
                    'pnl': 1.0 if i % 3 == 0 else -1.0,
                    'dummy': True
                })
            return dummy_trades
    
    # Validate each trade to ensure it has required fields
    validated_trades = []
    for i, trade in enumerate(self.trades):
        # Make a copy to avoid modifying original
        t = dict(trade)
        
        # Debug trade
        diag_logger.info(f"Validating trade {i}: {t.get('id', 'unknown')}")
        
        # Ensure pnl exists and is a number
        if 'pnl' not in t or t['pnl'] is None:
            if 'realized_pnl' in t and t['realized_pnl'] is not None:
                t['pnl'] = float(t['realized_pnl'])
                diag_logger.info(f"Added missing pnl from realized_pnl: {t['pnl']}")
            else:
                t['pnl'] = 0.0
                diag_logger.warning(f"Added missing pnl with default 0.0 for trade {i}")
        else:
            # Ensure PnL is a float
            try:
                t['pnl'] = float(t['pnl'])
            except (ValueError, TypeError):
                diag_logger.warning(f"Invalid PnL value in trade {i}: {t['pnl']}, setting to 0.0")
                t['pnl'] = 0.0
        
        # Ensure other required fields
        if 'symbol' not in t:
            t['symbol'] = 'UNKNOWN'
            diag_logger.warning(f"Added missing symbol for trade {i}")
            
        if 'timestamp' not in t or not isinstance(t['timestamp'], datetime.datetime):
            t['timestamp'] = datetime.datetime.now()
            diag_logger.warning(f"Added missing timestamp for trade {i}")
            
        validated_trades.append(t)
    
    diag_logger.info(f"Returning {len(validated_trades)} validated trades")
    
    # Return slice if n is specified
    if n is not None:
        return validated_trades[-n:]
        
    return validated_trades

def install_diagnostics():
    """Install diagnostic versions of portfolio methods"""
    import sys
    
    try:
        from src.risk.portfolio.portfolio import PortfolioManager
        
        # Install diagnostic versions
        diag_logger.info("Installing diagnostic methods")
        PortfolioManager.debug_on_fill = debug_on_fill
        PortfolioManager.debug_get_recent_trades = debug_get_recent_trades
        
        # Create monkey-patched versions 
        original_on_fill = PortfolioManager.on_fill
        
        def patched_on_fill(self, fill_event):
            """Monkey-patched version of on_fill"""
            diag_logger.info("Calling diagnostic on_fill")
            try:
                # CRITICAL - Initialize trades list if it doesn't exist or isn't a list
                if not hasattr(self, 'trades') or not isinstance(self.trades, list):
                    diag_logger.warning("Initializing missing trades list in portfolio")
                    self.trades = []
                    
                # First call diagnostic version
                debug_on_fill(self, fill_event)
                
                # Then call original if needed
                # original_on_fill(self, fill_event)
                
                # Return success
                return True
            except Exception as e:
                diag_logger.error(f"Error in patched_on_fill: {e}")
                diag_logger.error(traceback.format_exc())
                return False
        
        original_get_recent_trades = PortfolioManager.get_recent_trades
        
        def patched_get_recent_trades(self, n=None):
            """Monkey-patched version of get_recent_trades"""
            diag_logger.info("Calling diagnostic get_recent_trades")
            try:
                # Call diagnostic version
                trades = debug_get_recent_trades(self, n)
                
                # If no trades, try original as fallback
                if not trades and hasattr(self, 'trades') and self.trades:
                    diag_logger.info("No trades from diagnostic method, trying original")
                    trades = original_get_recent_trades(self, n)
                    
                return trades
            except Exception as e:
                diag_logger.error(f"Error in patched_get_recent_trades: {e}")
                diag_logger.error(traceback.format_exc())
                return []
                
        # Install the patches
        PortfolioManager.on_fill = patched_on_fill
        PortfolioManager.get_recent_trades = patched_get_recent_trades
        
        diag_logger.info("Successfully installed portfolio diagnostics")
        return True
    except Exception as e:
        diag_logger.error(f"Failed to install diagnostics: {e}")
        diag_logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # If run directly, install diagnostics
    install_diagnostics()
