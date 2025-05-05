#!/usr/bin/env python3
"""
Simple diagnostic tool for ADMF-trader event system.

This script runs a simple test to check if trade events are properly flowing
through your system. It focuses specifically on the issue of trades not being
closed which leads to 0 reported trades despite active trading.
"""
import os
import sys
import logging
import pandas as pd
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("debug")

def get_latest_results(results_dir='results/head_test'):
    """Get the latest backtest results."""
    equity_files = [f for f in os.listdir(results_dir) if f.startswith("equity_curve_")]
    if not equity_files:
        logger.error(f"No equity curve files found in {results_dir}")
        return None, None
        
    # Sort by timestamp (descending)
    equity_files.sort(reverse=True)
    run_id = equity_files[0].replace("equity_curve_", "").replace(".csv", "")
    
    # Get paths
    equity_path = os.path.join(results_dir, f"equity_curve_{run_id}.csv")
    trades_path = os.path.join(results_dir, f"trades_{run_id}.csv")
    
    # Check if trades file exists
    if not os.path.exists(trades_path):
        logger.warning(f"No trades file found for run {run_id}")
        trades_path = None
        
    return equity_path, trades_path

def analyze_source_code():
    """Analyze key components of the trading system."""
    results = {
        "strategy": {
            "file": None,
            "issues": []
        },
        "risk_manager": {
            "file": None,
            "issues": []
        },
        "order_manager": {
            "file": None,
            "issues": []
        },
        "portfolio": {
            "file": None,
            "issues": []
        }
    }
    
    # Check MA crossover strategy
    strategy_file = "src/strategy/implementations/ma_crossover.py"
    if os.path.exists(strategy_file):
        results["strategy"]["file"] = strategy_file
        with open(strategy_file, 'r') as f:
            content = f.read()
            # Check for crossover detection
            if "crossover" not in content.lower() and "cross over" not in content.lower():
                results["strategy"]["issues"].append("No crossover detection found in strategy")
            # Check if it emits signals
            if "emit" not in content.lower() and "signal" not in content.lower():
                results["strategy"]["issues"].append("Strategy may not be emitting signals")
    else:
        results["strategy"]["issues"].append(f"Strategy file not found: {strategy_file}")
        
    # Check risk manager
    risk_files = ["src/risk/managers/risk_manager.py", "src/risk/managers/simple.py"]
    for risk_file in risk_files:
        if os.path.exists(risk_file):
            results["risk_manager"]["file"] = risk_file
            with open(risk_file, 'r') as f:
                content = f.read()
                # Check if it handles signals
                if "signal" not in content.lower():
                    results["risk_manager"]["issues"].append(f"{risk_file} may not be handling signals")
                # Check if it creates orders
                if "order" not in content.lower():
                    results["risk_manager"]["issues"].append(f"{risk_file} may not be creating orders")
                # Check if it handles position closures
                if "close" not in content.lower() and "exit" not in content.lower():
                    results["risk_manager"]["issues"].append(f"{risk_file} may not handle position closures")
                    
    # Check order manager
    order_manager_file = "src/execution/order_manager.py"
    if os.path.exists(order_manager_file):
        results["order_manager"]["file"] = order_manager_file
        with open(order_manager_file, 'r') as f:
            content = f.read()
            # Look for artificial trade generation
            if "create" in content.lower() and "trade_close" in content.lower():
                results["order_manager"]["issues"].append("Order manager may be artificially creating trade close events")
            # Check if it properly handles fills
            if "fill" not in content.lower():
                results["order_manager"]["issues"].append("Order manager may not properly handle fills")
                
    # Check portfolio manager
    portfolio_file = "src/risk/portfolio/portfolio.py"
    if os.path.exists(portfolio_file):
        results["portfolio"]["file"] = portfolio_file
        with open(portfolio_file, 'r') as f:
            content = f.read()
            # Check if it processes trade events
            if "trade_open" not in content.lower() or "trade_close" not in content.lower():
                results["portfolio"]["issues"].append("Portfolio may not be handling trade events")
            # Check if it tracks positions
            if "position" not in content.lower():
                results["portfolio"]["issues"].append("Portfolio may not be tracking positions")
                
    return results

def analyze_results(equity_path, trades_path):
    """Analyze the backtest results."""
    results = {
        "equity": None,
        "trades": None,
        "issues": []
    }
    
    # Analyze equity curve
    if equity_path and os.path.exists(equity_path):
        try:
            equity_df = pd.read_csv(equity_path)
            results["equity"] = {
                "points": len(equity_df),
                "initial": equity_df['equity'].iloc[0] if not equity_df.empty else None,
                "final": equity_df['equity'].iloc[-1] if not equity_df.empty else None,
                "change": None
            }
            
            if not equity_df.empty:
                initial = results["equity"]["initial"]
                final = results["equity"]["final"]
                results["equity"]["change"] = (final - initial) / initial if initial else 0
                
                # Check for equity changes without trades
                if results["equity"]["change"] != 0 and (trades_path is None or not os.path.exists(trades_path)):
                    results["issues"].append("Equity changed but no trades file exists - positions may be open but not closed")
        except Exception as e:
            results["issues"].append(f"Error analyzing equity curve: {e}")
    else:
        results["issues"].append("No equity curve file found")
        
    # Analyze trades
    if trades_path and os.path.exists(trades_path):
        try:
            trades_df = pd.read_csv(trades_path)
            results["trades"] = {
                "count": len(trades_df),
                "winning": len(trades_df[trades_df['pnl'] > 0]) if 'pnl' in trades_df.columns else 0,
                "losing": len(trades_df[trades_df['pnl'] < 0]) if 'pnl' in trades_df.columns else 0,
                "breakeven": len(trades_df[trades_df['pnl'] == 0]) if 'pnl' in trades_df.columns else 0
            }
            
            # Check for trade issues
            if results["trades"]["count"] == 0:
                results["issues"].append("No trades recorded despite equity changes - trades may be open but not closed")
                
            if 'pnl' in trades_df.columns:
                win_rate = results["trades"]["winning"] / results["trades"]["count"] if results["trades"]["count"] > 0 else 0
                if win_rate == 1.0 and results["trades"]["count"] > 5:
                    results["issues"].append("100% win rate detected - may indicate artificial trade generation")
        except Exception as e:
            results["issues"].append(f"Error analyzing trades: {e}")
    else:
        results["issues"].append("No trades file found")
        
    return results

