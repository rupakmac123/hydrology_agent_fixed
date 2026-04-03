"""
HEC-RAS to Excel Converter Module
Converts HEC-RAS .txt output to structured Excel format
Based on proven working code
"""

import pandas as pd
import os
from typing import Dict, Optional


def parse_hecras_to_excel(file_path: str, output_path: str = None) -> pd.DataFrame:
    """
    Convert HEC-RAS .txt output to Excel format
    """
    if output_path is None:
        output_path = os.path.splitext(file_path)[0] + "_Table_Output.xlsx"
    
    global_list = []
    bridge_list = []
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip('\n')
            if line.startswith("Plan:"):
                continue
            
            parts = [p.strip() for p in line.split('\t')]
            
            if len(parts) >= 2 and parts[0]:
                global_list.append({"Global Parameter": parts[0], "Value": parts[1]})
            
            if len(parts) >= 3 and parts[2] and "Element" not in parts[2]:
                bridge_list.append({
                    "Bridge Element": parts[2],
                    "Inside BR US": parts[3] if len(parts) > 3 else "",
                    "Inside BR DS": parts[4] if len(parts) > 4 else ""
                })
    
    max_rows = max(len(global_list), len(bridge_list))
    final_table = []
    
    for i in range(max_rows):
        row = {}
        if i < len(global_list):
            row.update(global_list[i])
        else:
            row.update({"Global Parameter": "", "Value": ""})
        
        if i < len(bridge_list):
            row.update(bridge_list[i])
        else:
            row.update({"Bridge Element": "", "Inside BR US": "", "Inside BR DS": ""})
        
        final_table.append(row)
    
    df = pd.DataFrame(final_table)
    
    try:
        df.to_excel(output_path, index=False)
        print(f"✅ Excel file created: {output_path}")
        print(f"📊 Rows: {len(df)}, Columns: {len(df.columns)}")
    except Exception as e:
        print(f"❌ Error saving Excel file: {e}")
    
    return df


