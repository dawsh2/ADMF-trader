#!/usr/bin/env python3
# Script to fetch SPY ATM calls/puts 1-minute bar data from Alpaca

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import pytz
import matplotlib.pyplot as plt
import re

# Import Alpaca modules based on available modules
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionBarsRequest, OptionChainRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import OptionsFeed

# Get API credentials from environment variables
API_KEY = os.environ.get("ALPACA_API_KEY")
API_SECRET = os.environ.get("ALPACA_API_SECRET")

# If environment variables aren't set, use these defaults
if not API_KEY:
    API_KEY = "PK4HCHWRV5536LVRBQIP"
if not API_SECRET:
    API_SECRET = "97lHxjxHyd4faIB4eBKNlpFcLi8DI5MPkAFGxS1N"

# Create an OptionHistoricalDataClient instance
client = OptionHistoricalDataClient(API_KEY, API_SECRET)

def parse_option_symbol(symbol):
    """
    Parse an OCC-format option symbol to extract its components.
    Format: {SYMBOL}{YYMMDD}{C/P}{STRIKE_PRICE}
    Example: SPY250508C00590000 (SPY $590 Call expiring May 8, 2025)
    
    Returns a dictionary with the extracted components.
    """
    # Regular expression pattern for OCC-format option symbols
    pattern = r'^([A-Z]+)(\d{6})([CP])(\d+)$'
    match = re.match(pattern, symbol)
    
    if match:
        underlying, date_str, option_type, strike_str = match.groups()
        
        # Parse the date (YYMMDD)
        year = 2000 + int(date_str[0:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        expiration_date = date(year, month, day)
        
        # Parse the strike (divide by 1000 to get the actual strike price)
        strike_price = float(strike_str) / 1000.0
        
        # Determine option type
        option_type = "Call" if option_type == "C" else "Put"
        
        return {
            "underlying": underlying,
            "expiration_date": expiration_date,
            "option_type": option_type,
            "strike_price": strike_price,
            "symbol": symbol
        }
    else:
        return None

def get_spy_price():
    """Get the latest price of SPY using stock data"""
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    
    # Create stock client
    stock_client = StockHistoricalDataClient(API_KEY, API_SECRET)
    
    try:
        # Get the latest stock data
        # When creating the request, explicitly request the OPRA feed

        request = StockBarsRequest(
            symbol_or_symbols=["SPY"],
            timeframe=TimeFrame.Day,
            start=datetime.now(pytz.UTC) - timedelta(days=5),  # Look back 5 days to ensure we get data
            end=datetime.now(pytz.UTC)
        )
        
        bars = stock_client.get_stock_bars(request)
        
        if "SPY" in bars.data and bars.data["SPY"]:
            # Get the most recent bar
            latest_bar = bars.data["SPY"][-1]
            return latest_bar.close
        else:
            # Return a default value if we couldn't get the actual price
            print("Could not get SPY price from API, using default value")
            return 530.0
    except Exception as e:
        print(f"Error getting SPY price: {e}")
        return 530.0  # Default value

def get_atm_options(current_price=None):
    """
    Get ATM call and put options for SPY
    """
    print("Fetching ATM options for SPY...")
    
    # Get the current price if not provided
    if current_price is None:
        current_price = get_spy_price()
    
    print(f"Current SPY price: ${current_price:.2f}")
    
    # Calculate the target strike (nearest $5)
    strike_increment = 5.0
    target_strike = round(current_price / strike_increment) * strike_increment
    
    print(f"Target strike price: ${target_strike:.2f}")
    
    # Get today's date
    today = datetime.now().date()
    
    # Look for options expiring in the next 1-3 weeks
    exp_date_min = (today + timedelta(days=7)).isoformat()
    exp_date_max = (today + timedelta(days=21)).isoformat()
    
    print(f"Looking for options expiring between {exp_date_min} and {exp_date_max}")
    
    # Request option chain
    try:
        request = OptionChainRequest(
            underlying_symbol="SPY",
            expiration_date_gte=exp_date_min,
            expiration_date_lte=exp_date_max
        )
        
        chain = client.get_option_chain(request)
        
        print(f"Retrieved {len(chain)} options in the chain")
        
        # Find the closest ATM call and put
        closest_call = None
        closest_put = None
        min_call_diff = float('inf')
        min_put_diff = float('inf')
        
        # Process the options
        for symbol, option in chain.items():
            # Parse the symbol to get strike price and option type
            parsed = parse_option_symbol(symbol)
            
            if parsed:
                strike = parsed["strike_price"]
                diff = abs(strike - current_price)
                
                # Store the call or put with strike closest to current price
                if parsed["option_type"] == "Call" and diff < min_call_diff:
                    min_call_diff = diff
                    closest_call = {
                        "symbol": symbol,
                        "option": option,
                        "parsed": parsed
                    }
                
                elif parsed["option_type"] == "Put" and diff < min_put_diff:
                    min_put_diff = diff
                    closest_put = {
                        "symbol": symbol,
                        "option": option,
                        "parsed": parsed
                    }
        
        # Print the selected options
        if closest_call:
            call_info = closest_call["parsed"]
            print(f"\nSelected ATM call: {closest_call['symbol']}")
            print(f"  Strike: ${call_info['strike_price']:.2f}")
            print(f"  Expiration: {call_info['expiration_date']}")
            print(f"  Option Type: {call_info['option_type']}")
            
            # Print the quote if available
            if closest_call["option"].latest_quote:
                quote = closest_call["option"].latest_quote
                print(f"  Bid: ${quote.bid_price:.2f} (size: {quote.bid_size})")
                print(f"  Ask: ${quote.ask_price:.2f} (size: {quote.ask_size})")
                print(f"  Last Updated: {quote.timestamp}")
            
            # Print the latest trade if available
            if closest_call["option"].latest_trade:
                trade = closest_call["option"].latest_trade
                print(f"  Last Trade: ${trade.price:.2f} (size: {trade.size})")
                print(f"  Trade Time: {trade.timestamp}")
            
            # Print implied volatility if available
            if closest_call["option"].implied_volatility:
                iv = closest_call["option"].implied_volatility
                print(f"  Implied Volatility: {iv:.2f} ({iv*100:.2f}%)")
        else:
            print("\nNo suitable call option found")
        
        if closest_put:
            put_info = closest_put["parsed"]
            print(f"\nSelected ATM put: {closest_put['symbol']}")
            print(f"  Strike: ${put_info['strike_price']:.2f}")
            print(f"  Expiration: {put_info['expiration_date']}")
            print(f"  Option Type: {put_info['option_type']}")
            
            # Print the quote if available
            if closest_put["option"].latest_quote:
                quote = closest_put["option"].latest_quote
                print(f"  Bid: ${quote.bid_price:.2f} (size: {quote.bid_size})")
                print(f"  Ask: ${quote.ask_price:.2f} (size: {quote.ask_size})")
                print(f"  Last Updated: {quote.timestamp}")
            
            # Print the latest trade if available
            if closest_put["option"].latest_trade:
                trade = closest_put["option"].latest_trade
                print(f"  Last Trade: ${trade.price:.2f} (size: {trade.size})")
                print(f"  Trade Time: {trade.timestamp}")
            
            # Print implied volatility if available
            if closest_put["option"].implied_volatility:
                iv = closest_put["option"].implied_volatility
                print(f"  Implied Volatility: {iv:.2f} ({iv*100:.2f}%)")
        else:
            print("\nNo suitable put option found")
        
        # Return the symbols only
        return {
            'call': closest_call["symbol"] if closest_call else None,
            'put': closest_put["symbol"] if closest_put else None
        }
    
    except Exception as e:
        print(f"Error fetching option chain: {e}")
        return {'call': None, 'put': None}

def get_option_minute_bars(option_symbol, days_back=3):
    """
    Get 1-minute bars for a specific option contract
    
    Parameters:
    option_symbol (str): Option contract symbol
    days_back (int): Number of trading days to look back
    
    Returns:
    pandas.DataFrame: DataFrame containing the option bars
    """
    if not option_symbol:
        return None
    
    print(f"\nFetching 1-minute bars for {option_symbol}...")
    
    # Calculate start and end times
    end_time = datetime.now(pytz.UTC)
    start_time = end_time - timedelta(days=days_back)
    
    # Request parameters
    request_params = OptionBarsRequest(
    symbol_or_symbols=[option_symbol],
        timeframe=TimeFrame.Minute,
        start=start_time,
        end=end_time,
        feed=OptionsFeed.OPRA  # Explicitly request OPRA feed
    )

    
    try:
        # Get the option bars
        bars = client.get_option_bars(request_params)
        
        # Convert to DataFrame for easier analysis
        if option_symbol in bars.data:
            # Use model_dump instead of dict (as per the deprecation warning)
            df = pd.DataFrame([bar.model_dump() for bar in bars.data[option_symbol]])
            
            # Convert timestamp to datetime and set as index
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            
            print(f"Retrieved {len(df)} minute bars from {df.index[0]} to {df.index[-1]}")
            return df
        else:
            print(f"No data found for {option_symbol}")
            return None
    
    except Exception as e:
        print(f"Error getting minute bars for {option_symbol}: {e}")
        return None

def plot_option_data(call_df, put_df, call_symbol, put_symbol):
    """
    Plot the option price and volume data
    
    Parameters:
    call_df (pandas.DataFrame): DataFrame with call option data
    put_df (pandas.DataFrame): DataFrame with put option data
    call_symbol (str): Call option symbol
    put_symbol (str): Put option symbol
    """
    if call_df is None and put_df is None:
        print("No data to plot")
        return
    
    # Parse symbols to get strike prices for better labels
    call_info = parse_option_symbol(call_symbol) if call_symbol else None
    put_info = parse_option_symbol(put_symbol) if put_symbol else None
    
    call_strike = f"${call_info['strike_price']:.2f}" if call_info else ""
    put_strike = f"${put_info['strike_price']:.2f}" if put_info else ""
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Plot price data
    if call_df is not None:
        ax1.plot(call_df.index, call_df['close'], label=f'Call {call_strike}', color='green')
    
    if put_df is not None:
        ax1.plot(put_df.index, put_df['close'], label=f'Put {put_strike}', color='red')
    
    ax1.set_title('SPY Option Prices')
    ax1.set_ylabel('Price ($)')
    ax1.legend()
    ax1.grid(True)
    
    # Plot volume data
    if call_df is not None:
        ax2.bar(call_df.index, call_df['volume'], label=f'Call Volume', color='green', alpha=0.5, width=0.02)
    
    if put_df is not None:
        ax2.bar(put_df.index, put_df['volume'], label=f'Put Volume', color='red', alpha=0.5, width=0.02)
    
    ax2.set_title('Option Volume')
    ax2.set_ylabel('Volume')
    ax2.set_xlabel('Time')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig('spy_options_data.png')
    print("Plot saved as 'spy_options_data.png'")
    plt.show()

def save_data_to_csv(call_df, put_df, call_symbol, put_symbol):
    """
    Save the option data to CSV files
    
    Parameters:
    call_df (pandas.DataFrame): DataFrame with call option data
    put_df (pandas.DataFrame): DataFrame with put option data
    call_symbol (str): Call option symbol
    put_symbol (str): Put option symbol
    """
    if call_df is not None:
        csv_call = f"{call_symbol}_1min.csv"
        call_df.to_csv(csv_call)
        print(f"Call data saved to {csv_call}")
    
    if put_df is not None:
        csv_put = f"{put_symbol}_1min.csv"
        put_df.to_csv(csv_put)
        print(f"Put data saved to {csv_put}")

def analyze_data(call_df, put_df, call_symbol=None, put_symbol=None):
    """
    Analyze the option data and print some statistics
    
    Parameters:
    call_df (pandas.DataFrame): DataFrame with call option data
    put_df (pandas.DataFrame): DataFrame with put option data
    call_symbol (str): Call option symbol
    put_symbol (str): Put option symbol
    """
    print("\n=== Data Analysis ===")
    
    # Function to analyze a single dataframe
    def analyze_single_df(df, option_type, symbol=None):
        if df is None or len(df) == 0:
            print(f"No {option_type} data to analyze")
            return
        
        # Parse symbol if provided
        info = None
        if symbol:
            info = parse_option_symbol(symbol)
        
        # Basic statistics
        print(f"\n{option_type} Option Analysis:")
        
        if info:
            print(f"  Symbol: {symbol}")
            print(f"  Underlying: {info['underlying']}")
            print(f"  Strike: ${info['strike_price']:.2f}")
            print(f"  Expiration: {info['expiration_date']}")
            print(f"  Option Type: {info['option_type']}")
        
        print(f"  Number of records: {len(df)}")
        print(f"  Date range: {df.index[0].date()} to {df.index[-1].date()}")
        print(f"  Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
        print(f"  Average price: ${df['close'].mean():.2f}")
        print(f"  Average volume: {df['volume'].mean():.2f}")
        print(f"  Maximum volume: {df['volume'].max()}")
        
        # Calculate hourly volatility (option price movement)
        df['returns'] = df['close'].pct_change()
        print(f"  Volatility (std of returns): {df['returns'].std() * 100:.2f}%")
        
        # Show a sample of the data
        print("\n  Sample data:")
        print(df.head().to_string())
    
    # Analyze call and put data
    if call_df is not None:
        analyze_single_df(call_df, "Call", call_symbol)
    
    if put_df is not None:
        analyze_single_df(put_df, "Put", put_symbol)

def main():
    print("=== Fetching SPY ATM Option Data ===\n")
    
    # Get ATM options
    options = get_atm_options()
    
    if not options['call'] and not options['put']:
        print("No options found. Please check your API credentials and connection.")
        return
    
    # Get 1-minute bars for the ATM options
    call_df = get_option_minute_bars(options['call']) if options['call'] else None
    put_df = get_option_minute_bars(options['put']) if options['put'] else None
    
    # Save data to CSV
    save_data_to_csv(call_df, put_df, options['call'], options['put'])
    
    # Analyze the data
    analyze_data(call_df, put_df, options['call'], options['put'])
    
    # Plot the data
    plot_option_data(call_df, put_df, options['call'], options['put'])

if __name__ == "__main__":
    main()
