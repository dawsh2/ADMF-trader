"""
Parameter space implementation for optimization.

This module provides classes for defining parameter spaces for strategy optimization,
including different parameter types, constraints, and search methods.
"""

import json
import random
import itertools
import math
import uuid
from typing import Dict, Any, List, Tuple, Union, Optional, Iterator, Callable

from src.core.exceptions import OptimizationError, ParameterSpaceError


class Parameter:
    """Base class for a parameter in the parameter space."""
    
    def __init__(self, name: str, param_type: str):
        """Initialize a parameter.
        
        Args:
            name: Name of the parameter
            param_type: Type of the parameter
        """
        self.name = name
        self.type = param_type
        self.id = str(uuid.uuid4())
    
    def get_grid_points(self, num_points: Optional[int] = None) -> List[Any]:
        """Get a list of grid points for this parameter.
        
        Args:
            num_points: Optional number of points to generate
            
        Returns:
            List of parameter values for grid search
        """
        raise NotImplementedError("Subclasses must implement get_grid_points")
    
    def get_random_point(self) -> Any:
        """Get a random point in the parameter space.
        
        Returns:
            Random parameter value
        """
        raise NotImplementedError("Subclasses must implement get_random_point")
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a parameter value.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        raise NotImplementedError("Subclasses must implement validate")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter to dictionary representation.
        
        Returns:
            Dictionary representation of parameter
        """
        return {
            "name": self.name,
            "type": self.type,
            "id": self.id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Parameter':
        """Create parameter from dictionary representation.
        
        Args:
            data: Dictionary representation of parameter
            
        Returns:
            Parameter instance
        
        Raises:
            ParameterSpaceError: If parameter type is unknown
        """
        param_type = data.get("type")
        if param_type == "integer":
            return IntegerParameter.from_dict(data)
        elif param_type == "float":
            return FloatParameter.from_dict(data)
        elif param_type == "categorical":
            return CategoricalParameter.from_dict(data)
        elif param_type == "boolean":
            return BooleanParameter.from_dict(data)
        else:
            raise ParameterSpaceError(
                message=f"Unknown parameter type: {param_type}"
            )


class IntegerParameter(Parameter):
    """Integer parameter with min, max, and step."""
    
    def __init__(self, name: str, min_value: int, max_value: int, 
                 step: Optional[int] = 1, log_scale: bool = False):
        """Initialize an integer parameter.
        
        Args:
            name: Name of the parameter
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            step: Step size between values (default: 1)
            log_scale: Whether to use logarithmic scale for grid points (default: False)
            
        Raises:
            ParameterSpaceError: If min > max or step <= 0
        """
        super().__init__(name, "integer")
        
        if min_value > max_value:
            raise ParameterSpaceError(
                parameter=name,
                message=f"Minimum value ({min_value}) must be <= maximum value ({max_value})"
            )
        
        if step <= 0:
            raise ParameterSpaceError(
                parameter=name,
                message=f"Step ({step}) must be > 0"
            )
        
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.log_scale = log_scale
    
    def get_grid_points(self, num_points: Optional[int] = None) -> List[int]:
        """Get a list of grid points for this parameter.
        
        Args:
            num_points: Optional number of points to generate
                (ignores step if provided)
            
        Returns:
            List of parameter values for grid search
        """
        if num_points is not None:
            # Generate num_points evenly spaced points
            if self.log_scale and self.min_value > 0:
                # Logarithmic scale
                log_min = math.log(self.min_value)
                log_max = math.log(self.max_value)
                return [
                    round(math.exp(log_min + i * (log_max - log_min) / (num_points - 1)))
                    for i in range(num_points)
                ]
            else:
                # Linear scale
                if num_points == 1:
                    return [self.min_value]
                return [
                    round(self.min_value + i * (self.max_value - self.min_value) / (num_points - 1))
                    for i in range(num_points)
                ]
        else:
            # Use step
            return list(range(self.min_value, self.max_value + 1, self.step))
    
    def get_random_point(self) -> int:
        """Get a random point in the parameter space.
        
        Returns:
            Random integer between min_value and max_value
        """
        if self.log_scale and self.min_value > 0:
            # Logarithmic scale
            log_min = math.log(self.min_value)
            log_max = math.log(self.max_value)
            return round(math.exp(random.uniform(log_min, log_max)))
        else:
            # Linear scale - ensure we respect the step size
            steps = (self.max_value - self.min_value) // self.step
            return self.min_value + random.randint(0, steps) * self.step
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a parameter value.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Type check
            if not isinstance(value, int):
                return False, f"Value must be an integer, got {type(value).__name__}"
            
            # Range check
            if value < self.min_value:
                return False, f"Value {value} is below minimum {self.min_value}"
            
            if value > self.max_value:
                return False, f"Value {value} is above maximum {self.max_value}"
            
            # Step check (if step > 1)
            if self.step > 1:
                if (value - self.min_value) % self.step != 0:
                    return False, f"Value {value} does not match step size {self.step}"
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter to dictionary representation."""
        result = super().to_dict()
        result.update({
            "min_value": self.min_value,
            "max_value": self.max_value,
            "step": self.step,
            "log_scale": self.log_scale
        })
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntegerParameter':
        """Create parameter from dictionary representation."""
        param = cls(
            name=data["name"],
            min_value=data["min_value"],
            max_value=data["max_value"],
            step=data.get("step", 1),
            log_scale=data.get("log_scale", False)
        )
        if "id" in data:
            param.id = data["id"]
        return param