def parse_excel_to_dict(excel_path: str) -> Dict:
    """
    Read HEC-RAS data from Excel file and convert to dictionary format
    for use in calculations and report generation
    
    CRITICAL: Save data with keys that match report_generator.py expectations
    """
    try:
        df = pd.read_excel(excel_path)
        data = {}
        
        print(f"📖 Reading HEC-RAS data from Excel: {excel_path}")
        print(f"📊 DataFrame shape: {df.shape}")
        print(f"📊 DataFrame columns: {list(df.columns)}")
        
        # Parse each row
        for idx, row in df.iterrows():
            # Get values from LEFT column (Global Parameter + Value)
            param = str(row.get('Global Parameter', '')).strip()
            value_str = str(row.get('Value', '')).strip()
            
            # Get values from RIGHT column (Bridge Element + Inside BR US/DS)
            element = str(row.get('Bridge Element', '')).strip()
            us_str = str(row.get('Inside BR US', '')).strip()
            ds_str = str(row.get('Inside BR DS', '')).strip()
            
            # Extract numeric values from LEFT and RIGHT
            import re
            left_numbers = re.findall(r"[-+]?\d*\.\d+|\d+", value_str)
            right_us_numbers = re.findall(r"[-+]?\d*\.\d+|\d+", us_str)
            right_ds_numbers = re.findall(r"[-+]?\d*\.\d+|\d+", ds_str)
            
            def get_first_num(numbers):
                return float(numbers[0]) if numbers else None
            
            left_val = get_first_num(left_numbers)
            us_val = get_first_num(right_us_numbers)
            ds_val = get_first_num(right_ds_numbers)
            
            # Debug for key parameters
            if any(x in element.upper() for x in ['VEL TOTAL', 'FLOW AREA', 'HYDR DEPTH', 'FRCTN', 'C & E']):
                print(f"DEBUG Row {idx}: element='{element}', us_val={us_val}, ds_val={ds_val}")
            
            # Parse LEFT column (Global Parameters)
            if 'E.G. US.' in param or 'EG US' in param:
                data['EG_US'] = left_val if left_val is not None else us_val
            elif 'W.S. US.' in param or 'WS US' in param:
                data['WSE'] = left_val if left_val is not None else us_val
            elif 'Q Total' in param:
                data['Q_total'] = left_val if left_val is not None else us_val
            elif 'Q Bridge' in param:
                data['Q_bridge'] = left_val if left_val is not None else us_val
            elif 'Delta EG' in param:
                data['Delta_EG'] = left_val if left_val is not None else us_val
            elif 'Delta WS' in param:
                data['Delta_WS'] = left_val if left_val is not None else us_val
            elif 'BR Open Area' in param:
                data['BR_Open_Area'] = left_val if left_val is not None else us_val
            elif 'BR Open Vel' in param:
                data['BR_Open_Vel'] = left_val if left_val is not None else us_val
            
            # Parse RIGHT column (Inside Bridge) - CRITICAL: Use correct keys!
            if element:
                if 'E.G. Elev' in element or 'EG Elev' in element:
                    data['EG_BR_US'] = us_val
                    data['EG_BR_DS'] = ds_val
                elif 'W.S. Elev' in element or 'WS Elev' in element:
                    data['WS_BR_US'] = us_val
                    data['WS_BR_DS'] = ds_val
                elif 'Max Chl Dpth' in element:
                    data['Max_Chl_Dpth_US'] = us_val
                    data['Max_Chl_Dpth_DS'] = ds_val
                elif 'Vel Total' in element:
                    # CRITICAL: Save as Vel_BR_US/DS for report generator
                    data['Vel_BR_US'] = us_val
                    data['Vel_BR_DS'] = ds_val
                    # ALSO save as velocity_avg for Section 4.2/5.2
                    if 'velocity_avg' not in data:
                        data['velocity_avg'] = us_val
                    print(f"✅ Vel_BR_US={us_val}, Vel_BR_DS={ds_val}")
                elif 'Flow Area' in element:
                    # CRITICAL: Save as flow_area_us/ds for report generator
                    data['flow_area_us'] = us_val
                    data['flow_area_ds'] = ds_val
                    # ALSO save as flow_area for Section 4.2/5.2
                    if 'flow_area' not in data:
                        data['flow_area'] = us_val
                    print(f"✅ flow_area_us={us_val}, flow_area_ds={ds_val}")
                elif 'Hydr Depth' in element:
                    # CRITICAL: Save as Hydr_Dpth_US/DS for report generator
                    data['Hydr_Dpth_US'] = us_val
                    data['Hydr_Dpth_DS'] = ds_val
                    # ALSO save as hydraulic_depth for Section 4.2/5.2
                    if 'hydraulic_depth' not in data:
                        data['hydraulic_depth'] = us_val
                    print(f"✅ Hydr_Dpth_US={us_val}, Hydr_Dpth_DS={ds_val}")
                elif 'Froude' in element:
                    data['Froude_US'] = us_val
                    data['Froude_DS'] = ds_val
                elif 'W.P. Total' in element or 'Wetted Perimeter' in element:
                    data['WP_Total_US'] = us_val
                    data['WP_Total_DS'] = ds_val
                elif 'Conv. Total' in element or 'Conveyance' in element:
                    data['Conv_Total_US'] = us_val
                    data['Conv_Total_DS'] = ds_val
                elif 'Frctn Loss' in element:
                    # CRITICAL: Save as Frctn_Loss for report generator
                    data['Frctn_Loss'] = us_val
                    print(f"✅ Frctn_Loss={us_val}")
                elif 'C & E Loss' in element:
                    # CRITICAL: Save as CE_Loss for report generator
                    data['CE_Loss'] = us_val
                    print(f"✅ CE_Loss={us_val}")
                elif 'Shear Total' in element:
                    data['Shear_Total_US'] = us_val
                    data['Shear_Total_DS'] = ds_val
                elif 'Power Total' in element:
                    data['Power_Total_US'] = us_val
                    data['Power_Total_DS'] = ds_val
                elif 'Top Width' in element:
                    data['top_width_us'] = us_val
                    data['top_width_ds'] = ds_val
                    # ALSO save as top_width for Section 4.2/5.2
                    if 'top_width' not in data:
                        data['top_width'] = us_val
            
            # ALSO save general parameters from RIGHT column for Section 4.2/5.2
            if 'Top Width' in element and 'top_width' not in data:
                data['top_width'] = us_val
        
        # Calculate q_avg and q_max
        if data.get('Q_bridge') and data.get('top_width') and data.get('top_width') > 0:
            q_avg = data['Q_bridge'] / data['top_width']
            data['q_avg'] = round(q_avg, 3)
            data['q_max'] = round(q_avg * 1.4, 3)
            print(f"✅ Calculated q_avg={data['q_avg']}, q_max={data['q_max']}")
        
        print(f"\n✅ Parsed {len(data.keys())} parameters from Excel")
        print(f"📊 WSE={data.get('WSE')}, Q_bridge={data.get('Q_bridge')}")
        print(f"📊 flow_area={data.get('flow_area')}, top_width={data.get('top_width')}")
        print(f"📊 velocity_avg={data.get('velocity_avg')}, hydraulic_depth={data.get('hydraulic_depth')}")
        print(f"📊 Vel_BR_US={data.get('Vel_BR_US')}, Vel_BR_DS={data.get('Vel_BR_DS')}")
        print(f"📊 flow_area_us={data.get('flow_area_us')}, flow_area_ds={data.get('flow_area_ds')}")
        print(f"📊 Hydr_Dpth_US={data.get('Hydr_Dpth_US')}, Hydr_Dpth_DS={data.get('Hydr_Dpth_DS')}")
        print(f"📊 Frctn_Loss={data.get('Frctn_Loss')}, CE_Loss={data.get('CE_Loss')}")
        print(f"📊 q_avg={data.get('q_avg')}, q_max={data.get('q_max')}")
        
        return data
        
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        import traceback
        traceback.print_exc()
        return {}