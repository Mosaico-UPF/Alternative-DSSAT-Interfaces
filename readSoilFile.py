from DSSATTools.soil import SoilProfile
import numpy as np
from hydrology import slope_from_cn, cn_to_group
from soil_utils import drainage_class

def get_color_from_scom(scom):
    """Converte o código scom para nome de cor"""
    if not scom or str(scom).strip() in ['-99', '', 'None']:
        return ""
    
    color_map = {
        'BRO': 'Brown', 'BROW': 'Brown', 'BN': 'Brown', 'BR': 'Brown', 'BROWN': 'Brown',
        'RED': 'Red', 'R': 'Red', 'RD': 'Red',
        'BLA': 'Black', 'BLAC': 'Black', 'BL': 'Black', 'BK': 'Black', 'BLACK': 'Black',
        'YEL': 'Yellow', 'YELL': 'Yellow', 'Y': 'Yellow', 'YL': 'Yellow', 'YELLOW': 'Yellow',
        'GRE': 'Grey', 'GREY': 'Grey', 'GRAY': 'Grey', 'G': 'Grey', 'GY': 'Grey',
    }
    
    return color_map.get(str(scom).strip().upper(), "")


def format_value(value):
    """Converte valores para string, tratando None e nan como -99"""
    if value is None:
        return '-99'
    
    if isinstance(value, float):
        if np.isnan(value):
            return '-99'
    
    str_val = str(value).strip()
    
    if str_val == '' or str_val.lower() == 'nan':
        return '-99'
    
    return str_val


def calculate_slope_from_soil(slro):
    """
    Calcula % Slope a partir do Curve Number (slro) usando hydrology.py
    
    Args:
        slro (float): Runoff Curve Number do SOIL.SOL
        
    Returns:
        int: % Slope (1, 3, 8 ou 12) ou None
    """
    if slro is None or slro < 0 or (isinstance(slro, float) and np.isnan(slro)):
        return None
    
    runoff_group = cn_to_group(slro)
    
    if not runoff_group:
        return None
    
    slope = slope_from_cn(runoff_group, slro)
    
    return slope


def get_soil_display_data(profile_id, soil_file='SOIL.SOL'):
    """Lê dados de um perfil de solo e retorna os valores formatados para display"""
    try:
        soil = SoilProfile.from_file(profile_id, soil_file)
        
        color = get_color_from_scom(soil['scom'])
        drainage = drainage_class(soil['sldr'])
        runoff = cn_to_group(soil['slro'])
        
        slpf_val = soil['slpf']
        if slpf_val is None or (isinstance(slpf_val, float) and np.isnan(slpf_val)) or slpf_val < 0:
            fertility = None
        else:
            fertility = slpf_val
        
        slope = calculate_slope_from_soil(soil['slro'])
        
        return {
            'color': color,
            'drainage': drainage,
            'runoff_potential': runoff,
            'fertility_factor': fertility,
            'slope': slope
        }
        
    except FileNotFoundError:
        print(f"Erro: Arquivo {soil_file} não encontrado")
        return None
    except KeyError:
        print(f"Erro: Perfil {profile_id} não encontrado no arquivo {soil_file}")
        return None
    except Exception as e:
        print(f"Erro ao ler perfil {profile_id}: {e}")
        return None


def read_profile(soil_file, profile_id):
    """Lê um perfil de solo completo do arquivo .SOL"""
    try:
        soil = SoilProfile.from_file(profile_id, soil_file)
        
        slro_val = soil.get('slro')
        slope_str = '-99'
        
        if slro_val is not None and not (isinstance(slro_val, float) and np.isnan(slro_val)):
            try:
                slro_float = float(slro_val)
                if slro_float > 0:
                    slope_value = calculate_slope_from_soil(slro_float)
                    if slope_value is not None:
                        slope_str = str(slope_value)
            except (TypeError, ValueError):
                pass
        
        data = {
            'code': profile_id,
            'country': format_value(soil.get('country', '')),
            'site_name': format_value(soil.get('site', '')),
            'institute_code': soil.get('soil_data_source', '')[:2] if soil.get('soil_data_source') else '-99',
            'latitude': format_value(soil.get('lat', '')),
            'longitude': format_value(soil.get('long', '')),
            'soil_data_source': format_value(soil.get('soil_data_source', '')),
            'soil_series_name': format_value(soil.get('soil_series_name', '')),
            'soil_classification': format_value(soil.get('scs_family', '')),
            'color_code': format_value(soil.get('scom', '')),
            'drainage_rate': format_value(soil.get('sldr', '')),
            'runoff_curve': format_value(soil.get('slro', '')),
            'slope': slope_str,
            'fertility_factor': format_value(soil.get('slpf', '')),
            'albedo': format_value(soil.get('salb', '')),
            'layers': []
        }
        
        for layer in soil.table:
            layer_data = {
                'depth': format_value(layer.get('slb', '')),
                'texture': format_value(layer.get('slmh', '')),
                'clay': format_value(layer.get('slcl', '')),
                'silt': format_value(layer.get('slsi', '')),
                'stones': format_value(layer.get('slcf', '')),
                'oc': format_value(layer.get('sloc', '')),
                'ph': format_value(layer.get('slhw', '')),
                'cec': format_value(layer.get('scec', '')),
                'tn': format_value(layer.get('slni', '')),
                'lll': format_value(layer.get('slll', '')),
                'dul': format_value(layer.get('sdul', '')),
                'sat': format_value(layer.get('ssat', '')),
                'bd': format_value(layer.get('sbdm', '')),
                'ksat': format_value(layer.get('ssks', '')),
                'srgf': format_value(layer.get('srgf', ''))
            }
            data['layers'].append(layer_data)
        
        return data
        
    except Exception as e:
        print(f"Erro ao ler perfil {profile_id}: {e}")
        return None

