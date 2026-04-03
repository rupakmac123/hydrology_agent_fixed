"""
Peak Discharge Calculation Module
Implements multiple empirical methods for flood estimation
Based on Department of Roads (DoR) Nepal Guidelines
Matches Charnath Bridge Excel calculations and Reports 37-44
"""

import math
import numpy as np
from typing import Dict, Tuple


def calculate_wecs_discharge(area_km2: float, return_period: int = 100) -> float:
    """Calculate peak discharge using WECS/DHM method (Nepal Standard)"""
    if area_km2 <= 0:
        return 0.0
    
    Q100 = 14.63 * math.pow(area_km2 + 1, 0.7342)
    return round(Q100, 2)


def calculate_modified_dickens(area_km2: float, return_period: int = 100) -> float:
    """Calculate peak discharge using Modified Dickens formula"""
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
    """Calculate peak discharge using B.D. Richards method (ITERATIVE)"""
    if area_km2 <= 0 or length_km <= 0 or r100_mm <= 0:
        return 0.0, 0.0
    
    # CRITICAL: Slope per 100m
    slope_per_100m = (hmax_m - hmin_m) / (length_km * 1000) * 100
    F = 1.09352 - 0.06628 * math.log(area_km2)
    D = 1.102 * (length_km ** 2) / (slope_per_100m * F)
    tc_assumed = 5.893
    
    I = 0.0
    for iteration in range(50):
        R_TC = r100_mm * 22.127 * math.pow(tc_assumed, 0.476577) / 100
        I = R_TC / tc_assumed
        KR = 0.651 * (tc_assumed + 1)
        CKR = 0.95632 / math.pow(KR, 1.4806)
        TC3 = D * CKR
        TC2 = math.pow(TC3 / 0.585378, 1 / 2.17608)
        
        if tc_assumed > 0:
            diff_percent = abs(tc_assumed - TC2) / tc_assumed * 100
        else:
            diff_percent = 100
        
        if diff_percent < 5:
            Q = 0.222 * area_km2 * I * F  # NO 0.694 factor!
            return round(Q, 2), round(TC2, 2)
        
        tc_assumed = TC2
    
    Q = 0.222 * area_km2 * I * F
    return round(Q, 2), round(tc_assumed, 2)


def calculate_snyders_full(
    area_km2: float, length_km: float, lc_km: float,
    ct: float = 1.40, cp: float = 0.655, r100_mm: float = 246.38
) -> float:
    """Calculate peak discharge using Snyder's method (WITH DURATION CORRECTION)"""
    if area_km2 <= 0 or length_km <= 0 or lc_km <= 0 or r100_mm <= 0:
        return 0.0
    
    tp = 0.75 * ct * math.pow(length_km * lc_km, 0.3)
    tr = tp / 5.5
    tR = 24.0
    tpR = tp + 0.25 * (tR - tr)
    Qps = 2.78 * cp * area_km2 / tpR
    Q = Qps * (r100_mm / 10)
    
    return round(Q, 2)


