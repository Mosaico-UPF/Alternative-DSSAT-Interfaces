# showSoilProfiles.py
from pathlib import Path
from DSSATTools.soil import SoilProfile

def show_profiles(sol_path: str | Path) -> None:
    sol_path = Path(sol_path)
    lines = sol_path.read_text().splitlines()

    # captura todos os códigos (10 caracteres depois do '*')
    codes = [
        line[1:11]
        for line in lines
        if line.startswith("*") and "SOILS:" not in line
    ]

    if not codes:
        print("Nenhum perfil encontrado.")
        return

    print(f"\nEncontrados {len(codes)} perfil(is) em «{sol_path.name}»\n")

    for idx, code in enumerate(codes, start=1):
        prof: SoilProfile = SoilProfile.from_file(code, sol_path)
        print(f"===== Perfil {idx}: {code.strip()} =====")
        print(prof._write_sol())          # <-- texto completo do perfil

if __name__ == "__main__":
    show_profiles("AG.SOL")
