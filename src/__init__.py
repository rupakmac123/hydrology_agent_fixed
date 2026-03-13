"""
Hydrology Agent - Bridge Hydrological Analysis Package
Based on Ratu Bridge Hydrology Report (DoR Nepal)
"""

__version__ = "1.0.0"
__author__ = "Hydrology Agent Team"
__description__ = "Automated bridge hydrology analysis for Nepal roads"

# Import main classes for easier access
from .discharge import DischargeCalculator
from .rainfall import RainfallFrequencyAnalysis
from .reporter import ReportGenerator
# Note: gis.py is optional (requires heavy dependencies)
# from .gis import CatchmentDelineator

# Define what gets imported with "from src import *"
__all__ = [
    'DischargeCalculator',
    'RainfallFrequencyAnalysis', 
    'ReportGenerator',
    # 'CatchmentDelineator',  # Uncomment if using GIS module
]

# Package metadata
METADATA = {
    'name': 'hydrology_agent',
    'version': __version__,
    'description': __description__,
    'methods': [
        'WECS',
        'Modified Dickens',
        'B.D. Richards',
        'Snyder'
    ],
    'distributions': [
        'GEV',
        'Gumbel',
        'Log-Pearson III',
        'Normal',
        'Laplace'
    ],
    'return_periods': [2, 5, 10, 20, 50, 100, 200]
}

def get_package_info():
    """Return package metadata"""
    return METADATA

def validate_installation():
    """Check if all dependencies are installed"""
    try:
        import numpy
        import pandas
        import scipy
        # Optional heavy dependencies
        # import rasterio
        # import geopandas
        # import whitebox
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        return False
