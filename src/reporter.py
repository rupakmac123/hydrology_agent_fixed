"""
Report Generator Module
Generates tables and exports matching Ratu Bridge Report format (Table 5, 6, 7, 8, 9)
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict

class ReportGenerator:
    """
    Generates hydrology reports matching Department of Roads (DoR) Nepal format
    Based on Ratu Bridge Hydrology Report structure
    """
    
    def __init__(self, output_dir: str = './outputs/reports'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_table_5(self, catchment_props: Dict, rainfall_results: Dict, 
                         discharge_results: Dict, Ct: float = 1.4, 
                         Cp: float = 0.655) -> pd.DataFrame:
        
        data = {
            'Parameter': [
                '24 hr rainfall of 100 y return period (R100yr), mm',
                'Ct',
                'Cp',
                'Methods of peak discharge estimation',
                'WECS Method',
                'Modified Dickens Method',
                'B.D. Richards Method',
                'Snyder Method',
                'Adopted 100 years return period peak discharges (Q100)',
                'Adopted design discharge (Qdesign)'
            ],
            'Value': [
                rainfall_results.get('R100yr', 0),
                Ct,
                Cp,
                'Peak discharge (m3/s) of 100 y return period',
                discharge_results.get('WECS_100yr', 0),
                discharge_results.get('Dickens_100yr', 0),
                discharge_results.get('Richards_100yr', 0),
                discharge_results.get('Snyder_100yr', 0),
                discharge_results.get('Adopted_Q100', 0),
                discharge_results.get('Design_Discharge', 0)
            ]
        }
        
        df = pd.DataFrame(data)
        output_path = self.output_dir / 'table_5_summary.csv'
        df.to_csv(output_path, index=False)
        
        json_path = self.output_dir / 'table_5_summary.json'
        with open(json_path, 'w') as f:
            json.dump({
                'R100yr_mm': rainfall_results.get('R100yr', 0),
                'Ct': Ct,
                'Cp': Cp,
                'discharge_methods': {
                    'WECS': discharge_results.get('WECS_100yr', 0),
                    'Dickens': discharge_results.get('Dickens_100yr', 0),
                    'Richards': discharge_results.get('Richards_100yr', 0),
                    'Snyder': discharge_results.get('Snyder_100yr', 0)
                },
                'Q100': discharge_results.get('Adopted_Q100', 0),
                'Q_design': discharge_results.get('Design_Discharge', 0)
            }, f, indent=2)
        
        print(f"Table 5 saved to: {output_path}")
        return df
    
    def generate_table_1(self, catchment_props: Dict) -> pd.DataFrame:
        data = {
            'Basin': ['Ratu River at Bridge site'],
            'A (km2)': [catchment_props.get('A_km2', 0)],
            'L (km)': [catchment_props.get('L_km', 0)],
            'Lc (km)': [catchment_props.get('Lc_km', 0)],
            'Hmax (m)': [catchment_props.get('Hmax_m', 0)],
            'Hmin (m)': [catchment_props.get('Hmin_m', 0)]
        }
        
        df = pd.DataFrame(data)
        output_path = self.output_dir / 'table_1_catchment.csv'
        df.to_csv(output_path, index=False)
        
        print(f"Table 1 saved to: {output_path}")
        return df
    
    def generate_hec_ras_input(self, discharge_results: Dict, 
                                manning_n: Dict = None) -> Dict:
        if manning_n is None:
            manning_n = {'channel': 0.03, 'overbank': 0.035}
        
        hec_ras_data = {
            'boundary_conditions': {
                'upstream_flow': discharge_results.get('Design_Discharge', 0),
                'flow_type': 'steady',
                'return_period': 100
            },
            'manning_coefficients': {
                'main_channel': manning_n['channel'],
                'overbank': manning_n['overbank']
            },
            'metadata': {
                'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'climate_change_factor': 1.10,
                'source': 'Hydrology Agent v1.0'
            }
        }
        
        output_path = self.output_dir.parent / 'hec_ras' / 'boundary_conditions.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(hec_ras_data, f, indent=2)
        
        print(f"HEC-RAS input saved to: {output_path}")
        return hec_ras_data
    
    def generate_full_report(self, catchment_props: Dict, rainfall_results: Dict,
                             discharge_results: Dict, Ct: float = 1.4, 
                             Cp: float = 0.655) -> Dict:
        
        print("\n" + "="*60)
        print("GENERATING HYDROLOGY REPORT")
        print("="*60)
        
        table1 = self.generate_table_1(catchment_props)
        table5 = self.generate_table_5(catchment_props, rainfall_results, 
                                       discharge_results, Ct, Cp)
        hec_ras = self.generate_hec_ras_input(discharge_results)
        
        print("\n" + "-"*60)
        print("SUMMARY OF HYDROLOGIC CALCULATION (Table 5)")
        print("-"*60)
        print(f"24 hr rainfall of 100 y return period (R100yr): {rainfall_results.get('R100yr', 0):.2f} mm")
        print(f"Ct: {Ct} | Cp: {Cp}")
        print("-"*60)
        print(f"{'Method':<35} {'Discharge (m3/s)':<20}")
        print("-"*60)
        print(f"{'WECS Method':<35} {discharge_results.get('WECS_100yr', 0):<20.2f}")
        print(f"{'Modified Dickens Method':<35} {discharge_results.get('Dickens_100yr', 0):<20.2f}")
        print(f"{'B.D. Richards Method':<35} {discharge_results.get('Richards_100yr', 0):<20.2f}")
        print(f"{'Snyder Method':<35} {discharge_results.get('Snyder_100yr', 0):<20.2f}")
        print("-"*60)
        print(f"Adopted Q100: {discharge_results.get('Adopted_Q100', 0):.2f} m3/s")
        print(f"Design Discharge (Q100 x 1.1): {discharge_results.get('Design_Discharge', 0):.2f} m3/s")
        print("="*60)
        
        return {
            'table_1': table1,
            'table_5': table5,
            'hec_ras_input': hec_ras,
            'output_directory': str(self.output_dir)
        }