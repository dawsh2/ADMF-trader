"""
Strategy state management for persistence and restoration.

This module provides functionality to save and restore strategy state,
allowing strategies to persist their internal state between runs.
"""

import json
import os
import time
import uuid
from typing import Dict, Any, Optional, List, Tuple, Type

from src.core.exceptions import StrategyError


class StrategyState:
    """Manages state for a strategy, enabling serialization and persistence."""
    
    def __init__(self, strategy_id: str, strategy_type: str, parameters: Dict[str, Any] = None):
        """Initialize strategy state.
        
        Args:
            strategy_id: Unique identifier for the strategy
            strategy_type: Type/class of the strategy
            parameters: Strategy parameters (default: None)
        """
        self.strategy_id = strategy_id
        self.strategy_type = strategy_type
        self.parameters = parameters or {}
        self.state_data = {}
        self.metadata = {
            "created_at": time.time(),
            "updated_at": time.time(),
            "version": 1,
            "uuid": str(uuid.uuid4())
        }
    
    def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Update strategy parameters.
        
        Args:
            parameters: New parameters to update
        """
        self.parameters.update(parameters)
        self._update_metadata()
    
    def set_state_data(self, state_data: Dict[str, Any]) -> None:
        """Set complete state data.
        
        Args:
            state_data: Complete state data to set
        """
        self.state_data = dict(state_data)
        self._update_metadata()
    
    def update_state_data(self, state_data: Dict[str, Any]) -> None:
        """Update state data with new values.
        
        Args:
            state_data: New state data to update
        """
        self.state_data.update(state_data)
        self._update_metadata()
    
    def get_state_value(self, key: str, default: Any = None) -> Any:
        """Get a value from state data.
        
        Args:
            key: Key to retrieve
            default: Default value if key does not exist (default: None)
            
        Returns:
            Value from state or default if not found
        """
        return self.state_data.get(key, default)
    
    def set_state_value(self, key: str, value: Any) -> None:
        """Set a single value in state data.
        
        Args:
            key: Key to set
            value: Value to set
        """
        self.state_data[key] = value
        self._update_metadata()
    
    def _update_metadata(self) -> None:
        """Update metadata when state changes."""
        self.metadata["updated_at"] = time.time()
        self.metadata["version"] += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary representation.
        
        Returns:
            Dictionary representation of state
        """
        return {
            "strategy_id": self.strategy_id,
            "strategy_type": self.strategy_type,
            "parameters": self.parameters,
            "state_data": self.state_data,
            "metadata": self.metadata
        }
    
    def to_json(self, pretty: bool = False) -> str:
        """Convert state to JSON representation.
        
        Args:
            pretty: Whether to format JSON with indentation (default: False)
            
        Returns:
            JSON representation of state
        """
        indent = 2 if pretty else None
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyState':
        """Create strategy state from dictionary representation.
        
        Args:
            data: Dictionary representation of state
            
        Returns:
            StrategyState instance
            
        Raises:
            StrategyError: If required fields are missing
        """
        required_fields = ["strategy_id", "strategy_type"]
        for field in required_fields:
            if field not in data:
                raise StrategyError(f"Missing required field '{field}' in strategy state data")
        
        state = cls(
            strategy_id=data["strategy_id"],
            strategy_type=data["strategy_type"],
            parameters=data.get("parameters", {})
        )
        
        if "state_data" in data:
            state.state_data = dict(data["state_data"])
        
        if "metadata" in data:
            state.metadata.update(data["metadata"])
        
        return state
    
    @classmethod
    def from_json(cls, json_str: str) -> 'StrategyState':
        """Create strategy state from JSON representation.
        
        Args:
            json_str: JSON representation of state
            
        Returns:
            StrategyState instance
            
        Raises:
            StrategyError: If JSON is invalid
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise StrategyError(f"Invalid JSON: {e}")
        except Exception as e:
            raise StrategyError(f"Error parsing strategy state: {e}")
    
    def save_to_file(self, filepath: str, pretty: bool = False) -> None:
        """Save strategy state to a file.
        
        Args:
            filepath: Path to save JSON file
            pretty: Whether to format JSON with indentation (default: False)
            
        Raises:
            StrategyError: If file cannot be written
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(self.to_json(pretty=pretty))
        except Exception as e:
            raise StrategyError(f"Error saving strategy state to file: {e}")
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'StrategyState':
        """Load strategy state from a file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            StrategyState instance
            
        Raises:
            StrategyError: If file cannot be read or parsed
        """
        try:
            with open(filepath, 'r') as f:
                return cls.from_json(f.read())
        except FileNotFoundError:
            raise StrategyError(f"Strategy state file not found: {filepath}")
        except Exception as e:
            raise StrategyError(f"Error loading strategy state from file: {e}")


