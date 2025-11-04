import re

def parse_data_cde(path="C:/DSSAT48/DATA.CDE"):
    """
    Robust parser for DSSAT DATA.CDE files.
    Returns {acronym: "Full variable name (units)"}.
    """
    variable_map = {}
    pattern = re.compile(r"^([A-Z0-9#]+)\s+(.+?)\s{2,}(.+?)(?:\s{2,}|$)")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith(("*", "@")):
                continue

            # Normalize whitespace
            line = re.sub(r"\s+", " ", line)

            # Try main regex first
            match = pattern.match(raw_line)
            if match:
                acronym = match.group(1).strip()
                label = match.group(2).strip()
                desc = match.group(3).strip(" .")
            else:
                # Fallback: split by double or triple spaces
                parts = re.split(r"\s{2,}", raw_line.strip())
                acronym = parts[0].strip() if len(parts) > 0 else None
                label = parts[1].strip() if len(parts) > 1 else acronym
                desc = parts[2].strip(" .") if len(parts) > 2 else label

            # Sanity check
            if acronym:
                # Combine label and acronym if DSSAT GBuild style is desired
                display_name = f"{label} ({acronym})" if acronym not in label else label
                variable_map[acronym] = display_name

    return variable_map
