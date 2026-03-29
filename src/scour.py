"""
Scour Depth Calculation Module
Implements Lacey's, Blench's, and other scour estimation methods
Per IRC:78-2014 and Nepal DoR Guidelines
"""

import numpy as np
from typing import Dict, Optional


class ScourCalculator:
    """
    Calculate scour depths for bridge foundations
    """
    
    def __init__(self, Q_design: float, L_bridge: float, 
                 dmean_mm: float = 2.8, Ksf: float = 2.9, 
                 Blench_Fb: float = 0.8):
        """
        Initialize scour calculator
        
        Args:
            Q_design: Design discharge for scour analysis (m³/s)
            L_bridge: Bridge length (m)
            dmean_mm: Mean bed material size (mm)
            Ksf: Silt factor
            Blench_Fb: Blench's zero bed factor
        """
        self.Q_design = Q_design
        self.L_bridge = L_bridge
        self.dmean_mm = dmean_mm
        self.Ksf = Ksf
        self.Blench_Fb = Blench_Fb
        self.freeboard = 1.5  # Default freeboard (m)
    
    def calculate_lacey_scour_avg_q(self, q_avg: float) -> float:
        """
        Calculate Lacey's scour depth using average discharge intensity
        
        Formula: D = 0.473 × (q² / Ksf)^(1/3)
        
        Args:
            q_avg: Average discharge intensity (m²/s)
        
        Returns:
            Scour depth (m)
        """
        if q_avg <= 0 or self.Ksf <= 0:
            return 0.0
        
        D = 0.473 * ((q_avg ** 2) / self.Ksf) ** (1/3)
        return round(D, 2)
    
    def calculate_lacey_scour_max_q(self, q_max: float) -> float:
        """
        Calculate Lacey's scour depth using maximum discharge intensity
        
        Formula: D = 0.473 × (q² / Ksf)^(1/3)
        
        Args:
            q_max: Maximum discharge intensity (m²/s)
        
        Returns:
            Scour depth (m)
        """
        if q_max <= 0 or self.Ksf <= 0:
            return 0.0
        
        D = 0.473 * ((q_max ** 2) / self.Ksf) ** (1/3)
        return round(D, 2)
    
    def calculate_blench_scour(self, q_avg: float) -> float:
        """
        Calculate Blench's scour depth
        
        Formula: D = (q² / Fb)^(1/3)
        
        Args:
            q_avg: Average discharge intensity (m²/s)
        
        Returns:
            Scour depth (m)
        """
        if q_avg <= 0 or self.Blench_Fb <= 0:
            return 0.0
        
        D = ((q_avg ** 2) / self.Blench_Fb) ** (1/3)
        return round(D, 2)
    
    def calculate_mean_scour(self, q_avg: float, q_max: float) -> Dict:
        """
        Calculate mean scour depth using multiple methods
        
        Args:
            q_avg: Average discharge intensity (m²/s)
            q_max: Maximum discharge intensity (m²/s)
        
        Returns:
            Dictionary with scour depths from all methods
        """
        D_lacey_avg = self.calculate_lacey_scour_avg_q(q_avg)
        D_lacey_max = self.calculate_lacey_scour_max_q(q_max)
        D_blench = self.calculate_blench_scour(q_avg)
        
        # Adopt highest of all methods
        D_adopted = max(D_lacey_avg, D_lacey_max, D_blench)
        
        return {
            'D_lacey_avg': D_lacey_avg,
            'D_lacey_max': D_lacey_max,
            'D_blench': D_blench,
            'D_adopted': D_adopted
        }
    
    def calculate_pier_abutment_scour(self, D_adopted: float) -> Dict:
        """
        Calculate pier and abutment scour depths
        
        Per IRC:78-2014:
        - Piers: 2.0 × D
        - Abutments: 1.27 × D
        
        Args:
            D_adopted: Adopted mean scour depth (m)
        
        Returns:
            Dictionary with pier and abutment scour depths
        """
        D_abutment = 1.27 * D_adopted
        D_pier = 2.00 * D_adopted
        
        return {
            'D_abutment': round(D_abutment, 2),
            'D_pier': round(D_pier, 2)
        }
    
    def calculate_scour_levels(self, wse_scour: float, 
                               pier_abutment_scour: Dict) -> Dict:
        """
        Calculate scour levels below water surface
        
        Args:
            wse_scour: Water Surface Elevation at scour discharge (m)
            pier_abutment_scour: Dictionary with pier and abutment scour depths
        
        Returns:
            Dictionary with scour levels
        """
        scour_level_abutment = wse_scour - pier_abutment_scour['D_abutment']
        scour_level_pier = wse_scour - pier_abutment_scour['D_pier']
        
        return {
            'scour_level_abutment': round(scour_level_abutment, 2),
            'scour_level_pier': round(scour_level_pier, 2)
        }
    
    def calculate_minimum_soffit_level(self, wse_scour: float) -> float:
        """
        Calculate minimum soffit level
        
        Formula: Soffit Level = WSE + Freeboard
        
        Args:
            wse_scour: Water Surface Elevation at scour discharge (m)
        
        Returns:
            Minimum soffit level (m)
        """
        return round(wse_scour + self.freeboard, 2)
    
    def full_scour_analysis(self, wse_scour: float, q_avg: float, q_max: float) -> Dict:
        """
        Complete scour analysis workflow per IRC:78-2014
        
        Args:
            wse_scour: Water Surface Elevation at scour discharge (Q×1.30), NOT HFL
            q_avg: Average discharge intensity (m²/s)
            q_max: Maximum discharge intensity (m²/s)
        
        Returns:
            Dictionary with all scour calculations and levels
        """
        try:
            # Calculate mean scour depth
            mean_scour = self.calculate_mean_scour(q_avg, q_max)
            
            # Calculate pier and abutment scour depths
            pier_abutment_scour = self.calculate_pier_abutment_scour(
                mean_scour['D_adopted']
            )
            
            # Calculate scour levels - KEY FIX: Use WSE at Q_scour, not HFL
            scour_levels = self.calculate_scour_levels(
                wse_scour,  # ← Use WSE at scour discharge, not HFL
                pier_abutment_scour
            )
            
            # Calculate minimum soffit level
            min_soffit_level = self.calculate_minimum_soffit_level(wse_scour)
            
            return {
                'mean_scour': mean_scour,
                'pier_abutment_scour': pier_abutment_scour,
                'scour_levels': scour_levels,
                'min_soffit_level': min_soffit_level,
                'wse_scour': round(wse_scour, 2),  # ← Store reference level
                'methodology': 'IRC:78-2014 Clause 703.1.1'
            }
            
        except Exception as e:
            print(f"Scour analysis error: {e}")
            return {}