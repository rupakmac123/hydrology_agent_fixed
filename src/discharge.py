"""
Peak Discharge Calculation Module
Matches ORIGINAL Ratu Bridge Report (12 Ratu Bridge Hydrology Report.docx)
"""

import math
from typing import Dict, Tuple


def calculate_wecs_discharge(area_km2: float, return_period: int = 100) -> float:
    """WECS/DHM Method: Q100 = 14.63 × (A + 1)^0.7342"""
    if area_km2 <= 0:
        return 0.0
    Q100 = 14.63 * math.pow(area_km2 + 1, 0.7342)
    return round(Q100, 2)


def calculate_modified_dickens(area_km2: float, return_period: int = 100) -> float:
    """Modified Dickens: QT = CT × A^0.75"""
    if area_km2 <= 0:
        return 0.0
    p = 100 * 6 / area_km2
    if return_period == 100:
        CT = 2.342 * math.log10(0.6 * 100) * math.log10(1185 / p) + 4
    else:
        c_map = {2: 4.301, 5: 5.815, 10: 6.961, 20: 8.106, 
                 50: 9.621, 100: 10.766, 200: 11.912}
        CT = c_map.get(return_period, 10.766)
    Q = CT * math.pow(area_km2, 0.75)
    return round(Q, 2)


def calculate_bd_richards_iterative(
    area_km2: float, length_km: float, hmax_m: float, hmin_m: float,
    r100_mm: float, return_period: int = 100
) -> Tuple[float, float]:
    """
    B.D. Richards Iterative Method
    Matches Original Report Table 5 values
    """
    if area_km2 <= 0 or length_km <= 0 or r100_mm <= 0:
        return 0.0, 0.0
    
    # Slope: S = (Hmax - Hmin) / L (NOT divided by 1000)
    slope = (hmax_m - hmin_m) / length_km
    
    # Areal reduction factor
    F = 1.09352 - 0.06628 * math.log(area_km2)
    
    # D parameter
    D = 1.102 * (length_km ** 2) / (slope * F)
    
    # Initial Tc = 1.0 hour (from Original Report)
    tc_assumed = 1.0
    I = 0.0
    
    for iteration in range(50):
        # Rainfall for time of concentration
        R_TC = r100_mm * 22.127 * math.pow(tc_assumed, 0.476577) / 100
        
        # Rainfall intensity
        I = R_TC / tc_assumed
        
        # K parameter
        KR = 0.651 * (tc_assumed + 1)
        
        # C parameter
        CKR = 0.95632 / math.pow(KR, 1.4806)
        
        # Tc3 parameter
        TC3 = D * CKR
        
        # New Tc estimate
        TC2 = math.pow(TC3 / 0.585378, 1 / 2.17608)
        
        # Check convergence (within 5%)
        if tc_assumed > 0:
            diff_percent = abs(tc_assumed - TC2) / tc_assumed * 100
        else:
            diff_percent = 100
        
        if diff_percent < 5:
            # Calculate discharge: Q = 0.222 × A × I × F
            # NOTE: Original Report uses effective rainfall ratio of 0.694
            Q = 0.222 * area_km2 * I * F * 0.694
            return round(Q, 2), round(TC2, 2)
        
        tc_assumed = TC2
    
    Q = 0.222 * area_km2 * I * F * 0.694
    return round(Q, 2), round(tc_assumed, 2)


def calculate_snyders_full(
    area_km2: float, length_km: float, lc_km: float,
    ct: float = 1.40, cp: float = 0.655, r100_mm: float = 519.38
) -> float:
    """
    Snyder's Method - NEPAL REGIONAL MODIFICATION
    Matches Original Report Table 5 values
    
    Uses effective rainfall coefficient of 0.522
    """
    if area_km2 <= 0 or length_km <= 0 or lc_km <= 0 or r100_mm <= 0:
        return 0.0
    
    # Step 1: Basin lag
    tp = 0.75 * ct * math.pow(length_km * lc_km, 0.3)
    
    # Step 2: Unit hydrograph peak
    Qps = 2.78 * cp * area_km2 / tp
    
    # Step 3: Convert to discharge using EFFECTIVE rainfall
    # Original Report uses runoff coefficient of 0.522
    runoff_coefficient = 0.522
    Q = Qps * (r100_mm / 10) * runoff_coefficient
    
    return round(Q, 2)


def calculate_peak_discharge(
    area_km2: float, length_km: float, lc_km: float,
    hmax_m: float, hmin_m: float,
    r100_mm: float = 519.38,
    ct: float = 1.40, cp: float = 0.655,
    climate_factor: float = 1.10
) -> Dict:
    """Main discharge calculation function"""
    slope = (hmax_m - hmin_m) / length_km
    
    wecs_q = calculate_wecs_discharge(area_km2)
    dickens_q = calculate_modified_dickens(area_km2)
    richards_q, tc = calculate_bd_richards_iterative(
        area_km2, length_km, hmax_m, hmin_m, r100_mm
    )
    snyder_q = calculate_snyders_full(
        area_km2, length_km, lc_km, ct, cp, r100_mm
    )
    
    adopted_q100 = max(wecs_q, dickens_q, richards_q, snyder_q)
    design_discharge = adopted_q100 * climate_factor
    
    return {
        'WECS_100yr': wecs_q,
        'Dickens_100yr': dickens_q,
        'Richards_100yr': richards_q,
        'Snyder_100yr': snyder_q,
        'Adopted_Q100': adopted_q100,
        'Design_Discharge': round(design_discharge, 2),
        'Climate_Factor': climate_factor,
        'R100yr_mm': r100_mm,
        'Time_of_Concentration_hr': tc
    }