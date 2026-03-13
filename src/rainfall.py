import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Tuple

class RainfallFrequencyAnalysis:
    """
    Performs frequency distribution analysis on rainfall data
    (Section 3.2 from report)
    """
    
    def __init__(self, rainfall_csv_path: str):
        """
        Initialize with rainfall CSV file
        
        CSV Format: Year, Max_24hr_Rainfall (mm)
        """
        self.df = pd.read_csv(rainfall_csv_path)
        self.data = self.df['Max_24hr_Rainfall'].values
        self.years = self.df['Year'].values
        
    def fit_distributions(self) -> Dict:
        """
        Fit multiple distributions and return parameters
        Distributions: GEV, Log-Pearson III, Gumbel, Normal
        """
        results = {}
        
        # GEV (Generalized Extreme Value)
        gev_params = stats.genextreme.fit(self.data)
        results['GEV'] = {
            'params': gev_params,
            'distribution': stats.genextreme(*gev_params)
        }
        
        # Gumbel (Extreme Value Type I)
        gumbel_params = stats.gumbel_r.fit(self.data)
        results['Gumbel'] = {
            'params': gumbel_params,
            'distribution': stats.gumbel_r(*gumbel_params)
        }
        
        # Normal
        normal_params = stats.norm.fit(self.data)
        results['Normal'] = {
            'params': normal_params,
            'distribution': stats.norm(*normal_params)
        }
        
        # Log-Pearson Type III (manual implementation)
        log_data = np.log(self.data)
        lp3_params = stats.pearson3.fit(log_data)
        results['Log_Pearson_III'] = {
            'params': lp3_params,
            'distribution': stats.pearson3(*lp3_params),
            'is_log': True
        }
        
        return results
    
    def goodness_of_fit_tests(self, distributions: Dict) -> Dict:
        """
        Perform Chi-Square, KS, and Anderson-Darling tests
        Returns ranking of best fit distributions
        """
        test_results = {}
        
        for name, dist_info in distributions.items():
            dist = dist_info['distribution']
            is_log = dist_info.get('is_log', False)
            
            data_to_test = np.log(self.data) if is_log else self.data
            
            # Kolmogorov-Smirnov Test
            ks_stat, ks_pvalue = stats.kstest(data_to_test, dist.cdf)
            
            # Anderson-Darling Test
            ad_result = stats.anderson(data_to_test, dist=name.lower())
            
            # Chi-Square Test (binned)
            observed_freq, bin_edges = np.histogram(data_to_test, bins='auto')
            expected_prob = dist.cdf(bin_edges[1:]) - dist.cdf(bin_edges[:-1])
            expected_freq = expected_prob * len(data_to_test)
            chi2_stat, chi2_pvalue = stats.chisquare(observed_freq, expected_freq)
            
            test_results[name] = {
                'KS_statistic': ks_stat,
                'KS_pvalue': ks_pvalue,
                'AD_statistic': ad_result.statistic,
                'Chi2_statistic': chi2_stat,
                'Chi2_pvalue': chi2_pvalue,
                'score': ks_pvalue + chi2_pvalue  # Simple ranking score
            }
        
        return test_results
    
    def get_best_distribution(self, test_results: Dict) -> str:
        """
        Recommend best fitting distribution based on test results
        """
        best_dist = max(test_results.keys(), 
                       key=lambda x: test_results[x]['score'])
        return best_dist
    
    def calculate_return_period_rainfall(self, distribution: dict, 
                                         return_periods: list) -> Dict:
        """
        Calculate rainfall depth for different return periods
        """
        dist = distribution['distribution']
        is_log = distribution.get('is_log', False)
        
        results = {}
        for T in return_periods:
            # Probability of exceedance
            p = 1 - (1 / T)
            
            # Inverse CDF (Percent Point Function)
            if is_log:
                rainfall_mm = np.exp(dist.ppf(p))
            else:
                rainfall_mm = dist.ppf(p)
            
            results[f'{T}_year'] = round(rainfall_mm, 2)
        
        return results
    
    def full_analysis(self, return_periods: list = [2, 5, 10, 20, 50, 100, 200]) -> Dict:
        """
        Complete rainfall frequency analysis workflow
        """
        distributions = self.fit_distributions()
        test_results = self.goodness_of_fit_tests(distributions)
        best_dist_name = self.get_best_distribution(test_results)
        best_dist = distributions[best_dist_name]
        rainfall_estimates = self.calculate_return_period_rainfall(
            best_dist, return_periods
        )
        
        return {
            'best_distribution': best_dist_name,
            'test_results': test_results,
            'rainfall_estimates': rainfall_estimates,
            'R100yr': rainfall_estimates.get('100_year', 0)
        }