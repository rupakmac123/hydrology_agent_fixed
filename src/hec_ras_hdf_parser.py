"""
HEC-RAS Output Parser Module
Parses HEC-RAS output files (.txt, .hdf) for bridge hydraulic analysis
Handles both Ratu and Aurahi format variations
"""

import pandas as pd
from typing import Dict, Optional


def parse_hec_ras_file(file) -> Dict:
    """
    Parse HEC-RAS output file (.txt format)
    Handles tab-separated values from Aurahi format
    """
    try:
        # Read file content
        if hasattr(file, 'read'):
            content = file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
        else:
            content = str(file)
        
        lines = content.split('\n')
        
        data = {}
        
        # First pass: Parse general parameters (left side of table)
        for line in lines:
            if not line.strip():
                continue
            
            parts = line.split('\t')
            
            # General parameters (left column)
            if 'E.G. US. (m)' in line and len(parts) >= 2:
                try:
                    data['EG_US'] = float(parts[1].strip())
                except: pass
            elif 'W.S. US. (m)' in line and len(parts) >= 2:
                try:
                    data['WSE'] = float(parts[1].strip())
                except: pass
            elif 'Q Total (m3/s)' in line and len(parts) >= 2:
                try:
                    data['Q_total'] = float(parts[1].strip())
                except: pass
            elif 'Q Bridge (m3/s)' in line and len(parts) >= 2:
                try:
                    data['Q_bridge'] = float(parts[1].strip())
                except: pass
            elif 'Flow Area (m2)' in line and 'Inside BR' not in line and len(parts) >= 2:
                try:
                    data['flow_area'] = float(parts[1].strip())
                except: pass
            elif 'Top Width (m)' in line and 'Inside BR' not in line and len(parts) >= 2:
                try:
                    data['top_width'] = float(parts[1].strip())
                except: pass
            elif 'Vel Total (m/s)' in line and len(parts) >= 2:
                try:
                    data['velocity_avg'] = float(parts[1].strip())
                except: pass
            elif 'Hydr Depth (m)' in line and 'Inside BR' not in line and len(parts) >= 2:
                try:
                    data['hydraulic_depth'] = float(parts[1].strip())
                except: pass
            elif 'Delta EG (m)' in line and len(parts) >= 2:
                try:
                    data['Delta_EG'] = float(parts[1].strip())
                except: pass
            elif 'Delta WS (m)' in line and len(parts) >= 2:
                try:
                    data['Delta_WS'] = float(parts[1].strip())
                except: pass
            elif 'Frctn Loss (m)' in line and len(parts) >= 2:
                try:
                    data['Frctn_Loss'] = float(parts[1].strip())
                except: pass
            elif 'C & E Loss (m)' in line and len(parts) >= 2:
                try:
                    data['CE_Loss'] = float(parts[1].strip())
                except: pass
        
        # Second pass: Parse Inside Bridge table (right side)
        in_bridge_table = False
        for i, line in enumerate(lines):
            if 'Element' in line and 'Inside BR' in line:
                in_bridge_table = True
                continue
            
            if in_bridge_table:
                parts = line.split('\t')
                if len(parts) >= 3:
                    try:
                        if 'E.G. Elev (m)' in line:
                            data['EG_BR_US'] = float(parts[1].strip())
                            data['EG_BR_DS'] = float(parts[2].strip())
                        elif 'W.S. Elev (m)' in line:
                            data['WS_BR_US'] = float(parts[1].strip())
                            data['WS_BR_DS'] = float(parts[2].strip())
                        elif 'Max Chl Dpth (m)' in line:
                            data['Max_Chl_Dpth_US'] = float(parts[1].strip())
                            data['Max_Chl_Dpth_DS'] = float(parts[2].strip())
                        elif 'Vel Total (m/s)' in line:
                            data['Vel_BR_US'] = float(parts[1].strip())
                            data['Vel_BR_DS'] = float(parts[2].strip())
                        elif 'Flow Area (m2)' in line:
                            data['flow_area_us'] = float(parts[1].strip())
                            data['flow_area_ds'] = float(parts[2].strip())
                        elif 'Hydr Depth (m)' in line:
                            data['Hydr_Dpth_US'] = float(parts[1].strip())
                            data['Hydr_Dpth_DS'] = float(parts[2].strip())
                        elif 'W.P. Total (m)' in line:
                            data['WP_Total_US'] = float(parts[1].strip())
                            data['WP_Total_DS'] = float(parts[2].strip())
                        elif 'Conv. Total (m3/s)' in line:
                            data['Conv_Total_US'] = float(parts[1].strip())
                            data['Conv_Total_DS'] = float(parts[2].strip())
                        elif 'Shear Total (N/m2)' in line:
                            data['Shear_Total_US'] = float(parts[1].strip())
                            data['Shear_Total_DS'] = float(parts[2].strip())
                        elif 'Power Total (N/m s)' in line:
                            data['Power_Total_US'] = float(parts[1].strip())
                            data['Power_Total_DS'] = float(parts[2].strip())
                    except:
                        pass
            
            # Stop parsing when we reach empty line or new section
            if line.strip() == '' and in_bridge_table:
                in_bridge_table = False
        
        return data
    
    except Exception as e:
        print(f"Error parsing HEC-RAS file: {e}")
        return {}


def parse_hec_ras_hdf_file(file_path: str) -> Optional[Dict]:
    """Parse HEC-RAS HDF5 output file"""
    try:
        import h5py
        
        data = {}
        
        with h5py.File(file_path, 'r') as f:
            # Extract relevant data from HDF5 structure
            if 'Geometry' in f:
                geom = f['Geometry']
                if 'River Rch' in geom:
                    for river in geom['River Rch'].keys():
                        data['river_name'] = river
            
            if 'Results' in f:
                results = f['Results']
                if 'Unsteady' in results:
                    unsteady = results['Unsteady']
                    if 'Output' in unsteady:
                        output = unsteady['Output']
                        if 'River Rch' in output:
                            for river in output['River Rch'].keys():
                                river_data = output['River Rch'][river]
                                if 'Profile' in river_data:
                                    for profile in river_data['Profile'].keys():
                                        prof = river_data['Profile'][profile]
                                        if 'WS' in prof:
                                            data['WSE'] = float(prof['WS'][0])
                                        if 'Q' in prof:
                                            data['Q_total'] = float(prof['Q'][0])
        
        return data
    
    except Exception as e:
        print(f"Error parsing HDF5 file: {e}")
        return None


def auto_parse_hec_ras(project_folder: str) -> Optional[Dict]:
    """Auto-detect and parse HEC-RAS output from project folder"""
    import os
    from pathlib import Path
    
    folder = Path(project_folder)
    
    # Look for HDF5 file first
    hdf_files = list(folder.glob('*.hdf'))
    if hdf_files:
        return parse_hec_ras_hdf_file(str(hdf_files[0]))
    
    # Look for text output files
    txt_files = list(folder.glob('*.txt')) + list(folder.glob('*.O01'))
    if txt_files:
        with open(txt_files[0], 'r') as f:
            return parse_hec_ras_file(f)
    
    return None