def main():
    """Main function."""
    logger.info("Running ADMF-trader diagnostic tool")
    
    # Get latest results
    equity_path, trades_path = get_latest_results()
    
    # Analyze source code
    code_analysis = analyze_source_code()
    
    # Analyze results
    results_analysis = analyze_results(equity_path, trades_path)
    
    # Print diagnostic report
    print("\n======== ADMF-TRADER DIAGNOSTIC REPORT ========")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n----- SOURCE CODE ANALYSIS -----")
    
    # Print strategy analysis
    print("\nStrategy:")
    print(f"  File: {code_analysis['strategy']['file'] or 'Not found'}")
    if code_analysis['strategy']['issues']:
        print("  Issues:")
        for issue in code_analysis['strategy']['issues']:
            print(f"    - {issue}")
    else:
        print("  No issues detected")
        
    # Print risk manager analysis
    print("\nRisk Manager:")
    print(f"  File: {code_analysis['risk_manager']['file'] or 'Not found'}")
    if code_analysis['risk_manager']['issues']:
        print("  Issues:")
        for issue in code_analysis['risk_manager']['issues']:
            print(f"    - {issue}")
    else:
        print("  No issues detected")
        
    # Print order manager analysis
    print("\nOrder Manager:")
    print(f"  File: {code_analysis['order_manager']['file'] or 'Not found'}")
    if code_analysis['order_manager']['issues']:
        print("  Issues:")
        for issue in code_analysis['order_manager']['issues']:
            print(f"    - {issue}")
    else:
        print("  No issues detected")
        
    # Print portfolio analysis
    print("\nPortfolio:")
    print(f"  File: {code_analysis['portfolio']['file'] or 'Not found'}")
    if code_analysis['portfolio']['issues']:
        print("  Issues:")
        for issue in code_analysis['portfolio']['issues']:
            print(f"    - {issue}")
    else:
        print("  No issues detected")
        
    # Print results analysis
    print("\n----- BACKTEST RESULTS ANALYSIS -----")
    
    if results_analysis['equity']:
        print("\nEquity Curve:")
        print(f"  Points: {results_analysis['equity']['points']}")
        print(f"  Initial: {results_analysis['equity']['initial']:.2f}")
        print(f"  Final: {results_analysis['equity']['final']:.2f}")
        print(f"  Change: {results_analysis['equity']['change']*100:.2f}%")
    else:
        print("\nEquity Curve: Not available")
        
    if results_analysis['trades']:
        print("\nTrades:")
        print(f"  Count: {results_analysis['trades']['count']}")
        print(f"  Winning: {results_analysis['trades']['winning']}")
        print(f"  Losing: {results_analysis['trades']['losing']}")
        print(f"  Breakeven: {results_analysis['trades']['breakeven']}")
        if results_analysis['trades']['count'] > 0:
            win_rate = results_analysis['trades']['winning'] / results_analysis['trades']['count']
            print(f"  Win Rate: {win_rate*100:.2f}%")
    else:
        print("\nTrades: Not available")
        
    # Print overall issues
    print("\n----- DIAGNOSTIC SUMMARY -----")
    
    all_issues = (code_analysis['strategy']['issues'] + 
                 code_analysis['risk_manager']['issues'] + 
                 code_analysis['order_manager']['issues'] + 
                 code_analysis['portfolio']['issues'] + 
                 results_analysis['issues'])
                 
    if all_issues:
        print(f"\nDetected {len(all_issues)} issues:")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("\nNo issues detected.")
        
    # Add recommendations
    print("\n----- RECOMMENDATIONS -----")
    
    if any("artificial" in issue for issue in all_issues):
        print("\n1. Fix the artificial trade generation:")
        print("   Check order_manager.py for code that automatically creates TRADE_CLOSE events with")
        print("   artificial prices. The system should let your strategy determine when to close trades.")
        
    if any("trade events" in issue for issue in all_issues) or any("trade close" in issue for issue in all_issues):
        print("\n2. Ensure proper trade event flow:")
        print("   - Strategy should emit signals when MA crossovers occur")
        print("   - Risk manager should convert signals to orders with proper position_action")
        print("   - Order manager should handle fills and emit TRADE_OPEN events")
        print("   - Risk manager should emit opposite signals when crossovers occur in the opposite direction")
        print("   - Those signals should lead to TRADE_CLOSE events")
        
    if results_analysis.get('trades', {}) == None or results_analysis.get('trades', {}).get('count', 0) == 0:
        print("\n3. Check why trades aren't being closed:")
        print("   - Verify MA crossover detection is working in both directions")
        print("   - Ensure that when a crossover occurs, it generates a signal to close existing positions")
        print("   - Check if the risk manager is properly handling these signals")
        
    print("\n===========================================")
    
if __name__ == "__main__":
    main()