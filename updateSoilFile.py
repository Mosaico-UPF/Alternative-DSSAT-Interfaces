from pathlib import Path
from readSoilFile import show_profiles
from DSSATTools.soil import SoilProfile

def update_soil_file(file_path: str | Path, profile_id: str, updates: dict) -> None:
    """
    Atualiza o perfil `profile_id` no arquivo .SOL, preservando os demais perfis.
    Update the profile 'profile_id' in the .SOL file, preserving the other profiles.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"The file {file_path} was not found.")

    # reads all the profiles from the file
    profiles = show_profiles(file_path)  # readSoilFile.py

    # Loads the profile to be updated
    soil_profile = SoilProfile.from_file(profile_id, file_path)  # Py_DSSATTools/DSSATTools/soil.py

    # Applies all the updates
    for key, value in updates.items():
        if key in soil_profile:
            soil_profile[key] = value
        else:
            updated = False
            for layer in soil_profile.table:
                if key in layer:
                    layer[key] = value
                    updated = True
            if not updated:
                print(f"Warning: The field '{key}' does not exist in the soil profile and will be ignored.")

    # Reconstructs the file:
    # 1. Extracts the header before the first profile
    lines = file_path.read_text(encoding="utf-8").splitlines()
    starts = [i for i, l in enumerate(lines) if l.startswith("*") and "SOILS:" not in l]
    header = "\n".join(lines[:starts[0]]) + "\n"

    # 2. For each profile: If it has been edited, generates a new block, if not, reuses the content
    blocks: list[str] = []
    for p in profiles:
        if p["code"] == profile_id:
            # soil_profile._write_sol() includes header; remove the first two lines
            new_block = soil_profile._write_sol().splitlines()[2:]
            blocks.append("\n".join(new_block))
        else:
            blocks.append(p["content"])

    # 3. Unites all and saves
    full_content = header + "\n".join(blocks)
    file_path.write_text(full_content, encoding="utf-8")
    print(f"Perfil de solo '{profile_id}' updated successfully {file_path}.")

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