class FloatParameter(Parameter):
    """Float parameter with min, max, and step."""
    
    def __init__(self, name: str, min_value: float, max_value: float, 
                 step: Optional[float] = None, log_scale: bool = False):
        """Initialize a float parameter.
        
        Args:
            name: Name of the parameter
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            step: Step size between values (default: None)
            log_scale: Whether to use logarithmic scale for grid points (default: False)
            
        Raises:
            ParameterSpaceError: If min > max or step <= 0
        """
        super().__init__(name, "float")
        
        if min_value > max_value:
            raise ParameterSpaceError(
                parameter=name,
                message=f"Minimum value ({min_value}) must be <= maximum value ({max_value})"
            )
        
        if step is not None and step <= 0:
            raise ParameterSpaceError(
                parameter=name,
                message=f"Step ({step}) must be > 0"
            )
        
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.log_scale = log_scale
    
    def get_grid_points(self, num_points: Optional[int] = None) -> List[float]:
        """Get a list of grid points for this parameter.
        
        Args:
            num_points: Optional number of points to generate
                (overrides step if provided)
            
        Returns:
            List of parameter values for grid search
        """
        if num_points is None:
            if self.step is None:
                # Default to 10 points if no step and no num_points
                num_points = 10
            else:
                # Use step if provided
                num_steps = int((self.max_value - self.min_value) / self.step) + 1
                return [self.min_value + i * self.step for i in range(num_steps)]
        
        # Generate num_points evenly spaced points
        if num_points == 1:
            return [self.min_value]
        
        if self.log_scale and self.min_value > 0:
            # Logarithmic scale
            log_min = math.log(self.min_value)
            log_max = math.log(self.max_value)
            return [
                math.exp(log_min + i * (log_max - log_min) / (num_points - 1))
                for i in range(num_points)
            ]
        else:
            # Linear scale
            return [
                self.min_value + i * (self.max_value - self.min_value) / (num_points - 1)
                for i in range(num_points)
            ]
    
    def get_random_point(self) -> float:
        """Get a random point in the parameter space.
        
        Returns:
            Random float between min_value and max_value
        """
        if self.log_scale and self.min_value > 0:
            # Logarithmic scale
            log_min = math.log(self.min_value)
            log_max = math.log(self.max_value)
            return math.exp(random.uniform(log_min, log_max))
        else:
            # Linear scale
            value = random.uniform(self.min_value, self.max_value)
            
            # Respect step if provided
            if self.step is not None:
                steps = round((value - self.min_value) / self.step)
                value = self.min_value + steps * self.step
                # Ensure we don't exceed max_value due to rounding
                value = min(value, self.max_value)
            
            return value
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a parameter value.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Type check
            if not isinstance(value, (int, float)):
                return False, f"Value must be a number, got {type(value).__name__}"
            
            # Range check
            if value < self.min_value:
                return False, f"Value {value} is below minimum {self.min_value}"
            
            if value > self.max_value:
                return False, f"Value {value} is above maximum {self.max_value}"
            
            # Step check (if provided)
            if self.step is not None:
                # Allow small floating-point errors
                step_diff = abs(((value - self.min_value) / self.step) % 1)
                if step_diff > 1e-10 and step_diff < (1 - 1e-10):
                    return False, f"Value {value} does not match step size {self.step}"
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter to dictionary representation."""
        result = super().to_dict()
        result.update({
            "min_value": self.min_value,
            "max_value": self.max_value,
            "step": self.step,
            "log_scale": self.log_scale
        })
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FloatParameter':
        """Create parameter from dictionary representation."""
        param = cls(
            name=data["name"],
            min_value=data["min_value"],
            max_value=data["max_value"],
            step=data.get("step"),
            log_scale=data.get("log_scale", False)
        )
        if "id" in data:
            param.id = data["id"]
        return param


class CategoricalParameter(Parameter):
    """Categorical parameter with a list of possible values."""
    
    def __init__(self, name: str, categories: List[Any]):
        """Initialize a categorical parameter.
        
        Args:
            name: Name of the parameter
            categories: List of possible values
            
        Raises:
            ParameterSpaceError: If categories is empty
        """
        super().__init__(name, "categorical")
        
        if not categories:
            raise ParameterSpaceError(
                parameter=name,
                message="Categories cannot be empty"
            )
        
        self.categories = list(categories)
    
    def get_grid_points(self, num_points: Optional[int] = None) -> List[Any]:
        """Get a list of grid points for this parameter.
        
        Args:
            num_points: Optional number of points to generate
                (ignores categories if provided)
            
        Returns:
            List of parameter values for grid search
        """
        if num_points is not None and num_points < len(self.categories):
            # Return a subset of categories if num_points is less than total
            indices = [int(i * len(self.categories) / num_points) for i in range(num_points)]
            return [self.categories[i] for i in indices]
        else:
            # Return all categories
            return list(self.categories)
    
    def get_random_point(self) -> Any:
        """Get a random point in the parameter space.
        
        Returns:
            Random value from categories
        """
        return random.choice(self.categories)
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a parameter value.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value not in self.categories:
            categories_str = str(self.categories)
            if len(categories_str) > 100:
                categories_str = f"{str(self.categories[:3])[:-1]}, ... (total: {len(self.categories)})]"
            return False, f"Value '{value}' is not in categories: {categories_str}"
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter to dictionary representation."""
        result = super().to_dict()
        result.update({
            "categories": self.categories
        })
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CategoricalParameter':
        """Create parameter from dictionary representation."""
        param = cls(
            name=data["name"],
            categories=data["categories"]
        )
        if "id" in data:
            param.id = data["id"]
        return param


