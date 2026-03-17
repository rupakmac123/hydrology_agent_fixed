"""
HEC-RAS HDF5 Structure Diagnostic Script
Checks the structure of your HEC-RAS HDF5 file
"""

import h5py
import sys

# Replace this with your actual HDF5 file path
hdf_path = r"D:/7879/KDP REPORT/KDP Work/KDP2023/HEC RAS For DoR Comments on Hydr/RevisedHECRAS2023wousbridge/HECRASKDP/Ratu/ratu.p01.hdf"

print("=" * 70)
print("HEC-RAS HDF5 STRUCTURE DIAGNOSTIC")
print("=" * 70)
print(f"\nOpening: {hdf_path}\n")

try:
    with h5py.File(hdf_path, 'r') as f:
        print("=== TOP LEVEL KEYS ===")
        for key in f.keys():
            print(f"  ✓ {key}")
        
        print("\n=== FULL STRUCTURE ===")
        
        def print_structure(name, obj):
            if isinstance(obj, h5py.Group):
                print(f"\n[GROUP] {name}")
            else:
                print(f"  [DATASET] {name}")
                print(f"    - Shape: {obj.shape}")
                print(f"    - Dtype: {obj.dtype}")
                if len(obj.shape) == 1 and obj.shape[0] < 20:
                    try:
                        print(f"    - Values: {obj[:]}")
                    except:
                        pass
        
        f.visititems(print_structure)
        
        print("\n" + "=" * 70)
        print("✓ Structure analysis complete!")
        print("=" * 70)
        
        print("\n=== KEY PATHS FOR BRIDGE ANALYSIS ===")
        
        # Check for common paths
        paths_to_check = [
            'Plan',
            'Plan Data',
            'Geometry',
            'Results',
            'Results/Unsteady',
            'Results/Steady',
            'Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Cross Sections',
            'Results/Steady/Output/Output Blocks/Base Output/Cross Sections',
            'Cross Sections',
        ]
        
        for path in paths_to_check:
            if path in f:
                print(f"  ✓ FOUND: {path}")
            else:
                print(f"  ✗ NOT FOUND: {path}")
        
        print("\n" + "=" * 70)
        
except FileNotFoundError:
    print(f"❌ ERROR: File not found: {hdf_path}")
    print("\nPlease update the 'hdf_path' variable in this script with your actual file path")
    print("\nExample:")
    print('  hdf_path = r"C:\\Users\\user\\HEC-RAS\\Ratu_Bridge\\ratu.p01.hdf"')
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\nPress Enter to exit...")
input()