#!/usr/bin/env python
"""
Simple script to fix the indentation issue with the debug report method.
"""

def fix_file():
    """Fix the indentation of _generate_debug_report in backtest.py"""
    with open("src/execution/backtest/backtest.py", "r") as f:
        lines = f.readlines()
    
    with open("src/execution/backtest/backtest.py", "w") as f:
        in_debug_method = False
        for i, line in enumerate(lines):
            # Fix the method declaration line
            if "def _generate_debug_report(self):" in line and "    def" not in line:
                f.write("    def _generate_debug_report(self):\n")
                in_debug_method = True
            # Skip the opening docstring line if we just fixed the method line
            elif in_debug_method and i > 0 and '"""Generate a detailed debug report' in line:
                f.write("        \"\"\"Generate a detailed debug report to help diagnose issues.\"\"\"\n")
            # Write all other lines normally
            else:
                f.write(line)
    
    print("Fixed the indentation in backtest.py")
    print("Now you can run: python main.py --config config/fixed_config.yaml")

if __name__ == "__main__":
    fix_file()
