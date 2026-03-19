# -*- coding: utf-8 -*-
"""
Created on Thu Mar 19 10:55:25 2026

@author: user
"""

"""
Test IDF Curve Generation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.rainfall import RainfallFrequencyAnalysis
import pandas as pd

# Create test data
test_data = pd.DataFrame({
    'Year': list(range(1985, 2021)),
    'Max_24hr_Rainfall': [
        152.4, 112.8, 233.8, 182.3, 118.2, 123.5, 164.2, 69.4, 145.3, 114.3,
        252.3, 127.4, 128.3, 146.3, 96.5, 125.3, 93.2, 92.2, 104.5, 275.5,
        153.4, 124.3, 131.2, 108.3, 107.4, 84.4, 168.3, 94.4, 78.4, 126.4,
        135.3, 126.5, 410.3, 117.2, 436.1, 144.2
    ]
})

# Save to temp file
test_path = Path('data/rainfall/test_idf.csv')
test_path.parent.mkdir(parents=True, exist_ok=True)
test_data.to_csv(test_path, index=False)

print(f"Test data saved to: {test_path}")

# Run analysis
print("\nRunning rainfall analysis...")
analysis = RainfallFrequencyAnalysis(str(test_path))
results = analysis.full_analysis()

print(f"\nBest Distribution: {results['best_distribution']}")
print(f"R100yr: {results['R100yr']} mm")
print(f"IDF Plot Path: {results.get('idf_plot_path')}")
print(f"IDF Table Exists: {bool(results.get('idf_table'))}")
print(f"IDF Data Exists: {bool(results.get('idf_data'))}")

# Check if file was created
if results.get('idf_plot_path'):
    import os
    if os.path.exists(results['idf_plot_path']):
        print(f"\n✅ IDF plot created successfully: {results['idf_plot_path']}")
    else:
        print(f"\n❌ IDF plot file not found: {results['idf_plot_path']}")
else:
    print("\n❌ IDF plot path is None")

print("\nTest complete!")