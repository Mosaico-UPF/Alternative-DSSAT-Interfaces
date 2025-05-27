from pathlib import Path
from DSSATTools.soil import SoilProfile

def update_soil_file(file_path: str | Path, profile_id: str, updates: dict) -> None:
    
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"O arquivo {file_path} não foi encontrado.")

    soil_profile = SoilProfile.from_file(profile_id, file_path)

    # Atualiza os campos do perfil de solo utilizando acesso por chave
    for key, value in updates.items():
        if key in soil_profile:
            soil_profile[key] = value
        elif "table" in soil_profile.__dict__:
            atualizado = False
            for layer in soil_profile.table:
                if key in layer:
                    layer[key] = value
                    atualizado = True
            if not atualizado:
                print(f"Aviso: O campo '{key}' não existe no perfil de solo e será ignorado.")
        else:
            print(f"Aviso: O campo '{key}' não existe no perfil de solo e será ignorado.")

    with file_path.open("w", encoding="utf-8") as f:
        f.write(soil_profile._write_sol())

    print(f"Perfil de solo '{profile_id}' atualizado com sucesso no arquivo {file_path}.")

if __name__ == "__main__":
    # Caminho para o arquivo .SOL
    sol_file = "UMVA030003.SOL"

    # ID do perfil de solo a ser atualizado
    profile_id = "UMVA030003"

    # Campos a serem atualizados
    updates = {
        "salb": 0.13,               
        "sldr": 0.6,                
        "soil_series_name": "Updated Soil"  
    }

    try:
        update_soil_file(sol_file, profile_id, updates)
    except (FileNotFoundError, AttributeError, ValueError) as e:
        print(f"Erro: {e}")