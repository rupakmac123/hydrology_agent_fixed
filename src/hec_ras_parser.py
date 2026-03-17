"""
HEC-RAS Output Parser Module
Auto-extracts data from HEC-RAS project files
Handles HDF5 (.hdf), text (.txt, .out, .O01), and CSV formats
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, List
import pandas as pd
import io


# ═══════════════════════════════════════════════════════════════
# TEXT/CSV PARSING FUNCTIONS (Existing functionality)
# ═══════════════════════════════════════════════════════════════

def parse_hec_ras_file(uploaded_file) -> Optional[Dict]:
    """
    Parse uploaded HEC-RAS output file
    Handles .txt, .out, .O01, .csv formats
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
            'hydraulic_depth': None
        }
        
        # ─────────────────────────────────────────────────────────────
        # Try CSV format first
        # ─────────────────────────────────────────────────────────────
        if filename.endswith('.csv'):
            try:
                text_content = file_content.decode('utf-8', errors='ignore')
                df = pd.read_csv(io.StringIO(text_content))
                
                column_mapping = {
                    'q_avg': ['q_avg', 'avg_discharge_intensity', 'average q'],
                    'q_max': ['q_max', 'max_discharge_intensity', 'maximum q'],
                    'WSE': ['wse', 'water_surface_elevation', 'hfl', 'water level'],
                    'Q_total': ['q_total', 'total discharge'],
                    'Q_bridge': ['q_bridge', 'bridge discharge'],
                    'velocity_avg': ['velocity_avg', 'avg_velocity'],
                    'top_width': ['width', 'channel_width', 'top width'],
                    'flow_area': ['area', 'flow_area', 'flow area']
                }
                
                for key, possible_names in column_mapping.items():
                    for col_name in df.columns:
                        col_lower = col_name.lower().strip()
                        for possible_name in possible_names:
                            if possible_name in col_lower:
                                hec_ras_data[key] = float(df[col_name].iloc[0])
                                print(f"DEBUG: Found {key} = {hec_ras_data[key]}")
                                break
                
                if hec_ras_data['WSE'] and hec_ras_data['q_avg']:
                    return hec_ras_data
                    
            except Exception as e:
                print(f"DEBUG: CSV parsing failed: {e}")
        
        # ─────────────────────────────────────────────────────────────
        # Try text format (.txt, .out, .O01)
        # ─────────────────────────────────────────────────────────────
        else:
            # Decode with error handling
            text_content = file_content.decode('utf-8', errors='ignore')
            
            # Clean binary garbage - keep lines with >50% printable ASCII
            clean_lines = []
            for line in text_content.split('\n'):
                printable_chars = sum(1 for c in line if 32 <= ord(c) <= 126 or c in '\t\n\r')
                if len(line) > 0 and printable_chars / max(len(line), 1) > 0.5:
                    clean_lines.append(line.strip())
            
            print(f"DEBUG: Cleaned {len(clean_lines)} readable lines")
            
            # Show first 50 clean lines for debugging
            print("DEBUG: === FIRST 50 CLEAN LINES ===")
            for i, line in enumerate(clean_lines[:50]):
                print(f"DEBUG Line {i}: [{line}]")
            print("DEBUG: === END OF CLEAN LINES ===")
            
            # Parse each line
            for line in clean_lines:
                if not line.strip():
                    continue
                
                line_upper = line.upper()
                
                # ─────────────────────────────────────────────────────────────
                # Extract Water Surface Elevation (WSE/HFL)
                # ─────────────────────────────────────────────────────────────
                if hec_ras_data['WSE'] is None:
                    if 'W.S.' in line or 'WATER SURFACE' in line_upper or 'HFL' in line_upper:
                        numbers = re.findall(r'\d+\.\d+', line)
                        for num in numbers:
                            try:
                                val = float(num)
                                # Reasonable elevation range for Nepal (100-1000m)
                                if 100 < val < 1000:
                                    hec_ras_data['WSE'] = val
                                    print(f"DEBUG: Found WSE = {val}")
                                    break
                            except:
                                pass
                
                # ─────────────────────────────────────────────────────────────
                # Extract Total Discharge
                # ─────────────────────────────────────────────────────────────
                if hec_ras_data['Q_total'] is None:
                    if 'Q TOTAL' in line_upper or 'TOTAL (M3/S)' in line_upper:
                        numbers = re.findall(r'\d+\.\d+', line)
                        if numbers:
                            try:
                                val = float(numbers[0])
                                if val > 0:
                                    hec_ras_data['Q_total'] = val
                                    print(f"DEBUG: Found Q_total = {val}")
                            except:
                                pass
                
                # ─────────────────────────────────────────────────────────────
                # Extract Bridge Discharge
                # ─────────────────────────────────────────────────────────────
                if hec_ras_data['Q_bridge'] is None:
                    if 'Q BRIDGE' in line_upper or 'BRIDGE (M3/S)' in line_upper:
                        numbers = re.findall(r'\d+\.\d+', line)
                        if numbers:
                            try:
                                val = float(numbers[0])
                                if val > 0:
                                    hec_ras_data['Q_bridge'] = val
                                    print(f"DEBUG: Found Q_bridge = {val}")
                            except:
                                pass
                
                # ─────────────────────────────────────────────────────────────
                # Extract Top Width - LOOK FOR NUMBERS AFTER "TOP WIDTH" TEXT
                # ─────────────────────────────────────────────────────────────
                if hec_ras_data['top_width'] is None:
                    if 'TOP WIDTH' in line_upper:
                        # Find position of "TOP WIDTH" and extract numbers after it
                        idx = line_upper.find('TOP WIDTH')
                        if idx != -1:
                            # Get the part of line after "TOP WIDTH"
                            after_text = line[idx:]
                            numbers = re.findall(r'\d+\.\d+', after_text)
                            if numbers:
                                try:
                                    val = float(numbers[0])
                                    # Top width typically 50-500m for bridges
                                    if 50 < val < 500:
                                        hec_ras_data['top_width'] = val
                                        print(f"DEBUG: Found top_width = {val}")
                                except:
                                    pass
                
                # ─────────────────────────────────────────────────────────────
                # Extract Velocity
                # ─────────────────────────────────────────────────────────────
                if hec_ras_data['velocity_avg'] is None:
                    if 'VEL' in line_upper and 'M/S' in line_upper:
                        numbers = re.findall(r'\d+\.\d+', line)
                        if numbers:
                            try:
                                val = float(numbers[0])
                                if 0 < val < 20:
                                    hec_ras_data['velocity_avg'] = val
                                    print(f"DEBUG: Found velocity = {val}")
                            except:
                                pass
                
                # ─────────────────────────────────────────────────────────────
                # Extract Flow Area
                # ─────────────────────────────────────────────────────────────
                if hec_ras_data['flow_area'] is None:
                    if 'FLOW AREA' in line_upper or 'AREA (M2)' in line_upper:
                        numbers = re.findall(r'\d+\.\d+', line)
                        if numbers:
                            try:
                                val = float(numbers[0])
                                if val > 0:
                                    hec_ras_data['flow_area'] = val
                                    print(f"DEBUG: Found flow_area = {val}")
                            except:
                                pass
                
                # ─────────────────────────────────────────────────────────────
                # Extract Hydraulic Depth
                # ─────────────────────────────────────────────────────────────
                if hec_ras_data['hydraulic_depth'] is None:
                    if 'HYDR DEPTH' in line_upper or 'HYDRAULIC DEPTH' in line_upper:
                        numbers = re.findall(r'\d+\.\d+', line)
                        if numbers:
                            try:
                                val = float(numbers[0])
                                if 0 < val < 50:
                                    hec_ras_data['hydraulic_depth'] = val
                                    print(f"DEBUG: Found hydraulic_depth = {val}")
                            except:
                                pass
        
        # ─────────────────────────────────────────────────────────────
        # Calculate discharge intensity if we have Q and width
        # ─────────────────────────────────────────────────────────────
        if hec_ras_data['Q_bridge'] and hec_ras_data['top_width']:
            hec_ras_data['q_avg'] = hec_ras_data['Q_bridge'] / hec_ras_data['top_width']
            hec_ras_data['q_max'] = hec_ras_data['q_avg'] * 1.4
            print(f"DEBUG: Calculated q_avg = {hec_ras_data['q_avg']:.3f} m²/s")
            print(f"DEBUG: Calculated q_max = {hec_ras_data['q_max']:.3f} m²/s")
        
        # ─────────────────────────────────────────────────────────────
        # Validate - need at least WSE and one discharge value
        # ─────────────────────────────────────────────────────────────
        if hec_ras_data['WSE'] is not None and (hec_ras_data['Q_bridge'] or hec_ras_data['q_avg']):
            print(f"DEBUG: ✅✅✅ PARSING SUCCESSFUL! ✅✅✅")
            print(f"DEBUG: Extracted values:")
            print(f"DEBUG:   WSE = {hec_ras_data['WSE']} m")
            print(f"DEBUG:   Q_bridge = {hec_ras_data['Q_bridge']} m³/s")
            print(f"DEBUG:   top_width = {hec_ras_data['top_width']} m")
            print(f"DEBUG:   q_avg = {hec_ras_data['q_avg']} m²/s")
            return hec_ras_data
        else:
            print(f"DEBUG: ❌❌❌ PARSING FAILED ❌❌❌")
            print(f"DEBUG: Missing required values:")
            print(f"DEBUG:   WSE = {hec_ras_data['WSE']}")
            print(f"DEBUG:   Q_bridge = {hec_ras_data['Q_bridge']}")
            print(f"DEBUG:   top_width = {hec_ras_data['top_width']}")
            print(f"DEBUG:   q_avg = {hec_ras_data['q_avg']}")
            return None
            
    except Exception as e:
        print(f"ERROR: Exception in parse_hec_ras_file: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_hec_ras_directory(project_folder_path: str) -> Optional[Dict]:
    """
    Read HEC-RAS project directory and extract data from output files
    """
    try:
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
            'hydraulic_depth': None
        }
        
        project_path = Path(project_folder_path)
        
        if not project_path.exists():
            print(f"ERROR: Path does not exist: {project_folder_path}")
            return None
        
        # Find output files (.txt, .out, .O##)
        out_files = list(project_path.glob('*.O*')) + list(project_path.glob('*.out')) + list(project_path.glob('*.txt'))
        
        if not out_files:
            print(f"ERROR: No HEC-RAS output files found in {project_folder_path}")
            return None
        
        print(f"DEBUG: Found output files: {[f.name for f in out_files]}")
        
        # Use first output file
        out_file = out_files[0]
        
        with open(out_file, 'rb') as f:
            file_content = f.read()
        
        # Decode with error handling
        text_content = file_content.decode('utf-8', errors='ignore')
        
        # Clean binary garbage
        clean_lines = []
        for line in text_content.split('\n'):
            printable_chars = sum(1 for c in line if 32 <= ord(c) <= 126 or c in '\t\n\r')
            if len(line) > 0 and printable_chars / max(len(line), 1) > 0.5:
                clean_lines.append(line.strip())
        
        print(f"DEBUG: Processing {len(clean_lines)} readable lines from {out_file.name}")
        
        # Parse each line
        for line in clean_lines:
            if not line.strip():
                continue
            
            line_upper = line.upper()
            
            # Extract WSE
            if hec_ras_data['WSE'] is None:
                if 'W.S.' in line or 'WATER SURFACE' in line_upper or 'HFL' in line_upper:
                    numbers = re.findall(r'\d+\.\d+', line)
                    for num in numbers:
                        try:
                            val = float(num)
                            if 100 < val < 1000:
                                hec_ras_data['WSE'] = val
                                break
                        except:
                            pass
            
            # Extract Q_bridge
            if hec_ras_data['Q_bridge'] is None:
                if 'Q BRIDGE' in line_upper or 'BRIDGE (M3/S)' in line_upper:
                    numbers = re.findall(r'\d+\.\d+', line)
                    if numbers:
                        try:
                            val = float(numbers[0])
                            if val > 0:
                                hec_ras_data['Q_bridge'] = val
                        except:
                            pass
            
            # Extract Top Width - LOOK FOR NUMBERS AFTER "TOP WIDTH" TEXT
            if hec_ras_data['top_width'] is None:
                if 'TOP WIDTH' in line_upper:
                    idx = line_upper.find('TOP WIDTH')
                    if idx != -1:
                        after_text = line[idx:]
                        numbers = re.findall(r'\d+\.\d+', after_text)
                        if numbers:
                            try:
                                val = float(numbers[0])
                                if 50 < val < 500:
                                    hec_ras_data['top_width'] = val
                            except:
                                pass
            
            # Extract Velocity
            if hec_ras_data['velocity_avg'] is None:
                if 'VEL' in line_upper and 'M/S' in line_upper:
                    numbers = re.findall(r'\d+\.\d+', line)
                    if numbers:
                        try:
                            val = float(numbers[0])
                            if 0 < val < 20:
                                hec_ras_data['velocity_avg'] = val
                        except:
                            pass
            
            # Extract Flow Area
            if hec_ras_data['flow_area'] is None:
                if 'FLOW AREA' in line_upper or 'AREA (M2)' in line_upper:
                    numbers = re.findall(r'\d+\.\d+', line)
                    if numbers:
                        try:
                            val = float(numbers[0])
                            if val > 0:
                                hec_ras_data['flow_area'] = val
                        except:
                            pass
        
        # Calculate discharge intensity
        if hec_ras_data['Q_bridge'] and hec_ras_data['top_width']:
            hec_ras_data['q_avg'] = hec_ras_data['Q_bridge'] / hec_ras_data['top_width']
            hec_ras_data['q_max'] = hec_ras_data['q_avg'] * 1.4
        
        if hec_ras_data['WSE'] and hec_ras_data['q_avg']:
            print(f"DEBUG: ✅ Directory parsing successful!")
            return hec_ras_data
        else:
            print(f"DEBUG: ❌ Directory parsing failed - missing values")
            return None
            
    except Exception as e:
        print(f"ERROR: Exception in parse_hec_ras_directory: {e}")
        import traceback
        traceback.print_exc()
        return None


