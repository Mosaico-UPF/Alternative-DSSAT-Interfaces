from DSSATTools.filex import read_filex

def get_slope_from_filex(filex_path, treatment_number=1):
    """
    Lê o % Slope do Field no arquivo FileX
    
    Args:
        filex_path (str): Caminho para o arquivo .XYX (ex: BRPI0202.MZX)
        treatment_number (int): Número do tratamento (default: 1)
        
    Returns:
        float: % Slope ou None se não disponível
    """
    try:
        # Lê o FileX usando DSSATTools
        treatments = read_filex(filex_path)
        
        # Verifica se o tratamento existe
        if treatment_number not in treatments:
            print(f"Tratamento {treatment_number} não encontrado no FileX")
            return None
        
        treatment = treatments[treatment_number]
        
        # Obtém o Field do tratamento
        if "Field" not in treatment:
            print(f"Field não encontrado no tratamento {treatment_number}")
            return None
        
        field = treatment["Field"]
        
        # O campo flsa contém slope (e aspect se disponível)
        # Formato: pode ser um número único (slope) ou dois valores (slope aspect)
        flsa = field.get("flsa")
        
        if flsa is None:
            return None
        
        # Converte para string e separa por espaço
        flsa_str = str(flsa).strip()
        
        if not flsa_str or flsa_str == '-99':
            return None
        
        # Se houver espaço, pega o primeiro valor
        parts = flsa_str.split()
        slope = float(parts[0])
        
        return slope
        
    except FileNotFoundError:
        print(f"Erro: Arquivo {filex_path} não encontrado")
        return None
    except KeyError as e:
        print(f"Erro ao acessar campo: {e}")
        return None
    except ValueError as e:
        print(f"Erro ao converter slope para número: {e}")
        return None
    except Exception as e:
        print(f"Erro ao ler FileX: {e}")
        return None


def get_soil_id_from_filex(filex_path, treatment_number=1):
    """
    Lê o ID do perfil de solo usado no tratamento
    
    Args:
        filex_path (str): Caminho para o arquivo FileX
        treatment_number (int): Número do tratamento
        
    Returns:
        str: ID do perfil de solo (ex: 'IBSB910015') ou None
    """
    try:
        treatments = read_filex(filex_path)
        
        if treatment_number not in treatments:
            return None
        
        treatment = treatments[treatment_number]
        
        if "Field" not in treatment:
            return None
        
        field = treatment["Field"]
        
        # O campo id_soil pode ser um objeto SoilProfile ou uma string
        id_soil = field.get("id_soil")
        
        if id_soil is None:
            return None
        
        # Se for um objeto SoilProfile, pega o código
        if hasattr(id_soil, 'code'):
            return id_soil.code
        
        # Se for string, retorna diretamente
        return str(id_soil).strip()
        
    except Exception as e:
        print(f"Erro ao ler soil ID do FileX: {e}")
        return None


def get_complete_soil_data(soil_file, filex_path=None, treatment_number=1):
    """
    Combina dados do SOIL.SOL com % Slope do FileX
    
    Args:
        soil_file (str): Caminho para SOIL.SOL
        filex_path (str, optional): Caminho para o FileX
        treatment_number (int): Número do tratamento
        
    Returns:
        dict: Dados completos incluindo slope se FileX for fornecido
    """
    from readSoilFile import get_soil_display_data
    
    # Se FileX foi fornecido, obtém o soil ID dele
    if filex_path:
        profile_id = get_soil_id_from_filex(filex_path, treatment_number)
        if not profile_id:
            print("Não foi possível obter o soil ID do FileX")
            return None
    else:
        print("FileX não fornecido, é necessário fornecer o profile_id manualmente")
        return None
    
    # Lê dados do SOIL.SOL
    soil_data = get_soil_display_data(profile_id, soil_file)
    
    if not soil_data:
        return None
    
    # Adiciona o slope do FileX
    if filex_path:
        slope = get_slope_from_filex(filex_path, treatment_number)
        soil_data['slope'] = slope
    
    return soil_data


# Exemplo de uso
if __name__ == "__main__":
    import os
    
    # Teste 1: Ler slope de um FileX
    print("=== Teste 1: Lendo slope do FileX ===")
    filex_path = os.path.join("Py_DSSATTools", "tests", "data", "Maize", "BRPI0202.MZX")
    
    if os.path.exists(filex_path):
        slope = get_slope_from_filex(filex_path, treatment_number=1)
        print(f"% Slope do tratamento 1: {slope}")
        
        soil_id = get_soil_id_from_filex(filex_path, treatment_number=1)
        print(f"Soil ID do tratamento 1: {soil_id}")
    else:
        print(f"Arquivo não encontrado: {filex_path}")
    
    print()
    
    # Teste 2: Combinar dados SOIL.SOL e FileX
    print("=== Teste 2: Dados completos (SOIL.SOL + FileX) ===")
    
    soil_file = "SOIL.SOL"
    if os.path.exists(soil_file) and os.path.exists(filex_path):
        complete_data = get_complete_soil_data(soil_file, filex_path, treatment_number=1)
        
        if complete_data:
            print(f"Color: {complete_data['color'] or '(empty)'}")
            print(f"Drainage: {complete_data['drainage']}")
            print(f"% Slope: {complete_data['slope']}")
            print(f"Runoff Potential: {complete_data['runoff_potential']}")
            print(f"Fertility Factor: {complete_data['fertility_factor']}")
    else:
        print("Arquivos necessários não encontrados")