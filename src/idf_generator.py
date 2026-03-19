# -*- coding: utf-8 -*-
"""
Created on Wed Mar 18 15:33:44 2026

@author: user
"""

"""
IDF (Intensity-Duration-Frequency) Curve Generator
Based on fitted rainfall distribution
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # For non-interactive backend


class IDFGenerator:
    """
    Generate IDF curves from rainfall frequency analysis
    """
    
    def __init__(self, distribution_name: str, distribution_params: Dict, 
                 annual_max_24hr: float):
        """
        Initialize IDF generator
        
        Args:
            distribution_name: Name of fitted distribution (GEV, Gumbel, etc.)
            distribution_params: Parameters of the fitted distribution
            annual_max_24hr: Annual maximum 24-hour rainfall (mm)
        """
        self.distribution_name = distribution_name
        self.distribution_params = distribution_params
        self.annual_max_24hr = annual_max_24hr
        
        # Standard durations (in hours)
        self.durations_hours = [0.25, 0.5, 1, 2, 6, 12, 24]  # 15min to 24hr
        self.durations_labels = ['15 min', '30 min', '1 hr', '2 hr', '6 hr', '12 hr', '24 hr']
        
        # Return periods
        self.return_periods = [2, 5, 10, 50, 100, 200]
    
    def get_distribution_object(self):
        """Get scipy distribution object based on name"""
        dist_map = {
            'GEV': stats.genextreme,
            'Gumbel': stats.gumbel_r,
            'Normal': stats.norm,
            'Log_Pearson_III': stats.pearson3,
            'Laplace': stats.laplace
        }
        
        if self.distribution_name in dist_map:
            return dist_map[self.distribution_name]
        else:
            return stats.gumbel_r  # Default
    
    def calculate_rainfall_depth(self, duration_hr: float, return_period: int) -> float:
        """
        Calculate rainfall depth for given duration and return period
        
        Uses frequency factor method with duration adjustment
        """
        try:
            dist = self.get_distribution_object()
            
            # Probability of exceedance
            p = 1 - (1 / return_period)
            
            # For 24-hour duration, use fitted distribution directly
            if duration_hr == 24:
                if self.distribution_name == 'Log_Pearson_III':
                    # Log-Pearson Type III
                    log_data = np.log(self.annual_max_24hr)
                    depth_24hr = np.exp(dist.ppf(p, *self.distribution_params))
                else:
                    depth_24hr = dist.ppf(p, *self.distribution_params)
            else:
                # For other durations, use IDF relationship
                # R_t,d = R_t,24 * (d/24)^(1/n) where n ≈ 0.5-0.6
                # Simplified: R_t,d = R_t,24 * (d/24)^0.5
                
                if self.distribution_name == 'Log_Pearson_III':
                    depth_24hr = np.exp(dist.ppf(p, *self.distribution_params))
                else:
                    depth_24hr = dist.ppf(p, *self.distribution_params)
                
                # Duration adjustment (empirical relationship)
                duration_factor = (duration_hr / 24) ** 0.5
                depth_24hr = depth_24hr * duration_factor
            
            return max(0, float(depth_24hr))
            
        except Exception as e:
            print(f"Error calculating depth: {e}")
            return 0.0
    
    def calculate_intensity(self, depth_mm: float, duration_hr: float) -> float:
        """
        Calculate rainfall intensity (mm/hr)
        
        Intensity = Depth / Duration
        """
        if duration_hr <= 0:
            return 0.0
        return depth_mm / duration_hr
    
    def generate_idf_data(self) -> pd.DataFrame:
        """
        Generate complete IDF data table
        
        Returns:
            DataFrame with columns: Duration, Return Period, Depth, Intensity
        """
        data = []
        
        for duration_hr, duration_label in zip(self.durations_hours, self.durations_labels):
            for rp in self.return_periods:
                depth = self.calculate_rainfall_depth(duration_hr, rp)
                intensity = self.calculate_intensity(depth, duration_hr)
                
                data.append({
                    'Duration_hr': duration_hr,
                    'Duration_Label': duration_label,
                    'Return_Period': rp,
                    'Depth_mm': round(depth, 2),
                    'Intensity_mm_hr': round(intensity, 2)
                })
        
        return pd.DataFrame(data)
    
    def plot_idf_curves(self, figsize: Tuple[int, int] = (10, 6)) -> plt.Figure:
        """
        Generate IDF curve plot
        
        Returns:
            matplotlib Figure object
        """
        df = self.generate_idf_data()
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot IDF curves (Intensity vs Duration for each return period)
        colors = plt.cm.viridis(np.linspace(0, 1, len(self.return_periods)))
        
        for i, rp in enumerate(self.return_periods):
            rp_data = df[df['Return_Period'] == rp]
            ax.plot(rp_data['Duration_Label'], rp_data['Intensity_mm_hr'], 
                   marker='o', linewidth=2, markersize=6,
                   label=f'{rp}-year', color=colors[i])
        
        ax.set_xlabel('Duration', fontsize=11, fontweight='bold')
        ax.set_ylabel('Rainfall Intensity (mm/hr)', fontsize=11, fontweight='bold')
        ax.set_title(f'IDF Curves - {self.distribution_name} Distribution', 
                    fontsize=12, fontweight='bold', pad=15)
        ax.legend(title='Return Period', loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        return fig
    
    def plot_depth_duration(self, figsize: Tuple[int, int] = (10, 6)) -> plt.Figure:
        """
        Generate Depth-Duration-Frequency plot
        
        Returns:
            matplotlib Figure object
        """
        df = self.generate_idf_data()
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot DDF curves (Depth vs Duration for each return period)
        colors = plt.cm.plasma(np.linspace(0, 1, len(self.return_periods)))
        
        for i, rp in enumerate(self.return_periods):
            rp_data = df[df['Return_Period'] == rp]
            ax.plot(rp_data['Duration_Label'], rp_data['Depth_mm'], 
                   marker='s', linewidth=2, markersize=6,
                   label=f'{rp}-year', color=colors[i])
        
        ax.set_xlabel('Duration', fontsize=11, fontweight='bold')
        ax.set_ylabel('Rainfall Depth (mm)', fontsize=11, fontweight='bold')
        ax.set_title(f'Depth-Duration-Frequency Curves - {self.distribution_name}', 
                    fontsize=12, fontweight='bold', pad=15)
        ax.legend(title='Return Period', loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        return fig
    
    def get_idf_table(self) -> pd.DataFrame:
        """
        Get IDF data as formatted table for report
        
        Returns:
            Pivot table with durations as rows and return periods as columns
        """
        df = self.generate_idf_data()
        
        # Create pivot table for intensities
        intensity_table = df.pivot_table(
            values='Intensity_mm_hr', 
            index='Duration_Label', 
            columns='Return_Period',
            aggfunc='first'
        )
        
        return intensity_table.round(2)

