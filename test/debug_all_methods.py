# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 20:07:03 2026

@author: MSI
"""

"""
Debug script to show intermediate calculations for Richards and Snyder
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np

# Ratu Bridge Data from Report Table 1 & 5
A = 88.84       # km²
L = 26.93       # km
Lc = 14.28      # km
Hmax = 757.52   # m
Hmin = 229.63   # m
R100 = 519.38   # mm
Ct = 1.4
Cp = 0.655

S = (Hmax - Hmin) / L  # Slope

print("="*70)
print("SNYDER METHOD DEBUG")
print("="*70)

# Step 1: Basin lag
tp = 0.75 * Ct * ((L * Lc) ** 0.3)
print(f"tp = 0.75 × {Ct} × ({L} × {Lc})^0.3")
print(f"tp = 0.75 × {Ct} × {(L * Lc):.2f}^0.3")
print(f"tp = {tp:.4f} hours")
print()

# Step 2: Unit hydrograph peak
Qps = 2.78 * Cp * A / tp
print(f"Qps = 2.78 × {Cp} × {A} / {tp:.4f}")
print(f"Qps = {Qps:.4f} m³/s per cm of rainfall")
print()

# Step 3: Try different rainfall conversions
print("Testing different rainfall conversions:")
print("-"*70)

conversions = [
    ("R in mm (no conversion)", R100),
    ("R in cm (/10)", R100/10),
    ("R in cm (/100)", R100/100),
    ("R × 0.54 runoff coeff", R100 * 0.54 / 10),
    ("R / 19.15 (calculated)", R100 / 19.15),
]

for name, R_val in conversions:
    Q = Qps * R_val
    diff = abs(Q - 700.86) / 700.86 * 100
    status = "✓ CLOSE" if diff < 5 else "✗ FAR"
    print(f"{name:<30} → Q = {Q:>10.2f} m³/s  ({diff:>6.2f}% error) {status}")

print()
print(f"Expected Q100: 700.86 m³/s")
print("="*70)

print("\n" + "="*70)
print("RICHARDS METHOD DEBUG")
print("="*70)

# Initial Tc
Tc = 1.0
print(f"Initial Tc = {Tc} hours")
print()

for iteration in range(10):
    F = 1.09352 - 0.06628 * np.log(A)
    D = 1.102 * (L ** 2) / (S * F)
    R_TC = R100 * 22.127 * (Tc ** 0.476577) / 100
    I = R_TC / Tc
    KR = 0.651 * (Tc + 1)
    CKR = 0.95632 / (KR ** 1.4806)
    TC3 = D * CKR
    TC2 = (TC3 / 0.585378) ** (1 / 2.17608)
    
    Q = 0.222 * A * I * F
    
    print(f"Iteration {iteration+1}:")
    print(f"  F = {F:.6f}")
    print(f"  D = {D:.6f}")
    print(f"  R_TC = {R_TC:.6f} mm")
    print(f"  I = {I:.6f} mm/hr")
    print(f"  KR = {KR:.6f}")
    print(f"  CKR = {CKR:.6f}")
    print(f"  TC2 = {TC2:.6f} hours")
    print(f"  Q = {Q:.2f} m³/s")
    
    diff_percent = abs(Tc - TC2) / Tc * 100
    print(f"  Convergence: {diff_percent:.2f}%")
    
    if diff_percent < 5:
        print(f"  ✓ Converged!")
        break
    
    Tc = TC2
    print()

print()
print(f"Final Q (Richards): {Q:.2f} m³/s")
print(f"Expected Q (Richards): 646.17 m³/s")
print("="*70)