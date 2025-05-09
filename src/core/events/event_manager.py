import logging
import inspect
import asyncio
import os
import datetime
from typing import Dict, Any, Optional, List, Union, Set

from .event_bus import EventBus
# Import canonical implementations
from src.core.event_system.event_types import EventType
from src.core.event_system.event import Event
# Import factory functions for lifecycle and error events
from .event_utils import create_lifecycle_event, create_error_event
from .event_handlers import EventHandler, AsyncEventHandler

logger = logging.getLogger(__name__)

class EventManager:
    """Manager for coordinating event flow between system components."""
    
    def __init__(self, event_bus=None):
        self.event_bus = event_bus or EventBus()
        self.components = {}
        self.async_components = set()  # Track which components are async
    
    def register_component(self, name, component, event_types=None):
        """
        Register a component with the event manager.
        
        Args:
            name: Name for the component
            component: Component object
            event_types: List of EventType to register handlers for
        """
        self.components[name] = component
        
        # Check if component has async handlers
        is_async = False
        
        # Set event bus on component if it has the attribute
        if hasattr(component, 'set_event_bus'):
            component.set_event_bus(self.event_bus)
        elif hasattr(component, 'event_bus'):
            component.event_bus = self.event_bus
            
        # Register component handlers
        if event_types:
            for event_type in event_types:
                # Check for dedicated handler method
                handler_name = f"on_{event_type.name.lower()}"
                if hasattr(component, handler_name):
                    handler = getattr(component, handler_name)
                    
                    # Check if handler is async
                    if inspect.iscoroutinefunction(handler):
                        self.event_bus.register_async(event_type, handler)
                        is_async = True
                    else:
                        self.event_bus.register(event_type, handler)
                        
                # Check for generic handle method
                elif hasattr(component, 'handle'):
                    handler = component.handle
                    
                    # Check if handler is async
                    if inspect.iscoroutinefunction(handler):
                        self.event_bus.register_async(event_type, handler)
                        is_async = True
                    else:
                        self.event_bus.register(event_type, handler)
                        
        # Mark component as async if any handlers are async
        if is_async:
            self.async_components.add(name)
            
        # Emit lifecycle event
        self._emit_lifecycle_event(LifecycleEvent.INITIALIZED, name)
    
    def unregister_component(self, name):
        """Unregister a component from the event manager."""
        if name not in self.components:
            logger.warning(f"Component {name} not found")
            return
            
        component = self.components[name]
        is_async = name in self.async_components
        
        # Unregister handlers
        for event_type in EventType:
            # Check for dedicated handler method
            handler_name = f"on_{event_type.name.lower()}"
            if hasattr(component, handler_name):
                handler = getattr(component, handler_name)
                if is_async:
                    self.event_bus.unregister_async(event_type, handler)
                else:
                    self.event_bus.unregister(event_type, handler)
            # Check for generic handle method
            elif hasattr(component, 'handle'):
                handler = component.handle
                if is_async:
                    self.event_bus.unregister_async(event_type, handler)
                else:
                    self.event_bus.unregister(event_type, handler)
                
        del self.components[name]
        if name in self.async_components:
            self.async_components.remove(name)
            
        # Emit lifecycle event
        self._emit_lifecycle_event(LifecycleEvent.STOPPED, name)
        
        logger.debug(f"Unregistered component {name}")
    
    def get_component(self, name):
        """Get a component by name."""
        return self.components.get(name)
    
    def reset_components(self):
        """Reset all components to initial state."""
        for name, component in self.components.items():
            if hasattr(component, 'reset'):
                try:
                    if name in self.async_components and inspect.iscoroutinefunction(component.reset):
                        # Create a task for async reset
                        asyncio.create_task(component.reset())
                    else:
                        component.reset()
                except Exception as e:
                    logger.error(f"Error resetting component {name}: {e}", exc_info=True)
                    self._emit_error_event("RESET_ERROR", f"Error resetting component {name}", name, e)
        
        if hasattr(self.event_bus, 'reset'):
            self.event_bus.reset()
            
        # Emit lifecycle event
        self._emit_lifecycle_event(LifecycleEvent.INITIALIZED, "event_manager")
    
    async def reset_components_async(self):
        """Reset all components to initial state asynchronously."""
        tasks = []
        
        for name, component in self.components.items():
            if hasattr(component, 'reset'):
                try:
                    if name in self.async_components and inspect.iscoroutinefunction(component.reset):
                        # Create a task for async reset
                        task = asyncio.create_task(component.reset())
                        tasks.append(task)
                    else:
                        component.reset()
                except Exception as e:
                    logger.error(f"Error resetting component {name}: {e}", exc_info=True)
                    await self._emit_error_event_async("RESET_ERROR", f"Error resetting component {name}", name, e)
        
        # Wait for all async resets to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        if hasattr(self.event_bus, 'reset'):
            self.event_bus.reset()
            
        # Emit lifecycle event
        await self._emit_lifecycle_event_async(LifecycleEvent.INITIALIZED, "event_manager")
    
    def get_event_bus(self):
        """Get the event bus."""
        return self.event_bus
        
    def get_components(self):
        """Get all registered components."""
        return self.components
    
    def get_async_components(self):
        """Get all registered async components."""
        return {name: self.components[name] for name in self.async_components}
    
    def _emit_lifecycle_event(self, state, component=None, data=None):
        """Emit a lifecycle event."""
        # Use factory function instead of direct class constructor
        event = create_lifecycle_event(state, component, data)
        try:
            self.event_bus.emit(event)
        except Exception as e:
            logger.error(f"Error emitting lifecycle event: {e}", exc_info=True)
    
    async def _emit_lifecycle_event_async(self, state, component=None, data=None):
        """Emit a lifecycle event asynchronously."""
        # Use factory function instead of direct class constructor
        event = create_lifecycle_event(state, component, data)
        try:
            if hasattr(self.event_bus, 'emit_async'):
                await self.event_bus.emit_async(event)
            else:
                self.event_bus.emit(event)
        except Exception as e:
            logger.error(f"Error emitting async lifecycle event: {e}", exc_info=True)
    
    def _emit_error_event(self, error_type, message, source=None, exception=None):
        """Emit an error event."""
        # Use factory function instead of direct class constructor
        event = create_error_event(error_type, message, source, exception)
        try:
            self.event_bus.emit(event)
        except Exception as e:
            logger.error(f"Error emitting error event: {e}", exc_info=True)
    
    async def _emit_error_event_async(self, error_type, message, source=None, exception=None):
        """Emit an error event asynchronously."""
        # Use factory function instead of direct class constructor
        event = create_error_event(error_type, message, source, exception)
        try:
            if hasattr(self.event_bus, 'emit_async'):
                await self.event_bus.emit_async(event)
            else:
                self.event_bus.emit(event)
        except Exception as e:
            logger.error(f"Error emitting async error event: {e}", exc_info=True)

    async def reset_components_async(self):
        """Reset all components to initial state asynchronously."""
        tasks = []
        
        for name, component in self.components.items():
            if hasattr(component, 'reset'):
                try:
                    if name in self.async_components and asyncio.iscoroutinefunction(component.reset):
                        # Create a task for async reset
                        task = asyncio.create_task(component.reset())
                        tasks.append(task)
                    else:
                        component.reset()
                except Exception as e:
                    logger.error(f"Error resetting component {name}: {e}", exc_info=True)
                    await self._emit_error_event_async("RESET_ERROR", f"Error resetting component {name}", name, e)
        
        # Wait for all async resets to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        if hasattr(self.event_bus, 'reset'):
            self.event_bus.reset()
            
        # Emit lifecycle event
        await self._emit_lifecycle_event_async(LifecycleEvent.INITIALIZED, "event_manager")


