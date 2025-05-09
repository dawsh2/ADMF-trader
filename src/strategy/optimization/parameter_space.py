"""
Parameter space definition for strategy optimization.

This module provides classes for defining parameter spaces for strategy optimization,
supporting different parameter types and constraints.
"""

import numpy as np
from itertools import product

class Parameter:
    """Base class for optimization parameters."""
    
    def __init__(self, name, description=None):
        """
        Initialize a parameter.
        
        Args:
            name (str): Parameter name
            description (str, optional): Parameter description
        """
        self.name = name
        self.description = description
        
    def get_values(self):
        """
        Get possible values for this parameter.
        
        Returns:
            list: Possible values
        """
        raise NotImplementedError("Subclasses must implement get_values")
        
    def validate(self, value):
        """
        Validate a parameter value.
        
        Args:
            value: Value to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        raise NotImplementedError("Subclasses must implement validate")
        
    def __str__(self):
        """String representation of the parameter."""
        return f"{self.__class__.__name__}({self.name})"

class IntegerParameter(Parameter):
    """Integer parameter for optimization."""
    
    def __init__(self, name, min_value, max_value, step=1, log_scale=False, description=None):
        """
        Initialize an integer parameter.
        
        Args:
            name (str): Parameter name
            min_value (int): Minimum value
            max_value (int): Maximum value
            step (int, optional): Step size
            log_scale (bool, optional): Whether to use logarithmic scale
            description (str, optional): Parameter description
        """
        super().__init__(name, description)
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.log_scale = log_scale
        
        self._validate_bounds()
        
    def _validate_bounds(self):
        """Validate parameter bounds."""
        if self.min_value > self.max_value:
            raise ValueError(f"Min value {self.min_value} is greater than max value {self.max_value}")
            
        if self.step <= 0:
            raise ValueError(f"Step must be positive, got {self.step}")
            
        if self.log_scale and self.min_value <= 0:
            raise ValueError(f"Min value must be positive for log scale, got {self.min_value}")
            
    def get_values(self):
        """
        Get possible values for this parameter.
        
        Returns:
            list: Possible values
        """
        if self.log_scale:
            # Generate values on a logarithmic scale
            log_min = np.log10(self.min_value)
            log_max = np.log10(self.max_value)
            log_step = (log_max - log_min) / ((self.max_value - self.min_value) / self.step)
            
            log_values = np.arange(log_min, log_max + log_step, log_step)
            values = np.power(10, log_values)
            
            # Convert to integers and ensure uniqueness
            values = np.unique(np.round(values).astype(int))
            
            # Ensure bounds are respected
            values = values[(values >= self.min_value) & (values <= self.max_value)]
            
            return values.tolist()
        else:
            # Generate values on a linear scale
            return list(range(self.min_value, self.max_value + 1, self.step))
            
    def validate(self, value):
        """
        Validate a parameter value.
        
        Args:
            value: Value to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check if value is an integer
        if not isinstance(value, int):
            return False
            
        # Check if value is within bounds
        if value < self.min_value or value > self.max_value:
            return False
            
        # For non-log scale, check if value is a multiple of step
        if not self.log_scale and (value - self.min_value) % self.step != 0:
            return False
            
        return True