def calculate_rational_method(
    area_km2: float,
    length_km: float,
    slope: float,
    runoff_coefficient: float = 0.30,
    idf_data: dict = None,
    return_period: int = 100
) -> Tuple[float, float, float]:
    """
    Calculate peak discharge using Rational Method
    Formula: Q = 0.278 × C × I × A
    Uses IDF curve interpolation for rainfall intensity.
    """
    import math

    if area_km2 <= 0 or length_km <= 0 or slope <= 0:
        return 0.0, 0.0, 0.0

    # Step 1: Time of Concentration (Kirpich)
    L_m = length_km * 1000
    Tc_minutes = 0.0195 * (L_m) ** 0.77 * (slope) ** -0.385
    Tc_hours = Tc_minutes / 60

    # Step 2: Get rainfall intensity from IDF curve
    I = 0.0
    idf_used = False

    if idf_data and isinstance(idf_data, dict) and len(idf_data) > 0:
        try:
            # Check if return period exists
            if return_period in idf_data:
                idf_rp_data = idf_data[return_period]

                if isinstance(idf_rp_data, dict) and len(idf_rp_data) > 0:
                    # Sort durations
                    durations = sorted([float(k) for k in idf_rp_data.keys()])
                    intensities = [idf_rp_data[d] for d in durations]

                    print(f"DEBUG: Tc={Tc_hours:.2f}hr, Durations={durations}")

                    # Boundary cases
                    if Tc_hours <= durations[0]:
                        I = intensities[0]
                        idf_used = True
                        print(f"DEBUG: Using min duration I={I:.2f}")
                    elif Tc_hours >= durations[-1]:
                        I = intensities[-1]
                        idf_used = True
                        print(f"DEBUG: Using max duration I={I:.2f}")
                    else:
                        # Log-log interpolation
                        log_dur = [math.log(d) for d in durations]
                        log_int = [math.log(i) for i in intensities]
                        log_tc = math.log(Tc_hours)

                        for i in range(len(durations) - 1):
                            if durations[i] <= Tc_hours <= durations[i+1]:
                                frac = (log_tc - log_dur[i]) / (log_dur[i+1] - log_dur[i])
                                log_I = log_int[i] + frac * (log_int[i+1] - log_int[i])
                                I = math.exp(log_I)
                                idf_used = True
                                print(f"DEBUG: Interpolated I={I:.2f} between {durations[i]}hr and {durations[i+1]}hr")
                                break
        except Exception as e:
            print(f"IDF interpolation error: {e}")

    # Fallback if IDF failed
    if I == 0.0:
        print(f"⚠️ WARNING: Using fallback IDF equation (Tc={Tc_hours:.2f}hr)")
        I = 50.0 / (Tc_hours + 0.5) ** 0.7

    # Step 3: Calculate discharge
    Q = 0.278 * runoff_coefficient * I * area_km2

    print(f"\n=== RATIONAL METHOD ===")
    print(f"Tc = {Tc_hours:.2f} hours")
    print(f"I = {I:.2f} mm/hr {'✅ (IDF)' if idf_used else '❌ (Fallback)'}")
    print(f"C = {runoff_coefficient}, A = {area_km2} km²")
    print(f"Q = 0.278 × {runoff_coefficient} × {I:.2f} × {area_km2} = {Q:.2f} m³/s")
    print(f"========================\n")

    return round(Q, 2), round(Tc_hours, 2), round(I, 2)


def calculate_peak_discharge(
    area_km2: float, length_km: float, lc_km: float,
    hmax_m: float, hmin_m: float, r100_mm: float = 246.38,
    ct: float = 1.40, cp: float = 0.655, climate_factor: float = 1.10,
    runoff_coefficient: float = 0.30, idf_data: dict = None
) -> Dict:
    """Calculate peak discharge using multiple methods"""
    slope = (hmax_m - hmin_m) / (length_km * 1000)
    
    wecs_q = calculate_wecs_discharge(area_km2)
    dickens_q = calculate_modified_dickens(area_km2)
    richards_q, tc_richards = calculate_bd_richards_iterative(
        area_km2, length_km, hmax_m, hmin_m, r100_mm
    )
    snyder_q = calculate_snyders_full(
        area_km2, length_km, lc_km, ct, cp, r100_mm
    )
    
    rational_q, tc_rational, intensity = calculate_rational_method(
        area_km2, length_km, slope, runoff_coefficient, idf_data
    )
    
    adopted_q100 = max(wecs_q, dickens_q, richards_q, snyder_q)
    design_discharge = adopted_q100 * climate_factor
    
    return {
        'WECS_100yr': wecs_q,
        'Dickens_100yr': dickens_q,
        'Richards_100yr': richards_q,
        'Snyder_100yr': snyder_q,
        'Rational_100yr': rational_q,
        'Adopted_Q100': adopted_q100,
        'Design_Discharge': round(design_discharge, 2),
        'Climate_Factor': climate_factor,
        'R100yr_mm': r100_mm,
        'Time_of_Concentration_hr': tc_rational,
        'Runoff_Coefficient': runoff_coefficient,
        'Rainfall_Intensity_mm_hr': intensity
    }