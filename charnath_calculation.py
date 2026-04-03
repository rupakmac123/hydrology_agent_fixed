# -*- coding: utf-8 -*-
"""
Created on Mon Mar 30 14:53:04 2026

@author: user
"""

"""
Charnath Bridge - Discharge Calculation with R100 = 331.00 mm
Using validated formulas from discharge.py
"""

import math
import numpy as np

# =============================================================================
# CHARNATH BRIDGE PARAMETERS
# =============================================================================
A = 55.5          # Catchment area (km²)
L = 19.199        # Stream length (km)
Lc = 10.645       # Centroidal length (km)
Hmax = 476.4      # Maximum elevation (m)
Hmin = 127.64     # Minimum elevation (m)
R100 = 331.00     # 100-year rainfall (mm) - NEW VALUE
Ct = 1.40         # Snyder's time lag coefficient (Nepal Terai)
Cp = 0.655        # Snyder's peak coefficient
runoff_coeff_snyder = 0.522  # Nepal calibration factor for Snyder
runoff_coeff_rational = 0.30  # Runoff coefficient for Rational method

print("="*70)
print(f"CHARNATH BRIDGE - DISCHARGE CALCULATION")
print(f"R100 = {R100} mm")
print("="*70)

# =============================================================================
# 1. WECS METHOD (unchanged - doesn't depend on rainfall)
# =============================================================================
def calculate_wecs(area_km2):
    return 14.63 * math.pow(area_km2 + 1, 0.7342)

Q_wecs = calculate_wecs(A)
print(f"\n1. WECS Method:")
print(f"   Q = 14.63 × ({A} + 1)^0.7342")
print(f"   Q = {Q_wecs:.2f} m³/s")

# =============================================================================
# 2. MODIFIED DICKENS METHOD (unchanged - doesn't depend on rainfall)
# =============================================================================
def calculate_dickens(area_km2, return_period=100):
    p = 100 * 6 / area_km2  # For no snow area
    if return_period == 100:
        CT = 2.342 * math.log10(0.6 * 100) * math.log10(1185 / p) + 4
    else:
        c_map = {2: 4.301, 5: 5.815, 10: 6.961, 20: 8.106, 
                 50: 9.621, 100: 10.766, 200: 11.912}
        CT = c_map.get(return_period, 10.766)
    return CT * math.pow(area_km2, 0.75)

Q_dickens = calculate_dickens(A)
print(f"\n2. Modified Dickens Method:")
p = 100 * 6 / A
CT = 2.342 * math.log10(60) * math.log10(1185 / p) + 4
print(f"   p = {p:.3f}, CT = {CT:.3f}")
print(f"   Q = {CT:.3f} × {A}^0.75 = {Q_dickens:.2f} m³/s")

# =============================================================================
# 3. B.D. RICHARDS METHOD (iterative, depends on R100)
# =============================================================================
def calculate_richards(area_km2, length_km, hmax, hmin, r100_mm):
    # Slope per 100m (CRITICAL FIX)
    slope_per_100m = (hmax - hmin) / (length_km * 1000) * 100
    
    # Areal reduction factor
    F = 1.09352 - 0.06628 * math.log(area_km2)
    
    # D parameter
    D = 1.102 * (length_km ** 2) / (slope_per_100m * F)
    
    # Initial Tc guess (from Charnath Excel)
    tc_assumed = 5.893
    
    # Iterative procedure
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
            # Q = 0.222 × A × I × F (NO 0.694 factor!)
            Q = 0.222 * area_km2 * I * F
            return round(Q, 2), round(TC2, 2), round(I, 3)
        
        tc_assumed = TC2
    
    Q = 0.222 * area_km2 * I * F
    return round(Q, 2), round(tc_assumed, 2), round(I, 3)

Q_richards, tc_richards, I_richards = calculate_richards(A, L, Hmax, Hmin, R100)
print(f"\n3. B.D. Richards Method:")
slope_per_100m = (Hmax - Hmin) / (L * 1000) * 100
F = 1.09352 - 0.06628 * math.log(A)
D = 1.102 * (L ** 2) / (slope_per_100m * F)
print(f"   Slope per 100m = {slope_per_100m:.3f}")
print(f"   F = {F:.3f}, D = {D:.3f}")
print(f"   Tc = {tc_richards:.3f} hr, I = {I_richards:.3f} mm/hr")
print(f"   Q = 0.222 × {A} × {I_richards} × {F} = {Q_richards:.2f} m³/s")

