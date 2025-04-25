from typing import Dict, Any, Optional, Callable, Type, TypeVar, List, Set, Union

T = TypeVar('T')

class Container:
    """Dependency injection container."""
    
    def __init__(self):
        self._components = {}  # name -> component info
        self._instances = {}   # name -> singleton instance
        self._factories = {}   # name -> factory function
    
    def register(self, name: str, component_class: Type[T], 
                dependencies: Dict[str, str] = None, singleton: bool = True) -> 'Container':
        """Register a component with the container."""
        self._components[name] = {
            'class': component_class,
            'dependencies': dependencies or {},
            'singleton': singleton
        }
        return self
    
    def register_instance(self, name: str, instance: Any) -> 'Container':
        """Register a pre-created instance."""
        self._instances[name] = instance
        return self
    
    def register_factory(self, name: str, factory: Callable[['Container'], T]) -> 'Container':
        """Register a factory function for complex initialization."""
        self._factories[name] = factory
        return self

    def get(self, name: str) -> Any:
        """Get a component instance by name."""
        return self._get(name, set())

    def _get(self, name: str, resolving: Set[str]) -> Any:
        """Internal method that tracks currently resolving components."""
        # Check for circular dependencies
        if name in resolving:
            raise ValueError(f"Circular dependency detected: {' -> '.join(resolving)} -> {name}")

        # Add to currently resolving set
        resolving = resolving.union({name})

        # Check if it's already instantiated (singleton case)
        if name in self._instances:
            return self._instances[name]

        # Check if it has a factory
        if name in self._factories:
            instance = self._factories[name](self)
            if self._components.get(name, {}).get('singleton', True):
                self._instances[name] = instance
            return instance

        # Get component info
        if name not in self._components:
            raise ValueError(f"Component not registered: {name}")

        component_info = self._components[name]

        # Resolve dependencies
        resolved_deps = {}
        for dep_name, dep_key in component_info['dependencies'].items():
            try:
                resolved_deps[dep_name] = self._get(dep_key, resolving)
            except ValueError as e:
                raise ValueError(f"Error resolving dependency '{dep_name}' for component '{name}': {str(e)}")

        # Create instance
        try:
            instance = component_info['class'](**resolved_deps)
        except Exception as e:
            raise ValueError(f"Error creating instance of '{name}': {str(e)}")

        # Store if singleton
        if component_info['singleton']:
            self._instances[name] = instance

        return instance
    

    def has(self, name: str) -> bool:
        """Check if a component is registered."""
        return name in self._components or name in self._instances or name in self._factories

    def create(self, component_class: Type[T], **kwargs) -> T:
        """Create a new instance of a class with dependencies."""
        # Resolve constructor parameters
        sig = inspect.signature(component_class.__init__)
        params = {}

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            if param_name in kwargs:
                # Use provided value
                params[param_name] = kwargs[param_name]
            elif param_name in self._components or param_name in self._instances or param_name in self._factories:
                # Resolve from container
                params[param_name] = self.get(param_name)
            elif param.default is not inspect.Parameter.empty:
                # Use default value
                params[param_name] = param.default
            else:
                # Cannot resolve
                raise ValueError(f"Cannot resolve parameter '{param_name}' for {component_class.__name__}")

        # Create instance
        return component_class(**params)
    
    
    def inject(self, instance: Any) -> Any:
        """Inject dependencies into an existing instance."""
        # Find setter methods (set_X)
        for name in self._components:
            setter_name = f"set_{name}"
            if hasattr(instance, setter_name) and callable(getattr(instance, setter_name)):
                # Get dependency and inject
                dependency = self.get(name)
                getattr(instance, setter_name)(dependency)
        
        return instance
    
    def reset(self) -> None:
        """Reset all singleton instances."""
        self._instances.clear()


class ConfigurableContainer(Container):
    def __init__(self, config=None):
        super().__init__()
        self.config = config or Config()
        
    def register_component_with_config(self, name, component_class, config_section):
        """Register a component with configuration from a specific section."""
        # Get configuration for this component
        section = self.config.get_section(config_section)
        
        # Register component
        self.register(name, component_class)
        
        # Configure component after creation
        component = self.get(name)
        if hasattr(component, 'configure'):
            component.configure(section)
            
        return component        
