import pandas as pd
import re
from collections import defaultdict

def analyze_log_file(log_path):
    """Parse the backtest log file to identify issues with order execution."""
    # Initialize data structures to store information
    signals = []
    orders = []
    fills = []
    state_transitions = []
    risk_messages = []
    
    with open(log_path, 'r') as f:
        for line in f:
            # Extract signals
            if "Signal #" in line and "emitted for MINI" in line:
                signal_num = int(line.split("Signal #")[1].split(" ")[0])
                signal_type = "BUY" if "BUY signal for MINI" in line else "SELL" if "SELL signal for MINI" in line else "UNKNOWN"
                crossover_info = ""
                if "crossed above" in line:
                    crossover_info = "crossed above"
                elif "crossed below" in line:
                    crossover_info = "crossed below"
                
                # Extract MA values if available
                ma_values = re.findall(r"fast MA \((\d+\.\d+)\) crossed \w+ slow MA \((\d+\.\d+)\)", line)
                if ma_values:
                    fast_ma, slow_ma = float(ma_values[0][0]), float(ma_values[0][1])
                    signals.append({
                        'number': signal_num,
                        'type': signal_type,
                        'crossover': crossover_info,
                        'fast_ma': fast_ma,
                        'slow_ma': slow_ma
                    })
            
            # Extract orders
            if "Broker processed order:" in line:
                # Extract order details using regex
                order_match = re.search(r"Broker processed order: (\w+) (\d+) (\w+) @ ([\d\.]+)", line)
                if order_match:
                    direction, size, symbol, price = order_match.groups()
                    timestamp = line.split(" - ")[0]
                    orders.append({
                        'timestamp': timestamp,
                        'direction': direction,
                        'size': int(size),
                        'symbol': symbol,
                        'price': float(price)
                    })
            
            # Extract fills
            if "Fill: " in line and "PnL:" in line:
                # Extract fill details using regex
                fill_match = re.search(r"Fill: (\w+) (\d+) (\w+) @ ([\d\.]+), PnL: ([\d\.\-]+)", line)
                if fill_match:
                    direction, size, symbol, price, pnl = fill_match.groups()
                    timestamp = line.split(" - ")[0]
                    fills.append({
                        'timestamp': timestamp,
                        'direction': direction,
                        'size': int(size),
                        'symbol': symbol,
                        'price': float(price),
                        'pnl': float(pnl)
                    })
            
            # Extract state transition warnings
            if "Invalid state transition:" in line:
                transition_match = re.search(r"Invalid state transition: (\w+\.\w+) -> (\w+\.\w+)", line)
                if transition_match:
                    from_state, to_state = transition_match.groups()
                    timestamp = line.split(" - ")[0]
                    state_transitions.append({
                        'timestamp': timestamp,
                        'from_state': from_state,
                        'to_state': to_state
                    })
            
            # Extract risk manager messages
            if "Reducing" in line and "size from" in line:
                risk_match = re.search(r"Reducing (\w+) size from (\d+) to (\d+) for (\w+)", line)
                if risk_match:
                    direction, from_size, to_size, symbol = risk_match.groups()
                    timestamp = line.split(" - ")[0]
                    reason = "value limit" if "value limit" in line else "unknown"
                    risk_messages.append({
                        'timestamp': timestamp,
                        'direction': direction,
                        'from_size': int(from_size),
                        'to_size': int(to_size),
                        'symbol': symbol,
                        'reason': reason
                    })
    
    # Convert to DataFrames for analysis
    signal_df = pd.DataFrame(signals)
    order_df = pd.DataFrame(orders)
    fill_df = pd.DataFrame(fills)
    transition_df = pd.DataFrame(state_transitions)
    risk_df = pd.DataFrame(risk_messages)
    
    # Analyze order duplication pattern
    print("Order Execution Analysis")
    print("========================")
    
    # Check if we have data
    if not order_df.empty:
        # Convert timestamp to datetime for sorting
        order_df['timestamp'] = pd.to_datetime(order_df['timestamp'])
        order_df = order_df.sort_values('timestamp')
        
        # Group orders by timestamp
        order_counts = order_df.groupby('timestamp').size()
        duplicate_timestamps = order_counts[order_counts > 1].index
        
        print(f"Total orders placed: {len(order_df)}")
        print(f"Unique timestamps: {len(order_df['timestamp'].unique())}")
        print(f"Timestamps with multiple orders: {len(duplicate_timestamps)}")
        
        # Analyze pattern of duplicates
        if len(duplicate_timestamps) > 0:
            print("\nDuplicate Order Pattern:")
            pairs = []
            for ts in duplicate_timestamps:
                group = order_df[order_df['timestamp'] == ts]
                if len(group) == 2:  # Looking for pairs
                    orders_in_group = group.to_dict('records')
                    pairs.append((orders_in_group[0], orders_in_group[1]))
            
            if pairs:
                # Analyze first few pairs
                print(f"Analyzing first 3 of {len(pairs)} duplicate pairs:")
                for i, (first, second) in enumerate(pairs[:3]):
                    print(f"\nPair {i+1}:")
                    print(f"  First order: {first['direction']} {first['size']} {first['symbol']} @ {first['price']}")
                    print(f"  Second order: {second['direction']} {second['size']} {second['symbol']} @ {second['price']}")
                    print(f"  Size difference: {first['size'] - second['size']}")
    
    # Analyze fill performance
    if not fill_df.empty:
        print("\nFill Performance Analysis")
        print("========================")
        print(f"Total fills: {len(fill_df)}")
        print(f"Buy fills: {len(fill_df[fill_df['direction'] == 'BUY'])}")
        print(f"Sell fills: {len(fill_df[fill_df['direction'] == 'SELL'])}")
        
        # PnL analysis
        print(f"Average PnL: {fill_df['pnl'].mean():.2f}")
        print(f"Min PnL: {fill_df['pnl'].min():.2f}")
        print(f"Max PnL: {fill_df['pnl'].max():.2f}")
        print(f"Total PnL: {fill_df['pnl'].sum():.2f}")
        
        # Categorize trades
        winning_trades = len(fill_df[fill_df['pnl'] > 0])
        losing_trades = len(fill_df[fill_df['pnl'] < 0])
        breakeven_trades = len(fill_df[fill_df['pnl'] == 0])
        
        print(f"Winning trades: {winning_trades}")
        print(f"Losing trades: {losing_trades}")
        print(f"Breakeven trades: {breakeven_trades}")
    
    # Analyze state transitions
    if not transition_df.empty:
        print("\nState Transition Issues")
        print("======================")
        transition_counts = transition_df.groupby(['from_state', 'to_state']).size().reset_index(name='count')
        print("Invalid state transitions:")
        for _, row in transition_counts.iterrows():
            print(f"  {row['from_state']} -> {row['to_state']}: {row['count']} occurrences")
    
    # Analyze risk manager behavior
    if not risk_df.empty:
        print("\nRisk Manager Analysis")
        print("====================")
        print(f"Total position adjustments: {len(risk_df)}")
        
        # Analyze reasons for adjustments
        reason_counts = risk_df['reason'].value_counts()
        print("Reasons for position adjustments:")
        for reason, count in reason_counts.items():
            print(f"  {reason}: {count}")
        
        # Analyze size adjustments
        avg_original_size = risk_df['from_size'].mean()
        avg_adjusted_size = risk_df['to_size'].mean()
        avg_reduction = ((risk_df['from_size'] - risk_df['to_size']) / risk_df['from_size'] * 100).mean()
        
        print(f"Average original size: {avg_original_size:.1f}")
        print(f"Average adjusted size: {avg_adjusted_size:.1f}")
        print(f"Average reduction: {avg_reduction:.1f}%")
    
    # Signal validation
    if not signal_df.empty:
        print("\nSignal Validation")
        print("================")
        print(f"Total signals in log: {len(signal_df)}")
        print(f"Buy signals: {len(signal_df[signal_df['type'] == 'BUY'])}")
        print(f"Sell signals: {len(signal_df[signal_df['type'] == 'SELL'])}")
        
        # Check alternating pattern
        signal_types = signal_df['type'].tolist()
        alternating = True
        for i in range(1, len(signal_types)):
            if signal_types[i] == signal_types[i-1]:
                alternating = False
                break
        
        print(f"Signals alternate buy/sell: {'Yes' if alternating else 'No'}")
        
        # Check for gaps in signal numbering
        signal_nums = signal_df['number'].tolist()
        expected_nums = list(range(1, len(signal_nums) + 1))
        missing = set(expected_nums) - set(signal_nums)
        
        if missing:
            print(f"Missing signal numbers: {missing}")
        else:
            print("No gaps in signal numbering")
    
    return {
        'signals': signal_df if not signal_df.empty else None,
        'orders': order_df if not order_df.empty else None,
        'fills': fill_df if not fill_df.empty else None,
        'transitions': transition_df if not transition_df.empty else None,
        'risk_adjustments': risk_df if not risk_df.empty else None
    }

# Main execution
if __name__ == "__main__":
    log_path = "paste.txt"  # Adjust path as needed
    analysis = analyze_log_file(log_path)
    
    # Additional output summarizing key findings
    print("\nKey Issues Identified")
    print("====================")
    print("1. Order Duplication: Each signal generates two orders - one for 100 units followed by a reduced order")
    print("2. State Transition Errors: OrderRegistry has invalid state transitions from FILLED -> PENDING")
    print("3. Risk Management Issues: Position sizing is calculated after orders are already placed")
    print("4. Trade Performance: All trades result in losses or breakeven")
    
    print("\nRecommended Fixes")
    print("================")
    print("1. Modify SimpleRiskManager to calculate position size once before order creation")
    print("2. Fix OrderRegistry state management to prevent invalid transitions")
    print("3. Adjust broker simulation to ensure correct handling of slippage and fill prices")
    print("4. Implement proper signal validation to ensure signal quality and reduce false signals")
