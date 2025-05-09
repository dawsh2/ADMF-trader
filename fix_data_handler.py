#!/usr/bin/env python
"""
Fix the data handler to add missing get_symbols method
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_data_handler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fix_data')

def add_get_symbols_method():
    """Add the get_symbols method to the data handler"""
    data_handler_path = "src/data/historical_data_handler.py"
    
    logger.info(f"Adding get_symbols method to data handler: {data_handler_path}")
    
    try:
        # Read the current file
        with open(data_handler_path, 'r') as f:
            content = f.read()
        
        # Create a backup
        with open(f"{data_handler_path}.bak", 'w') as f:
            f.write(content)
        
        # Check if the get_symbols method already exists
        if "def get_symbols" in content:
            logger.info("get_symbols method already exists, but might not be working correctly")
            
            # Update it to be more reliable
            if "return list(self.data.keys())" not in content:
                # Add a fixed implementation by replacing any existing implementation
                content_lines = content.split('\n')
                method_added = False
                
                for i, line in enumerate(content_lines):
                    if "def get_symbols" in line:
                        # Find the end of the method
                        method_end = i + 1
                        indent = line.split("def")[0]
                        
                        while method_end < len(content_lines) and (
                            content_lines[method_end].startswith(indent + " ") or 
                            not content_lines[method_end].strip()
                        ):
                            method_end += 1
                        
                        # Replace the method
                        new_method = [
                            f"{indent}def get_symbols(self):",
                            f"{indent}    \"\"\"",
                            f"{indent}    Get the list of symbols in the data handler.",
                            f"{indent}    ",
                            f"{indent}    Returns:",
                            f"{indent}        list: List of symbol strings",
                            f"{indent}    \"\"\"",
                            f"{indent}    # Return list of keys from the data dictionary",
                            f"{indent}    symbols = list(self.data.keys())",
                            f"{indent}    import logging",
                            f"{indent}    logger = logging.getLogger(__name__)",
                            f"{indent}    logger.info(f\"Data handler returning symbols: {{symbols}}\")",
                            f"{indent}    return symbols"
                        ]
                        
                        # Replace the method in the content
                        content_lines[i:method_end] = new_method
                        method_added = True
                        break
                
                if method_added:
                    # Join the lines back together
                    modified_content = '\n'.join(content_lines)
                    
                    # Write the modified content
                    with open(data_handler_path, 'w') as f:
                        f.write(modified_content)
                    
                    logger.info("Updated get_symbols method in data handler")
                    return True
                else:
                    logger.warning("Could not find get_symbols method to update")
            else:
                logger.info("get_symbols method already returns list(self.data.keys())")
                return True
        
        # If the method doesn't exist, add it
        # Find where to insert the method - after get_current_symbol
        if "def get_current_symbol" in content:
            modified_content = content.replace(
                "def get_current_symbol(self):",
                """def get_symbols(self):
        \"\"\"
        Get the list of symbols in the data handler.
        
        Returns:
            list: List of symbol strings
        \"\"\"
        # Return list of keys from the data dictionary
        symbols = list(self.data.keys())
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Data handler returning symbols: {symbols}")
        return symbols
        
    def get_current_symbol(self)"""
            )
            
            # Write the modified content
            with open(data_handler_path, 'w') as f:
                f.write(modified_content)
            
            logger.info("Added get_symbols method to data handler")
            return True
        else:
            logger.warning("Could not find get_current_symbol method to insert after")
            
            # Add to the end of the class as a fallback
            modified_content = content.replace(
                "            return not any(len(df) > 0 for df in self.data.values())",
                """            return not any(len(df) > 0 for df in self.data.values())
            
    def get_symbols(self):
        \"\"\"
        Get the list of symbols in the data handler.
        
        Returns:
            list: List of symbol strings
        \"\"\"
        # Return list of keys from the data dictionary
        symbols = list(self.data.keys())
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Data handler returning symbols: {symbols}")
        return symbols"""
            )
            
            # Write the modified content
            with open(data_handler_path, 'w') as f:
                f.write(modified_content)
            
            logger.info("Added get_symbols method to the end of the data handler class")
            return True
    
    except Exception as e:
        logger.error(f"Error adding get_symbols method: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def fix_strategy_adapter():
    """Make the strategy adapter more resilient to missing methods"""
    adapter_path = "src/strategy/strategy_adapters.py"
    
    logger.info(f"Making strategy adapter more resilient: {adapter_path}")
    
    try:
        # Read the current file
        with open(adapter_path, 'r') as f:
            content = f.read()
        
        # Create a backup
        with open(f"{adapter_path}.bak", 'w') as f:
            f.write(content)
        
        # Make the code more resilient to missing get_symbols method
        if "if data_handler and hasattr(data_handler, 'get_symbols')" in content:
            # Add fallback symbols if get_symbols method is missing
            modified_content = content.replace(
                "if data_handler and hasattr(data_handler, 'get_symbols') and callable(data_handler.get_symbols):",
                """if data_handler:
            # Try to get symbols from data_handler
            symbols = None
            
            # First, try get_symbols method
            if hasattr(data_handler, 'get_symbols') and callable(data_handler.get_symbols):"""
            )
            
            modified_content = modified_content.replace(
                "else:\n            logger.warning(\"Data handler has no get_symbols method or no symbols available\")",
                """else:
                # Try to get symbols from data property
                if hasattr(data_handler, 'data') and isinstance(data_handler.data, dict):
                    symbols = list(data_handler.data.keys())
                    logger.info(f"Got symbols from data_handler.data keys: {symbols}")
                    
                    # Pass symbols to strategy if it has a symbols attribute
                    if hasattr(self.strategy, 'symbols'):
                        if not self.strategy.symbols and symbols:
                            self.strategy.symbols = symbols
                            logger.info(f"Updated strategy symbols from data keys: {self.strategy.symbols}")
                        elif self.strategy.symbols:
                            logger.info(f"Strategy already has symbols: {self.strategy.symbols}")
                    
                # Final fallback - check for backtest configuration
                elif hasattr(data_handler, 'data_config') and isinstance(data_handler.data_config, dict):
                    # Try to extract symbols from the configuration
                    sources = data_handler.data_config.get('sources', [])
                    if sources:
                        symbols = [source.get('symbol') for source in sources if source.get('symbol')]
                        if symbols:
                            logger.info(f"Got symbols from data_config sources: {symbols}")
                            
                            # Pass symbols to strategy if it has a symbols attribute
                            if hasattr(self.strategy, 'symbols'):
                                if not self.strategy.symbols and symbols:
                                    self.strategy.symbols = symbols
                                    logger.info(f"Updated strategy symbols from config sources: {self.strategy.symbols}")
                                elif self.strategy.symbols:
                                    logger.info(f"Strategy already has symbols: {self.strategy.symbols}")
                
                # If we still don't have symbols, try to get from context or config
                if not symbols and context:
                    if 'config' in context and isinstance(context['config'], dict):
                        config_symbols = context['config'].get('symbols')
                        if config_symbols:
                            symbols = config_symbols
                            logger.info(f"Got symbols from context config: {symbols}")
                            
                            # Pass symbols to strategy if it has a symbols attribute
                            if hasattr(self.strategy, 'symbols'):
                                if not self.strategy.symbols and symbols:
                                    self.strategy.symbols = symbols
                                    logger.info(f"Updated strategy symbols from context config: {self.strategy.symbols}")
                                elif self.strategy.symbols:
                                    logger.info(f"Strategy already has symbols: {self.strategy.symbols}")
                
                # If still no symbols, use default symbol
                if not symbols:
                    logger.warning("Data handler has no get_symbols method or no symbols available")
                    
                    # Use predefined symbols from the strategy
                    if hasattr(self.strategy, 'symbols') and self.strategy.symbols:
                        logger.info(f"Using strategy's predefined symbols: {self.strategy.symbols}")
                    # Use default symbol as last resort
                    elif hasattr(self.strategy, 'symbols'):
                        default_symbol = "HEAD"  # Using HEAD as the default symbol
                        self.strategy.symbols = [default_symbol]
                        logger.info(f"Using default symbol: {default_symbol}")"""
            )
            
            # Write the modified content
            with open(adapter_path, 'w') as f:
                f.write(modified_content)
            
            logger.info("Made strategy adapter more resilient to missing get_symbols method")
            return True
        else:
            logger.warning("Could not find get_symbols check in strategy adapter")
            return False
    
    except Exception as e:
        logger.error(f"Error fixing strategy adapter: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Apply all data handler fixes"""
    logger.info("Applying data handler fixes...")
    
    # Fix the data handler to add get_symbols method
    if add_get_symbols_method():
        logger.info("Successfully added get_symbols method to data handler")
    else:
        logger.warning("Failed to add get_symbols method to data handler")
    
    # Fix the strategy adapter to be more resilient
    if fix_strategy_adapter():
        logger.info("Successfully made strategy adapter more resilient")
    else:
        logger.warning("Failed to make strategy adapter more resilient")
    
    logger.info("Data handler fixes completed")
    logger.info("Now run the optimization again with:")
    logger.info("python run_all_fixes_and_optimize.py")

if __name__ == "__main__":
    main()
