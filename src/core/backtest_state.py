"""
BacktestState for managing isolated state across runs.

This class helps to ensure proper state isolation between optimization
runs by providing a centralized mechanism for storing and resetting
backtest state.
"""

class BacktestState:
    """
    Container for maintaining isolated backtest state.
    
    This class ensures that each backtest run has proper state isolation,
    preventing state leakage between optimization iterations.
    """
    
    def __init__(self):
        """Initialize the backtest state container."""
        # Strategy-specific state
        self.strategy_state = {}
        
        # Position tracking
        self.positions = {}  # symbol -> position size
        self.active_trades = {}  # symbol -> list of trade IDs
        
        # Signal tracking
        self.active_signals = {}  # symbol -> current signal direction
        
        # Performance metrics
        self.equity_points = []
        self.trade_history = []
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)
        
    def get_strategy_state(self, strategy_name, key=None, default=None):
        """
        Get strategy-specific state.
        
        Args:
            strategy_name (str): Strategy identifier
            key (str, optional): Specific state key to retrieve
            default: Default value if key not found
            
        Returns:
            Value of the requested state or entire state dict
        """
        # Initialize strategy state if not present
        if strategy_name not in self.strategy_state:
            self.strategy_state[strategy_name] = {}
            
        if key is not None:
            return self.strategy_state[strategy_name].get(key, default)
        return self.strategy_state[strategy_name]
        
    def set_strategy_state(self, strategy_name, key, value):
        """
        Set strategy-specific state.
        
        Args:
            strategy_name (str): Strategy identifier
            key (str): State key
            value: Value to store
        """
        # Initialize strategy state if not present
        if strategy_name not in self.strategy_state:
            self.strategy_state[strategy_name] = {}
            
        self.strategy_state[strategy_name][key] = value
        
    def get_position(self, symbol, default=0):
        """
        Get current position for a symbol.
        
        Args:
            symbol (str): Instrument symbol
            default: Default value if position not found
            
        Returns:
            float: Current position size
        """
        return self.positions.get(symbol, default)
        
    def set_position(self, symbol, size):
        """
        Set position for a symbol.
        
        Args:
            symbol (str): Instrument symbol
            size (float): Position size
        """
        self.positions[symbol] = size
        
    def add_trade(self, trade_id, symbol, direction, quantity):
        """
        Add a trade to tracking.
        
        Args:
            trade_id (str): Trade identifier
            symbol (str): Instrument symbol
            direction (str): Trade direction ('LONG' or 'SHORT')
            quantity (float): Trade quantity
        """
        if symbol not in self.active_trades:
            self.active_trades[symbol] = []
            
        self.active_trades[symbol].append({
            'id': trade_id,
            'direction': direction,
            'quantity': quantity
        })
        
    def remove_trade(self, trade_id, symbol):
        """
        Remove a trade from tracking.
        
        Args:
            trade_id (str): Trade identifier
            symbol (str): Instrument symbol
            
        Returns:
            bool: True if trade was found and removed, False otherwise
        """
        if symbol not in self.active_trades:
            return False
            
        # Find and remove the trade
        for i, trade in enumerate(self.active_trades[symbol]):
            if trade['id'] == trade_id:
                self.active_trades[symbol].pop(i)
                return True
                
        return False
        
    def get_active_trades(self, symbol=None):
        """
        Get active trades, optionally filtered by symbol.
        
        Args:
            symbol (str, optional): Instrument symbol
            
        Returns:
            list: Active trades
        """
        if symbol is not None:
            return self.active_trades.get(symbol, [])
            
        # Return all active trades
        all_trades = []
        for symbol_trades in self.active_trades.values():
            all_trades.extend(symbol_trades)
        return all_trades
        
    def get_active_signal(self, symbol):
        """
        Get current active signal for a symbol.
        
        Args:
            symbol (str): Instrument symbol
            
        Returns:
            dict: Active signal information or None if not found
        """
        return self.active_signals.get(symbol)
        
    def set_active_signal(self, symbol, direction, rule_id):
        """
        Set active signal for a symbol.
        
        Args:
            symbol (str): Instrument symbol
            direction (str): Signal direction ('LONG' or 'SHORT')
            rule_id (str): Rule identifier for the signal
        """
        self.active_signals[symbol] = {
            'direction': direction,
            'rule_id': rule_id
        }
        
    def clear_active_signal(self, symbol):
        """
        Clear active signal for a symbol.
        
        Args:
            symbol (str): Instrument symbol
            
        Returns:
            bool: True if signal was found and cleared, False otherwise
        """
        if symbol in self.active_signals:
            del self.active_signals[symbol]
            return True
        return False
        
    def add_equity_point(self, timestamp, equity, cash, market_value):
        """
        Add an equity curve data point.
        
        Args:
            timestamp: Time of the equity point
            equity (float): Total portfolio equity
            cash (float): Cash balance
            market_value (float): Market value of positions
        """
        self.equity_points.append({
            'timestamp': timestamp,
            'equity': equity,
            'cash': cash,
            'market_value': market_value
        })
        
    def add_trade_result(self, trade):
        """
        Add a completed trade to history.
        
        Args:
            trade (dict): Trade information
        """
        self.trade_history.append(trade.copy())
        
    def get_equity_curve(self):
        """
        Get the equity curve.
        
        Returns:
            list: Equity curve data points
        """
        return self.equity_points
        
    def get_trade_history(self):
        """
        Get trade history.
        
        Returns:
            list: Trade history
        """
        return self.trade_history
        
    def reset(self):
        """Reset all state to initial values."""
        self.strategy_state = {}
        self.positions = {}
        self.active_trades = {}
        self.active_signals = {}
        self.equity_points = []
        self.trade_history = []
        
        self.logger.info("BacktestState reset to initial values")
