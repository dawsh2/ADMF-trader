"""
Parameter Store for Managing and Versioning Configuration Parameters.

This module provides functionality for:
1. Saving parameters to persistent storage
2. Loading parameters from storage
3. Tracking parameter version history
4. Comparing parameter versions
5. Rolling back to previous parameter versions
"""
import os
import json
import yaml
import uuid
import logging
import datetime
from typing import Dict, Any, List, Tuple, Optional, Union

logger = logging.getLogger(__name__)

class ParameterStore:
    """
    Parameter storage and versioning system.
    
    This class provides methods to:
    - Save parameters with version tracking
    - Load parameters with version selection
    - Compare parameter versions
    - Roll back to previous versions
    - Document parameter changes
    
    Parameters are stored in a structured directory hierarchy with
    version history and metadata to support parameter optimization workflows.
    """
    
    def __init__(self, base_dir: str = "./params", create_dirs: bool = True):
        """
        Initialize the parameter store.
        
        Args:
            base_dir: Base directory for parameter storage
            create_dirs: Whether to create directories if they don't exist
        """
        self.base_dir = base_dir
        
        # Create base directory if needed
        if create_dirs and not os.path.exists(base_dir):
            os.makedirs(base_dir)
            logger.info(f"Created parameter base directory: {base_dir}")
            
        # Create standard subdirectories
        self.dirs = {
            'strategies': os.path.join(base_dir, 'strategies'),
            'risk_managers': os.path.join(base_dir, 'risk_managers'),
            'regimes': os.path.join(base_dir, 'regimes'),
            'optimizations': os.path.join(base_dir, 'optimizations'),
            'profiles': os.path.join(base_dir, 'profiles')
        }
        
        if create_dirs:
            for dir_path in self.dirs.values():
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                    logger.info(f"Created parameter subdirectory: {dir_path}")
    
    def save_parameters(self, 
                       component_type: str, 
                       component_name: str, 
                       parameters: Dict[str, Any], 
                       metadata: Optional[Dict[str, Any]] = None,
                       version: Optional[str] = None,
                       comment: Optional[str] = None) -> str:
        """
        Save parameters with versioning.
        
        Args:
            component_type: Type of component (strategy, risk_manager, etc.)
            component_name: Name of component (ma_crossover, enhanced, etc.)
            parameters: Parameter dictionary to save
            metadata: Optional metadata to store with parameters
            version: Optional explicit version identifier (default: auto-generated)
            comment: Optional comment describing this version
            
        Returns:
            str: Version identifier
        """
        # Validate component type
        if component_type not in self.dirs:
            component_type = 'profiles'  # Default to profiles for unknown types
            
        # Create component directory if needed
        component_dir = os.path.join(self.dirs[component_type], component_name)
        if not os.path.exists(component_dir):
            os.makedirs(component_dir)
            logger.info(f"Created component directory: {component_dir}")
            
        # Generate version if not provided
        if version is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            version = f"v_{timestamp}"
            
        # Create version directory
        version_dir = os.path.join(component_dir, version)
        if not os.path.exists(version_dir):
            os.makedirs(version_dir)
            
        # Prepare metadata
        if metadata is None:
            metadata = {}
            
        metadata.update({
            'timestamp': datetime.datetime.now().isoformat(),
            'version': version,
            'component_type': component_type,
            'component_name': component_name
        })
        
        if comment:
            metadata['comment'] = comment
            
        # Write parameters to JSON file
        params_path = os.path.join(version_dir, 'parameters.json')
        with open(params_path, 'w') as f:
            json.dump(parameters, f, indent=2, sort_keys=True)
            
        # Write metadata to JSON file
        metadata_path = os.path.join(version_dir, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, sort_keys=True)
            
        # Write parameters to YAML file for human readability
        yaml_path = os.path.join(version_dir, 'parameters.yaml')
        with open(yaml_path, 'w') as f:
            yaml.dump(parameters, f, sort_keys=True)
            
        # Update version index
        index_path = os.path.join(component_dir, 'version_index.json')
        
        # Load existing index or create new one
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                try:
                    version_index = json.load(f)
                except json.JSONDecodeError:
                    version_index = {'versions': []}
        else:
            version_index = {'versions': []}
            
        # Add version to index
        version_info = {
            'version': version,
            'timestamp': metadata['timestamp'],
            'comment': comment or '',
            'path': os.path.relpath(version_dir, component_dir)
        }
        
        version_index['versions'].append(version_info)
        version_index['latest'] = version
        
        # Write updated index
        with open(index_path, 'w') as f:
            json.dump(version_index, f, indent=2)
            
        logger.info(f"Saved parameters for {component_type}/{component_name} version {version}")
        return version
    
    def load_parameters(self, 
                       component_type: str, 
                       component_name: str, 
                       version: Optional[str] = None,
                       include_metadata: bool = False) -> Union[Dict[str, Any], Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Load parameters for a specific component.
        
        Args:
            component_type: Type of component (strategy, risk_manager, etc.)
            component_name: Name of component (ma_crossover, enhanced, etc.)
            version: Version to load (default: latest)
            include_metadata: Whether to include metadata in the result
            
        Returns:
            Dict or (Dict, Dict): Parameters dict, or tuple of (parameters, metadata)
        """
        # Validate component type
        if component_type not in self.dirs:
            raise ValueError(f"Unknown component type: {component_type}")
            
        # Check if component exists
        component_dir = os.path.join(self.dirs[component_type], component_name)
        if not os.path.exists(component_dir):
            raise FileNotFoundError(f"Component not found: {component_type}/{component_name}")
            
        # If version not specified, load latest
        if version is None:
            # Try to load from version index
            index_path = os.path.join(component_dir, 'version_index.json')
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    version_index = json.load(f)
                version = version_index.get('latest')
                
            # If still no version, find most recent directory
            if version is None:
                version_dirs = [d for d in os.listdir(component_dir) 
                              if os.path.isdir(os.path.join(component_dir, d)) 
                              and d != '__pycache__']
                if not version_dirs:
                    raise FileNotFoundError(f"No versions found for {component_type}/{component_name}")
                version_dirs.sort(reverse=True)  # Assuming version names are sortable (like timestamps)
                version = version_dirs[0]
                
        # Load parameters
        version_dir = os.path.join(component_dir, version)
        if not os.path.exists(version_dir):
            raise FileNotFoundError(f"Version not found: {component_type}/{component_name}/{version}")
            
        params_path = os.path.join(version_dir, 'parameters.json')
        if not os.path.exists(params_path):
            raise FileNotFoundError(f"Parameters file not found: {params_path}")
            
        with open(params_path, 'r') as f:
            parameters = json.load(f)
            
        if include_metadata:
            # Load metadata
            metadata_path = os.path.join(version_dir, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {'version': version}
                
            return parameters, metadata
            
        return parameters
    
    def get_version_history(self, component_type: str, component_name: str) -> List[Dict[str, Any]]:
        """
        Get version history for a component.
        
        Args:
            component_type: Type of component (strategy, risk_manager, etc.)
            component_name: Name of component (ma_crossover, enhanced, etc.)
            
        Returns:
            List of version info dictionaries
        """
        # Validate component type
        if component_type not in self.dirs:
            raise ValueError(f"Unknown component type: {component_type}")
            
        # Check if component exists
        component_dir = os.path.join(self.dirs[component_type], component_name)
        if not os.path.exists(component_dir):
            raise FileNotFoundError(f"Component not found: {component_type}/{component_name}")
            
        # Try to load from version index
        index_path = os.path.join(component_dir, 'version_index.json')
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                version_index = json.load(f)
            versions = version_index.get('versions', [])
            
            # Sort by timestamp (newest first)
            versions.sort(key=lambda v: v.get('timestamp', ''), reverse=True)
            return versions
            
        # If no index, scan directories
        version_dirs = [d for d in os.listdir(component_dir) 
                      if os.path.isdir(os.path.join(component_dir, d)) 
                      and d != '__pycache__']
        
        versions = []
        for version in version_dirs:
            metadata_path = os.path.join(component_dir, version, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    try:
                        metadata = json.load(f)
                        
                        version_info = {
                            'version': version,
                            'timestamp': metadata.get('timestamp', ''),
                            'comment': metadata.get('comment', ''),
                            'path': version
                        }
                        versions.append(version_info)
                    except json.JSONDecodeError:
                        # Skip invalid metadata
                        pass
                        
        # Sort by timestamp (newest first)
        versions.sort(key=lambda v: v.get('timestamp', ''), reverse=True)
        return versions
    
    def compare_versions(self, 
                        component_type: str, 
                        component_name: str, 
                        version1: str, 
                        version2: str) -> Dict[str, Any]:
        """
        Compare two parameter versions.
        
        Args:
            component_type: Type of component (strategy, risk_manager, etc.)
            component_name: Name of component (ma_crossover, enhanced, etc.)
            version1: First version to compare
            version2: Second version to compare
            
        Returns:
            Dict: Comparison result with added, removed, and changed parameters
        """
        # Load both parameter sets
        params1, meta1 = self.load_parameters(component_type, component_name, version1, include_metadata=True)
        params2, meta2 = self.load_parameters(component_type, component_name, version2, include_metadata=True)
        
        # Find differences
        added = {}
        removed = {}
        changed = {}
        
        # Parameters in version2 but not in version1
        for key, value in params2.items():
            if key not in params1:
                added[key] = value
                
        # Parameters in version1 but not in version2
        for key, value in params1.items():
            if key not in params2:
                removed[key] = value
                
        # Parameters in both but with different values
        for key, value1 in params1.items():
            if key in params2:
                value2 = params2[key]
                if value1 != value2:
                    changed[key] = {
                        'from': value1,
                        'to': value2
                    }
        
        # Build comparison result
        result = {
            'component_type': component_type,
            'component_name': component_name,
            'version1': {
                'version': version1,
                'timestamp': meta1.get('timestamp', ''),
                'comment': meta1.get('comment', '')
            },
            'version2': {
                'version': version2,
                'timestamp': meta2.get('timestamp', ''),
                'comment': meta2.get('comment', '')
            },
            'differences': {
                'added': added,
                'removed': removed,
                'changed': changed
            },
            'summary': {
                'added_count': len(added),
                'removed_count': len(removed),
                'changed_count': len(changed),
                'unchanged_count': len([k for k in params1 if k in params2 and params1[k] == params2[k]])
            }
        }
        
        return result
    
    def save_config_snapshot(self, config: Dict[str, Any], name: Optional[str] = None) -> str:
        """
        Save a snapshot of the entire configuration.
        
        Args:
            config: Configuration to save
            name: Optional name for the snapshot (default: timestamp)
            
        Returns:
            str: Snapshot identifier
        """
        if name is None:
            name = f"snapshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        # Create snapshot directory
        snapshot_dir = os.path.join(self.base_dir, 'snapshots')
        if not os.path.exists(snapshot_dir):
            os.makedirs(snapshot_dir)
            
        # Create snapshot subdirectory
        snapshot_path = os.path.join(snapshot_dir, name)
        if not os.path.exists(snapshot_path):
            os.makedirs(snapshot_path)
            
        # Save config to multiple formats
        json_path = os.path.join(snapshot_path, 'config.json')
        with open(json_path, 'w') as f:
            json.dump(config, f, indent=2, sort_keys=True)
            
        yaml_path = os.path.join(snapshot_path, 'config.yaml')
        with open(yaml_path, 'w') as f:
            yaml.dump(config, f, sort_keys=True)
            
        # Create metadata
        metadata = {
            'timestamp': datetime.datetime.now().isoformat(),
            'name': name
        }
        
        metadata_path = os.path.join(snapshot_path, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        # Update snapshot index
        index_path = os.path.join(snapshot_dir, 'snapshot_index.json')
        
        # Load existing index or create new one
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                try:
                    snapshot_index = json.load(f)
                except json.JSONDecodeError:
                    snapshot_index = {'snapshots': []}
        else:
            snapshot_index = {'snapshots': []}
            
        # Add snapshot to index
        snapshot_info = {
            'name': name,
            'timestamp': metadata['timestamp'],
            'path': name
        }
        
        snapshot_index['snapshots'].append(snapshot_info)
        snapshot_index['latest'] = name
        
        # Write updated index
        with open(index_path, 'w') as f:
            json.dump(snapshot_index, f, indent=2)
            
        logger.info(f"Saved configuration snapshot: {name}")
        return name
    
    def load_config_snapshot(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load a configuration snapshot.
        
        Args:
            name: Name of snapshot to load (default: latest)
            
        Returns:
            Dict: Configuration snapshot
        """
        # Find snapshot directory
        snapshot_dir = os.path.join(self.base_dir, 'snapshots')
        if not os.path.exists(snapshot_dir):
            raise FileNotFoundError(f"Snapshot directory not found: {snapshot_dir}")
            
        # If no name specified, load latest
        if name is None:
            # Try to load from snapshot index
            index_path = os.path.join(snapshot_dir, 'snapshot_index.json')
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    snapshot_index = json.load(f)
                name = snapshot_index.get('latest')
                
            # If still no name, find most recent directory
            if name is None:
                snapshot_dirs = [d for d in os.listdir(snapshot_dir) 
                               if os.path.isdir(os.path.join(snapshot_dir, d)) 
                               and d != '__pycache__']
                if not snapshot_dirs:
                    raise FileNotFoundError(f"No snapshots found")
                snapshot_dirs.sort(reverse=True)  # Assuming snapshot names are sortable (like timestamps)
                name = snapshot_dirs[0]
                
        # Load snapshot
        snapshot_path = os.path.join(snapshot_dir, name)
        if not os.path.exists(snapshot_path):
            raise FileNotFoundError(f"Snapshot not found: {name}")
            
        json_path = os.path.join(snapshot_path, 'config.json')
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Config file not found: {json_path}")
            
        with open(json_path, 'r') as f:
            config = json.load(f)
            
        return config
    
    def export_parameters(self, 
                         component_type: str, 
                         component_name: str, 
                         version: Optional[str] = None, 
                         export_dir: Optional[str] = None,
                         format: str = 'yaml') -> str:
        """
        Export parameters to a standalone file.
        
        Args:
            component_type: Type of component (strategy, risk_manager, etc.)
            component_name: Name of component (ma_crossover, enhanced, etc.)
            version: Version to export (default: latest)
            export_dir: Directory to export to (default: current directory)
            format: Export format ('yaml' or 'json')
            
        Returns:
            str: Path to exported file
        """
        # Load parameters
        parameters, metadata = self.load_parameters(
            component_type, component_name, version, include_metadata=True)
            
        # Determine export directory
        if export_dir is None:
            export_dir = os.getcwd()
            
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
            
        # Get version string
        version_str = metadata.get('version', 'latest')
            
        # Create export file name
        file_name = f"{component_type}_{component_name}_{version_str}"
        
        if format.lower() == 'yaml':
            file_path = os.path.join(export_dir, f"{file_name}.yaml")
            with open(file_path, 'w') as f:
                yaml.dump(parameters, f)
                
        elif format.lower() == 'json':
            file_path = os.path.join(export_dir, f"{file_name}.json")
            with open(file_path, 'w') as f:
                json.dump(parameters, f, indent=2)
                
        else:
            raise ValueError(f"Unsupported export format: {format}")
            
        logger.info(f"Exported parameters to {file_path}")
        return file_path
    
    def import_parameters(self, 
                        file_path: str, 
                        component_type: str, 
                        component_name: str,
                        comment: Optional[str] = None) -> str:
        """
        Import parameters from a file.
        
        Args:
            file_path: Path to parameter file (YAML or JSON)
            component_type: Type of component (strategy, risk_manager, etc.)
            component_name: Name of component (ma_crossover, enhanced, etc.)
            comment: Optional comment for the imported version
            
        Returns:
            str: Version identifier for the imported parameters
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Parameter file not found: {file_path}")
            
        # Determine file format from extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Load parameters from file
        if file_ext == '.yaml' or file_ext == '.yml':
            with open(file_path, 'r') as f:
                parameters = yaml.safe_load(f)
                
        elif file_ext == '.json':
            with open(file_path, 'r') as f:
                parameters = json.load(f)
                
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
            
        # Generate import metadata
        metadata = {
            'imported_from': file_path,
            'import_timestamp': datetime.datetime.now().isoformat()
        }
        
        # Generate version with import prefix
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        version = f"import_{timestamp}"
        
        # Add comment if provided
        if comment is None:
            comment = f"Imported from {os.path.basename(file_path)}"
            
        # Save imported parameters
        result_version = self.save_parameters(
            component_type, component_name, parameters, metadata, version, comment)
            
        logger.info(f"Imported parameters from {file_path} as version {result_version}")
        return result_version
    
    def optimize_parameters(self,
                          component_type: str,
                          component_name: str,
                          optimizer_config: Dict[str, Any]) -> str:
        """
        Save optimization results as a new parameter version.
        
        Args:
            component_type: Type of component (strategy, risk_manager, etc.)
            component_name: Name of component (ma_crossover, enhanced, etc.)
            optimizer_config: Optimization configuration and results
            
        Returns:
            str: Version identifier for the optimized parameters
        """
        # Extract optimized parameters
        parameters = optimizer_config.get('best_params', {})
        
        # Create metadata
        metadata = {
            'optimization': {
                'method': optimizer_config.get('method', 'unknown'),
                'metric': optimizer_config.get('metric', 'unknown'),
                'score': optimizer_config.get('best_score', None),
                'iterations': optimizer_config.get('iterations', 0),
                'duration': optimizer_config.get('duration', 0),
                'timestamp': datetime.datetime.now().isoformat()
            }
        }
        
        # Add start parameters for reference
        if 'start_params' in optimizer_config:
            metadata['optimization']['start_params'] = optimizer_config['start_params']
            
        # Generate version with optimization prefix
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        version = f"opt_{timestamp}"
        
        # Generate comment
        comment = f"Optimized using {metadata['optimization']['method']} " \
                f"(score: {metadata['optimization']['score']})"
                
        # Save optimized parameters
        result_version = self.save_parameters(
            component_type, component_name, parameters, metadata, version, comment)
            
        # Also save full optimization results
        opt_dir = os.path.join(self.dirs['optimizations'], f"{component_type}_{component_name}")
        if not os.path.exists(opt_dir):
            os.makedirs(opt_dir)
            
        # Save optimizer config with results
        opt_path = os.path.join(opt_dir, f"optimization_{timestamp}.json")
        with open(opt_path, 'w') as f:
            json.dump(optimizer_config, f, indent=2)
            
        logger.info(f"Saved optimization results to {opt_path}")
        logger.info(f"Saved optimized parameters as version {result_version}")
        
        return result_version