# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 20:08:12 2026

@author: MSI
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.discharge import DischargeCalculator
import numpy as np

# Ratu data
A = 88.84
L = 26.93
Lc = 14.28
Hmax = 757.52
Hmin = 229.63
R100 = 519.38
Ct = 1.4
Cp = 0.655

print("="*60)
print("SNYDER METHOD DEBUG")
print("="*60)

# Manual calculation
tp = 0.75 * Ct * ((L * Lc) ** 0.3)
print(f"Basin lag (tp): {tp:.4f} hours")

Qps = 2.78 * Cp * A / tp
print(f"Unit hydrograph peak (Qps): {Qps:.4f} m3/s per cm")

# Try different rainfall conversions
print(f"\nRainfall conversions:")
print(f"R100 in mm: {R100}")
print(f"R100 in cm (/10): {R100/10}")
print(f"R100 in cm (/100): {R100/100}")

print(f"\nDischarge calculations:")
print(f"Qps × R100 (mm): {Qps * R100:.2f} m3/s")
print(f"Qps × R100/10: {Qps * (R100/10):.2f} m3/s")
print(f"Qps × R100/100: {Qps * (R100/100):.2f} m3/s")
print(f"\nExpected Q100: 700.86 m3/s")
print("="*60)