"""
Direct import test to debug the Event class import issue.
"""

import sys
import os
import importlib.util
import time

# Add project root to path so 'src' can be found
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

def safe_timed_import(module_name, timeout=3):
    """Import a module with timeout protection."""
    print(f"Attempting to import {module_name} with {timeout}s timeout...")
    
    start_time = time.time()
    result = {"success": False, "module": None, "error": None, "elapsed": 0}
    
    def import_module():
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                return None, f"Module {module_name} not found"
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module, None
        except Exception as e:
            return None, str(e)
    
    # Actually attempt the import
    module, error = import_module()
    
    elapsed = time.time() - start_time
    result["elapsed"] = elapsed
    
    if module is not None:
        result["success"] = True
        result["module"] = module
        print(f"Successfully imported {module_name} in {elapsed:.3f}s")
    else:
        result["error"] = error
        print(f"Failed to import {module_name}: {error} (took {elapsed:.3f}s)")
    
    return result

def get_event_class():
    """Get the Event class using a direct approach."""
    # First, find the event_types.py file
    event_types_path = None
    for root, _, files in os.walk(os.path.join(project_root, 'src')):
        for file in files:
            if file == 'event_types.py':
                event_types_path = os.path.join(root, file)
                break
        if event_types_path:
            break
    
    if not event_types_path:
        print("Could not find event_types.py file")
        return None
    
    print(f"Found event_types.py at: {event_types_path}")
    
    # Get module name from path
    rel_path = os.path.relpath(event_types_path, project_root)
    module_name = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
    
    print(f"Module name: {module_name}")
    
    # Try to import the module
    result = safe_timed_import(module_name)
    
    if result["success"]:
        module = result["module"]
        
        # Get the EventType class
        if hasattr(module, 'EventType'):
            print("Found EventType class")
            EventType = module.EventType
        else:
            print("Could not find EventType class in module")
            return None
        
        # Get the Event class
        if hasattr(module, 'Event'):
            print("Found Event class")
            Event = module.Event
            return Event, EventType
        else:
            print("Could not find Event class in module")
            return None
    
    return None

def main():
    """Main function."""
    print("Starting direct import test...")
    print(f"Python sys.path: {sys.path}")
    
    # Try direct import
    result = get_event_class()
    
    if result:
        Event, EventType = result
        print("\nEvent class structure:")
        print(f"  Methods: {[attr for attr in dir(Event) if not attr.startswith('_') and callable(getattr(Event, attr))]}")
        print(f"  Attributes: {[attr for attr in dir(Event) if not attr.startswith('_') and not callable(getattr(Event, attr))]}")
        
        try:
            print("\nTrying to create an Event instance...")
            event = Event(EventType.BAR, {'test': 'data'})
            print("Successfully created Event instance!")
            
            # Test attributes
            print(f"event.event_type = {event.event_type}")
            print(f"event.data = {event.data}")
            
            # Add type property
            if not hasattr(Event, 'type'):
                @property
                def type_property(self):
                    """Bridge property to access event_type as type."""
                    return self.event_type
                
                Event.type = type_property
                print("Added 'type' property to Event class")
            
            # Test property
            print(f"event.type = {event.type}")
            
            print("\nAll tests passed!")
            return 0
        except Exception as e:
            print(f"Error creating Event instance: {e}")
            return 1
    
    return 1

if __name__ == "__main__":
    sys.exit(main())
