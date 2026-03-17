"""
Scour Calculation Module
Based on Ratu Bridge Hydrology Report (Tables 7, 8, 9)
"""

import numpy as np
from typing import Dict


class ScourCalculator:
    """
    Calculates scour depth for bridge foundations
    Following DoR Nepal guidelines
    """
    
    def __init__(self, Q_design: float, L_bridge: float, 
                 dmean_mm: float = 2.8, Ksf: float = 2.9,
                 Blench_Fb: float = 0.8):
        self.Q_design = Q_design
        self.Q_scour = Q_design * (1.3 / 1.1)
        self.L_bridge = L_bridge
        self.dmean_mm = dmean_mm
        self.Ksf = Ksf
        self.Blench_Fb = Blench_Fb
    
    def calculate_mean_scour_lacey(self, q: float) -> float:
        """
        Lacey's formula: D = (0.473 × q^(1/3)) / (Ksf^(1/3))
        """
        D = (0.473 * (q ** (1/3))) / (self.Ksf ** (1/3))
        return round(D, 2)
    
    def calculate_blench_scour(self, qm: float) -> float:
        """
        Blench approach: D = (qm² / Fb)^0.33
        """
        D = ((qm ** 2) / self.Blench_Fb) ** 0.33
        return round(D, 2)
    
    def calculate_scour_for_section(self, q_avg: float, q_max: float) -> Dict:
        """
        Calculate scour for a cross-section
        """
        D_lacey_avg = self.calculate_mean_scour_lacey(q_avg)
        D_lacey_max = self.calculate_mean_scour_lacey(q_max)
        D_blench = self.calculate_blench_scour(q_avg)
        
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
        """
        D_pier = 2.0 * D_mean
        D_abutment = 1.27 * D_mean
        
        return {
            'D_pier': round(D_pier, 2),
            'D_abutment': round(D_abutment, 2)
        }
    
    def calculate_scour_levels(self, HFL: float, D_mean: float, 
                                D_pier: float, D_abutment: float) -> Dict:
        """
        Calculate scour levels for foundation design
        """
        scour_level_abutment = HFL - D_abutment
        scour_level_pier = HFL - D_pier
        
        return {
            'scour_level_abutment': round(scour_level_abutment, 2),
            'scour_level_pier': round(scour_level_pier, 2)
        }
    
    def full_scour_analysis(self, HFL: float, q_avg: float, q_max: float) -> Dict:
        """
        Complete scour analysis for a bridge section
        """
        scour_results = self.calculate_scour_for_section(q_avg, q_max)
        D_adopted = scour_results['D_adopted']
        
        pier_abutment = self.calculate_pier_abutment_scour(D_adopted)
        
        levels = self.calculate_scour_levels(
            HFL, D_adopted, 
            pier_abutment['D_pier'], 
            pier_abutment['D_abutment']
        )
        
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