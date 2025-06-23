# test.py
from DSSATTools.soil import SoilProfile

# exemplo de uso:
solpath = r"C:\Users\migue\Downloads\projeto_interfaceSbuild\master\SOIL.SOL"
code    = "IBSB910017"
soil    = SoilProfile.from_file(code, solpath)
print(soil)