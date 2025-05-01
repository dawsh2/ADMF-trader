#!/usr/bin/env python3
"""
Parameter Store Demo Script.

This script demonstrates the use of the ParameterStore class for:
1. Saving parameters with version tracking
2. Loading parameters
3. Comparing different parameter versions
4. Creating and loading config snapshots
5. Simulating parameter optimization workflow
"""
import os
import json
import yaml
import time
import argparse
import datetime
from typing import Dict, Any

from src.core.config.parameter_store import ParameterStore

def demo_basic_usage(store):
    """Demonstrate basic parameter store usage."""
    print("\n=== Basic Parameter Store Demo ===\n")
    
    # Example strategy parameters
    ma_crossover_params = {
        "fast_window": 10,
        "slow_window": 30,
        "price_key": "close",
        "symbols": ["SPY", "QQQ"]
    }
    
    # Save parameters
    version1 = store.save_parameters(
        component_type="strategies",
        component_name="ma_crossover",
        parameters=ma_crossover_params,
        comment="Initial version"
    )
    
    print(f"Saved MA Crossover parameters as version: {version1}")
    
    # Modify parameters
    ma_crossover_params["fast_window"] = 5
    ma_crossover_params["slow_window"] = 20
    
    # Save updated parameters
    version2 = store.save_parameters(
        component_type="strategies",
        component_name="ma_crossover",
        parameters=ma_crossover_params,
        comment="Optimized windows"
    )
    
    print(f"Saved updated MA Crossover parameters as version: {version2}")
    
    # Load parameters
    loaded_params = store.load_parameters(
        component_type="strategies",
        component_name="ma_crossover"
    )
    
    print("\nLoaded parameters (latest version):")
    print(json.dumps(loaded_params, indent=2))
    
    # Compare versions
    comparison = store.compare_versions(
        component_type="strategies",
        component_name="ma_crossover",
        version1=version1,
        version2=version2
    )
    
    print("\nVersion comparison:")
    print(json.dumps(comparison["differences"], indent=2))

def demo_version_history(store):
    """Demonstrate parameter version history."""
    print("\n=== Parameter Version History Demo ===\n")
    
    # Create risk manager parameters
    risk_params = {
        "position_size": 100,
        "max_position_pct": 0.1
    }
    
    # Save initial version
    store.save_parameters(
        component_type="risk_managers",
        component_name="enhanced",
        parameters=risk_params,
        comment="Initial version"
    )
    
    # Create multiple versions
    for i in range(3):
        # Modify parameters
        risk_params["position_size"] += 50
        risk_params["max_position_pct"] += 0.02
        
        # Add a new parameter in later versions
        if i >= 1:
            risk_params["drawdown_threshold"] = 0.05 + (i * 0.01)
        
        # Save new version
        store.save_parameters(
            component_type="risk_managers",
            component_name="enhanced",
            parameters=risk_params,
            comment=f"Updated version {i+1}"
        )
        
        # Small delay to ensure different timestamps
        time.sleep(1)
    
    # Get version history
    history = store.get_version_history(
        component_type="risk_managers",
        component_name="enhanced"
    )
    
    print("Version history:")
    for version in history:
        print(f" - {version['version']}: {version['comment']} ({version['timestamp']})")
    
    # Load a specific version (not the latest)
    second_version = history[2]["version"]  # Third item (index 2) is the second version
    params = store.load_parameters(
        component_type="risk_managers",
        component_name="enhanced",
        version=second_version
    )
    
    print(f"\nLoaded specific version ({second_version}):")
    print(json.dumps(params, indent=2))

def demo_config_snapshots(store):
    """Demonstrate configuration snapshots."""
    print("\n=== Configuration Snapshots Demo ===\n")
    
    # Create a sample configuration
    config = {
        "backtest": {
            "initial_capital": 100000.0,
            "symbols": ["SPY", "QQQ"],
            "start_date": "2023-01-01",
            "end_date": "2023-12-31"
        },
        "strategies": {
            "ma_crossover": {
                "enabled": True,
                "fast_window": 5,
                "slow_window": 20
            },
            "mean_reversion": {
                "enabled": False,
                "window": 20,
                "std_dev_multiplier": 2.0
            }
        },
        "risk_manager": {
            "type": "enhanced",
            "position_size": 100,
            "max_position_pct": 0.1
        }
    }
    
    # Save snapshot
    snapshot_name = store.save_config_snapshot(config)
    print(f"Saved configuration snapshot: {snapshot_name}")
    
    # Modify configuration
    config["backtest"]["initial_capital"] = 200000.0
    config["strategies"]["mean_reversion"]["enabled"] = True
    
    # Save another snapshot
    snapshot_name2 = store.save_config_snapshot(config, "modified_config")
    print(f"Saved modified configuration snapshot: {snapshot_name2}")
    
    # Load snapshot
    loaded_config = store.load_config_snapshot(snapshot_name)
    print("\nLoaded original snapshot:")
    print(f"Initial capital: {loaded_config['backtest']['initial_capital']}")
    print(f"Mean reversion enabled: {loaded_config['strategies']['mean_reversion']['enabled']}")
    
    # Load latest snapshot
    latest_config = store.load_config_snapshot()
    print("\nLoaded latest snapshot:")
    print(f"Initial capital: {latest_config['backtest']['initial_capital']}")
    print(f"Mean reversion enabled: {latest_config['strategies']['mean_reversion']['enabled']}")

