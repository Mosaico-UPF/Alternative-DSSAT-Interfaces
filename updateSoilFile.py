from pathlib import Path
from readSoilFile import show_profiles
from DSSATTools.soil import SoilProfile
from DSSATTools.soil import SoilLayer

def update_soil_file(file_path: str | Path, profile_id: str, updates: dict) -> None:
    """
    Atualiza o perfil `profile_id` no arquivo .SOL, preservando os demais perfis.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"O arquivo {file_path} não foi encontrado.")

    # Lê todos os perfis do arquivo
    profiles = show_profiles(file_path)  # readSoilFile.py

    # Carrega o perfil a ser atualizado
    soil_profile = SoilProfile.from_file(profile_id, file_path)  # Py_DSSATTools/DSSATTools/soil.py

    # Aplica as atualizações
    for key, value in updates.items():
        if key == "layers":
            soil_profile.table = [SoilLayer(**lay) for lay in value]
            continue  # já tratou, pula para o próximo

        if key in soil_profile:
            soil_profile[key] = value
        else:
            print(f"Aviso: campo «{key}» ignorado – não existe no cabeçalho.")

    # Reconstrói o arquivo:
    # 1. Extrai o cabeçalho antes do primeiro perfil
    lines = file_path.read_text(encoding="utf-8").splitlines()
    starts = [i for i, l in enumerate(lines) if l.startswith("*") and "SOILS:" not in l]
    header = "\n".join(lines[:starts[0]]) + "\n"

    # 2. Para cada perfil: se for o que foi editado, gera bloco novo; senão, reutiliza conteúdo
    blocks: list[str] = []
    for p in profiles:
        if p["code"] == profile_id:             # perfil editado
            new_block = soil_profile._write_sol().splitlines()[2:]
            blocks.append("\n".join(new_block))  # já começa com '*'
        else:                                   # perfis não editados
            blk = p["content"].lstrip()         # veio sem espaços extras
            if not blk.startswith("*"):         # devolve o '*'
                blk = "*" + blk
            blocks.append(blk)

    # 3. Une tudo e salva
    full_content = header + "\n\n".join(
        blk.rstrip("\n") for blk in blocks
    ) + "\n"          # garante newline final
    file_path.write_text(full_content, encoding="utf-8")
    print(f"Perfil de solo '{profile_id}' atualizado com sucesso em {file_path}.")

if __name__ == "__main__":
    sol_file = "UMVA030003.SOL"
    profile_id = "UMVA030003"
    updates = {
        "salb": 0.13,
        "sldr": 0.6,
        "soil_series_name": "Updated Soil"
    }
    try:
        update_soil_file(sol_file, profile_id, updates)
    except Exception as e:
        print(f"Erro: {e}")