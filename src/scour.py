# -*- coding: utf-8 -*-
"""
Created on Fri Mar 13 21:39:41 2026

@author: user
"""

"""
Scour Calculation Module
Based on Ratu Bridge Hydrology Report (Tables 7, 8, 9)
"""

import numpy as np
from typing import Dict, Tuple

class ScourCalculator:
    """
    Calculates scour depth for bridge foundations
    Following DoR Nepal guidelines
    """
    
    def __init__(self, Q_design: float, L_bridge: float, 
                 dmean_mm: float = 2.8, Ksf: float = 2.9,
                 Blench_Fb: float = 0.8):
        """
        Initialize scour calculator
        
        Args:
            Q_design: Design discharge (m³/s) - Q100 × 1.1
            L_bridge: Length of bridge (m)
            dmean_mm: Mean diameter of bed material (mm)
            Ksf: Silt factor (= 1.76 * sqrt(dmean_mm))
            Blench_Fb: Blench's Zero Bed Factor
        """
        self.Q_design = Q_design
        self.Q_scour = Q_design * (1.3 / 1.1)  # Q100 × 1.3 for scour
        self.L_bridge = L_bridge
        self.dmean_mm = dmean_mm
        self.Ksf = Ksf
        self.Blench_Fb = Blench_Fb
        
    def calculate_mean_scour_lacey(self, q: float) -> float:
        """
        Calculate mean scour depth using Lacey's formula
        D = (0.473 * Q^(1/3)) / (Ksf^(1/3))
        
        Args:
            q: Discharge per unit width (m²/s)
            
        Returns:
            Mean scour depth (m)
        """
        D = (0.473 * (q ** (1/3))) / (self.Ksf ** (1/3))
        return round(D, 2)
    
    def calculate_blench_scour(self, qm: float) -> float:
        """
        Calculate scour using Blench Zero Bed Factor approach
        D = (qm² / Fb)^0.33
        
        Args:
            qm: Discharge per unit width (m³/s/m)
            
        Returns:
            Mean scour depth (m)
        """
        D = ((qm ** 2) / self.Blench_Fb) ** 0.33
        return round(D, 2)
    
    def calculate_scour_for_section(self, q_avg: float, q_max: float) -> Dict:
        """
        Calculate scour for a cross-section
        
        Args:
            q_avg: Average discharge intensity (m²/s)
            q_max: Maximum discharge intensity (m²/s)
            
        Returns:
            Dictionary with all scour calculations
        """
        # Method 1: Lacey's formula with average q
        D_lacey_avg = self.calculate_mean_scour_lacey(q_avg)
        
        # Method 2: Lacey's formula with maximum q
        D_lacey_max = self.calculate_mean_scour_lacey(q_max)
        
        # Method 3: Blench approach
        D_blench = self.calculate_blench_scour(q_avg)
        
        # Adopt highest value
        D_adopted = max(D_lacey_avg, D_lacey_max, D_blench)
        
        return {
            'D_lacey_avg': D_lacey_avg,
            'D_lacey_max': D_lacey_max,
            'D_blench': D_blench,
            'D_adopted': D_adopted
        }
    
    def calculate_pier_abutment_scour(self, D_mean: float) -> Dict:
        """
        Calculate maximum scour depth for piers and abutments
        
        Args:
            D_mean: Mean scour depth (m)
            
        Returns:
            Dictionary with pier and abutment scour depths
        """
        # For piers: 2.0 × D
        D_pier = 2.0 * D_mean
        
        # For abutments: 1.27 × D
        D_abutment = 1.27 * D_mean
        
        return {
            'D_pier': round(D_pier, 2),
            'D_abutment': round(D_abutment, 2)
        }
    
    def calculate_scour_levels(self, HFL: float, D_mean: float, 
                                D_pier: float, D_abutment: float) -> Dict:
        """
        Calculate scour levels for foundation design
        
        Args:
            HFL: Highest Flood Level (m)
            D_mean: Mean scour depth (m)
            D_pier: Pier scour depth (m)
            D_abutment: Abutment scour depth (m)
            
        Returns:
            Dictionary with scour levels
        """
        # Scour level = HFL - scour depth
        scour_level_abutment = HFL - D_abutment
        scour_level_pier = HFL - D_pier
        
        return {
            'scour_level_abutment': round(scour_level_abutment, 2),
            'scour_level_pier': round(scour_level_pier, 2)
        }
    
    def full_scour_analysis(self, HFL: float, q_avg: float, 
                           q_max: float) -> Dict:
        """
        Complete scour analysis for a bridge section
        
        Args:
            HFL: Highest Flood Level (m)
            q_avg: Average discharge intensity (m²/s)
            q_max: Maximum discharge intensity (m²/s)
            
        Returns:
            Complete scour analysis results
        """
        # Calculate mean scour
        scour_results = self.calculate_scour_for_section(q_avg, q_max)
        D_adopted = scour_results['D_adopted']
        
        # Calculate pier and abutment scour
        pier_abutment = self.calculate_pier_abutment_scour(D_adopted)
        
        # Calculate scour levels
        levels = self.calculate_scour_levels(
            HFL, D_adopted, 
            pier_abutment['D_pier'], 
            pier_abutment['D_abutment']
        )
        
        # Minimum soffit level (HFL + freeboard, typically 1.5m)
        min_soffit = HFL + 1.5
        
        return {
            'mean_scour': scour_results,
            'pier_abutment_scour': pier_abutment,
            'scour_levels': levels,
            'min_soffit_level': round(min_soffit, 2),
            'HFL': HFL,
            'q_avg': q_avg,
            'q_max': q_max
        }