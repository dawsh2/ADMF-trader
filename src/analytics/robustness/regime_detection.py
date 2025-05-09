"""
Market regime detection for strategy testing.

This module provides functionality for detecting different market regimes (trending, mean-reverting,
high-volatility, etc.) to test strategy performance across various market conditions.
"""

import numpy as np
import pandas as pd
import logging
from enum import Enum
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime types."""
    UNKNOWN = 0
    BULLISH_TREND = 1
    BEARISH_TREND = 2
    SIDEWAYS = 3
    HIGH_VOLATILITY = 4
    LOW_VOLATILITY = 5
    MEAN_REVERTING = 6


class RegimeDetector:
    """
    Detect market regimes from price data.
    
    This class provides different methods for identifying market regimes,
    including trend detection, volatility analysis, and statistical properties.
    """
    
    def __init__(self, window_size: int = 20):
        """
        Initialize regime detector.
        
        Args:
            window_size: Window size for rolling calculations
        """
        self.window_size = window_size
    
    def _calculate_features(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate features for regime detection.
        
        Args:
            price_data: DataFrame with price data (must have 'close' column)
            
        Returns:
            DataFrame with calculated features
        """
        if 'close' not in price_data.columns:
            raise ValueError("Price data must have 'close' column")
            
        # Create features DataFrame
        features = pd.DataFrame(index=price_data.index)
        
        # Calculate returns
        features['returns'] = price_data['close'].pct_change()
        
        # Calculate log returns
        features['log_returns'] = np.log(price_data['close']).diff()
        
        # Calculate rolling mean
        features['rolling_mean'] = price_data['close'].rolling(self.window_size).mean()
        
        # Calculate rolling volatility
        features['rolling_volatility'] = features['returns'].rolling(self.window_size).std()
        
        # Calculate distance from rolling mean (normalized)
        features['mean_distance'] = (price_data['close'] - features['rolling_mean']) / features['rolling_mean']
        
        # Calculate directional movement
        features['direction'] = features['returns'].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        
        # Calculate rolling autocorrelation (lag 1)
        features['autocorrelation'] = features['returns'].rolling(self.window_size).apply(
            lambda x: x.autocorr(lag=1) if len(x.dropna()) > 1 else np.nan
        )
        
        # Calculate rolling Hurst exponent (simplified)
        def hurst_exponent(series):
            if len(series.dropna()) < 10:
                return np.nan
                
            lags = range(2, min(10, len(series) // 4))
            tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
            
            if not tau or any(np.isnan(tau)) or any(np.isinf(tau)):
                return np.nan
                
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0] / 2.0
        
        features['hurst'] = features['log_returns'].rolling(self.window_size).apply(
            lambda x: hurst_exponent(x.dropna())
        )
        
        # Fill NaN values
        features = features.fillna(method='bfill').fillna(0)
        
        return features
    
    def detect_trend_based_regime(self, price_data: pd.DataFrame, 
                                  long_window: int = 50, 
                                  volatility_threshold: float = 0.015) -> pd.Series:
        """
        Detect regime based on trends and volatility.
        
        Args:
            price_data: DataFrame with price data (must have 'close' column)
            long_window: Window size for longer-term trend
            volatility_threshold: Threshold for high/low volatility
            
        Returns:
            Series with regime labels
        """
        features = self._calculate_features(price_data)
        
        # Calculate longer-term moving average
        long_ma = price_data['close'].rolling(long_window).mean()
        
        # Initialize regime series
        regimes = pd.Series(MarketRegime.UNKNOWN.value, index=price_data.index)
        
        # Determine regime based on trend direction and volatility
        for i in range(long_window, len(price_data)):
            price = price_data['close'].iloc[i]
            volatility = features['rolling_volatility'].iloc[i]
            auto_corr = features['autocorrelation'].iloc[i]
            
            # Check volatility
            high_vol = volatility > volatility_threshold
            
            # Check trend
            trend_up = price > long_ma.iloc[i] and features['returns'].iloc[i-5:i].mean() > 0
            trend_down = price < long_ma.iloc[i] and features['returns'].iloc[i-5:i].mean() < 0
            
            # Check mean reversion
            mean_reverting = auto_corr < -0.3 if not np.isnan(auto_corr) else False
            
            # Assign regime
            if high_vol:
                regimes.iloc[i] = MarketRegime.HIGH_VOLATILITY.value
            elif mean_reverting:
                regimes.iloc[i] = MarketRegime.MEAN_REVERTING.value
            elif trend_up:
                regimes.iloc[i] = MarketRegime.BULLISH_TREND.value
            elif trend_down:
                regimes.iloc[i] = MarketRegime.BEARISH_TREND.value
            else:
                regimes.iloc[i] = MarketRegime.SIDEWAYS.value
        
        return regimes
    
    def detect_volatility_based_regime(self, price_data: pd.DataFrame,
                                      high_threshold: float = 0.02,
                                      low_threshold: float = 0.005) -> pd.Series:
        """
        Detect regime based on volatility levels.
        
        Args:
            price_data: DataFrame with price data (must have 'close' column)
            high_threshold: Threshold for high volatility
            low_threshold: Threshold for low volatility
            
        Returns:
            Series with regime labels
        """
        features = self._calculate_features(price_data)
        
        # Initialize regime series
        regimes = pd.Series(MarketRegime.UNKNOWN.value, index=price_data.index)
        
        # Determine regime based on volatility
        for i in range(self.window_size, len(price_data)):
            volatility = features['rolling_volatility'].iloc[i]
            
            if volatility > high_threshold:
                regimes.iloc[i] = MarketRegime.HIGH_VOLATILITY.value
            elif volatility < low_threshold:
                regimes.iloc[i] = MarketRegime.LOW_VOLATILITY.value
            else:
                # Check trend direction for moderate volatility
                returns_mean = features['returns'].iloc[i-5:i].mean()
                
                if returns_mean > 0.001:
                    regimes.iloc[i] = MarketRegime.BULLISH_TREND.value
                elif returns_mean < -0.001:
                    regimes.iloc[i] = MarketRegime.BEARISH_TREND.value
                else:
                    regimes.iloc[i] = MarketRegime.SIDEWAYS.value
        
        return regimes
    
    def detect_hurst_based_regime(self, price_data: pd.DataFrame) -> pd.Series:
        """
        Detect regime based on Hurst exponent (trending vs. mean-reverting).
        
        Args:
            price_data: DataFrame with price data (must have 'close' column)
            
        Returns:
            Series with regime labels
        """
        features = self._calculate_features(price_data)
        
        # Initialize regime series
        regimes = pd.Series(MarketRegime.UNKNOWN.value, index=price_data.index)
        
        # Determine regime based on Hurst exponent
        for i in range(self.window_size, len(price_data)):
            hurst = features['hurst'].iloc[i]
            volatility = features['rolling_volatility'].iloc[i]
            returns_mean = features['returns'].iloc[i-5:i].mean()
            
            if np.isnan(hurst):
                continue
                
            # Hurst > 0.6 indicates trending, < 0.4 indicates mean-reverting
            if hurst > 0.6:
                # Trending - check direction
                if returns_mean > 0:
                    regimes.iloc[i] = MarketRegime.BULLISH_TREND.value
                else:
                    regimes.iloc[i] = MarketRegime.BEARISH_TREND.value
            elif hurst < 0.4:
                regimes.iloc[i] = MarketRegime.MEAN_REVERTING.value
            else:
                # Random walk - check volatility
                if volatility > 0.015:
                    regimes.iloc[i] = MarketRegime.HIGH_VOLATILITY.value
                else:
                    regimes.iloc[i] = MarketRegime.SIDEWAYS.value
        
        return regimes
    
    def detect_regime_clustering(self, price_data: pd.DataFrame, n_clusters: int = 5) -> pd.Series:
        """
        Detect regime using unsupervised clustering.
        
        Args:
            price_data: DataFrame with price data (must have 'close' column)
            n_clusters: Number of clusters (regimes) to detect
            
        Returns:
            Series with regime cluster labels
        """
        features = self._calculate_features(price_data)
        
        # Select features for clustering
        cluster_features = features[['returns', 'rolling_volatility', 'mean_distance', 'autocorrelation']]
        
        # Standardize features
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(cluster_features.dropna())
        
        # Apply KMeans clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(scaled_features)
        
        # Create a Series with cluster labels
        regime_clusters = pd.Series(MarketRegime.UNKNOWN.value, index=price_data.index)
        regime_clusters.iloc[self.window_size:self.window_size + len(clusters)] = clusters
        
        # Map clusters to regime types (simplified)
        cluster_volatility = {}
        cluster_returns = {}
        
        for cluster in range(n_clusters):
            cluster_mask = clusters == cluster
            cluster_volatility[cluster] = np.mean(scaled_features[cluster_mask, 1])  # volatility column
            cluster_returns[cluster] = np.mean(scaled_features[cluster_mask, 0])  # returns column
        
        # Map clusters to regimes based on their properties
        cluster_mapping = {}
        
        for cluster in range(n_clusters):
            vol = cluster_volatility[cluster]
            ret = cluster_returns[cluster]
            
            if vol > 1.0:  # high standardized volatility
                cluster_mapping[cluster] = MarketRegime.HIGH_VOLATILITY.value
            elif vol < -0.5:  # low standardized volatility
                cluster_mapping[cluster] = MarketRegime.LOW_VOLATILITY.value
            elif ret > 0.5:  # high positive returns
                cluster_mapping[cluster] = MarketRegime.BULLISH_TREND.value
            elif ret < -0.5:  # high negative returns
                cluster_mapping[cluster] = MarketRegime.BEARISH_TREND.value
            else:
                cluster_mapping[cluster] = MarketRegime.SIDEWAYS.value
        
        # Map cluster numbers to regime types
        mapped_regimes = regime_clusters.copy()
        for i in range(len(mapped_regimes)):
            if mapped_regimes.iloc[i] in cluster_mapping:
                mapped_regimes.iloc[i] = cluster_mapping[mapped_regimes.iloc[i]]
        
        return mapped_regimes
    
    def detect_regimes(self, price_data: pd.DataFrame, method: str = "trend") -> pd.Series:
        """
        Detect market regimes using the specified method.
        
        Args:
            price_data: DataFrame with price data (must have 'close' column)
            method: Detection method ('trend', 'volatility', 'hurst', or 'clustering')
            
        Returns:
            Series with regime labels
        """
        if method == "trend":
            return self.detect_trend_based_regime(price_data)
        elif method == "volatility":
            return self.detect_volatility_based_regime(price_data)
        elif method == "hurst":
            return self.detect_hurst_based_regime(price_data)
        elif method == "clustering":
            return self.detect_regime_clustering(price_data)
        else:
            raise ValueError(f"Unknown regime detection method: {method}")
    
    def get_regime_periods(self, regimes: pd.Series) -> Dict[int, List[Tuple[pd.Timestamp, pd.Timestamp]]]:
        """
        Get time periods for each regime.
        
        Args:
            regimes: Series with regime labels
            
        Returns:
            Dictionary mapping regime values to list of (start, end) timestamp tuples
        """
        regime_periods = {}
        
        # Initialize with empty lists for each regime
        for regime in MarketRegime:
            regime_periods[regime.value] = []
        
        # Find continuous periods for each regime
        current_regime = None
        start_idx = None
        
        for idx, regime in regimes.items():
            if regime != current_regime:
                if current_regime is not None and start_idx is not None:
                    # End of a regime period
                    regime_periods[current_regime].append((start_idx, idx))
                
                # Start of a new regime period
                current_regime = regime
                start_idx = idx
        
        # Add the last period
        if current_regime is not None and start_idx is not None:
            regime_periods[current_regime].append((start_idx, regimes.index[-1]))
        
        return regime_periods
    
    def get_regime_stats(self, price_data: pd.DataFrame, regimes: pd.Series) -> Dict[int, Dict[str, float]]:
        """
        Calculate statistics for each regime.
        
        Args:
            price_data: DataFrame with price data (must have 'close' column)
            regimes: Series with regime labels
            
        Returns:
            Dictionary mapping regime values to statistics
        """
        features = self._calculate_features(price_data)
        
        # Calculate returns
        returns = features['returns']
        
        # Initialize stats for each regime
        regime_stats = {}
        
        for regime in MarketRegime:
            regime_mask = (regimes == regime.value)
            regime_returns = returns[regime_mask]
            
            if len(regime_returns) > 0:
                # Calculate statistics
                regime_stats[regime.value] = {
                    'count': len(regime_returns),
                    'mean_return': regime_returns.mean(),
                    'std_return': regime_returns.std(),
                    'min_return': regime_returns.min(),
                    'max_return': regime_returns.max(),
                    'cumulative_return': (1 + regime_returns).prod() - 1,
                    'sharpe_ratio': regime_returns.mean() / regime_returns.std() if regime_returns.std() > 0 else 0
                }
            else:
                regime_stats[regime.value] = {
                    'count': 0,
                    'mean_return': 0,
                    'std_return': 0,
                    'min_return': 0,
                    'max_return': 0,
                    'cumulative_return': 0,
                    'sharpe_ratio': 0
                }
        
        return regime_stats


class RegimeAnalyzer:
    """
    Analyze strategy performance across different market regimes.
    
    This class helps assess strategy robustness by evaluating performance
    separately for each detected market regime.
    """
    
    def __init__(self, regime_detector: Optional[RegimeDetector] = None):
        """
        Initialize regime analyzer.
        
        Args:
            regime_detector: RegimeDetector instance (creates a new one if None)
        """
        self.regime_detector = regime_detector or RegimeDetector()
    
    def analyze_strategy_by_regime(self, price_data: pd.DataFrame, 
                                  strategy_returns: pd.Series,
                                  detection_method: str = "trend") -> Dict[str, Any]:
        """
        Analyze strategy performance across different market regimes.
        
        Args:
            price_data: DataFrame with price data (must have 'close' column)
            strategy_returns: Series with strategy returns
            detection_method: Regime detection method
            
        Returns:
            Dictionary with analysis results
        """
        # Detect regimes
        regimes = self.regime_detector.detect_regimes(price_data, method=detection_method)
        
        # Align strategy returns with regimes
        aligned_returns = strategy_returns.reindex(regimes.index, method='ffill')
        
        # Get regime names for reporting
        regime_names = {regime.value: regime.name for regime in MarketRegime}
        
        # Initialize results
        results = {
            'regime_performance': {},
            'regime_stats': {},
            'regime_periods': {},
            'regime_drawdowns': {},
            'regime_sharpe_ratios': {},
            'best_regime': None,
            'worst_regime': None,
            'consistency_score': 0.0
        }
        
        # Calculate performance metrics for each regime
        for regime in MarketRegime:
            regime_mask = (regimes == regime.value)
            regime_count = regime_mask.sum()
            
            if regime_count > 0:
                # Get returns for this regime
                regime_returns = aligned_returns[regime_mask]
                
                # Calculate metrics
                total_return = (1 + regime_returns).prod() - 1
                annualized_return = (1 + total_return) ** (252 / len(regime_returns)) - 1 if len(regime_returns) > 0 else 0
                volatility = regime_returns.std() * np.sqrt(252) if len(regime_returns) > 1 else 0
                sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
                
                # Calculate drawdown
                cum_returns = (1 + regime_returns).cumprod()
                rolling_max = cum_returns.cummax()
                drawdown = (cum_returns / rolling_max) - 1
                max_drawdown = drawdown.min()
                
                # Store results
                results['regime_performance'][regime.name] = total_return
                results['regime_sharpe_ratios'][regime.name] = sharpe_ratio
                results['regime_drawdowns'][regime.name] = max_drawdown
                
                results['regime_stats'][regime.name] = {
                    'count': regime_count,
                    'total_return': total_return,
                    'annualized_return': annualized_return,
                    'volatility': volatility,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown
                }
                
                # Store regime periods
                results['regime_periods'][regime.name] = self.regime_detector.get_regime_periods(regimes)[regime.value]
        
        # Determine best and worst regimes by return
        if results['regime_performance']:
            results['best_regime'] = max(results['regime_performance'].items(), key=lambda x: x[1])[0]
            results['worst_regime'] = min(results['regime_performance'].items(), key=lambda x: x[1])[0]
            
            # Calculate consistency score
            performance_values = list(results['regime_performance'].values())
            if performance_values:
                best_return = max(performance_values)
                worst_return = min(performance_values)
                
                if best_return > 0:
                    if worst_return >= 0:
                        # All regimes positive - calculate ratio of worst to best
                        results['consistency_score'] = worst_return / best_return
                    else:
                        # Some regimes negative - calculate ratio of range to best
                        results['consistency_score'] = (worst_return + best_return) / best_return
                else:
                    # All regimes negative or zero
                    results['consistency_score'] = 0.0
        
        return results
