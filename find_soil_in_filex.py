# save as find_soil_in_filex.py
import pathlib, sys, re

soil = sys.argv[1].upper()
root = pathlib.Path(r"C:\DSSAT48")

for fx in root.rglob("*.?x?"):
    if re.search(soil, fx.read_text(errors="ignore", encoding="latin-1"), re.I):
        print(fx)
