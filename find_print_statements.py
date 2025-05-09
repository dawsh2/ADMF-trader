#!/usr/bin/env python3
"""
Find print statements in Python source files that could be causing the
"Fixed Event class: Added 'type' property" message.
"""
import os
import re
import sys

def find_print_statements(directory):
    """Find print statements related to Event class."""
    pattern = re.compile(r'print\s*\(\s*[\'"]Fixed\s+Event\s+class', re.IGNORECASE)
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        if pattern.search(content):
                            print(f"Found potential match in {filepath}")
                            
                            # Show the context
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                if pattern.search(line):
                                    start = max(0, i - 3)
                                    end = min(len(lines), i + 4)
                                    print("Context:")
                                    for j in range(start, end):
                                        print(f"{j+1}: {lines[j]}")
                                    print("-" * 60)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Searching for Event class print statements in {directory}...")
    find_print_statements(directory)

if __name__ == "__main__":
    main()
