import pandas as pd
import re
import sys
from datetime import datetime
import dateutil.parser

def convert_to_utc(input_file, output_file=None):
    """
    Convert all timestamps in a CSV file to UTC without timezone information.
    
    Args:
        input_file (str): Path to the input CSV file
        output_file (str, optional): Path to the output CSV file. If not provided,
                                     will use input_file name with '_utc' suffix
    """
    if output_file is None:
        # Create output filename by adding '_utc' before the extension
        parts = input_file.rsplit('.', 1)
        output_file = f"{parts[0]}_utc.{parts[1]}" if len(parts) > 1 else f"{input_file}_utc"
    
    print(f"Processing {input_file}")
    print(f"Output will be saved to {output_file}")
    
    # Read the file as text first
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # Pattern to match datetime with timezone
    dt_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2})')
    
    # Process each line
    processed_lines = []
    for line in lines:
        # Find all datetime strings with timezone
        matches = dt_pattern.findall(line)
        
        processed_line = line
        for dt_str in matches:
            try:
                # Parse the datetime with timezone
                dt = dateutil.parser.parse(dt_str)
                # Convert to UTC and format without timezone info
                utc_dt = dt.astimezone(dateutil.tz.UTC).strftime('%Y-%m-%d %H:%M:%S')
                # Replace in the line
                processed_line = processed_line.replace(dt_str, utc_dt)
            except Exception as e:
                print(f"Error processing datetime {dt_str}: {e}")
        
        processed_lines.append(processed_line)
    
    # Write the processed lines to the output file
    with open(output_file, 'w') as f:
        f.writelines(processed_lines)
    
    print(f"All timestamps converted to UTC. File saved to {output_file}")
    
    # Verify the file looks good by displaying a few lines
    try:
        df = pd.read_csv(output_file, header=None)
        print("\nFirst 5 rows of the processed file:")
        print(df.head())
    except Exception as e:
        print(f"Could not display preview due to error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_to_utc.py input_file.csv [output_file.csv]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    convert_to_utc(input_file, output_file)
