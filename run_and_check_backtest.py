#!/usr/bin/env python
"""
Run the fixed backtest and check if it's successful.
"""
import subprocess
import re
import sys
import os

def run_backtest():
    """Run the fixed backtest and analyze the output."""
    print("Running fixed backtest...")
    
    # Run the backtest script
    process = subprocess.run(["python", "run_my_fixed_backtest.py"], 
                           capture_output=True, text=True)
    
    # Print the output
    print(process.stdout)
    
    # Check if trades were executed
    if "No trades were executed" in process.stdout:
        print("\n❌ BACKTEST FAILED: No trades were executed")
        return False
    else:
        print("\n✅ BACKTEST SUCCEEDED: Trades were executed!")
        
        # Parse and display key metrics
        try:
            # Look for trade statistics
            trade_stats = re.search(r"(\d+) trades, (\d+) wins, (\d+) losses", process.stdout)
            if trade_stats:
                trades = trade_stats.group(1)
                wins = trade_stats.group(2)
                losses = trade_stats.group(3)
                print(f"Trades: {trades}")
                print(f"Wins: {wins}")
                print(f"Losses: {losses}")
                print(f"Win rate: {float(wins) / float(trades) * 100:.2f}%")
            
            # Look for PnL information
            pnl_match = re.search(r"PnL sum: ([\d\.\-]+)", process.stdout)
            if pnl_match:
                pnl = pnl_match.group(1)
                print(f"Total PnL: ${pnl}")
        except Exception as e:
            print(f"Error parsing metrics: {str(e)}")
        
        return True

if __name__ == "__main__":
    run_backtest()
