#!/usr/bin/env python3
"""
Script to find any "Fixed Event class" print statements in the codebase.
"""
import os
import sys
import re

def search_files(directory, pattern):
    """Search for pattern in files."""
    matches = []
    
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.py'):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if pattern in content:
                            matches.append((filepath, content))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return matches

def extract_print_statements(content):
    """Extract print statements containing the pattern."""
    lines = content.split('\n')
    prints = []
    
    pattern = re.compile(r'print\s*\(.*Fixed.*Event.*class.*\)', re.IGNORECASE)
    
    for i, line in enumerate(lines):
        if pattern.search(line):
            context_start = max(0, i - 2)
            context_end = min(len(lines), i + 3)
            context = '\n'.join([f"{j+1}: {lines[j]}" for j in range(context_start, context_end)])
            prints.append(context)
    
    return prints

def main():
    """Main function."""
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Searching in {directory}...")
    
    # Search for "Fixed Event class" in files
    matches = search_files(directory, "Fixed Event class")
    
    if not matches:
        print("No matches found for 'Fixed Event class'")
        return
    
    print(f"Found {len(matches)} matches:")
    
    for filepath, content in matches:
        print(f"\nFile: {filepath}")
        prints = extract_print_statements(content)
        if prints:
            print("Print statements:")
            for p in prints:
                print(p)
                print("-" * 40)
        else:
            print("No print statements found, but 'Fixed Event class' is in the file")
            print("First 10 lines:")
            print('\n'.join(content.split('\n')[:10]))
            print("-" * 40)

if __name__ == "__main__":
    main()
