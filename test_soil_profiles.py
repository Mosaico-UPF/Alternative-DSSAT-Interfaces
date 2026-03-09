import pytest
from readSoilFile import get_soil_display_data

MANUAL_DATA = {
    'IBSB910015': {
        'color': '',
        'drainage': 'Well',
        'slope': 8,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.92
    },
    'IBCP910015': {
        'color': '',
        'drainage': 'Well',
        'slope': 8,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.94
    },
    'IBSB910009': {
        'color': 'Red',
        'drainage': 'Somewhat Poorly',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.95
    },
    'IBSB910017': {
        'color': 'Brown',
        'drainage': 'Moderately Well',
        'slope': 3,
        'runoff_potential': 'Moderately High',
        'fertility_factor': 0.97
    },
    'IBSB910026': {
        'color': 'Brown',
        'drainage': 'Moderately well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBSB910027': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBSB910055': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 3,
        'runoff_potential': 'Moderately Low',
        'fertility_factor': 0.92
    },
    'IBPN910015': {
        'color': '',
        'drainage': 'Well',
        'slope': 8,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.92
    },
    'IBPN910016': {
        'color': '',
        'drainage': 'Well',
        'slope': 8,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.92
    },
    'IBPN910024': {
        'color': '',
        'drainage': 'Somewhat poorly',
        'slope': 8,
        'runoff_potential': 'Moderately Low',
        'fertility_factor': 0.92
    },
    'IBPN910025': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.92
    },
    'IBPN910026': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBPN910040': {
        'color': '',
        'drainage': 'Well',
        'slope': 8,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.9
    },
    'IBMZ910013': {
        'color': 'Red',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBMZ913514': {
        'color': '',
        'drainage': 'Somewhat excessive',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.8
    },
    'IBMZ910014': {
        'color': '',
        'drainage': 'Somewhat excessive',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.92
    },
    'IBMZ910114': {
        'color': '',
        'drainage': 'Somewhat excessive',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.72
    },
    'IBMZ910023': {
        'color': 'Red',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBMZ910032': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 3,
        'runoff_potential': 'Moderately Low',
        'fertility_factor': 1.0
    },
    'IBWH980018': {
        'color': 'Red',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBWH980019': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBWH980020': {
        'color': 'Red',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBBN910015': {
        'color': '',
        'drainage': 'Well',
        'slope': 8,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.92
    },
    'IBBN910016': {
        'color': '',
        'drainage': 'Well',
        'slope': 8,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.9
    },
    'IBBN910030': {
        'color': 'Black',
        'drainage': 'Moderately Well',
        'slope': 3,
        'runoff_potential': 'Moderately High',
        'fertility_factor': 1.0
    },
    'IBBN910038': {
        'color': 'Brown',
        'drainage': 'Moderately Well',
        'slope': 8,
        'runoff_potential': 'Moderately Low',
        'fertility_factor': 0.8
    },
    'GAPN930001': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 3,
        'runoff_potential': 'Moderately Low',
        'fertility_factor': 1.0
    },
    'IBRI910001': {
        'color': 'Brown',
        'drainage': '',
        'slope': 8,
        'runoff_potential': 'Moderately High',
        'fertility_factor': 1.0
    },
    'IBRI910002': {
        'color': 'Brown',
        'drainage': '',
        'slope': 8,
        'runoff_potential': 'Moderately High',
        'fertility_factor': 1.0
    },
    'IBRI910023': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 8,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBRI910024': {
        'color': 'Brown',
        'drainage': '',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBWM860001': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 12,
        'runoff_potential': 'Moderately High',
        'fertility_factor': 1.0
    },
    'CCPA000030': {
        'color': 'Black',
        'drainage': 'Moderately well',
        'slope': 3,
        'runoff_potential': 'Moderately High',
        'fertility_factor': 1.0
    },
    'CCQU000033': {
        'color': 'Black',
        'drainage': 'Well',
        'slope': 3,
        'runoff_potential': 'Moderately Low',
        'fertility_factor': 1.0
    },
    'IBML910001': {
        'color': 'Red',
        'drainage': 'Excessive',
        'slope': 3,
        'runoff_potential': 'Moderately Low',
        'fertility_factor': 0.7
    },
    'IBML910083': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBSG910010': {
        'color': 'Brown',
        'drainage': 'Moderately well',
        'slope': 8,
        'runoff_potential': 'Moderately Low',
        'fertility_factor': 0.0
    },
    'IBSG910011': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 0.8
    },
    'IBSG910085': {
        'color': 'Brown',
        'drainage': 'Moderately Well',
        'slope': 8,
        'runoff_potential': 'Moderately Low',
        'fertility_factor': 1.0
    },
    'IBSG910086': {
        'color': 'Brown',
        'drainage': 'Somewhat poorly',
        'slope': 8,
        'runoff_potential': 'Moderately High',  
        'fertility_factor': 1.0
    },
    'IBSG910092': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
    'IBSG910093': {
        'color': 'Brown',
        'drainage': 'Moderately Well',
        'slope': 3,
        'runoff_potential': 'Moderately Low',
        'fertility_factor': 1.0
    },
    'IBSG910096': {
        'color': 'Brown',
        'drainage': 'Somewhat poorly',
        'slope': 8,
        'runoff_potential': 'Moderately High',
        'fertility_factor': 1.0
    },
    'IBBA980008': {
        'color': 'Red',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Moderately Low',  
        'fertility_factor': 1.0
    },
    'IBBA980060': {
        'color': 'Brown',
        'drainage': 'Well',
        'slope': 1,
        'runoff_potential': 'Lowest',
        'fertility_factor': 1.0
    },
}

SOIL_FILE = 'SOIL.SOL'