# ═══════════════════════════════════════════════════════════════
# HDF5 PARSING FUNCTIONS (NEW - Add these to existing file)
# ═══════════════════════════════════════════════════════════════

def parse_hec_ras_hdf_file(hdf_path: str) -> Optional[Dict]:
    """
    Parse HEC-RAS HDF5 file using HECRASHDFParser class
    
    Args:
        hdf_path: Path to HDF5 file
        
    Returns:
        Dictionary with extracted data or None
    """
    try:
        from src.hec_ras_hdf_parser import HECRASHDFParser, find_hdf_files
        
        print(f"DEBUG: Attempting HDF5 parsing: {hdf_path}")
        
        parser = HECRASHDFParser(hdf_path)
        
        if not parser.open():
            print("DEBUG: Failed to open HDF5 file")
            return None
        
        try:
            result = parser.extract_all_data()
            
            if result['success']:
                print(f"DEBUG: ✅ HDF5 parsing successful!")
                print(f"DEBUG:   WSE = {result['WSE']}")
                print(f"DEBUG:   Q_bridge = {result['Q_bridge']}")
                print(f"DEBUG:   top_width = {result['top_width']}")
                print(f"DEBUG:   q_avg = {result['q_avg']}")
                return result
            else:
                print("DEBUG: ❌ HDF5 parsing failed - no bridge data found")
                return None
                
        finally:
            parser.close()
            
    except Exception as e:
        print(f"ERROR: HDF5 parsing exception: {e}")
        import traceback
        traceback.print_exc()
        return None