class FloatParameter(Parameter):
    """Float parameter for optimization."""
    
    def __init__(self, name, min_value, max_value, step=None, num_points=10, 
                log_scale=False, description=None):
        """
        Initialize a float parameter.
        
        Args:
            name (str): Parameter name
            min_value (float): Minimum value
            max_value (float): Maximum value
            step (float, optional): Step size
            num_points (int, optional): Number of points if step not specified
            log_scale (bool, optional): Whether to use logarithmic scale
            description (str, optional): Parameter description
        """
        super().__init__(name, description)
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.num_points = num_points
        self.log_scale = log_scale
        
        self._validate_bounds()
        
    def _validate_bounds(self):
        """Validate parameter bounds."""
        if self.min_value > self.max_value:
            raise ValueError(f"Min value {self.min_value} is greater than max value {self.max_value}")
            
        if self.step is not None and self.step <= 0:
            raise ValueError(f"Step must be positive, got {self.step}")
            
        if self.log_scale and self.min_value <= 0:
            raise ValueError(f"Min value must be positive for log scale, got {self.min_value}")
            
    def get_values(self):
        """
        Get possible values for this parameter.
        
        Returns:
            list: Possible values
        """
        if self.log_scale:
            # Generate values on a logarithmic scale
            if self.step is not None:
                log_min = np.log10(self.min_value)
                log_max = np.log10(self.max_value)
                num_steps = int((log_max - log_min) / self.step) + 1
                log_values = np.linspace(log_min, log_max, num_steps)
            else:
                log_min = np.log10(self.min_value)
                log_max = np.log10(self.max_value)
                log_values = np.linspace(log_min, log_max, self.num_points)
                
            values = np.power(10, log_values)
        else:
            # Generate values on a linear scale
            if self.step is not None:
                num_steps = int((self.max_value - self.min_value) / self.step) + 1
                values = np.linspace(self.min_value, self.max_value, num_steps)
            else:
                values = np.linspace(self.min_value, self.max_value, self.num_points)
                
        return values.tolist()
        
    def validate(self, value):
        """
        Validate a parameter value.
        
        Args:
            value: Value to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check if value is a number
        if not isinstance(value, (int, float)):
            return False
            
        # Check if value is within bounds
        if value < self.min_value or value > self.max_value:
            return False
            
        # For non-log scale with step, check if value is approximately a multiple of step
        if (not self.log_scale and self.step is not None and 
            abs((value - self.min_value) % self.step) > 1e-10 and
            abs((value - self.min_value) % self.step - self.step) > 1e-10):
            return False
            
        return True

class CategoricalParameter(Parameter):
    """Categorical parameter for optimization."""
    
    def __init__(self, name, categories, description=None):
        """
        Initialize a categorical parameter.
        
        Args:
            name (str): Parameter name
            categories (list): Possible categories
            description (str, optional): Parameter description
        """
        super().__init__(name, description)
        self.categories = categories
        
        self._validate_categories()
        
    def _validate_categories(self):
        """Validate parameter categories."""
        if not self.categories:
            raise ValueError("Categories cannot be empty")
            
    def get_values(self):
        """
        Get possible values for this parameter.
        
        Returns:
            list: Possible values
        """
        return self.categories
        
    def validate(self, value):
        """
        Validate a parameter value.
        
        Args:
            value: Value to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        return value in self.categories

