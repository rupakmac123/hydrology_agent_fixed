"""
HEC-RAS Output Parser Module
Parses HEC-RAS output files (.txt) for bridge hydraulic analysis
Handles two-column tab-separated format from Aurahi/Ratu HEC-RAS output
"""

from typing import Dict, Optional


def parse_hec_ras_file(file) -> Dict:
    """
    Parse HEC-RAS output file (.txt format)
    Handles two-column tab-separated format
    
    LEFT COLUMN: Global Parameter | Value
    RIGHT COLUMN: Bridge Element | Inside BR US | Inside BR DS
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

        print(f"DEBUG: Parsing HEC-RAS file with {len(lines)} lines")

        # Parse each line - handle BOTH left and right columns
        for i, line in enumerate(lines):
            if not line.strip():
                continue

            # Split by TAB
            parts = line.split('\t')
            
            # Debug first few lines
            if i < 5:
                print(f"DEBUG Line {i}: {line[:100]}")
                print(f"DEBUG Parts count: {len(parts)}")
                for j, part in enumerate(parts):
                    print(f"  Part {j}: '{part.strip()}'")

            # === LEFT COLUMN PARSING (parts[0] and parts[1]) ===
            if len(parts) >= 2:
                left_param = parts[0].strip()
                left_value_str = parts[1].strip()
                
                # Extract numeric value from left column
                import re
                left_numbers = re.findall(r"[-+]?\d*\.\d+|\d+", left_value_str)
                left_value = float(left_numbers[0]) if left_numbers else None
                
                if left_value is not None:
                    if 'E.G. US.' in left_param or 'EG US' in left_param:
                        data['EG_US'] = left_value
                        print(f"✅ LEFT: EG_US = {left_value}")
                    elif 'W.S. US.' in left_param or 'WS US' in left_param:
                        data['WSE'] = left_value
                        print(f"✅ LEFT: WSE = {left_value}")
                    elif 'Q Total' in left_param:
                        data['Q_total'] = left_value
                        print(f"✅ LEFT: Q_total = {left_value}")
                    elif 'Q Bridge' in left_param:
                        data['Q_bridge'] = left_value
                        print(f"✅ LEFT: Q_bridge = {left_value}")
                    elif 'Delta EG' in left_param:
                        data['Delta_EG'] = left_value
                        print(f"✅ LEFT: Delta_EG = {left_value}")
                    elif 'Delta WS' in left_param:
                        data['Delta_WS'] = left_value
                        print(f"✅ LEFT: Delta_WS = {left_value}")
                    elif 'Min El Weir' in left_param:
                        data['Min_El_Weir'] = left_value
                    elif 'Min El Prs' in left_param:
                        data['Min_El_Prs'] = left_value
                    elif 'BR Open Area' in left_param:
                        data['BR_Open_Area'] = left_value
                    elif 'BR Open Vel' in left_param:
                        data['BR_Open_Vel'] = left_value

            # === RIGHT COLUMN PARSING (parts[2], parts[3], parts[4]) ===
            if len(parts) >= 4:
                right_param = parts[2].strip()
                right_us_str = parts[3].strip() if len(parts) > 3 else ''
                right_ds_str = parts[4].strip() if len(parts) > 4 else ''
                
                # Extract numeric values from right column
                import re
                us_numbers = re.findall(r"[-+]?\d*\.\d+|\d+", right_us_str)
                ds_numbers = re.findall(r"[-+]?\d*\.\d+|\d+", right_ds_str)
                
                us_value = float(us_numbers[0]) if us_numbers else None
                ds_value = float(ds_numbers[0]) if ds_numbers else None
                
                # CRITICAL: Save with keys that report_generator.py expects!
                if right_param and (us_value is not None or ds_value is not None):
                    if 'E.G. Elev' in right_param:
                        data['EG_BR_US'] = us_value
                        data['EG_BR_DS'] = ds_value
                        print(f"✅ RIGHT: EG_BR_US={us_value}, EG_BR_DS={ds_value}")
                    elif 'W.S. Elev' in right_param:
                        data['WS_BR_US'] = us_value
                        data['WS_BR_DS'] = ds_value
                        print(f"✅ RIGHT: WS_BR_US={us_value}, WS_BR_DS={ds_value}")
                    elif 'Max Chl Dpth' in right_param:
                        data['Max_Chl_Dpth_US'] = us_value
                        data['Max_Chl_Dpth_DS'] = ds_value
                        print(f"✅ RIGHT: Max_Chl_Dpth_US={us_value}, Max_Chl_Dpth_DS={ds_value}")
                    elif 'Vel Total' in right_param:
                        data['Vel_BR_US'] = us_value
                        data['Vel_BR_DS'] = ds_value
                        # ALSO save as velocity_avg for Section 4.2/5.2
                        if us_value is not None:
                            data['velocity_avg'] = us_value
                        print(f"✅ RIGHT: Vel_BR_US={us_value}, Vel_BR_DS={ds_value}, velocity_avg={us_value}")
                    elif 'Flow Area' in right_param:
                        data['flow_area_us'] = us_value
                        data['flow_area_ds'] = ds_value
                        # ALSO save as flow_area for Section 4.2/5.2
                        if us_value is not None:
                            data['flow_area'] = us_value
                        print(f"✅ RIGHT: flow_area_us={us_value}, flow_area_ds={ds_value}, flow_area={us_value}")
                    elif 'Hydr Depth' in right_param:
                        data['Hydr_Dpth_US'] = us_value
                        data['Hydr_Dpth_DS'] = ds_value
                        # ALSO save as hydraulic_depth for Section 4.2/5.2
                        if us_value is not None:
                            data['hydraulic_depth'] = us_value
                        print(f"✅ RIGHT: Hydr_Dpth_US={us_value}, Hydr_Dpth_DS={ds_value}, hydraulic_depth={us_value}")
                    elif 'Froude' in right_param:
                        data['Froude_US'] = us_value
                        data['Froude_DS'] = ds_value
                        print(f"✅ RIGHT: Froude_US={us_value}, Froude_DS={ds_value}")
                    elif 'W.P. Total' in right_param or 'Wetted Perimeter' in right_param:
                        data['WP_Total_US'] = us_value
                        data['WP_Total_DS'] = ds_value
                    elif 'Conv. Total' in right_param or 'Conveyance' in right_param:
                        data['Conv_Total_US'] = us_value
                        data['Conv_Total_DS'] = ds_value
                    elif 'Frctn Loss' in right_param or 'Friction Loss' in right_param:
                        data['Frctn_Loss'] = us_value
                        print(f"✅ RIGHT: Frctn_Loss={us_value}")
                    elif 'C & E Loss' in right_param or 'CE Loss' in right_param:
                        data['CE_Loss'] = us_value
                        print(f"✅ RIGHT: CE_Loss={us_value}")
                    elif 'Shear Total' in right_param:
                        data['Shear_Total_US'] = us_value
                        data['Shear_Total_DS'] = ds_value
                    elif 'Power Total' in right_param:
                        data['Power_Total_US'] = us_value
                        data['Power_Total_DS'] = ds_value
                    elif 'Top Width' in right_param:
                        data['top_width_us'] = us_value
                        data['top_width_ds'] = ds_value
                        # ALSO save as top_width for Section 4.2/5.2
                        if us_value is not None:
                            data['top_width'] = us_value
                        print(f"✅ RIGHT: top_width_us={us_value}, top_width_ds={ds_value}, top_width={us_value}")

        # Calculate q_avg and q_max
        if data.get('Q_bridge') and data.get('top_width') and data.get('top_width') > 0:
            q_avg = data['Q_bridge'] / data['top_width']
            data['q_avg'] = round(q_avg, 3)
            data['q_max'] = round(q_avg * 1.4, 3)
            print(f"✅ Calculated q_avg={data['q_avg']}, q_max={data['q_max']}")

        print(f"\nDEBUG: === PARSED DATA SUMMARY ===")
        print(f"DEBUG: Parsed data keys: {list(data.keys())}")
        print(f"DEBUG: WSE={data.get('WSE')}, Q_bridge={data.get('Q_bridge')}")
        print(f"DEBUG: flow_area={data.get('flow_area')}, flow_area_us={data.get('flow_area_us')}, flow_area_ds={data.get('flow_area_ds')}")
        print(f"DEBUG: top_width={data.get('top_width')}, top_width_us={data.get('top_width_us')}")
        print(f"DEBUG: velocity_avg={data.get('velocity_avg')}, Vel_BR_US={data.get('Vel_BR_US')}, Vel_BR_DS={data.get('Vel_BR_DS')}")
        print(f"DEBUG: hydraulic_depth={data.get('hydraulic_depth')}, Hydr_Dpth_US={data.get('Hydr_Dpth_US')}, Hydr_Dpth_DS={data.get('Hydr_Dpth_DS')}")
        print(f"DEBUG: Frctn_Loss={data.get('Frctn_Loss')}, CE_Loss={data.get('CE_Loss')}")
        print(f"==============================\n")

        return data

    except Exception as e:
        print(f"ERROR parsing HEC-RAS file: {e}")
        import traceback
        traceback.print_exc()
        return {}


def parse_hec_ras_hdf_file(file_path: str) -> Optional[Dict]:
    """Parse HEC-RAS HDF5 output file"""
    try:
        import h5py
        data = {}
        
        with h5py.File(file_path, 'r') as f:
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
        
        print(f"DEBUG: HDF5 parsed successfully, keys: {list(data.keys())}")
        return data
    
    except Exception as e:
        print(f"ERROR parsing HDF5 file: {e}")
        import traceback
        traceback.print_exc()
        return None


def auto_parse_hec_ras(project_folder: str) -> Optional[Dict]:
    """Auto-detect and parse HEC-RAS output from project folder"""
    import os
    from pathlib import Path
    
    folder = Path(project_folder)
    
    print(f"DEBUG: Auto-parsing HEC-RAS from folder: {folder}")
    
    # Look for HDF5 file first
    hdf_files = list(folder.glob('*.hdf'))
    if hdf_files:
        print(f"DEBUG: Found HDF5 file: {hdf_files[0]}")
        return parse_hec_ras_hdf_file(str(hdf_files[0]))
    
    # Look for text output files
    txt_files = list(folder.glob('*.txt')) + list(folder.glob('*.O01'))
    if txt_files:
        print(f"DEBUG: Found text file: {txt_files[0]}")
        with open(txt_files[0], 'r') as f:
            return parse_hec_ras_file(f)
    
    print(f"DEBUG: No HEC-RAS files found in {folder}")
    return None