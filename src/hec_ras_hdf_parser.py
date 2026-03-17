"""
HEC-RAS HDF5 Output Parser Module
Updated for HEC-RAS v6.3.1 Steady Flow Structure
Based on actual file structure from ratu.p01.hdf
"""

import h5py
import numpy as np
from typing import Dict, Optional, List
from pathlib import Path


class HECRASHDFParser:
    """
    Parse HEC-RAS HDF5 output files for bridge analysis
    Compatible with HEC-RAS v6.3.1 Steady Flow
    """
    
    def __init__(self, hdf_path: str):
        self.hdf_path = hdf_path
        self.file = None
        self.is_open = False
        
    def open(self) -> bool:
        """Open HDF5 file"""
        try:
            self.file = h5py.File(self.hdf_path, 'r')
            self.is_open = True
            print(f"DEBUG HDF5: Successfully opened {self.hdf_path}")
            
            # Print top-level structure
            print("DEBUG HDF5: Top-level keys:")
            for key in self.file.keys():
                print(f"  - {key}")
            
            return True
        except Exception as e:
            print(f"ERROR: Could not open HDF5 file: {e}")
            return False
    
    def close(self):
        """Close HDF5 file"""
        if self.file and self.is_open:
            self.file.close()
            self.is_open = False
            print("DEBUG HDF5: File closed")
    
    def get_cross_section_attributes(self) -> List[Dict]:
        """
        Get cross-section attributes (River, Reach, RS, Name)
        """
        xs_attrs = []
        
        try:
            if 'Geometry/Cross Sections/Attributes' in self.file:
                attrs = self.file['Geometry/Cross Sections/Attributes'][:]
                
                for attr in attrs:
                    xs_attrs.append({
                        'river': attr['River'].decode('utf-8').strip(),
                        'reach': attr['Reach'].decode('utf-8').strip(),
                        'rs': attr['RS'].decode('utf-8').strip(),
                        'name': attr['Name'].decode('utf-8').strip()
                    })
                
                print(f"DEBUG HDF5: Found {len(xs_attrs)} cross-sections")
                
        except Exception as e:
            print(f"ERROR getting XS attributes: {e}")
        
        return xs_attrs
    
    def get_bridge_locations(self) -> List[Dict]:
        """
        Get bridge locations from Geometry/Structures
        """
        bridges = []
        
        try:
            if 'Geometry/Structures/Attributes' in self.file:
                structs = self.file['Geometry/Structures/Attributes'][:]
                
                for struct in structs:
                    if struct['Type'].decode('utf-8').strip() == 'Bridge':
                        bridges.append({
                            'river': struct['River'].decode('utf-8').strip(),
                            'reach': struct['Reach'].decode('utf-8').strip(),
                            'rs': struct['RS'].decode('utf-8').strip(),
                            'us_xs': struct['US RS'].decode('utf-8').strip(),
                            'ds_xs': struct['DS RS'].decode('utf-8').strip()
                        })
                
                print(f"DEBUG HDF5: Found {len(bridges)} bridges")
                for b in bridges:
                    print(f"  Bridge at RS {b['rs']}, US XS: {b['us_xs']}, DS XS: {b['ds_xs']}")
                    
        except Exception as e:
            print(f"ERROR getting bridge locations: {e}")
        
        return bridges
    
    def get_steady_flow_data(self) -> Dict:
        """
        Extract steady flow data for all cross-sections
        Path: Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Cross Sections/
        """
        data = {
            'river_stations': [],
            'profile_names': [],
            'WSE': [],
            'Flow': [],
            'Velocity': [],
            'Top_Width': [],
            'Flow_Area': [],
            'Depth': [],
            'Energy_Grade': []
        }
        
        try:
            # Base path for steady flow results
            base_path = 'Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Cross Sections'
            
            # Get profile names
            if f'{base_path}/Profile Names' in self.file:
                profile_names = self.file[f'{base_path}/Profile Names'][:]
                data['profile_names'] = [name.decode('utf-8').strip() for name in profile_names]
                print(f"DEBUG HDF5: Profiles: {data['profile_names']}")
            
            # Get cross-section attributes for river stations
            xs_attrs = self.get_cross_section_attributes()
            data['river_stations'] = [xs['rs'] for xs in xs_attrs]
            
            # Extract hydraulic variables (shape: [n_profiles, n_xs])
            variable_paths = {
                'WSE': f'{base_path}/Water Surface',
                'Flow': f'{base_path}/Flow',
                'Velocity': f'{base_path}/Additional Variables/Velocity Total',
                'Top_Width': f'{base_path}/Additional Variables/Top Width Total',
                'Flow_Area': f'{base_path}/Additional Variables/Area Flow Total',
                'Depth': f'{base_path}/Additional Variables/Hydraulic Depth Total',
                'Energy_Grade': f'{base_path}/Energy Grade'
            }
            
            for var_name, path in variable_paths.items():
                try:
                    if path in self.file:
                        dataset = self.file[path][:]
                        # Store all profiles (we'll use first profile by default)
                        data[var_name] = dataset
                        print(f"DEBUG HDF5: Found {var_name} - Shape: {dataset.shape}")
                    else:
                        print(f"DEBUG HDF5: {var_name} not found at {path}")
                except Exception as e:
                    print(f"DEBUG HDF5: Error reading {var_name}: {e}")
            
        except Exception as e:
            print(f"ERROR getting steady flow data: {e}")
            import traceback
            traceback.print_exc()
        
        return data
    
    def get_bridge_data(self, profile_index: int = 0) -> Dict:
        """
        Extract bridge-specific parameters
        Uses first profile by default (PF 1)
        """
        bridge_data = {
            'upstream_wse': None,
            'downstream_wse': None,
            'bridge_wse': None,
            'bridge_flow': None,
            'velocity_avg': None,
            'velocity_max': None,
            'top_width': None,
            'flow_area': None,
            'hydraulic_depth': None,
            'bridge_detected': False,
            'bridge_rs': None,
            'us_xs_rs': None,
            'ds_xs_rs': None
        }
        
        try:
            # Get bridge locations
            bridges = self.get_bridge_locations()
            
            if not bridges:
                print("DEBUG HDF5: No bridges found in geometry")
                return bridge_data
            
            # Use first bridge
            bridge = bridges[0]
            bridge_data['bridge_rs'] = bridge['rs']
            bridge_data['us_xs_rs'] = bridge['us_xs']
            bridge_data['ds_xs_rs'] = bridge['ds_xs']
            bridge_data['bridge_detected'] = True
            
            print(f"DEBUG HDF5: Analyzing bridge at RS {bridge['rs']}")
            
            # Get steady flow data
            flow_data = self.get_steady_flow_data()
            
            if not flow_data['river_stations']:
                print("DEBUG HDF5: No cross-section data found")
                return bridge_data
            
            # Find indices for bridge, upstream, and downstream cross-sections
            bridge_idx = None
            us_idx = None
            ds_idx = None
            
            for i, rs in enumerate(flow_data['river_stations']):
                if rs == bridge['rs']:
                    bridge_idx = i
                elif rs == bridge['us_xs']:
                    us_idx = i
                elif rs == bridge['ds_xs']:
                    ds_idx = i
            
            print(f"DEBUG HDF5: Indices - Bridge: {bridge_idx}, US: {us_idx}, DS: {ds_idx}")
            
            # If bridge XS not found, use upstream XS
            if bridge_idx is None and us_idx is not None:
                bridge_idx = us_idx
                print("DEBUG HDF5: Bridge XS not found, using upstream XS")
            
            # Extract data for bridge cross-section (use first profile)
            if bridge_idx is not None:
                if flow_data['WSE'] is not None and bridge_idx < flow_data['WSE'].shape[1]:
                    bridge_data['bridge_wse'] = float(flow_data['WSE'][profile_index, bridge_idx])
                    bridge_data['upstream_wse'] = bridge_data['bridge_wse']
                
                if flow_data['Flow'] is not None and bridge_idx < flow_data['Flow'].shape[1]:
                    bridge_data['bridge_flow'] = float(flow_data['Flow'][profile_index, bridge_idx])
                
                if flow_data['Velocity'] is not None and bridge_idx < flow_data['Velocity'].shape[1]:
                    bridge_data['velocity_avg'] = float(flow_data['Velocity'][profile_index, bridge_idx])
                    bridge_data['velocity_max'] = bridge_data['velocity_avg'] * 1.3
                
                if flow_data['Top_Width'] is not None and bridge_idx < flow_data['Top_Width'].shape[1]:
                    bridge_data['top_width'] = float(flow_data['Top_Width'][profile_index, bridge_idx])
                
                if flow_data['Flow_Area'] is not None and bridge_idx < flow_data['Flow_Area'].shape[1]:
                    bridge_data['flow_area'] = float(flow_data['Flow_Area'][profile_index, bridge_idx])
                
                if flow_data['Depth'] is not None and bridge_idx < flow_data['Depth'].shape[1]:
                    bridge_data['hydraulic_depth'] = float(flow_data['Depth'][profile_index, bridge_idx])
            
            # Get downstream WSE
            if ds_idx is not None:
                if flow_data['WSE'] is not None and ds_idx < flow_data['WSE'].shape[1]:
                    bridge_data['downstream_wse'] = float(flow_data['WSE'][profile_index, ds_idx])
            
            print(f"DEBUG HDF5: Bridge data extracted:")
            print(f"  WSE: {bridge_data['upstream_wse']}")
            print(f"  Flow: {bridge_data['bridge_flow']}")
            print(f"  Top Width: {bridge_data['top_width']}")
            print(f"  Velocity: {bridge_data['velocity_avg']}")
            
        except Exception as e:
            print(f"ERROR getting bridge data: {e}")
            import traceback
            traceback.print_exc()
        
        return bridge_data
    
    def extract_all_data(self, plan_name: str = None, profile_index: int = 0) -> Dict:
        """
        Extract all relevant data for hydrology analysis
        
        Args:
            plan_name: Not used in v6.3.1 (only one plan per HDF5)
            profile_index: Which profile to use (0 = PF 1, 1 = PF 2)
        """
        result = {
            'success': False,
            'WSE': None,
            'Q_total': None,
            'Q_bridge': None,
            'velocity_avg': None,
            'velocity_max': None,
            'top_width': None,
            'flow_area': None,
            'hydraulic_depth': None,
            'q_avg': None,
            'q_max': None,
            'source': 'HDF5'
        }
        
        try:
            bridge_data = self.get_bridge_data(profile_index)
            
            if bridge_data['bridge_detected']:
                result['WSE'] = bridge_data['upstream_wse']
                result['Q_bridge'] = bridge_data['bridge_flow']
                result['Q_total'] = bridge_data['bridge_flow']
                result['velocity_avg'] = bridge_data['velocity_avg']
                result['velocity_max'] = bridge_data['velocity_max']
                result['top_width'] = bridge_data['top_width']
                result['flow_area'] = bridge_data['flow_area']
                result['hydraulic_depth'] = bridge_data['hydraulic_depth']
                
                # Calculate discharge intensity
                if result['Q_bridge'] and result['top_width']:
                    result['q_avg'] = result['Q_bridge'] / result['top_width']
                    result['q_max'] = result['q_avg'] * 1.4
                    
                    print(f"DEBUG HDF5: Calculated q_avg = {result['q_avg']:.3f} m²/s")
                    print(f"DEBUG HDF5: Calculated q_max = {result['q_max']:.3f} m²/s")
                
                result['success'] = True
            else:
                print("DEBUG HDF5: Bridge not detected")
            
        except Exception as e:
            print(f"ERROR extracting all data: {e}")
            import traceback
            traceback.print_exc()
        
        return result


def parse_hec_ras_hdf(hdf_path: str, profile_index: int = 0) -> Optional[Dict]:
    """
    Convenience function to parse HEC-RAS HDF5 file
    
    Args:
        hdf_path: Path to HDF5 file
        profile_index: Which profile to use (0 = PF 1, 1 = PF 2)
    """
    parser = HECRASHDFParser(hdf_path)
    
    if not parser.open():
        return None
    
    try:
        result = parser.extract_all_data(profile_index=profile_index)
        return result if result['success'] else None
    finally:
        parser.close()


def find_hdf_files(project_folder: str) -> List[str]:
    """Find all HEC-RAS HDF5 files in a project folder"""
    folder_path = Path(project_folder)
    
    if not folder_path.exists():
        return []
    
    hdf_files = list(folder_path.glob('*.p??.hdf')) + \
                list(folder_path.glob('*.P??.HDF'))
    
    print(f"DEBUG HDF5: Found {len(hdf_files)} HDF5 files in {project_folder}")
    
    return [str(f) for f in hdf_files]