import os
import re

def parse_data_cde(path="C:/DSSAT48/DATA.CDE"):
    """
    Parses the DSSAT DATA.CDE file and returns a dictionary mapping variable acronyms to full descriptions.

    Args:
        path (str): Full path to the DATA.CDE file. Defaults to DSSAT48's standard location.

    Returns:
        dict: A dictionary where keys are acronyms and values are full variable descriptions including units.

    Raises:
        FileNotFoundError: If the DATA.CDE file is not found at the specified path.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"DATA.CDE not found at: {path}")

    variable_map = {}

    with open(path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            line = line.strip()
            # Skip comments, empty lines, or header lines
            if not line or line.startswith('*') or line.startswith('@'):
                continue

            # Match lines with CDE, LABEL, DESCRIPTION, and optional SYNONYMS
            # Ensure DESCRIPTION starts after a clear space boundary
            match = re.match(r'^([A-Z0-9]{2,8})\s{1,}(.+?)\s{2,}(.+?)(?=\s{2,}\.|$)', line)
            if match:
                acronym = match.group(1).strip()
                label = match.group(2).strip()
                description = match.group(3).strip()
                # Additional check to avoid LABEL spillover
                if description.startswith(label):
                    description = description[len(label):].strip()
                    if not description or description == '.':
                        description = label
                        #print(f"Warning: DESCRIPTION starts with LABEL for {acronym}, using LABEL: {label}")
                elif not description or description == '.':
                    description = label
                    #print(f"Warning: Empty or invalid DESCRIPTION for {acronym}, using LABEL: {label}")
                variable_map[acronym] = description
            else:
                print(f"Warning: Could not parse line: {line}")

    return variable_map