class StrategyStateManager:
    """Manages strategy states across the system."""
    
    def __init__(self, state_dir: str = None):
        """Initialize strategy state manager.
        
        Args:
            state_dir: Directory to store state files (default: None)
        """
        self.state_dir = state_dir or os.path.join("data", "strategy_states")
        self.states: Dict[str, StrategyState] = {}
        
        # Create directory if it doesn't exist
        os.makedirs(self.state_dir, exist_ok=True)
    
    def get_state(self, strategy_id: str) -> Optional[StrategyState]:
        """Get strategy state by ID.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            StrategyState if found, None otherwise
        """
        return self.states.get(strategy_id)
    
    def add_state(self, state: StrategyState) -> None:
        """Add a strategy state to the manager.
        
        Args:
            state: StrategyState instance
        """
        self.states[state.strategy_id] = state
    
    def create_state(self, strategy_id: str, strategy_type: str, 
                    parameters: Dict[str, Any] = None) -> StrategyState:
        """Create a new strategy state and add it to the manager.
        
        Args:
            strategy_id: Unique identifier for the strategy
            strategy_type: Type/class of the strategy
            parameters: Strategy parameters (default: None)
            
        Returns:
            Created StrategyState instance
        """
        state = StrategyState(strategy_id, strategy_type, parameters)
        self.add_state(state)
        return state
    
    def remove_state(self, strategy_id: str) -> bool:
        """Remove a strategy state from the manager.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            True if state was removed, False if not found
        """
        if strategy_id in self.states:
            del self.states[strategy_id]
            return True
        return False
    
    def save_state(self, strategy_id: str, overwrite: bool = True) -> str:
        """Save a strategy state to a file.
        
        Args:
            strategy_id: Strategy identifier
            overwrite: Whether to overwrite existing file (default: True)
            
        Returns:
            Path to saved file
            
        Raises:
            StrategyError: If state not found or cannot be saved
        """
        state = self.get_state(strategy_id)
        if not state:
            raise StrategyError(f"No state found for strategy '{strategy_id}'")
        
        filename = f"{strategy_id}.json"
        filepath = os.path.join(self.state_dir, filename)
        
        if os.path.exists(filepath) and not overwrite:
            raise StrategyError(f"State file already exists: {filepath}")
        
        state.save_to_file(filepath, pretty=True)
        return filepath
    
    def load_state(self, strategy_id: str) -> StrategyState:
        """Load a strategy state from a file.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Loaded StrategyState instance
            
        Raises:
            StrategyError: If state file not found or cannot be loaded
        """
        filename = f"{strategy_id}.json"
        filepath = os.path.join(self.state_dir, filename)
        
        state = StrategyState.load_from_file(filepath)
        self.add_state(state)
        return state
    
    def list_available_states(self) -> List[str]:
        """List available state files in the state directory.
        
        Returns:
            List of strategy IDs with available state files
        """
        try:
            files = os.listdir(self.state_dir)
            return [os.path.splitext(f)[0] for f in files if f.endswith('.json')]
        except Exception:
            return []
    
    def save_all_states(self) -> Dict[str, str]:
        """Save all managed states to files.
        
        Returns:
            Dictionary mapping strategy IDs to saved file paths
        """
        saved = {}
        for strategy_id, state in self.states.items():
            try:
                filepath = self.save_state(strategy_id)
                saved[strategy_id] = filepath
            except Exception as e:
                # Log error but continue with other states
                # (logging would be added here in a real implementation)
                pass
        
        return saved