class BooleanParameter(CategoricalParameter):
    """Boolean parameter (special case of categorical with [True, False])."""
    
    def __init__(self, name: str):
        """Initialize a boolean parameter.
        
        Args:
            name: Name of the parameter
        """
        super().__init__(name, [True, False])
        self.type = "boolean"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter to dictionary representation."""
        result = Parameter.to_dict(self)  # Skip CategoricalParameter.to_dict
        result.update({
            "categories": [True, False]
        })
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BooleanParameter':
        """Create parameter from dictionary representation."""
        param = cls(name=data["name"])
        if "id" in data:
            param.id = data["id"]
        return param


class ParameterSpace:
    """A space of parameters for optimization."""
    
    def __init__(self, name: str = "default"):
        """Initialize a parameter space.
        
        Args:
            name: Name of the parameter space
        """
        self.name = name
        self.parameters: Dict[str, Parameter] = {}
    
    def add_parameter(self, parameter: Parameter) -> None:
        """Add a parameter to the space.
        
        Args:
            parameter: Parameter to add
            
        Raises:
            ParameterSpaceError: If parameter with same name already exists
        """
        if parameter.name in self.parameters:
            raise ParameterSpaceError(
                parameter=parameter.name,
                message=f"Parameter '{parameter.name}' already exists in space"
            )
        
        self.parameters[parameter.name] = parameter
    
    def add_integer(self, name: str, min_value: int, max_value: int, 
                   step: int = 1, log_scale: bool = False) -> IntegerParameter:
        """Add an integer parameter to the space.
        
        Args:
            name: Name of the parameter
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            step: Step size between values (default: 1)
            log_scale: Whether to use logarithmic scale for grid points (default: False)
            
        Returns:
            The created parameter
            
        Raises:
            ParameterSpaceError: If parameter with same name already exists
        """
        param = IntegerParameter(name, min_value, max_value, step, log_scale)
        self.add_parameter(param)
        return param
    
    def add_float(self, name: str, min_value: float, max_value: float, 
                 step: Optional[float] = None, log_scale: bool = False) -> FloatParameter:
        """Add a float parameter to the space.
        
        Args:
            name: Name of the parameter
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            step: Step size between values (default: None)
            log_scale: Whether to use logarithmic scale for grid points (default: False)
            
        Returns:
            The created parameter
            
        Raises:
            ParameterSpaceError: If parameter with same name already exists
        """
        param = FloatParameter(name, min_value, max_value, step, log_scale)
        self.add_parameter(param)
        return param
    
    def add_categorical(self, name: str, categories: List[Any]) -> CategoricalParameter:
        """Add a categorical parameter to the space.
        
        Args:
            name: Name of the parameter
            categories: List of possible values
            
        Returns:
            The created parameter
            
        Raises:
            ParameterSpaceError: If parameter with same name already exists
        """
        param = CategoricalParameter(name, categories)
        self.add_parameter(param)
        return param
    
    def add_boolean(self, name: str) -> BooleanParameter:
        """Add a boolean parameter to the space.
        
        Args:
            name: Name of the parameter
            
        Returns:
            The created parameter
            
        Raises:
            ParameterSpaceError: If parameter with same name already exists
        """
        param = BooleanParameter(name)
        self.add_parameter(param)
        return param
    
    def get_parameter(self, name: str) -> Optional[Parameter]:
        """Get a parameter by name.
        
        Args:
            name: Name of the parameter
            
        Returns:
            Parameter if found, None otherwise
        """
        return self.parameters.get(name)
    
    def get_grid_points(self, parameter_name: str, num_points: Optional[int] = None) -> List[Any]:
        """Get grid points for a parameter.
        
        Args:
            parameter_name: Name of the parameter
            num_points: Optional number of points to generate
            
        Returns:
            List of parameter values for grid search
            
        Raises:
            ParameterSpaceError: If parameter does not exist
        """
        param = self.get_parameter(parameter_name)
        if param is None:
            raise ParameterSpaceError(
                parameter=parameter_name,
                message=f"Parameter '{parameter_name}' does not exist in space"
            )
        
        return param.get_grid_points(num_points)
    
    def get_grid_size(self) -> int:
        """Get the total size of the grid search space.
        
        Returns:
            Number of points in the grid
        """
        sizes = [len(param.get_grid_points()) for param in self.parameters.values()]
        if not sizes:
            return 0
        
        total = 1
        for size in sizes:
            total *= size
        
        return total
    
    def get_all_grid_points(self) -> List[Dict[str, Any]]:
        """Get all grid points as a Cartesian product.
        
        Returns:
            List of parameter dictionaries for grid search
        """
        if not self.parameters:
            return []
        
        # Get grid points for each parameter
        param_points = {
            name: param.get_grid_points()
            for name, param in self.parameters.items()
        }
        
        # Generate Cartesian product
        param_names = list(param_points.keys())
        param_values = [param_points[name] for name in param_names]
        
        result = []
        for value_combo in itertools.product(*param_values):
            point = {name: value for name, value in zip(param_names, value_combo)}
            result.append(point)
        
        return result
    
    def get_random_point(self) -> Dict[str, Any]:
        """Get a random point in the parameter space.
        
        Returns:
            Random parameter values as a dictionary
        """
        return {
            name: param.get_random_point()
            for name, param in self.parameters.items()
        }
    
    def get_random_points(self, num_points: int) -> List[Dict[str, Any]]:
        """Get multiple random points in the parameter space.
        
        Args:
            num_points: Number of points to generate
            
        Returns:
            List of random parameter dictionaries
        """
        return [self.get_random_point() for _ in range(num_points)]
    
    def validate_point(self, point: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate a point in the parameter space.
        
        Args:
            point: Dictionary of parameter values
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for unknown parameters
        unknown_params = set(point.keys()) - set(self.parameters.keys())
        if unknown_params:
            return False, f"Unknown parameters: {', '.join(unknown_params)}"
        
        # Validate each parameter
        for name, param in self.parameters.items():
            if name in point:
                valid, message = param.validate(point[name])
                if not valid:
                    return False, f"Parameter '{name}': {message}"
        
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter space to dictionary representation.
        
        Returns:
            Dictionary representation of parameter space
        """
        return {
            "name": self.name,
            "parameters": {
                name: param.to_dict()
                for name, param in self.parameters.items()
            }
        }
    
    def to_json(self) -> str:
        """Convert parameter space to JSON representation.
        
        Returns:
            JSON representation of parameter space
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParameterSpace':
        """Create parameter space from dictionary representation.
        
        Args:
            data: Dictionary representation of parameter space
            
        Returns:
            ParameterSpace instance
        """
        space = cls(name=data.get("name", "default"))
        
        # Add parameters
        for name, param_data in data.get("parameters", {}).items():
            param_data["name"] = name  # Ensure name is set
            param = Parameter.from_dict(param_data)
            space.add_parameter(param)
        
        return space
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ParameterSpace':
        """Create parameter space from JSON representation.
        
        Args:
            json_str: JSON representation of parameter space
            
        Returns:
            ParameterSpace instance
            
        Raises:
            OptimizationError: If JSON is invalid
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise OptimizationError(f"Invalid JSON: {e}")
        except Exception as e:
            raise OptimizationError(f"Error parsing parameter space: {e}")
