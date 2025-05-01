"""
Script to extract and print the Event class definition without importing it.
This helps us understand the class structure without executing any code.
"""

import os
import sys
import re

def find_file_in_directory(directory, filename_pattern):
    """Find files matching a pattern in a directory (recursive)."""
    matches = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if re.search(filename_pattern, file):
                matches.append(os.path.join(root, file))
    return matches

def extract_class_definition(file_path, class_name):
    """Extract a class definition from a file without executing any code."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Find class definition using regex
        class_pattern = r'class\s+' + class_name + r'\s*\([^)]*\):\s*(?:[^\n]*\n)+(?:\s+[^\n]*\n)+'
        match = re.search(class_pattern, content, re.MULTILINE)
        
        if match:
            return match.group(0)
        else:
            # Try a simpler pattern
            class_pattern = r'class\s+' + class_name + r'[:\(][^{]*:'
            match = re.search(class_pattern, content)
            if match:
                # Get the whole class definition
                start_pos = match.start()
                
                # Find indent level of first line after class definition
                class_def_end = content.find(':', start_pos) + 1
                next_line_start = content.find('\n', class_def_end) + 1
                
                if next_line_start >= len(content):
                    return content[start_pos:]
                
                # Get indent level
                indent_match = re.match(r'(\s+)', content[next_line_start:])
                if not indent_match:
                    return "Could not determine class indent level"
                
                indent_level = indent_match.group(1)
                
                # Extract all lines with this indent level or more
                lines = content[start_pos:].split('\n')
                class_lines = [lines[0]]
                
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == '' or line.startswith(indent_level):
                        class_lines.append(line)
                    else:
                        # Check if we've reached a line with less indentation
                        # which means we're out of the class definition
                        if line.strip() and not line.startswith(' '):
                            break
                        # Otherwise keep collecting lines
                        class_lines.append(line)
                
                return '\n'.join(class_lines)
            
            return "Class definition not found"
    except Exception as e:
        return f"Error extracting class: {e}"

def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # Look for files that might contain the Event class
    print(f"Searching for event_types.py in {project_root}...")
    event_files = find_file_in_directory(os.path.join(project_root, 'src'), r'event_types\.py$')
    
    if not event_files:
        print("No event_types.py files found!")
        return 1
    
    print(f"Found {len(event_files)} potential files:")
    for file in event_files:
        print(f"  - {file}")
    
    for file in event_files:
        print(f"\nExtracting Event class from {file}:")
        event_class = extract_class_definition(file, 'Event')
        print("-" * 80)
        print(event_class)
        print("-" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
