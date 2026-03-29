"""
HEC-RAS Output Parser Module
Auto-extracts data from HEC-RAS project files
Handles HDF5 (.hdf), text (.txt, .out, .O01), and CSV formats
Optimized for ratu.txt Bridge Output table format
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, List
import pandas as pd
import io


def parse_hec_ras_file(uploaded_file) -> Optional[Dict]:
    """
    Parse uploaded HEC-RAS output file (Bridge Output Table)
    Handles the specific ratu.txt format with tab-separated columns
    """
    try:
        file_content = uploaded_file.read()
        filename = uploaded_file.name.lower()
        
        print(f"DEBUG: Parsing file: {filename}")
        print(f"DEBUG: File size: {len(file_content)} bytes")
        
        hec_ras_data = {
            'WSE': None,
            'Q_total': None,
            'Q_bridge': None,
            'velocity_avg': None,
            'velocity_max': None,
            'flow_area': None,
            'top_width': None,
            'q_avg': None,
            'q_max': None,
            'hydraulic_depth': None,
            'EG_US': None,
            'WS_BR_US': None,
            'WS_BR_DS': None,
            'EG_BR_US': None,
            'EG_BR_DS': None,
            'Crit_WS_US': None,
            'Crit_WS_DS': None,
            'Max_Chl_Dpth_US': None,
            'Max_Chl_Dpth_DS': None,
            'Vel_BR_DS': None,
            'Flow_Area_BR_DS': None,
            'Froude_US': None,
            'Froude_DS': None,
            'Specif_Force_US': None,
            'Specif_Force_DS': None,
            'Hydr_Dpth_DS': None,
            'WP_Total_US': None,
            'WP_Total_DS': None,
            'Conv_Total_US': None,
            'Conv_Total_DS': None,
            'Shear_Total_US': None,
            'Shear_Total_DS': None,
            'Power_Total_US': None,
            'Power_Total_DS': None,
            'Delta_EG': None,
            'Delta_WS': None,
            'Frctn_Loss': None,
            'CE_Loss': None,
            'bridge_rs': '-524',
            'us_xs': '-500',
            'ds_xs': '-525',
            'L_bridge': 226.17
        }
        
        text_content = file_content.decode('utf-8', errors='ignore')
        print("DEBUG: === PARSING HEC-RAS TEXT OUTPUT ===")
        
        lines = text_content.split('\n')
        print(f"DEBUG: Total lines: {len(lines)}")
        
        for line_num, line in enumerate(lines):
            if not line.strip():
                continue
            
            line_upper = line.upper()
            all_numbers = re.findall(r'\d+\.\d+', line)
            
            # LEFT COLUMN PARAMETERS - Use INDEPENDENT if statements (NOT elif)
            
            # W.S. US. (m) - CRITICAL! Check this FIRST for WSE
            # FIX: Removed 'ELEV' not in line_upper condition
            if 'W.S. US' in line_upper and '(M)' in line_upper:
                if len(all_numbers) >= 1:
                    hec_ras_data['WSE'] = float(all_numbers[0])
                    print(f"DEBUG Line {line_num}: Found W.S. US = {hec_ras_data['WSE']}")
            
            # E.G. US. (m)
            if 'E.G. US' in line_upper and '(M)' in line_upper and 'ELEV' not in line_upper:
                if len(all_numbers) >= 1:
                    hec_ras_data['EG_US'] = float(all_numbers[0])
                    print(f"DEBUG Line {line_num}: Found E.G. US = {hec_ras_data['EG_US']}")
            
            # Q Total (m3/s)
            if 'Q TOTAL' in line_upper and '(M3/S)' in line_upper:
                if len(all_numbers) >= 1:
                    hec_ras_data['Q_total'] = float(all_numbers[0])
                    hec_ras_data['Q_bridge'] = float(all_numbers[0])
                    print(f"DEBUG Line {line_num}: Found Q Total = {hec_ras_data['Q_total']}")
            
            # Q Bridge (m3/s)
            if 'Q BRIDGE' in line_upper and '(M3/S)' in line_upper:
                if len(all_numbers) >= 1:
                    hec_ras_data['Q_bridge'] = float(all_numbers[0])
                    print(f"DEBUG Line {line_num}: Found Q Bridge = {hec_ras_data['Q_bridge']}")
            
            # Delta EG (m)
            if 'DELTA EG' in line_upper and '(M)' in line_upper:
                if len(all_numbers) >= 1:
                    hec_ras_data['Delta_EG'] = float(all_numbers[0])
                    print(f"DEBUG Line {line_num}: Found Delta EG = {hec_ras_data['Delta_EG']}")
            
            # Delta WS (m)
            if 'DELTA WS' in line_upper and '(M)' in line_upper:
                if len(all_numbers) >= 1:
                    hec_ras_data['Delta_WS'] = float(all_numbers[0])
                    print(f"DEBUG Line {line_num}: Found Delta WS = {hec_ras_data['Delta_WS']}")
            
            # Frctn Loss (m)
            if 'FRCTN LOSS' in line_upper and '(M)' in line_upper:
                for num in reversed(all_numbers):
                    val = float(num)
                    if val < 1.0:
                        hec_ras_data['Frctn_Loss'] = val
                        print(f"DEBUG Line {line_num}: Found Friction Loss = {hec_ras_data['Frctn_Loss']}")
                        break
            
            # C & E Loss (m)
            if 'C & E LOSS' in line_upper and '(M)' in line_upper:
                for num in reversed(all_numbers):
                    val = float(num)
                    if val < 1.0:
                        hec_ras_data['CE_Loss'] = val
                        print(f"DEBUG Line {line_num}: Found C&E Loss = {hec_ras_data['CE_Loss']}")
                        break
            
            # RIGHT COLUMN PARAMETERS - Use INDEPENDENT if statements
            
            # E.G. Elev (m)
            if 'E.G. ELEV' in line_upper and '(M)' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['EG_BR_US'] = float(all_numbers[-2])
                    hec_ras_data['EG_BR_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found E.G. Elev US={hec_ras_data['EG_BR_US']}, DS={hec_ras_data['EG_BR_DS']}")
            
            # W.S. Elev (m)
            if 'W.S. ELEV' in line_upper and '(M)' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['WS_BR_US'] = float(all_numbers[-2])
                    hec_ras_data['WS_BR_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found W.S. Elev US={hec_ras_data['WS_BR_US']}, DS={hec_ras_data['WS_BR_DS']}")
            
            # Crit W.S. (m)
            if 'CRIT W.S.' in line_upper and '(M)' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['Crit_WS_US'] = float(all_numbers[-2])
                    hec_ras_data['Crit_WS_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found Crit W.S. US={hec_ras_data['Crit_WS_US']}, DS={hec_ras_data['Crit_WS_DS']}")
            
            # Max Chl Dpth (m)
            if 'MAX CHL DPTH' in line_upper and '(M)' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['Max_Chl_Dpth_US'] = float(all_numbers[-2])
                    hec_ras_data['Max_Chl_Dpth_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found Max Chl Dpth US={hec_ras_data['Max_Chl_Dpth_US']}, DS={hec_ras_data['Max_Chl_Dpth_DS']}")
            
            # Vel Total (m/s)
            if 'VEL TOTAL' in line_upper and '(M/S)' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['velocity_avg'] = float(all_numbers[-2])
                    hec_ras_data['Vel_BR_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found Velocity US={hec_ras_data['velocity_avg']}, DS={hec_ras_data['Vel_BR_DS']}")
            
           # Flow Area (m2)
            if 'FLOW AREA' in line_upper and '(M2)' in line_upper:
                if len(all_numbers) >= 2:
                    # Extract US and DS values
                    # For lines like: "Flow Area (m2)	204.15 	143.80"
                    # all_numbers[0] = 204.15 (US)
                    # all_numbers[1] = 143.80 (DS)
                    hec_ras_data['flow_area'] = float(all_numbers[0])
                    hec_ras_data['Flow_Area_BR_DS'] = float(all_numbers[1])
                    print(f"DEBUG Line {line_num}: Found Flow Area US={hec_ras_data['flow_area']}, DS={hec_ras_data['Flow_Area_BR_DS']}")
            
            # Froude # Chl
            if 'FROUDE' in line_upper and 'CHL' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['Froude_US'] = float(all_numbers[-2])
                    hec_ras_data['Froude_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found Froude US={hec_ras_data['Froude_US']}, DS={hec_ras_data['Froude_DS']}")
            
            # Specif Force (m3)
            if 'SPECIF FORCE' in line_upper and '(M3)' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['Specif_Force_US'] = float(all_numbers[-2])
                    hec_ras_data['Specif_Force_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found Specific Force US={hec_ras_data['Specif_Force_US']}, DS={hec_ras_data['Specif_Force_DS']}")
            
            # Hydr Depth (m)
            if 'HYDR DEPTH' in line_upper and '(M)' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['hydraulic_depth'] = float(all_numbers[-2])
                    hec_ras_data['Hydr_Dpth_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found Hydr Depth US={hec_ras_data['hydraulic_depth']}, DS={hec_ras_data['Hydr_Dpth_DS']}")
            
            # W.P. Total (m)
            if 'W.P. TOTAL' in line_upper and '(M)' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['WP_Total_US'] = float(all_numbers[-2])
                    hec_ras_data['WP_Total_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found W.P. Total US={hec_ras_data['WP_Total_US']}, DS={hec_ras_data['WP_Total_DS']}")
            
            # Conv. Total (m3/s)
            if 'CONV. TOTAL' in line_upper and '(M3/S)' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['Conv_Total_US'] = float(all_numbers[-2])
                    hec_ras_data['Conv_Total_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found Conveyance US={hec_ras_data['Conv_Total_US']}, DS={hec_ras_data['Conv_Total_DS']}")
            
            # Shear Total (N/m2)
            if 'SHEAR TOTAL' in line_upper and '(N/M2)' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['Shear_Total_US'] = float(all_numbers[-2])
                    hec_ras_data['Shear_Total_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found Shear US={hec_ras_data['Shear_Total_US']}, DS={hec_ras_data['Shear_Total_DS']}")
            
            # Power Total (N/m s)
            if 'POWER TOTAL' in line_upper and '(N/M' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['Power_Total_US'] = float(all_numbers[-2])
                    hec_ras_data['Power_Total_DS'] = float(all_numbers[-1])
                    print(f"DEBUG Line {line_num}: Found Power US={hec_ras_data['Power_Total_US']}, DS={hec_ras_data['Power_Total_DS']}")
            
            # Top Width (m)
            if 'TOP WIDTH' in line_upper and '(M)' in line_upper:
                if len(all_numbers) >= 2:
                    hec_ras_data['top_width'] = float(all_numbers[-2])
                    print(f"DEBUG Line {line_num}: Found Top Width = {hec_ras_data['top_width']}")
        
        # Calculate discharge intensity
        if hec_ras_data['Q_bridge'] and hec_ras_data['top_width']:
            hec_ras_data['q_avg'] = hec_ras_data['Q_bridge'] / hec_ras_data['top_width']
            hec_ras_data['q_max'] = hec_ras_data['q_avg'] * 1.4
            print(f"DEBUG: Calculated q_avg = {hec_ras_data['q_avg']:.3f} m²/s")
            print(f"DEBUG: Calculated q_max = {hec_ras_data['q_max']:.3f} m²/s")
        
        # Validate
        if hec_ras_data['WSE'] and hec_ras_data['Q_bridge']:
            print(f"DEBUG: ✅✅✅ TEXT FILE PARSING SUCCESSFUL! ✅✅✅")
            print(f"DEBUG: Extracted {sum(1 for v in hec_ras_data.values() if v is not None)} parameters")
            print(f"DEBUG: Key values:")
            print(f"DEBUG:   WSE = {hec_ras_data['WSE']}")
            print(f"DEBUG:   Q_bridge = {hec_ras_data['Q_bridge']}")
            print(f"DEBUG:   Top Width = {hec_ras_data['top_width']}")
            print(f"DEBUG:   Velocity US = {hec_ras_data['velocity_avg']}")
            print(f"DEBUG:   Velocity DS = {hec_ras_data['Vel_BR_DS']}")
            print(f"DEBUG:   Max Chl Dpth US = {hec_ras_data['Max_Chl_Dpth_US']}")
            print(f"DEBUG:   Max Chl Dpth DS = {hec_ras_data['Max_Chl_Dpth_DS']}")
            return hec_ras_data
        else:
            print(f"DEBUG: ❌❌❌ TEXT FILE PARSING FAILED ❌❌❌")
            print(f"DEBUG: Missing required values:")
            print(f"DEBUG:   WSE = {hec_ras_data['WSE']}")
            print(f"DEBUG:   Q_bridge = {hec_ras_data['Q_bridge']}")
            print(f"DEBUG:   Top Width = {hec_ras_data['top_width']}")
            print(f"DEBUG: Total lines processed: {len(lines)}")
            return None
            
    except Exception as e:
        print(f"ERROR: Exception in parse_hec_ras_file: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_hec_ras_directory(project_folder_path: str) -> Optional[Dict]:
    """Read HEC-RAS project directory and extract data from output files"""
    try:
        project_path = Path(project_folder_path)
        
        if not project_path.exists():
            print(f"ERROR: Path does not exist: {project_folder_path}")
            return None
        
        out_files = list(project_path.glob('*.O*')) + list(project_path.glob('*.out')) + list(project_path.glob('*.txt'))
        
        if not out_files:
            print(f"ERROR: No HEC-RAS output files found in {project_folder_path}")
            return None
        
        print(f"DEBUG: Found output files: {[f.name for f in out_files]}")
        
        out_file = out_files[0]
        
        with open(out_file, 'rb') as f:
            file_content = f.read()
        
        class MockFile:
            def __init__(self, content, name):
                self.content = content
                self.name = name
            def read(self):
                return self.content
        
        mock_file = MockFile(file_content, out_file.name)
        result = parse_hec_ras_file(mock_file)
        
        if result:
            print(f"DEBUG: ✅ Directory parsing successful!")
            return result
        else:
            print(f"DEBUG: ❌ Directory parsing failed")
            return None
            
    except Exception as e:
        print(f"ERROR: Exception in parse_hec_ras_directory: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_hec_ras_hdf_file(hdf_path: str) -> Optional[Dict]:
    """Parse HEC-RAS HDF5 file using HECRASHDFParser class"""
    try:
        from src.hec_ras_hdf_parser import HECRASHDFParser
        
        print(f"DEBUG: Attempting HDF5 parsing: {hdf_path}")
        
        parser = HECRASHDFParser(hdf_path)
        
        if not parser.open():
            print("DEBUG: Failed to open HDF5 file")
            return None
        
        try:
            result = parser.extract_all_data()
            
            if result and result.get('success'):
                print(f"DEBUG: ✅ HDF5 parsing successful!")
                print(f"DEBUG:   WSE = {result.get('WSE')}")
                print(f"DEBUG:   Q_bridge = {result.get('Q_bridge')}")
                print(f"DEBUG:   top_width = {result.get('top_width')}")
                return result
            else:
                print("DEBUG: ❌ HDF5 parsing failed")
                return None
                
        except Exception as e:
            print(f"DEBUG: Error during extraction: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            parser.close()
            
    except Exception as e:
        print(f"ERROR: HDF5 parsing exception: {e}")
        import traceback
        traceback.print_exc()
        return None


def auto_parse_hec_ras(project_folder: str) -> Optional[Dict]:
    """Auto-detect and parse HEC-RAS output using best available method"""
    project_path = Path(project_folder)
    
    if not project_path.exists():
        print(f"ERROR: Project folder not found: {project_folder}")
        return None
    
    print(f"DEBUG: Auto-detecting HEC-RAS output in {project_folder}")
    
    txt_files = list(project_path.glob('*.O??')) + list(project_path.glob('*.out')) + list(project_path.glob('*.txt'))
    
    if txt_files:
        print(f"DEBUG: Found text output: {txt_files[0].name}")
        with open(txt_files[0], 'rb') as f:
            file_content = f.read()
        
        class MockFile:
            def __init__(self, content, name):
                self.content = content
                self.name = name
            def read(self):
                return self.content
        
        mock_file = MockFile(file_content, txt_files[0].name)
        result = parse_hec_ras_file(mock_file)
        if result:
            return result
    
    hdf_files = list(project_path.glob('*.p??.hdf')) + list(project_path.glob('*.P??.HDF'))
    
    if hdf_files:
        print(f"DEBUG: Found HDF5 file: {hdf_files[0].name}")
        result = parse_hec_ras_hdf_file(str(hdf_files[0]))
        if result:
            return result
    
    csv_files = list(project_path.glob('*.csv'))
    
    if csv_files:
        print(f"DEBUG: Found CSV file: {csv_files[0].name}")
        with open(csv_files[0], 'rb') as f:
            file_content = f.read()
        
        class MockFile:
            def __init__(self, content, name):
                self.content = content
                self.name = name
            def read(self):
                return self.content
        
        mock_file = MockFile(file_content, csv_files[0].name)
        result = parse_hec_ras_file(mock_file)
        if result:
            return result
    
    print("ERROR: No HEC-RAS output files found")
    return None