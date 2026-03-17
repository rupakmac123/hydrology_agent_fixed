# -*- coding: utf-8 -*-
"""
Created on Tue Mar 17 18:18:00 2026

@author: user
"""

import h5py

hdf_path = r"D:/7879/KDP REPORT/KDP Work/KDP2023/HEC RAS For DoR Comments on Hydr/RevisedHECRAS2023wousbridge/HECRASKDP/Ratu/ratu.p01.hdf"

print(f"Opening: {hdf_path}")
print("=" * 60)

with h5py.File(hdf_path, 'r') as f:
    print("\n=== TOP LEVEL KEYS ===")
    for key in f.keys():
        print(f"  {key}")
    
    print("\n=== FULL STRUCTURE ===")
    def print_structure(name, obj):
        if isinstance(obj, h5py.Group):
            print(f"[GROUP] {name}")
        else:
            print(f"  [DATASET] {name} - Shape: {obj.shape}, Dtype: {obj.dtype}")
    
    f.visititems(print_structure)

print("\n" + "=" * 60)
print("Structure analysis complete!")