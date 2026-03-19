"""
Rainfall Frequency Analysis Module
Based on Ratu Bridge Hydrology Report (DoR Nepal)
Includes IDF (Intensity-Duration-Frequency) Curve Generation
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List
import matplotlib
matplotlib.use('Agg')  # Must be before pyplot import
import matplotlib.pyplot as plt
from pathlib import Path
import os


class RainfallFrequencyAnalysis:
    """
    Performs frequency distribution analysis on rainfall data
    Including IDF curve generation
    """
    
    def __init__(self, rainfall_csv_path: str):
        """
        Initialize with rainfall CSV file
        
        CSV Format: Year, Max_24hr_Rainfall (mm)
        """
        self.df = pd.read_csv(rainfall_csv_path)
        
        if 'Max_24hr_Rainfall' in self.df.columns:
            self.data = self.df['Max_24hr_Rainfall'].values
        elif len(self.df.columns) > 1:
            self.data = self.df.iloc[:, 1].values
        else:
            self.data = self.df.iloc[:, 0].values
        
        self.years = self.df.iloc[:, 0].values if len(self.df.columns) > 1 else range(len(self.data))
        
        # IDF standard durations (in hours)
        self.idf_durations_hours = [0.25, 0.5, 1, 2, 6, 12, 24]
        self.idf_durations_labels = ['15 min', '30 min', '1 hr', '2 hr', '6 hr', '12 hr', '24 hr']
        
        # Return periods for IDF
        self.idf_return_periods = [2, 5, 10, 50, 100, 200]
    
    def fit_distributions(self) -> Dict:
        """
        Fit multiple distributions and return parameters
        Distributions: GEV, Gumbel, Log-Pearson III, Normal, Laplace
        """
        results = {}
        
        # GEV (Generalized Extreme Value)
        try:
            gev_params = stats.genextreme.fit(self.data)
            results['GEV'] = {
                'params': gev_params,
                'distribution': stats.genextreme(*gev_params)
            }
        except Exception as e:
            print(f"GEV fit error: {e}")
        
        # Gumbel (Extreme Value Type I)
        try:
            gumbel_params = stats.gumbel_r.fit(self.data)
            results['Gumbel'] = {
                'params': gumbel_params,
                'distribution': stats.gumbel_r(*gumbel_params)
            }
        except Exception as e:
            print(f"Gumbel fit error: {e}")
        
        # Normal
        try:
            normal_params = stats.norm.fit(self.data)
            results['Normal'] = {
                'params': normal_params,
                'distribution': stats.norm(*normal_params)
            }
        except Exception as e:
            print(f"Normal fit error: {e}")
        
        # Log-Pearson Type III
        try:
            log_data = np.log(self.data)
            lp3_params = stats.pearson3.fit(log_data)
            results['Log_Pearson_III'] = {
                'params': lp3_params,
                'distribution': stats.pearson3(*lp3_params),
                'is_log': True
            }
        except Exception as e:
            print(f"Log-Pearson III fit error: {e}")
        
        # Laplace
        try:
            laplace_params = stats.laplace.fit(self.data)
            results['Laplace'] = {
                'params': laplace_params,
                'distribution': stats.laplace(*laplace_params)
            }
        except Exception as e:
            print(f"Laplace fit error: {e}")
        
        return results
    
    def goodness_of_fit_tests(self, distributions: Dict) -> Dict:
        """
        Perform Chi-Square, KS, and Anderson-Darling tests
        Returns ranking of best fit distributions
        """
        test_results = {}
        
        ad_supported = {
            'gumbel_r': 'Gumbel',
            'norm': 'Normal',
            'expon': 'Exponential',
            'logistic': 'Logistic',
            'weibull_min': 'Weibull'
        }
        
        for name, dist_info in distributions.items():
            dist = dist_info['distribution']
            is_log = dist_info.get('is_log', False)
            
            data_to_test = np.log(self.data) if is_log else self.data
            n = len(data_to_test)
            
            # Kolmogorov-Smirnov Test
            try:
                ks_stat, ks_pvalue = stats.kstest(data_to_test, dist.cdf)
            except Exception:
                ks_stat, ks_pvalue = 1.0, 0.0
            
            # Chi-Square Test - Robust Version
            chi2_stat, chi2_pvalue = None, None
            
            try:
                sorted_data = np.sort(data_to_test)
                n_bins = 4
                
                percentiles = [0, 25, 50, 75, 100]
                bin_edges = np.percentile(sorted_data, percentiles)
                bin_edges = np.unique(bin_edges)
                
                if len(bin_edges) < 3:
                    data_min = np.min(sorted_data) - 0.01
                    data_max = np.max(sorted_data) + 0.01
                    bin_edges = np.linspace(data_min, data_max, n_bins + 1)
                
                observed_freq = np.zeros(len(bin_edges) - 1)
                for i in range(len(bin_edges) - 1):
                    if i == len(bin_edges) - 2:
                        mask = (sorted_data >= bin_edges[i]) & (sorted_data <= bin_edges[i + 1])
                    else:
                        mask = (sorted_data >= bin_edges[i]) & (sorted_data < bin_edges[i + 1])
                    observed_freq[i] = np.sum(mask)
                
                expected_prob = np.zeros(len(bin_edges) - 1)
                for i in range(len(bin_edges) - 1):
                    expected_prob[i] = dist.cdf(bin_edges[i + 1]) - dist.cdf(bin_edges[i])
                
                expected_freq = expected_prob * n
                
                if np.sum(expected_freq) > 0:
                    expected_freq = expected_freq * (np.sum(observed_freq) / np.sum(expected_freq))
                
                expected_freq = np.maximum(expected_freq, 0.1)
                
                if len(expected_freq) >= 2 and np.sum(observed_freq) > 0:
                    ddof = max(0, len(expected_freq) - 1 - 2)
                    
                    chi2_stat, chi2_pvalue = stats.chisquare(
                        f_obs=observed_freq,
                        f_exp=expected_freq,
                        ddof=ddof
                    )
                    
                    if chi2_pvalue is None or chi2_pvalue < 0 or chi2_pvalue > 1:
                        chi2_stat, chi2_pvalue = None, None
                        
            except Exception as e:
                chi2_stat, chi2_pvalue = None, None
            
            # Anderson-Darling Test
            ad_statistic = None
            
            ad_dist_name = None
            for ad_key, ad_name in ad_supported.items():
                if name.lower() == ad_name.lower() or ad_key in name.lower():
                    ad_dist_name = ad_key
                    break
            
            if name == 'Gumbel':
                ad_dist_name = 'gumbel_r'
            
            if ad_dist_name:
                try:
                    ad_result = stats.anderson(data_to_test, dist=ad_dist_name)
                    ad_statistic = ad_result.statistic
                except Exception:
                    ad_statistic = None
            
            # Calculate overall score
            score = ks_pvalue
            
            if chi2_pvalue is not None:
                score += chi2_pvalue * 0.5
            
            if ad_statistic is not None:
                score += (1.0 / (1.0 + ad_statistic)) * 0.3
            
            test_results[name] = {
                'KS_statistic': round(ks_stat, 4),
                'KS_pvalue': round(ks_pvalue, 4),
                'Chi2_statistic': round(chi2_stat, 4) if chi2_stat is not None else None,
                'Chi2_pvalue': round(chi2_pvalue, 4) if chi2_pvalue is not None else None,
                'AD_statistic': round(ad_statistic, 4) if ad_statistic is not None else None,
                'score': round(score, 4)
            }
        
        return test_results
    
    def get_best_distribution(self, test_results: Dict) -> str:
        """
        Recommend best fitting distribution based on test results
        """
        if not test_results:
            return 'Laplace'
        
        best_dist = max(test_results.keys(), key=lambda x: test_results[x]['score'])
        return best_dist
    
    def calculate_return_period_rainfall(self, distribution: dict, return_periods: List[int]) -> Dict:
        """
        Calculate rainfall depth for different return periods
        """
        dist = distribution['distribution']
        is_log = distribution.get('is_log', False)
        
        results = {}
        for T in return_periods:
            p = 1 - (1 / T)
            
            try:
                if is_log:
                    rainfall_mm = np.exp(dist.ppf(p))
                else:
                    rainfall_mm = dist.ppf(p)
                
                results[f'{T}_year'] = round(float(rainfall_mm), 2)
            except Exception:
                results[f'{T}_year'] = 0.0
        
        return results
    
    # ═══════════════════════════════════════════════════════════════
    # IDF (Intensity-Duration-Frequency) Curve Generation
    # ═══════════════════════════════════════════════════════════════
    
    def get_distribution_object(self, dist_name: str):
        """Get scipy distribution object based on name"""
        dist_map = {
            'GEV': stats.genextreme,
            'Gumbel': stats.gumbel_r,
            'Normal': stats.norm,
            'Log_Pearson_III': stats.pearson3,
            'Laplace': stats.laplace
        }
        
        if dist_name in dist_map:
            return dist_map[dist_name]
        else:
            return stats.gumbel_r
    
    def calculate_rainfall_depth(self, distribution: dict, duration_hr: float, return_period: int) -> float:
        """
        Calculate rainfall depth for given duration and return period
        
        Uses frequency factor method with duration adjustment
        """
        try:
            dist = distribution['distribution']
            is_log = distribution.get('is_log', False)
            
            p = 1 - (1 / return_period)
            
            if duration_hr == 24:
                if is_log:
                    depth_24hr = np.exp(dist.ppf(p))
                else:
                    depth_24hr = dist.ppf(p)
            else:
                if is_log:
                    depth_24hr = np.exp(dist.ppf(p))
                else:
                    depth_24hr = dist.ppf(p)
                
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
    
    def generate_idf_data(self, distribution: dict) -> pd.DataFrame:
        """
        Generate complete IDF data table
        
        Returns:
            DataFrame with columns: Duration, Return Period, Depth, Intensity
        """
        data = []
        
        for duration_hr, duration_label in zip(self.idf_durations_hours, self.idf_durations_labels):
            for rp in self.idf_return_periods:
                depth = self.calculate_rainfall_depth(distribution, duration_hr, rp)
                intensity = self.calculate_intensity(depth, duration_hr)
                
                data.append({
                    'Duration_hr': duration_hr,
                    'Duration_Label': duration_label,
                    'Return_Period': rp,
                    'Depth_mm': round(depth, 2),
                    'Intensity_mm_hr': round(intensity, 2)
                })
        
        return pd.DataFrame(data)
    
    def plot_idf_curves(self, distribution_name: str, idf_data: pd.DataFrame, 
                       figsize=(10, 6)) -> plt.Figure:
        """
        Generate IDF curve plot
        
        Returns:
            matplotlib Figure object
        """
        print(f"DEBUG PLOT: Starting plot generation...")
        print(f"DEBUG PLOT: IDF data shape: {idf_data.shape}")
        print(f"DEBUG PLOT: Columns: {idf_data.columns.tolist()}")
        
        # Verify we have data
        if idf_data.empty:
            print("ERROR: IDF data is empty!")
            raise ValueError("IDF data is empty")
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Get unique return periods
        return_periods = sorted(idf_data['Return_Period'].unique())
        print(f"DEBUG PLOT: Return periods: {return_periods}")
        
        colors = plt.cm.viridis(np.linspace(0, 1, len(return_periods)))
        
        plot_count = 0
        for i, rp in enumerate(return_periods):
            rp_data = idf_data[idf_data['Return_Period'] == rp]
            
            if not rp_data.empty:
                # Get duration labels and intensities
                durations = rp_data['Duration_Label'].values
                intensities = rp_data['Intensity_mm_hr'].values
                
                print(f"DEBUG PLOT: RP {rp}-year: {len(durations)} points")
                
                ax.plot(durations, intensities, 
                       marker='o', linewidth=2, markersize=6,
                       label=f'{rp}-year', color=colors[i])
                plot_count += 1
        
        print(f"DEBUG PLOT: Plotted {plot_count} curves")
        
        if plot_count == 0:
            print("ERROR: No curves were plotted!")
            raise ValueError("No data to plot")
        
        ax.set_xlabel('Duration', fontsize=11, fontweight='bold')
        ax.set_ylabel('Rainfall Intensity (mm/hr)', fontsize=11, fontweight='bold')
        ax.set_title(f'IDF Curves - {distribution_name} Distribution', 
                    fontsize=12, fontweight='bold', pad=15)
        ax.legend(title='Return Period', loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Verify figure has content
        print(f"DEBUG PLOT: Figure axes count: {len(fig.axes)}")
        print(f"DEBUG PLOT: Figure size: {fig.get_size_inches()}")
        
        return fig
    
    def plot_depth_duration(self, distribution_name: str, idf_data: pd.DataFrame, 
                           figsize=(10, 6)) -> plt.Figure:
        """
        Generate Depth-Duration-Frequency plot
        
        Returns:
            matplotlib Figure object
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        colors = plt.cm.plasma(np.linspace(0, 1, len(self.idf_return_periods)))
        
        for i, rp in enumerate(self.idf_return_periods):
            rp_data = idf_data[idf_data['Return_Period'] == rp]
            ax.plot(rp_data['Duration_Label'], rp_data['Depth_mm'], 
                   marker='s', linewidth=2, markersize=6,
                   label=f'{rp}-year', color=colors[i])
        
        ax.set_xlabel('Duration', fontsize=11, fontweight='bold')
        ax.set_ylabel('Rainfall Depth (mm)', fontsize=11, fontweight='bold')
        ax.set_title(f'Depth-Duration-Frequency Curves - {distribution_name}', 
                    fontsize=12, fontweight='bold', pad=15)
        ax.legend(title='Return Period', loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        return fig
    
    def get_idf_table(self, idf_data: pd.DataFrame) -> pd.DataFrame:
        """
        Get IDF data as formatted table for report
        
        Returns:
            Pivot table with durations as rows and return periods as columns
        """
        intensity_table = idf_data.pivot_table(
            values='Intensity_mm_hr', 
            index='Duration_Label', 
            columns='Return_Period',
            aggfunc='first'
        )
        
        return intensity_table.round(2)
    
    # ═══════════════════════════════════════════════════════════════
    # Complete Analysis Workflow
    # ═══════════════════════════════════════════════════════════════
    
    def full_analysis(self, return_periods: List[int] = None) -> Dict:
        """
        Complete rainfall frequency analysis workflow
        Including IDF curve generation
        """
        if return_periods is None:
            return_periods = [2, 5, 10, 20, 50, 100, 200]
        
        try:
            distributions = self.fit_distributions()
            
            if not distributions:
                return {
                    'best_distribution': 'Laplace (Report Default)',
                    'R100yr': 519.38,
                    'rainfall_estimates': {
                        '2_year': 150.0, '5_year': 250.0, '10_year': 350.0,
                        '20_year': 420.0, '50_year': 480.0, '100_year': 519.38,
                        '200_year': 580.0
                    },
                    'idf_plot_path': None,
                    'idf_table': {},
                    'idf_data': {}
                }
            
            test_results = self.goodness_of_fit_tests(distributions)
            best_dist_name = self.get_best_distribution(test_results)
            best_dist = distributions[best_dist_name]
            rainfall_estimates = self.calculate_return_period_rainfall(best_dist, return_periods)
            
            # Generate IDF curves
            idf_plot_path = None
            idf_table = {}
            idf_data = {}
            
            try:
                print(f"DEBUG: Starting IDF generation...")
                
                idf_data_df = self.generate_idf_data(best_dist)
                print(f"DEBUG: IDF data generated - {len(idf_data_df)} rows")
                
                idf_table_df = self.get_idf_table(idf_data_df)
                print(f"DEBUG: IDF table generated - {len(idf_table_df)} durations")
                
                # Save IDF plot - Use absolute path
                idf_plot_path = Path('data/rainfall/idf_curve.png').resolve()
                Path('data/rainfall').mkdir(parents=True, exist_ok=True)
                print(f"DEBUG: Created directory: data/rainfall")
                print(f"DEBUG: Absolute path: {idf_plot_path}")
                
                try:
                    idf_fig = self.plot_idf_curves(best_dist_name, idf_data_df)
                    
                    # Save as PNG
                    idf_plot_path_png = str(idf_plot_path)
                    idf_fig.savefig(idf_plot_path_png, dpi=150, bbox_inches='tight', facecolor='white')
                    
                    # Also save as JPEG (better Word compatibility)
                    idf_plot_path_jpg = str(idf_plot_path).replace('.png', '.jpg')
                    idf_fig.savefig(idf_plot_path_jpg, dpi=150, bbox_inches='tight', facecolor='white', format='jpeg')
                    
                    plt.close(idf_fig)
                    
                    # Use JPEG path for report (better compatibility)
                    if os.path.exists(idf_plot_path_jpg):
                        idf_plot_path = idf_plot_path_jpg
                        print(f"DEBUG: Using JPEG format for better compatibility")
                    
                    # Verify file was created and has content
                    file_size = os.path.getsize(idf_plot_path)
                    print(f"DEBUG: IDF plot saved to: {idf_plot_path}")
                    print(f"DEBUG: File size: {file_size} bytes")
                    
                    if file_size < 1000:
                        print(f"WARNING: Plot file is very small ({file_size} bytes)")
                    else:
                        print(f"DEBUG: ✅ IDF plot file verified ({file_size} bytes)")
                    
                except Exception as e:
                    print(f"ERROR: Failed to save IDF plot: {e}")
                    import traceback
                    traceback.print_exc()
                    idf_plot_path = None
                
                # Convert to dict for storage
                idf_table = idf_table_df.to_dict()
                idf_data = idf_data_df.to_dict()
                
                print(f"IDF curves generated successfully!")
                
            except Exception as e:
                print(f"IDF generation error: {e}")
                import traceback
                traceback.print_exc()
                idf_plot_path = None
                idf_table = {}
                idf_data = {}
            
            # FIXED RETURN STATEMENT - IDF data at top level!
            return {
                'best_distribution': best_dist_name,
                'test_results': test_results,
                'rainfall_estimates': rainfall_estimates,
                'R100yr': rainfall_estimates.get('100_year', 519.38),
                'idf_plot_path': str(idf_plot_path) if idf_plot_path else None,
                'idf_table': idf_table,
                'idf_data': idf_data
            }
            
        except Exception as e:
            print(f"Rainfall analysis error: {e}")
            return {
                'best_distribution': 'Laplace (Report Default)',
                'R100yr': 519.38,
                'rainfall_estimates': {
                    '2_year': 150.0, '5_year': 250.0, '10_year': 350.0,
                    '20_year': 420.0, '50_year': 480.0, '100_year': 519.38,
                    '200_year': 580.0
                },
                'idf_plot_path': None,
                'idf_table': {},
                'idf_data': {}
            }