def demo_optimization_workflow(store):
    """Demonstrate parameter optimization workflow."""
    print("\n=== Parameter Optimization Workflow Demo ===\n")
    
    # Initial parameters
    initial_params = {
        "window": 20,
        "std_dev_multiplier": 2.0,
        "use_atr": False
    }
    
    # Save initial parameters
    initial_version = store.save_parameters(
        component_type="strategies",
        component_name="mean_reversion",
        parameters=initial_params,
        comment="Initial parameters"
    )
    
    print(f"Saved initial parameters as version: {initial_version}")
    
    # Simulate optimization process
    print("\nSimulating optimization process...")
    time.sleep(1)
    
    # Optimized parameters
    optimized_params = {
        "window": 15,
        "std_dev_multiplier": 1.5,
        "use_atr": True,
        "atr_period": 14,
        "atr_multiplier": 2.0
    }
    
    # Create optimizer results
    optimizer_config = {
        "method": "grid_search",
        "metric": "sharpe_ratio",
        "start_params": initial_params,
        "best_params": optimized_params,
        "best_score": 1.85,
        "iterations": 100,
        "duration": 120.5,
        "parameter_space": {
            "window": [10, 15, 20, 25],
            "std_dev_multiplier": [1.0, 1.5, 2.0, 2.5],
            "use_atr": [True, False]
        },
        "all_results": [
            {"params": {"window": 10, "std_dev_multiplier": 1.0}, "score": 1.2},
            {"params": {"window": 15, "std_dev_multiplier": 1.5}, "score": 1.85},
            {"params": {"window": 20, "std_dev_multiplier": 2.0}, "score": 1.4}
        ]
    }
    
    # Save optimization results
    opt_version = store.optimize_parameters(
        component_type="strategies",
        component_name="mean_reversion",
        optimizer_config=optimizer_config
    )
    
    print(f"Saved optimized parameters as version: {opt_version}")
    
    # Load optimized parameters
    opt_params, metadata = store.load_parameters(
        component_type="strategies",
        component_name="mean_reversion",
        include_metadata=True
    )
    
    print("\nLoaded optimized parameters:")
    print(json.dumps(opt_params, indent=2))
    
    if "optimization" in metadata:
        print("\nOptimization metadata:")
        print(f"Method: {metadata['optimization']['method']}")
        print(f"Metric: {metadata['optimization']['metric']}")
        print(f"Score: {metadata['optimization']['score']}")
        print(f"Iterations: {metadata['optimization']['iterations']}")

def demo_import_export(store):
    """Demonstrate parameter import/export functionality."""
    print("\n=== Parameter Import/Export Demo ===\n")
    
    # Sample parameters for export
    regime_params = {
        "trend_detector": {
            "period": 14,
            "trending_threshold": 25,
            "mean_reverting_threshold": 15
        },
        "volatility_detector": {
            "window": 20,
            "volatile_threshold": 1.5,
            "trend_threshold": 0.8
        },
        "weights": {
            "trend": 0.6,
            "volatility": 0.4
        }
    }
    
    # Save parameters
    version = store.save_parameters(
        component_type="regimes",
        component_name="multi_factor",
        parameters=regime_params,
        comment="Standard regime detector configuration"
    )
    
    print(f"Saved regime parameters as version: {version}")
    
    # Export parameters
    export_path = store.export_parameters(
        component_type="regimes",
        component_name="multi_factor",
        format="yaml"
    )
    
    print(f"Exported parameters to: {export_path}")
    
    # Modify parameters (to demonstrate reimport)
    regime_params["weights"]["trend"] = 0.7
    regime_params["weights"]["volatility"] = 0.3
    
    # Save modified parameters
    store.save_parameters(
        component_type="regimes",
        component_name="multi_factor",
        parameters=regime_params,
        comment="Modified weights"
    )
    
    # Import parameters from exported file
    import_version = store.import_parameters(
        file_path=export_path,
        component_type="regimes",
        component_name="multi_factor",
        comment="Reimported original weights"
    )
    
    print(f"Imported parameters as version: {import_version}")
    
    # Load imported parameters
    imported_params = store.load_parameters(
        component_type="regimes",
        component_name="multi_factor",
        version=import_version
    )
    
    print("\nLoaded imported parameters:")
    print(f"Trend weight: {imported_params['weights']['trend']}")
    print(f"Volatility weight: {imported_params['weights']['volatility']}")

def main():
    parser = argparse.ArgumentParser(description="Parameter Store Demo")
    parser.add_argument("--base-dir", default="./params", help="Base directory for parameter store")
    args = parser.parse_args()
    
    # Create parameter store
    store = ParameterStore(base_dir=args.base_dir)
    
    # Run demos
    demo_basic_usage(store)
    demo_version_history(store)
    demo_config_snapshots(store)
    demo_optimization_workflow(store)
    demo_import_export(store)
    
    print("\nParameter Store demo completed!")

if __name__ == "__main__":
    main()