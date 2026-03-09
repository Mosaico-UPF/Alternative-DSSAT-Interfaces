from DSSATTools.soil import SoilProfile

# Teste um perfil que deveria ter cor "Red"
soil = SoilProfile.from_file('IBSB910009', 'SOIL.SOL')
print(f"SCOM raw value: '{soil['scom']}'")
print(f"SCOM type: {type(soil['scom'])}")
print(f"SCOM repr: {repr(soil['scom'])}")

perfis = ['IBSB910009', 'IBSB910017', 'IBSB910026', 'IBSB910027']

for pid in perfis:
    soil = SoilProfile.from_file(pid, 'SOIL.SOL')
    print(f"\n{pid}:")
    print(f"  Nome: {soil['soil_series_name']}")
    print(f"  SCOM: '{soil['scom']}'")
    print(f"  SLDR: {soil['sldr']}")
    
    # Primeira camada
    layer = soil.table[0]
    print(f"  SLOC (1ª camada): {layer['sloc']}")
    print(f"  SLCL (1ª camada): {layer['slcl']}")