class EventStorage:
    """Store events for later replay."""
    
    def __init__(self, storage_path=None):
        self.storage_path = storage_path or './event_storage'
        os.makedirs(self.storage_path, exist_ok=True)
    
    def store_event(self, event):
        """Store an event."""
        event_json = event.serialize()
        event_type = event.get_type().name
        timestamp = event.get_timestamp().strftime('%Y%m%d_%H%M%S_%f')
        
        # Use event type and timestamp in filename
        filename = f"{event_type}_{timestamp}_{event.get_id()}.json"
        filepath = os.path.join(self.storage_path, filename)
        
        with open(filepath, 'w') as f:
            f.write(event_json)
        
        return filepath
    
    def load_events(self, event_types=None, start_time=None, end_time=None):
        """Load events matching criteria."""
        events = []
        files = os.listdir(self.storage_path)
        
        # Filter files by event type if specified
        if event_types:
            type_names = [t.name for t in event_types]
            files = [f for f in files if any(f.startswith(t + '_') for t in type_names)]
        
        for filename in sorted(files):
            # Extract timestamp from filename
            parts = filename.split('_')
            if len(parts) >= 3:
                try:
                    file_timestamp = datetime.datetime.strptime(
                        '_'.join(parts[1:3]), '%Y%m%d_%H%M%S_%f'
                    )
                    
                    # Skip if before start_time
                    if start_time and file_timestamp < start_time:
                        continue
                        
                    # Skip if after end_time
                    if end_time and file_timestamp > end_time:
                        continue
                        
                    # Load event
                    filepath = os.path.join(self.storage_path, filename)
                    with open(filepath, 'r') as f:
                        event_json = f.read()
                        event = Event.deserialize(event_json)
                        events.append(event)
                except:
                    # Skip files with invalid format
                    continue
        
        return events
    
    def replay_events(self, event_bus, event_types=None, start_time=None, end_time=None):
        """Replay events to an event bus."""
        events = self.load_events(event_types, start_time, end_time)
        
        for event in events:
            event_bus.emit(event)
            
        return len(events)        