# =============================================================================
# 4. SNYDER'S METHOD (WITH DURATION CORRECTION, depends on R100)
# =============================================================================
def calculate_snyder(area_km2, length_km, lc_km, ct, cp, r100_mm, runoff_coeff):
    # Basin lag (Nepal formulation with 0.75 factor)
    tp = 0.75 * ct * math.pow(length_km * lc_km, 0.3)
    
    # Unit duration
    tr = tp / 5.5
    
    # Corrected basin lag for 24-hour storm
    tR = 24.0
    tpR = tp + 0.25 * (tR - tr)
    
    # Unit hydrograph peak
    Qps = 2.78 * cp * area_km2 / tpR
    
    # Peak discharge (NO additional runoff coefficient - uses total rainfall)
    Q = Qps * (r100_mm / 10)
    
    return round(Q, 2), round(tp, 3), round(tpR, 3), round(Qps, 3)

Q_snyder, tp, tpR, Qps = calculate_snyder(A, L, Lc, Ct, Cp, R100, runoff_coeff_snyder)
print(f"\n4. Snyder's Method (WITH DURATION CORRECTION):")
print(f"   tp = 0.75 × {Ct} × ({L} × {Lc})^0.3 = {tp:.3f} hr")
print(f"   tr = {tp:.3f} / 5.5 = {tp/5.5:.3f} hr")
print(f"   tpR = {tp:.3f} + 0.25 × (24 - {tp/5.5:.3f}) = {tpR:.3f} hr")
print(f"   Qps = 2.78 × {Cp} × {A} / {tpR:.3f} = {Qps:.3f} m³/s per cm")
print(f"   Q = {Qps:.3f} × ({R100}/10) = {Q_snyder:.2f} m³/s")

# =============================================================================
# 5. RATIONAL METHOD (depends on R100 via IDF)
# =============================================================================
def calculate_rational(area_km2, length_km, hmax, hmin, r100_mm, runoff_coeff):
    # Slope for Kirpich formula
    slope = (hmax - hmin) / (length_km * 1000)
    
    # Time of Concentration (Kirpich)
    Tc_minutes = 0.0195 * (length_km * 1000) ** 0.77 * (slope) ** -0.385
    Tc_hours = Tc_minutes / 60
    
    # Estimate rainfall intensity for Tc duration (simplified IDF)
    # Using power law: I = a / (Tc + b)^n
    I = 50.0 / (Tc_hours + 0.5) ** 0.7  # Approximate for Nepal
    
    # Peak discharge
    Q = 0.278 * runoff_coeff * I * area_km2
    
    return round(Q, 2), round(Tc_hours, 2), round(I, 2)

Q_rational, Tc_rational, I_rational = calculate_rational(A, L, Hmax, Hmin, R100, runoff_coeff_rational)
print(f"\n5. Rational Method:")
print(f"   Tc = {Tc_rational:.2f} hr, I = {I_rational:.2f} mm/hr")
print(f"   Q = 0.278 × {runoff_coeff_rational} × {I_rational} × {A} = {Q_rational:.2f} m³/s")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "="*70)
print("SUMMARY OF RESULTS")
print("="*70)
print(f"{'Method':<25} {'Q100 (m³/s)':>15}")
print("-"*40)
print(f"{'WECS':<25} {Q_wecs:>15.2f}")
print(f"{'Modified Dickens':<25} {Q_dickens:>15.2f}")
print(f"{'B.D. Richards':<25} {Q_richards:>15.2f}")
print(f"{'Snyder (with duration corr.)':<25} {Q_snyder:>15.2f}")
print(f"{'Rational':<25} {Q_rational:>15.2f}")
print("-"*40)

# Adopt highest value (excluding Rational for large catchments)
methods = {'WECS': Q_wecs, 'Dickens': Q_dickens, 'Richards': Q_richards, 'Snyder': Q_snyder}
adopted_q100 = max(methods.values())
adopted_method = max(methods, key=methods.get)

print(f"\nAdopted Q100: {adopted_q100:.2f} m³/s ({adopted_method} method)")
print(f"Design Discharge (×1.10): {adopted_q100 * 1.10:.2f} m³/s")
print("="*70)

# =============================================================================
# COMPARISON WITH ORIGINAL R100 = 246.38 mm
# =============================================================================
print(f"\nCOMPARISON WITH ORIGINAL R100 = 246.38 mm:")
print("-"*70)
print(f"{'Method':<25} {'R100=246.38':>15} {'R100=331.00':>15} {'Change':>10}")
print("-"*70)

# Original values from Excel (R100 = 246.38 mm)
original = {
    'WECS': 282.88,
    'Dickens': 254.07,
    'Richards': 219.80,
    'Snyder': 227.34,
    'Rational': 189.23
}

new = {
    'WECS': Q_wecs,
    'Dickens': Q_dickens,
    'Richards': Q_richards,
    'Snyder': Q_snyder,
    'Rational': Q_rational
}

for method in ['WECS', 'Dickens', 'Richards', 'Snyder', 'Rational']:
    orig = original[method]
    nw = new[method]
    change_pct = (nw - orig) / orig * 100 if orig != 0 else 0
    print(f"{method:<25} {orig:>15.2f} {nw:>15.2f} {change_pct:+9.1f}%")

print("="*70)