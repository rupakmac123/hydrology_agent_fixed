# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 20:12:07 2026

@author: MSI
"""

"""
Configuration files for Hydrology Agent
"""

import json
import os
from pathlib import Path

# Get the config directory path
CONFIG_DIR = Path(__file__).parent

def load_regional_params():
    """Load regional parameters (Ct, Cp values)"""
    config_path = CONFIG_DIR / 'regional_params.json'
    with open(config_path, 'r') as f:
        return json.load(f)

def load_dhm_stations():
    """Load DHM rainfall station coordinates"""
    config_path = CONFIG_DIR / 'dhm_stations.json'
    with open(config_path, 'r') as f:
        return json.load(f)

def get_regional_coefficients(latitude, longitude):
    """
    Get Ct and Cp based on location (from Report Figures 2 & 3)
    
    For Ratu Bridge (Terai region):
    Ct = 1.4, Cp = 0.655
    """
    params = load_regional_params()
    
    # Simple region detection based on latitude
    if latitude < 27.0:  # Terai region
        return params['terai']
    elif latitude < 29.0:  # Mid-Hills
        return params['mid_hills']
    else:  # Himalayan
        return params['himalayan']

# Default values from Ratu Report (Table 5)
DEFAULT_CT = 1.4
DEFAULT_CP = 0.655
CLIMATE_CHANGE_FACTOR = 1.10