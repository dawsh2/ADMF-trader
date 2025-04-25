class ObjectRegistry:
    """Registry for reconstructing objects from serialized data."""
    
    _registry = {}  # class_name -> class
    
    @classmethod
    def register(cls, class_obj):
        """Register a class for reconstruction."""
        cls._registry[class_obj.__name__] = class_obj
        return class_obj  # Allow use as decorator
    
    @classmethod
    def get_class(cls, class_name):
        """Get class by name."""
        return cls._registry.get(class_name)
    
    @classmethod
    def from_dict(cls, data):
        """Reconstruct object from dictionary."""
        if "__type__" not in data:
            return data
            
        type_name = data.pop("__type__")
        obj_class = cls.get_class(type_name)
        
        if obj_class is None:
            return data  # Return as dict if class not registered
            
        # Use from_dict method if available
        if hasattr(obj_class, "from_dict") and callable(obj_class.from_dict):
            return obj_class.from_dict(data)
            
        return data
