# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 11:15:37 2026

@author: user
"""

# -*- coding: utf-8 -*-
"""
Test discharge calculations in Spyder
"""

import os
import sys

# Set working directory
os.chdir(r'C:\Users\user\hydrology_agent\hydrology_agent_fixed')
sys.path.insert(0, r'C:\Users\user\hydrology_agent\hydrology_agent_fixed')

# Clear cache
for module in list(sys.modules.keys()):
    if 'src' in module:
        del sys.modules[module]

# Import and test
from src.discharge import calculate_peak_discharge

print("="*70)
print("DISCHARGE CALCULATION TEST")
print("="*70)
print(f"Working Directory: {os.getcwd()}")
print(f"discharge.py location: {sys.modules['src.discharge'].__file__}")
print("="*70)

# Test with Ratu Bridge data
result = calculate_peak_discharge(
    area_km2=88.84,
    length_km=26.93,
    lc_km=14.28,
    hmax_m=757.52,
    hmin_m=229.63,
    r100_mm=519.38,
    ct=1.40,
    cp=0.655,
    climate_factor=1.10
)

print("\nResults:")
for key, value in result.items():
    print(f"  {key}: {value}")

print("="*70)
print("EXPECTED VALUES (from Original Report):")
print("  WECS_100yr: 397.63")
print("  Dickens_100yr: 386.19")
print("  Richards_100yr: 646.17")
print("  Snyder_100yr: 700.86")
print("  Adopted_Q100: 700.86")
print("  Design_Discharge: 770.95")
print("="*70)