"""
Adaptive risk manager implementation.

This module provides an adaptive risk manager that adjusts risk parameters 
based on market regimes, volatility, and recent performance.
"""
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import datetime

from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType
from src.risk.managers.standard_risk_manager import StandardRiskManager

logger = logging.getLogger(__name__)

class AdaptiveRiskManager(StandardRiskManager):
    """
    Adaptive risk manager that adjusts based on market conditions.
    
    Features:
    - Regime-based risk parameter adjustment
    - Performance-based risk scaling
    - Volatility-based position sizing
    - Dynamic risk limits
    """
    
    def __init__(self, portfolio_manager, event_bus=None, 
               position_sizer=None, limit_manager=None, name=None):
        """
        Initialize adaptive risk manager.
        
        Args:
            portfolio_manager: Portfolio manager instance
            event_bus: Optional event bus for communication
            position_sizer: Optional position sizer
            limit_manager: Optional limit manager
            name: Optional risk manager name
        """
        super().__init__(portfolio_manager, event_bus, position_sizer, limit_manager, name)
        
        # Current regime tracking
        self.current_regime = "normal"
        self.regime_parameters = {
            "normal": {},  # Default parameters
            "bullish": {
                "position_sizing": {"scale": 1.2},  # Increase size by 20%
                "risk_limits": {"max_exposure": 1.2}  # Increase exposure limit by 20%
            },
            "bearish": {
                "position_sizing": {"scale": 0.7},  # Decrease size by 30%
                "risk_limits": {"max_exposure": 0.7}  # Decrease exposure limit by 30%
            },
            "volatile": {
                "position_sizing": {"scale": 0.8},  # Decrease size by 20%
                "risk_limits": {"max_drawdown": 0.15}  # Lower drawdown threshold
            }
        }
        
        # Performance window tracking
        self.performance_window = 20  # days
        self.performance_scale_factor = 1.0
        self.last_performance_update = None
        
        # Volatility tracking
        self.volatility_lookback = 20  # days
        self.volatility_threshold = 0.015  # 1.5% daily
        self.current_volatility_scale = 1.0
        
        # Extended risk state
        self.risk_state.update({
            'regime': self.current_regime,
            'performance_scale': self.performance_scale_factor,
            'volatility_scale': self.current_volatility_scale,
            'aggregate_scale': 1.0  # Combined scaling factor
        })
        
        # Register for regime events
        if self.event_bus:
            self.event_bus.subscribe(EventType.REGIME_CHANGE, self.on_regime_change)
    
    def configure(self, config):
        """
        Configure the adaptive risk manager.
        
        Args:
            config: Configuration dictionary or ConfigSection
        """
        super().configure(config)
        
        if hasattr(config, 'as_dict'):
            config_dict = config.as_dict()
        else:
            config_dict = dict(config)
        
        # Configure regime parameters
        if 'regimes' in config_dict:
            for regime, params in config_dict['regimes'].items():
                if regime in self.regime_parameters:
                    # Update existing regime
                    for section, section_params in params.items():
                        if section in self.regime_parameters[regime]:
                            self.regime_parameters[regime][section].update(section_params)
                        else:
                            self.regime_parameters[regime][section] = section_params
                else:
                    # Add new regime
                    self.regime_parameters[regime] = params
        
        # Configure performance tracking
        if 'performance_tracking' in config_dict:
            perf_config = config_dict['performance_tracking']
            self.performance_window = perf_config.get('window', self.performance_window)
            
            # Configure scaling factors
            if 'scaling' in perf_config:
                scale_config = perf_config['scaling']
                self.performance_scale_max = scale_config.get('max', 1.5)
                self.performance_scale_min = scale_config.get('min', 0.5)
        
        # Configure volatility tracking
        if 'volatility_tracking' in config_dict:
            vol_config = config_dict['volatility_tracking']
            self.volatility_lookback = vol_config.get('lookback', self.volatility_lookback)
            self.volatility_threshold = vol_config.get('threshold', self.volatility_threshold)
            
            # Configure scaling factors
            if 'scaling' in vol_config:
                scale_config = vol_config['scaling']
                self.volatility_scale_max = scale_config.get('max', 1.2)
                self.volatility_scale_min = scale_config.get('min', 0.5)
        
        logger.info(f"Configured adaptive risk manager: {self.name}")
    
    def on_signal(self, signal_event):
        """
        Process a signal event and generate an order if appropriate.
        
        Args:
            signal_event: Signal event to process
            
        Returns:
            Generated order event or None
        """
        # Update adaptive factors
        self._update_adaptive_factors(signal_event)
        
        # Process signal using standard logic
        return super().on_signal(signal_event)
    
    def on_regime_change(self, regime_event):
        """
        Handle regime change events.
        
        Args:
            regime_event: Regime change event
        """
        regime = regime_event.data.get('regime')
        
        if not regime:
            logger.warning("Received regime change event with no regime specified")
            return
        
        if regime not in self.regime_parameters:
            logger.warning(f"Unknown regime: {regime}, ignoring")
            return
        
        # Update current regime
        self.current_regime = regime
        self.risk_state['regime'] = regime
        
        logger.info(f"Regime changed to: {regime}")
        
        # Apply regime-specific parameters
        self._apply_regime_parameters()
    
    def size_position(self, signal_event):
        """
        Calculate position size for a signal with adaptive scaling.
        
        Args:
            signal_event: Signal event to size
            
        Returns:
            float: Calculated position size
        """
        # Apply adaptive scaling
        aggregate_scale = self.risk_state['aggregate_scale']
        
        # Add scaling factors to context
        context = {
            'signal_metadata': signal_event.data.get('metadata', {}),
            'confidence': signal_event.data.get('confidence', 1.0),
            'size_adjustment': aggregate_scale
        }
        
        # Add regime information
        context['regime'] = self.current_regime
        
        # Add drawdown adjustment if applicable
        if self.config['drawdown_control']['enabled']:
            context['size_adjustment'] *= self.risk_state['drawdown_adjustment']
        
        # Add volatility if available
        if hasattr(self, 'market_volatility'):
            context['volatility'] = self.market_volatility
        
        # Extract signal information
        symbol = signal_event.data.get('symbol')
        direction = signal_event.data.get('direction')
        price = signal_event.data.get('price', 0.0)
        
        # Calculate position size
        size = self.position_sizer.calculate_position_size(
            symbol=symbol,
            direction=direction,
            price=price,
            portfolio=self.portfolio_manager,
            context=context
        )
        
        return size
    
    def _update_adaptive_factors(self, signal_event=None):
        """
        Update adaptive risk scaling factors.
        
        Args:
            signal_event: Optional signal event
        """
        # Update performance scaling
        self._update_performance_scaling()
        
        # Update volatility scaling
        self._update_volatility_scaling(signal_event)
        
        # Calculate aggregate scaling factor
        performance_scale = self.risk_state['performance_scale']
        volatility_scale = self.risk_state['volatility_scale']
        
        # Calculate aggregate scale (conservative approach - use minimum)
        aggregate_scale = min(performance_scale, volatility_scale)
        
        # Apply any regime-specific scaling
        regime = self.current_regime
        if regime in self.regime_parameters and 'position_sizing' in self.regime_parameters[regime]:
            regime_scale = self.regime_parameters[regime]['position_sizing'].get('scale', 1.0)
            aggregate_scale *= regime_scale
        
        # Update risk state
        self.risk_state['aggregate_scale'] = aggregate_scale
        
        logger.debug(f"Updated adaptive factors: performance={performance_scale:.2f}, volatility={volatility_scale:.2f}, aggregate={aggregate_scale:.2f}")
    
    def _update_performance_scaling(self):
        """Update performance-based scaling."""
        # Check if we have equity curve data
        if not hasattr(self.portfolio_manager, 'get_returns'):
            return
        
        now = datetime.datetime.now()
        
        # Only update periodically
        if (self.last_performance_update and 
            (now - self.last_performance_update).total_seconds() < 3600):  # Hourly updates
            return
        
        # Get recent returns
        returns = self.portfolio_manager.get_returns()
        
        if returns.empty:
            return
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(returns)
        
        # Calculate performance scale factor
        scale_factor = 1.0
        
        # Scale based on Sharpe ratio
        sharpe = performance_metrics.get('sharpe_ratio', 0.0)
        
        if sharpe >= 2.0:
            # Excellent performance - scale up
            scale_factor = min(1.5, 1.0 + (sharpe - 2.0) * 0.25)
        elif sharpe <= 0.0:
            # Poor performance - scale down
            scale_factor = max(0.5, 1.0 + sharpe * 0.25)
        
        # Scale based on win rate
        win_rate = performance_metrics.get('win_rate', 0.5)
        
        if win_rate >= 0.6:
            # Good win rate - scale up
            win_scale = 1.0 + (win_rate - 0.6) * 0.5
            scale_factor = max(scale_factor, win_scale)
        elif win_rate <= 0.4:
            # Poor win rate - scale down
            win_scale = 1.0 - (0.4 - win_rate) * 0.5
            scale_factor = min(scale_factor, win_scale)
        
        # Update scale factor
        self.performance_scale_factor = scale_factor
        self.risk_state['performance_scale'] = scale_factor
        self.last_performance_update = now
        
        logger.info(f"Updated performance scaling factor: {scale_factor:.2f} based on Sharpe={sharpe:.2f}, win_rate={win_rate:.2f}")
    
    def _update_volatility_scaling(self, signal_event=None):
        """
        Update volatility-based scaling.
        
        Args:
            signal_event: Optional signal event with volatility information
        """
        # Try to get volatility from signal event
        if signal_event and 'volatility' in signal_event.data:
            volatility = signal_event.data['volatility']
            self.market_volatility = volatility
        elif signal_event and 'metadata' in signal_event.data:
            metadata = signal_event.data['metadata']
            if 'volatility' in metadata:
                volatility = metadata['volatility']
                self.market_volatility = volatility
            else:
                return  # No volatility information
        else:
            # Try to calculate from returns
            if not hasattr(self.portfolio_manager, 'get_returns'):
                return
                
            returns = self.portfolio_manager.get_returns()
            
            if returns.empty:
                return
                
            # Calculate rolling volatility
            if len(returns) >= self.volatility_lookback:
                volatility = returns.rolling(self.volatility_lookback).std().iloc[-1]
                self.market_volatility = volatility
            else:
                return  # Not enough data
        
        # Calculate volatility scale factor
        threshold = self.volatility_threshold
        
        if volatility > threshold:
            # High volatility - scale down
            ratio = volatility / threshold
            scale_factor = 1.0 / ratio
            scale_factor = max(0.5, min(1.0, scale_factor))
        else:
            # Normal or low volatility - scale up or normal
            ratio = volatility / threshold
            scale_factor = min(1.2, 1.0 + (1.0 - ratio) * 0.2)
        
        # Update scale factor
        self.current_volatility_scale = scale_factor
        self.risk_state['volatility_scale'] = scale_factor
        
        logger.debug(f"Updated volatility scaling factor: {scale_factor:.2f} based on volatility={volatility:.4f}")
    
    def _apply_regime_parameters(self):
        """Apply parameters for the current regime."""
        regime = self.current_regime
        
        if regime not in self.regime_parameters:
            return
        
        regime_params = self.regime_parameters[regime]
        
        # Apply position sizing parameters
        if 'position_sizing' in regime_params and hasattr(self.position_sizer, 'set_parameters'):
            sizing_params = regime_params['position_sizing']
            logger.info(f"Applying regime '{regime}' position sizing parameters: {sizing_params}")
            # Filter out scale param as it's handled separately
            sizing_params_filtered = {k: v for k, v in sizing_params.items() if k != 'scale'}
            self.position_sizer.set_parameters(sizing_params_filtered)
        
        # Apply risk limit parameters
        if 'risk_limits' in regime_params:
            limit_params = regime_params['risk_limits']
            logger.info(f"Applying regime '{regime}' risk limit parameters: {limit_params}")
            
            # Update each limit
            for limit in self.limit_manager.limits:
                limit_name = limit.name.lower()
                if limit_name in limit_params:
                    if hasattr(limit, 'params'):
                        param_key = next((key for key in limit.params.keys() if key.startswith('max_')), None)
                        if param_key:
                            limit.params[param_key] = limit_params[limit_name]
                            logger.debug(f"Updated limit {limit_name}: {param_key}={limit_params[limit_name]}")
    
    def _calculate_performance_metrics(self, returns):
        """
        Calculate performance metrics from returns.
        
        Args:
            returns: Return series
            
        Returns:
            Dict with performance metrics
        """
        # Limit to performance window
        if len(returns) > self.performance_window:
            returns = returns.iloc[-self.performance_window:]
        
        # Calculate metrics
        metrics = {}
        
        # Sharpe ratio (annualized)
        if len(returns) > 1:
            trading_days_per_year = 252
            sharpe = returns.mean() / returns.std() * (trading_days_per_year ** 0.5) if returns.std() > 0 else 0
            metrics['sharpe_ratio'] = sharpe
        
        # Win rate (from trades)
        trades = self.portfolio_manager.get_closed_trades() if hasattr(self.portfolio_manager, 'get_closed_trades') else []
        
        if trades:
            # Limit to recent trades
            recent_trades = sorted(trades, key=lambda t: t.get('timestamp', datetime.datetime.now()))[-20:]
            
            # Calculate win rate
            win_count = sum(1 for trade in recent_trades if trade.get('realized_pnl', 0) > 0)
            win_rate = win_count / len(recent_trades) if recent_trades else 0.5
            metrics['win_rate'] = win_rate
        
        return metrics
    
    def reset(self):
        """Reset risk manager state."""
        super().reset()
        
        # Reset adaptive state
        self.current_regime = "normal"
        self.performance_scale_factor = 1.0
        self.current_volatility_scale = 1.0
        self.last_performance_update = None
        
        # Reset extended risk state
        self.risk_state.update({
            'regime': self.current_regime,
            'performance_scale': self.performance_scale_factor,
            'volatility_scale': self.current_volatility_scale,
            'aggregate_scale': 1.0
        })
        
        logger.info(f"Reset adaptive risk manager: {self.name}")
    
    def get_stats(self):
        """
        Get adaptive risk manager statistics.
        
        Returns:
            Dict with statistics
        """
        # Get base stats
        stats = super().get_stats()
        
        # Add adaptive stats
        stats.update({
            'regime': self.current_regime,
            'performance_scale': self.performance_scale_factor,
            'volatility_scale': self.current_volatility_scale,
            'aggregate_scale': self.risk_state['aggregate_scale']
        })
        
        return stats