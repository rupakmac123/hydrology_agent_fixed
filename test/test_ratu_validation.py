"""
Validation Test: Verify agent outputs match Ratu Bridge Report Table 5
"""

import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.discharge import DischargeCalculator

# Ratu Bridge validation data from Report Table 1 & Table 5
RATU_VALIDATION_DATA = {
    'catchment': {
        'A_km2': 88.84,
        'L_km': 26.93,
        'Lc_km': 14.28,
        'Hmax_m': 757.52,
        'Hmin_m': 229.63
    },
    'rainfall': {
        'R100yr_mm': 519.38,
        'best_distribution': 'Laplace'
    },
    'discharge': {
        'WECS': 397.63,
        'Dickens': 386.19,
        'Richards': 646.17,
        'Snyder': 700.86,
        'Q100': 700.86,
        'Q_design': 770.95
    }
}

def get_validation_tolerance():
    """Acceptable tolerance for validation tests (5%)"""
    return 0.05

def test_ratu_discharge():
    """Test discharge calculations against Ratu Report values"""
    
    print("\n" + "="*60)
    print("RATU BRIDGE VALIDATION TEST")
    print("="*60)
    
    calc = DischargeCalculator(
        area_km2=RATU_VALIDATION_DATA['catchment']['A_km2'],
        length_km=RATU_VALIDATION_DATA['catchment']['L_km'],
        lc_km=RATU_VALIDATION_DATA['catchment']['Lc_km'],
        hmax_m=RATU_VALIDATION_DATA['catchment']['Hmax_m'],
        hmin_m=RATU_VALIDATION_DATA['catchment']['Hmin_m']
    )
    
    results = calc.calculate_all_methods(
        rainfall_100yr_mm=RATU_VALIDATION_DATA['rainfall']['R100yr_mm'],
        Ct=1.4, Cp=0.655
    )
    
    tolerance = get_validation_tolerance()
    expected = RATU_VALIDATION_DATA['discharge']
    
    print(f"\n{'Method':<20} {'Expected':<15} {'Calculated':<15} {'Status':<15}")
    print("-"*65)
    
    all_passed = True
    
    tests = [
        ('WECS', results['WECS_100yr'], expected['WECS']),
        ('Dickens', results['Dickens_100yr'], expected['Dickens']),
        ('Richards', results['Richards_100yr'], expected['Richards']),
        ('Snyder', results['Snyder_100yr'], expected['Snyder']),
        ('Q100', results['Adopted_Q100'], expected['Q100']),
        ('Q_design', results['Design_Discharge'], expected['Q_design'])
    ]
    
    for name, calc_val, exp_val in tests:
        diff_percent = abs(calc_val - exp_val) / exp_val * 100
        passed = diff_percent <= (tolerance * 100)
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"{name:<20} {exp_val:<15.2f} {calc_val:<15.2f} {status:<15} ({diff_percent:.2f}%)")
    
    print("-"*65)
    if all_passed:
        print("ALL TESTS PASSED - Agent matches Ratu Bridge Report!")
    else:
        print("SOME TESTS FAILED - Review formulas")
    print("="*60 + "\n")
    
    return all_passed

if __name__ == "__main__":
    test_ratu_discharge()