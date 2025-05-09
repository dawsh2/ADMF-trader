#!/usr/bin/env python
"""
This is the simplest possible fix - directly override the _generate_debug_report method.
"""

# Create a very simple debug report method
debug_method = """
    def _generate_debug_report(self):
        \"\"\"Generate a detailed debug report to help diagnose issues.\"\"\"
        logger.info("======= DETAILED DEBUG REPORT =======")
        
        # Strategy state
        if hasattr(self.strategy, 'get_debug_info'):
            strategy_info = self.strategy.get_debug_info()
            logger.info(f"Strategy debug info: {strategy_info}")
        
        # Signal count
        signal_count = len(getattr(self.strategy, 'signals_history', []))
        logger.info(f"Total signals generated: {signal_count}")
        
        # Orders info
        if self.order_registry:
            orders = []
            if hasattr(self.order_registry, 'get_all_orders'):
                orders = self.order_registry.get_all_orders()
            elif hasattr(self.order_registry, 'get_active_orders'):
                orders = self.order_registry.get_active_orders()
                logger.info("Using get_active_orders() as get_all_orders() is not available")
            else:
                logger.warning("Order registry has neither get_all_orders nor get_active_orders method")
                
            logger.info(f"Total orders created: {len(orders)}")
            
        # Data info
        if self.data_handler:
            data_info = {
                "total_bars": self.iterations,
                "symbols": self.data_handler.get_symbols(),
                "start_date": None,
                "end_date": None
            }
            logger.info(f"Data information: {data_info}")
        
        logger.info("======= END DEBUG REPORT =======")
"""

# Read the current file
with open("src/execution/backtest/backtest.py", "r") as f:
    content = f.read()

# Check if we need to fix the indentation
if "        def _generate_debug_report" in content or "def _generate_debug_report" in content and "    def _generate_debug_report" not in content:
    # Find the position to insert the fixed method
    # First, try to find the start and end of the broken method
    start_pos = content.find("def _generate_debug_report(self):")
    if start_pos == -1:
        start_pos = content.find("        def _generate_debug_report(self):")
    
    if start_pos != -1:
        # Find the next method
        next_method = content.find("def ", start_pos + 10)
        if next_method == -1:
            next_method = content.find("# Factory", start_pos)
        
        if next_method != -1:
            # Replace the broken method with our fixed version
            fixed_content = content[:start_pos] + debug_method + content[next_method:]
            
            # Write the fixed content back to the file
            with open("src/execution/backtest/backtest.py", "w") as f:
                f.write(fixed_content)
            
            print("Fixed the _generate_debug_report method in backtest.py")
            print("Now run: python main.py --config config/fixed_config.yaml")
        else:
            print("Could not find the end of the broken method")
    else:
        print("Could not find the broken method")
else:
    print("The method seems to be properly indented already")