def normalize_text(text):
    """Normaliza texto para comparação (lowercase, sem espaços extras)"""
    if not text:
        return ''
    return str(text).strip().lower()


@pytest.mark.parametrize("profile_id", MANUAL_DATA.keys())
def test_color_matches(profile_id):
    """Verifica se a cor (SCOM) está correta"""
    expected = MANUAL_DATA[profile_id]['color']
    actual_data = get_soil_display_data(profile_id, SOIL_FILE)
    actual = actual_data['color'] if actual_data else ''
    
    assert normalize_text(actual) == normalize_text(expected), \
        f"{profile_id}: Color esperado='{expected}', obtido='{actual}'"


@pytest.mark.parametrize("profile_id", MANUAL_DATA.keys())
def test_drainage_matches(profile_id):
    """Verifica se a classe de drenagem (SLDR) está correta"""
    expected = MANUAL_DATA[profile_id]['drainage']
    actual_data = get_soil_display_data(profile_id, SOIL_FILE)
    actual = actual_data['drainage'] if actual_data else ''
    
    assert normalize_text(actual) == normalize_text(expected), \
        f"{profile_id}: Drainage esperado='{expected}', obtido='{actual}'"


@pytest.mark.parametrize("profile_id", MANUAL_DATA.keys())
def test_slope_matches(profile_id):
    """Verifica se o % Slope calculado está correto"""
    expected = MANUAL_DATA[profile_id]['slope']
    actual_data = get_soil_display_data(profile_id, SOIL_FILE)
    actual = actual_data['slope'] if actual_data else None
    
    assert actual == expected, \
        f"{profile_id}: Slope esperado={expected}, obtido={actual}"


@pytest.mark.parametrize("profile_id", MANUAL_DATA.keys())
def test_runoff_matches(profile_id):
    """Verifica se o Runoff Potential (grupo hidrológico) está correto"""
    expected = MANUAL_DATA[profile_id]['runoff_potential']
    actual_data = get_soil_display_data(profile_id, SOIL_FILE)
    actual = actual_data['runoff_potential'] if actual_data else ''
    
    assert normalize_text(actual) == normalize_text(expected), \
        f"{profile_id}: Runoff esperado='{expected}', obtido='{actual}'"


@pytest.mark.parametrize("profile_id", MANUAL_DATA.keys())
def test_fertility_matches(profile_id):
    """Verifica se o Fertility Factor (SLPF) está correto"""
    expected = MANUAL_DATA[profile_id]['fertility_factor']
    actual_data = get_soil_display_data(profile_id, SOIL_FILE)
    actual = actual_data['fertility_factor'] if actual_data else None
    
    # Compara com tolerância de 0.01 para floats
    if expected is not None and actual is not None:
        assert abs(actual - expected) < 0.01, \
            f"{profile_id}: Fertility esperado={expected}, obtido={actual}"
    else:
        assert actual == expected, \
            f"{profile_id}: Fertility esperado={expected}, obtido={actual}"

# Teste para gerar relatório completo
def test_generate_full_report():
    print("\n" + "="*80)
    print("RELATÓRIO DE VALIDAÇÃO MANUAL")
    print("="*80 + "\n")
    
    errors = []
    successes = 0
    failed_profiles = 0 
    
    for profile_id in MANUAL_DATA.keys():
        expected = MANUAL_DATA[profile_id]
        actual_data = get_soil_display_data(profile_id, SOIL_FILE)
        
        if not actual_data:
            errors.append(f"{profile_id}: ERRO - Não foi possível ler dados")
            failed_profiles += 1  
            continue
        
        profile_errors = []
        
        # Color
        if normalize_text(actual_data['color']) != normalize_text(expected['color']):
            profile_errors.append(
                f"  Color: esperado '{expected['color']}', obtido '{actual_data['color']}'"
            )
        
        # Drainage
        if normalize_text(actual_data['drainage']) != normalize_text(expected['drainage']):
            profile_errors.append(
                f"  Drainage: esperado '{expected['drainage']}', obtido '{actual_data['drainage']}'"
            )
        
        # Slope
        if actual_data['slope'] != expected['slope']:
            profile_errors.append(
                f"  Slope: esperado {expected['slope']}, obtido {actual_data['slope']}"
            )
        
        # Runoff
        if normalize_text(actual_data['runoff_potential']) != normalize_text(expected['runoff_potential']):
            profile_errors.append(
                f"  Runoff: esperado '{expected['runoff_potential']}', obtido '{actual_data['runoff_potential']}'"
            )
        
        # Fertility
        if expected['fertility_factor'] is not None and actual_data['fertility_factor'] is not None:
            if abs(actual_data['fertility_factor'] - expected['fertility_factor']) >= 0.01:
                profile_errors.append(
                    f"  Fertility: esperado {expected['fertility_factor']}, obtido {actual_data['fertility_factor']}"
                )
        elif actual_data['fertility_factor'] != expected['fertility_factor']:
            profile_errors.append(
                f"  Fertility: esperado {expected['fertility_factor']}, obtido {actual_data['fertility_factor']}"
            )
        
        if profile_errors:
            errors.append(f"\n{profile_id}:")
            errors.extend(profile_errors)
            failed_profiles += 1  
        else:
            successes += 1
    
    print(f"✅ Perfis corretos: {successes}/{len(MANUAL_DATA)}")
    
    if errors:
        print(f"\n❌ Perfis com erros: {failed_profiles}/{len(MANUAL_DATA)}")  
        for error in errors:
            print(error)
    else:
        print("\n🎉 TODOS OS PERFIS ESTÃO CORRETOS!")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    # Executar apenas o relatório completo
    test_generate_full_report()
    
    # Executa todos os testes com pytest
    # pytest.main([__file__, "-v"])