class BooleanParameter(Parameter):
    """Boolean parameter for optimization."""
    
    def __init__(self, name, description=None):
        """
        Initialize a boolean parameter.
        
        Args:
            name (str): Parameter name
            description (str, optional): Parameter description
        """
        super().__init__(name, description)
        
    def get_values(self):
        """
        Get possible values for this parameter.
        
        Returns:
            list: Possible values
        """
        return [True, False]
        
    def validate(self, value):
        """
        Validate a parameter value.
        
        Args:
            value: Value to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        return isinstance(value, bool)

class ConditionalParameter(Parameter):
    """Conditional parameter that depends on another parameter."""
    
    def __init__(self, name, parent_parameter, value_map, description=None):
        """
        Initialize a conditional parameter.
        
        Args:
            name (str): Parameter name
            parent_parameter (Parameter): Parent parameter this depends on
            value_map (dict): Mapping from parent values to this parameter's values
            description (str, optional): Parameter description
        """
        super().__init__(name, description)
        self.parent_parameter = parent_parameter
        self.value_map = value_map
        
        self._validate_value_map()
        
    def _validate_value_map(self):
        """Validate the value map."""
        if not self.value_map:
            raise ValueError("Value map cannot be empty")
            
        parent_values = self.parent_parameter.get_values()
        for parent_value in self.value_map:
            if parent_value not in parent_values:
                raise ValueError(f"Parent value {parent_value} not found in parent parameter values")
                
    def get_values(self, parent_value=None):
        """
        Get possible values for this parameter.
        
        Args:
            parent_value: Value of the parent parameter
            
        Returns:
            list: Possible values
        """
        if parent_value is None:
            # Return all possible values
            all_values = []
            for values in self.value_map.values():
                all_values.extend(values)
            return list(set(all_values))
        
        # Return values for specific parent value
        return self.value_map.get(parent_value, [])
        
    def validate(self, value, parent_value=None):
        """
        Validate a parameter value.
        
        Args:
            value: Value to validate
            parent_value: Value of the parent parameter
            
        Returns:
            bool: True if valid, False otherwise
        """
        if parent_value is None:
            # Check if value is valid for any parent value
            for values in self.value_map.values():
                if value in values:
                    return True
            return False
            
        # Check if value is valid for specific parent value
        return value in self.value_map.get(parent_value, [])

class ParameterSpace:
    """Parameter space for optimization."""
    
    def __init__(self):
        """Initialize a parameter space."""
        self.parameters = {}
        self.conditional_dependencies = {}
        
    def add_parameter(self, parameter):
        """
        Add a parameter to the space.
        
        Args:
            parameter (Parameter): Parameter to add
        """
        if parameter.name in self.parameters:
            raise ValueError(f"Parameter {parameter.name} already exists")
            
        self.parameters[parameter.name] = parameter
        
        # Add conditional dependencies
        if isinstance(parameter, ConditionalParameter):
            parent_name = parameter.parent_parameter.name
            if parent_name not in self.conditional_dependencies:
                self.conditional_dependencies[parent_name] = []
            self.conditional_dependencies[parent_name].append(parameter.name)
            
    def get_parameter(self, name):
        """
        Get a parameter by name.
        
        Args:
            name (str): Parameter name
            
        Returns:
            Parameter: Parameter instance
        """
        if name not in self.parameters:
            raise ValueError(f"Parameter {name} not found")
            
        return self.parameters[name]
        
    def get_combinations(self):
        """
        Get all valid parameter combinations.
        
        Returns:
            list: List of parameter dictionaries
        """
        # Identify top-level parameters (not conditional)
        top_level_params = {
            name: param for name, param in self.parameters.items()
            if not isinstance(param, ConditionalParameter)
        }
        
        # Get values for top-level parameters
        param_values = {
            name: param.get_values() for name, param in top_level_params.items()
        }
        
        # Generate combinations of top-level parameters
        param_names = list(param_values.keys())
        combinations = []
        
        for values in product(*param_values.values()):
            # Create parameter dictionary
            param_dict = dict(zip(param_names, values))
            
            # Add conditional parameters
            self._add_conditional_parameters(param_dict)
            
            combinations.append(param_dict)
            
        return combinations
        
    def _add_conditional_parameters(self, param_dict):
        """
        Add conditional parameters to a parameter dictionary.
        
        Args:
            param_dict (dict): Parameter dictionary to update
        """
        # Check each parent parameter
        for parent_name in self.conditional_dependencies:
            if parent_name not in param_dict:
                continue
                
            parent_value = param_dict[parent_name]
            
            # Add dependent parameters
            for dependent_name in self.conditional_dependencies[parent_name]:
                param = self.parameters[dependent_name]
                
                # Get values for this parent value
                values = param.get_values(parent_value)
                
                if values:
                    # Add first value to the dictionary
                    param_dict[dependent_name] = values[0]
                    
    def from_dict(self, config):
        """
        Create a parameter space from a configuration dictionary.
        
        Args:
            config (dict): Configuration dictionary
            
        Returns:
            ParameterSpace: Parameter space instance
        """
        for param_config in config.get('parameters', []):
            param_type = param_config.get('type')
            name = param_config.get('name')
            
            if not name:
                raise ValueError("Parameter name is required")
                
            if param_type == 'integer':
                param = IntegerParameter(
                    name=name,
                    min_value=param_config.get('min'),
                    max_value=param_config.get('max'),
                    step=param_config.get('step', 1),
                    log_scale=param_config.get('log_scale', False),
                    description=param_config.get('description')
                )
                
            elif param_type == 'float':
                param = FloatParameter(
                    name=name,
                    min_value=param_config.get('min'),
                    max_value=param_config.get('max'),
                    step=param_config.get('step'),
                    num_points=param_config.get('num_points', 10),
                    log_scale=param_config.get('log_scale', False),
                    description=param_config.get('description')
                )
                
            elif param_type == 'categorical':
                param = CategoricalParameter(
                    name=name,
                    categories=param_config.get('categories', []),
                    description=param_config.get('description')
                )
                
            elif param_type == 'boolean':
                param = BooleanParameter(
                    name=name,
                    description=param_config.get('description')
                )
                
            elif param_type == 'conditional':
                parent_name = param_config.get('parent')
                
                if not parent_name or parent_name not in self.parameters:
                    raise ValueError(f"Parent parameter {parent_name} not found")
                    
                param = ConditionalParameter(
                    name=name,
                    parent_parameter=self.parameters[parent_name],
                    value_map=param_config.get('value_map', {}),
                    description=param_config.get('description')
                )
                
            else:
                raise ValueError(f"Unknown parameter type: {param_type}")
                
            self.add_parameter(param)
            
        return self
