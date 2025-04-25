import pandas as pd
import matplotlib.pyplot as plt
import logging

# Configure more detailed logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def analyze_data_and_strategy():
    """
    Analyze the data and verify crossover detection
    """
    # Load the sample data directly
    aapl_data = pd.read_csv('data/AAPL_1d.csv')
    
    # Check if data is properly loaded
    print(f"Data shape: {aapl_data.shape}")
    print(f"First few rows:\n{aapl_data.head()}")
    
    # Add proper datetime index if missing
    if 'date' not in aapl_data.columns:
        # Create synthetic dates since they're missing
        aapl_data['date'] = pd.date_range(start='2022-01-01', periods=len(aapl_data))
    
    # Set date as index if not already
    if not isinstance(aapl_data.index, pd.DatetimeIndex):
        if 'date' in aapl_data.columns:
            aapl_data.set_index('date', inplace=True)
        else:
            # Just use the existing index but make it datetime
            aapl_data.index = pd.date_range(start='2022-01-01', periods=len(aapl_data))
    
    # Calculate the same moving averages used in the strategy
    fast_window = 5
    slow_window = 15
    
    aapl_data['fast_ma'] = aapl_data['close'].rolling(window=fast_window).mean()
    aapl_data['slow_ma'] = aapl_data['close'].rolling(window=slow_window).mean()
    
    # Calculate crossovers
    aapl_data['crossover'] = 0
    
    # Previous day fast ma < slow ma AND current day fast ma > slow ma --> BUY signal (1)
    # Previous day fast ma > slow ma AND current day fast ma < slow ma --> SELL signal (-1)
    for i in range(1, len(aapl_data)):
        if (aapl_data['fast_ma'].iloc[i-1] <= aapl_data['slow_ma'].iloc[i-1] and 
            aapl_data['fast_ma'].iloc[i] > aapl_data['slow_ma'].iloc[i]):
            aapl_data.loc[aapl_data.index[i], 'crossover'] = 1
        elif (aapl_data['fast_ma'].iloc[i-1] >= aapl_data['slow_ma'].iloc[i-1] and 
              aapl_data['fast_ma'].iloc[i] < aapl_data['slow_ma'].iloc[i]):
            aapl_data.loc[aapl_data.index[i], 'crossover'] = -1
    
    # Count signals
    buy_signals = (aapl_data['crossover'] == 1).sum()
    sell_signals = (aapl_data['crossover'] == -1).sum()
    
    print(f"Buy signals: {buy_signals}")
    print(f"Sell signals: {sell_signals}")
    
    # Plot for visualization
    plt.figure(figsize=(12, 6))
    plt.plot(aapl_data['close'], label='Close Price')
    plt.plot(aapl_data['fast_ma'], label=f'{fast_window} MA')
    plt.plot(aapl_data['slow_ma'], label=f'{slow_window} MA')
    
    # Plot buy/sell signals
    buys = aapl_data[aapl_data['crossover'] == 1]
    sells = aapl_data[aapl_data['crossover'] == -1]
    
    plt.scatter(buys.index, buys['close'], marker='^', color='green', s=100, label='Buy Signal')
    plt.scatter(sells.index, sells['close'], marker='v', color='red', s=100, label='Sell Signal')
    
    plt.legend()
    plt.title('Moving Average Crossover Analysis')
    plt.savefig('crossover_analysis.png')
    
    return aapl_data

def event_tracer(event_bus):
    """
    Add tracing to the event bus to see all events
    """
    original_emit = event_bus.emit
    original_register = event_bus.register
    event_count = {
        'BAR': 0,
        'SIGNAL': 0,
        'ORDER': 0,
        'FILL': 0,
        'PORTFOLIO': 0,
        'ALL': 0
    }
    handlers = {}
    
    def traced_emit(event):
        event_type = event.get_type().name
        event_count['ALL'] += 1
        if event_type in event_count:
            event_count[event_type] += 1
        print(f"EVENT EMIT: {event_type} #{event_count[event_type]}")
        return original_emit(event)
    
    def traced_register(event_type, handler):
        handler_name = getattr(handler, '__name__', str(handler.__class__.__name__)) 
        if event_type.name not in handlers:
            handlers[event_type.name] = []
        handlers[event_type.name].append(handler_name)
        print(f"HANDLER REGISTERED: {event_type.name} -> {handler_name}")
        return original_register(event_type, handler)
    
    # Replace methods with traced versions
    event_bus.emit = traced_emit
    event_bus.register = traced_register
    
    # Function to print stats
    def print_stats():
        print("\nEVENT STATISTICS:")
        for event_type, count in event_count.items():
            print(f"  {event_type}: {count}")
        
        print("\nREGISTERED HANDLERS:")
        for event_type, handler_list in handlers.items():
            print(f"  {event_type}: {', '.join(handler_list)}")
    
    # Add stats method to event bus
    event_bus.print_tracer_stats = print_stats
    
    return event_bus

def create_synthetic_signals(event_bus):
    """
    Create and emit synthetic signals to test the pipeline
    """
    from src.core.events.event_utils import create_signal_event
    import datetime
    
    # Create a buy signal for AAPL
    signal_event = create_signal_event(
        signal_value=1,  # Buy
        price=100.0, 
        symbol='AAPL',
        timestamp=datetime.datetime.now()
    )
    
    print("Emitting synthetic BUY signal for AAPL...")
    event_bus.emit(signal_event)
    
    # Create a sell signal for MSFT
    signal_event = create_signal_event(
        signal_value=-1,  # Sell
        price=200.0,
        symbol='MSFT',
        timestamp=datetime.datetime.now()
    )
    
    print("Emitting synthetic SELL signal for MSFT...")
    event_bus.emit(signal_event)
    
    return True

if __name__ == "__main__":
    # Analyze data and check for crossovers
    results = analyze_data_and_strategy()
    
    # If you want to run with event tracing
    # Uncomment below and modify your test_backtest.py to use this function
    
    # In test_backtest.py, add:
    from debug_script import event_tracer
    
    # After creating event_bus:
    event_bus = event_tracer(event_bus)
    
    # At the end of the backtest:
    event_bus.print_tracer_stats()
    
    # If you want to test with synthetic signals
    # Uncomment below and add to test_backtest.py
    
    """
    # In test_backtest.py, add:
    from debug_script import create_synthetic_signals
    
    # After setting up all components:
    create_synthetic_signals(event_bus)
    """