def auto_parse_hec_ras(project_folder: str) -> Optional[Dict]:
    """
    Auto-detect and parse HEC-RAS output using best available method
    
    Priority: HDF5 → Text Output → CSV
    
    Args:
        project_folder: Path to HEC-RAS project folder
        
    Returns:
        Dictionary with extracted data or None
    """
    project_path = Path(project_folder)
    
    if not project_path.exists():
        print(f"ERROR: Project folder not found: {project_folder}")
        return None
    
    print(f"DEBUG: Auto-detecting HEC-RAS output in {project_folder}")
    
    # Priority 1: Try HDF5 files
    hdf_files = list(project_path.glob('*.p??.hdf')) + \
                list(project_path.glob('*.P??.HDF'))
    
    if hdf_files:
        print(f"DEBUG: Found HDF5 file: {hdf_files[0].name}")
        result = parse_hec_ras_hdf_file(str(hdf_files[0]))
        if result:
            return result
    
    # Priority 2: Try text output files (.O01, .out, .txt)
    txt_files = list(project_path.glob('*.O??')) + \
                list(project_path.glob('*.out')) + \
                list(project_path.glob('*.txt'))
    
    if txt_files:
        print(f"DEBUG: Found text output: {txt_files[0].name}")
        # Use existing text parsing function
        with open(txt_files[0], 'rb') as f:
            file_content = f.read()
        
        # Create a mock uploaded file object
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
    
    # Priority 3: Try CSV files
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