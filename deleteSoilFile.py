from pathlib import Path

def delete_soil_profile(file_path: str | Path, profile_id: str) -> None:

    file_path = Path(file_path)
    if not file_path.exists():
        print(f"Arquivo '{file_path}' não encontrado.")
        return

    lines = file_path.read_text(encoding="utf-8").splitlines()

    # Identifica as linhas que iniciam um perfil. Considera todas as linhas que começam
    # com "*" e que não contêm "SOILS:"
    profile_indices = []
    for idx, line in enumerate(lines):
        if line.startswith("*") and "SOILS:" not in line:
            code = line[1:11].strip()
            profile_indices.append((idx, code))

    if not profile_indices:
        print("Nenhum perfil encontrado no arquivo. Excluindo o arquivo.")
        file_path.unlink()
        return

    # Procura o bloco correspondente ao perfil a ser excluído
    block_start = None
    block_end = None
    for i, (idx, code) in enumerate(profile_indices):
        if code == profile_id:
            block_start = idx
            # Define o fim do bloco como a linha de início do próximo perfil(se houver)
            if i + 1 < len(profile_indices):
                block_end = profile_indices[i + 1][0]
            else:
                block_end = len(lines)
            break

    if block_start is None:
        print(f"Perfil '{profile_id}' não encontrado no arquivo.")
        return

    # Remove o bloco do perfil escolhido
    new_lines = lines[:block_start] + lines[block_end:]

    # Verifica se ainda há perfis restantes no arquivo atualizado
    remaining_profiles = [
        line for line in new_lines 
        if line.startswith("*") and "SOILS:" not in line
    ]

    if not remaining_profiles:
        print("Após remoção, não há perfis restantes. Excluindo o arquivo.")
        file_path.unlink()
    else:
        file_path.write_text("\n".join(new_lines), encoding="utf-8")
        print(f"Perfil '{profile_id}' excluído com sucesso do arquivo {file_path}.")

if __name__ == "__main__":
    # Nome do arquivo .SOL e ID do perfil a ser excluído
    sol_file = "UMVA030003.SOL"
    profile_id = "AGcavero12"
    
    delete_soil_profile(sol_file, profile_id)