def _extract_soil_name_from_line(first_line):
    """
    Extrai o nome descritivo do solo da primeira linha do perfil SOIL.SOL.
    
    Formato da primeira linha (larguras fixas DSSAT):
    Posições 0-11:   *CÓDIGO (asterisco + 10 chars)
    Posições 12-23:  SOURCE (12 chars)
    Posições 24-28:  TEXTURE (5 chars)  
    Posições 29-38:  DEPTH (até 10 chars com espaços)
    Posição 39+:     NOME DO SOLO
    
    """
    if not first_line or len(first_line) < 40:
        return ""
    
    # Pula: código(12) + source(12) + texture(5) + depth(~10) = posição 39+
    name = first_line[39:].strip()
    
    # Remove -99 se vier no início
    if name.startswith('-99'):
        name = name[3:].strip()
    
    # Colapsa espaços múltiplos
    name = ' '.join(name.split())
    
    return name

def _get_profile_name_from_dssat(profile_id, soil_file, first_line=""):
    """
    Tenta usar DSSATTools para extrair o nome. Se falhar, usa fallback
    de parsing manual da primeira linha.
    """
    try:
        soil = SoilProfile.from_file(profile_id, soil_file)
        
        # Tenta soil_series_name primeiro
        name = soil.get('soil_series_name', '').strip()
        
        if not name or name in ['-99', 'None', '']:
            name = soil.get('site', '').strip()
        
        if not name or name in ['-99', 'None', '']:
            # parseia manualmente
            if first_line:
                return _extract_soil_name_from_line(first_line)
            return ""
        
        return name
        
    except Exception:
        # Se DSSATTools falhar completamente
        if first_line:
            return _extract_soil_name_from_line(first_line)
        return ""

def show_profiles(soil_file):
    """
    Lista todos os perfis de solo de um arquivo .SOL
    
    Returns:
        list[dict]: Lista com code, label e content para cada perfil
    """
    profiles = []
    
    try:
        with open(soil_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_profile = None
        profile_lines = []
        first_line = ""
        
        for line in lines:
            # Linha começa com * E tem código de 10 chars? > início de perfil
            if line.startswith('*') and len(line) > 11:
                # Extrai o código (posições 1-11)
                potential_code = line[1:11].strip()
                
                # Verifica se é realmente um código de perfil (10 chars alfanuméricos)
                # Ignora linhas como "*SOILS: General..." que são cabeçalhos
                if len(potential_code) == 10 and potential_code.replace('_', '').isalnum():
                    # Salva perfil anterior
                    if current_profile:
                        name = _get_profile_name_from_dssat(current_profile, soil_file, first_line)
                        
                        if name:
                            label = f"{name} ({current_profile})"
                        else:
                            label = current_profile
                        
                        profiles.append({
                            'code': current_profile,
                            'label': label,
                            'content': ''.join(profile_lines)
                        })
                    
                    # Novo perfil
                    current_profile = potential_code
                    first_line = line
                    profile_lines = [line]
                # Se não for código válido ignora
                continue
            
            elif current_profile and line.strip() == '':
                # Fim do perfil
                name = _get_profile_name_from_dssat(current_profile, soil_file, first_line)
                
                if name:
                    label = f"{name} ({current_profile})"
                else:
                    label = current_profile
                
                profiles.append({
                    'code': current_profile,
                    'label': label,
                    'content': ''.join(profile_lines)
                })
                current_profile = None
                profile_lines = []
                first_line = ""
            
            elif current_profile:
                profile_lines.append(line)
        
        # Último perfil
        if current_profile:
            name = _get_profile_name_from_dssat(current_profile, soil_file, first_line)
            
            if name:
                label = f"{name} ({current_profile})"
            else:
                label = current_profile
            
            profiles.append({
                'code': current_profile,
                'label': label,
                'content': ''.join(profile_lines)
            })
        
    except Exception as e:
        print(f"Erro ao ler arquivo {soil_file}: {e}")
        return []
    
    return profiles