"""
Catchment Parameter Calculation Module
Based on Department of Roads (DoR) Nepal Guidelines
"""

from typing import Dict


def calculate_catchment_parameters(
    area_km2: float,
    length_km: float,
    centroidal_length_km: float,
    hmax_m: float,
    hmin_m: float
) -> Dict:
    """
    Calculate catchment parameters
    
    Args:
        area_km2: Catchment area in km²
        length_km: Stream length in km
        centroidal_length_km: Centroidal length in km
        hmax_m: Maximum elevation in m
        hmin_m: Minimum elevation in m
    
    Returns:
        Dictionary with calculated parameters
    """
    # Calculate slope (for report display: NOT divided by 1000)
    slope = (hmax_m - hmin_m) / length_km
    
    # Calculate elevation difference
    elevation_diff = hmax_m - hmin_m
    
    return {
        'A_km2': area_km2,
        'L_km': length_km,
        'Lc_km': centroidal_length_km,
        'Hmax_m': hmax_m,
        'Hmin_m': hmin_m,
        'Elevation_Diff': elevation_diff,
        'Slope': slope
    }