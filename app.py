"""
Bridge Hydrology Agent - Streamlit Web Interface
Based on Department of Roads (DoR) Nepal Guidelines - Ratu Bridge Report
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import sys
import os
import re
import io
import tempfile

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.discharge import DischargeCalculator
from src.rainfall import RainfallFrequencyAnalysis
from src.reporter import ReportGenerator
from src.scour import ScourCalculator
from src.report_generator import HydrologyReportGenerator
from src.hec_ras_parser import parse_hec_ras_file, parse_hec_ras_directory, parse_hec_ras_hdf_file, auto_parse_hec_ras

# Page configuration
st.set_page_config(
    page_title="Bridge Hydrology Agent",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.title("🌉 Bridge Hydrology Agent")
st.markdown("**Based on Department of Roads (DoR) Nepal Guidelines - Ratu Bridge Report**")
st.markdown("---")

# Sidebar - Configuration
st.sidebar.header("⚙️ Configuration")

# Regional Parameters
st.sidebar.subheader("Regional Parameters (Snyder)")
region = st.sidebar.selectbox(
    "Select Region",
    ["Terai Plains", "Mid-Hills", "Himalayan"],
    help="Select based on bridge location"
)

region_params = {
    "Terai Plains": {"Ct": 1.4, "Cp": 0.655},
    "Mid-Hills": {"Ct": 1.8, "Cp": 0.55},
    "Himalayan": {"Ct": 2.2, "Cp": 0.45}
}

Ct = st.sidebar.number_input("Ct Coefficient", value=region_params[region]["Ct"], step=0.1)
Cp = st.sidebar.number_input("Cp Coefficient", value=region_params[region]["Cp"], step=0.01)

# Climate Change Factor
climate_factor = st.sidebar.number_input(
    "Climate Change Factor",
    value=1.10,
    min_value=1.0,
    max_value=1.5,
    step=0.01
)

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None
if 'catchment_props' not in st.session_state:
    st.session_state.catchment_props = None
if 'rainfall_results' not in st.session_state:
    st.session_state.rainfall_results = None
if 'rainfall_stats' not in st.session_state:
    st.session_state.rainfall_stats = None
if 'scour_results' not in st.session_state:
    st.session_state.scour_results = None
if 'hec_ras_data' not in st.session_state:
    st.session_state.hec_ras_data = None

# Main Content - Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📍 Location & Catchment",
    "🌧️ Rainfall Data",
    "📊 Analysis Results",
    "📋 Report Table 5",
    "🌊 Scour Calculation",
    "💾 Export"
])

# ============== TAB 1: Location & Catchment ==============
with tab1:
    st.header("📍 Bridge Location & Catchment Characteristics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Bridge Coordinates")
        latitude = st.number_input("Latitude (WGS 84)", value=26.983597, format="%.6f")
        longitude = st.number_input("Longitude (WGS 84)", value=85.910333, format="%.6f")
        bridge_name = st.text_input("Bridge Name", value="Ratu River Bridge")
        chainage = st.text_input("Chainage (km)", value="265.312")
    
    with col2:
        st.subheader("Catchment Characteristics (Table 1)")
        area_km2 = st.number_input("Catchment Area A (km²)", value=88.84, step=0.01)
        length_km = st.number_input("Stream Length L (km)", value=26.93, step=0.01)
        lc_km = st.number_input("Centroidal Length Lc (km)", value=14.28, step=0.01)
        hmax_m = st.number_input("Max Elevation Hmax (m)", value=757.52, step=0.01)
        hmin_m = st.number_input("Min Elevation Hmin (m)", value=229.63, step=0.01)
    
    slope = (hmax_m - hmin_m) / length_km if length_km > 0 else 0
    
    st.session_state.catchment_props = {
        'A_km2': area_km2,
        'L_km': length_km,
        'Lc_km': lc_km,
        'Hmax_m': hmax_m,
        'Hmin_m': hmin_m,
        'Slope': slope,
        'latitude': latitude,
        'longitude': longitude,
        'bridge_name': bridge_name,
        'chainage': chainage
    }
    
    st.success("✓ Catchment characteristics saved!")

# ============== TAB 2: Rainfall Data ==============
with tab2:
    st.header("🌧️ Rainfall Frequency Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload Rainfall Data (Table 2 Format)")
        
        sample_data = pd.DataFrame({
            'Year': list(range(1985, 2021)),
            'Max_24hr_Rainfall': [
                152.4, 112.8, 233.8, 182.3, 118.2, 123.5, 164.2, 69.4, 145.3, 114.3,
                252.3, 127.4, 128.3, 146.3, 96.5, 125.3, 93.2, 92.2, 104.5, 275.5,
                153.4, 124.3, 131.2, 108.3, 107.4, 84.4, 168.3, 94.4, 78.4, 126.4,
                135.3, 126.5, 410.3, 117.2, 436.1, 144.2
            ]
        })
        
        csv_sample = sample_data.to_csv(index=False)
        st.download_button(
            label="📥 Download Sample CSV (Ratu Data)",
            data=csv_sample,
            file_name="sample_rainfall_data.csv",
            mime="text/csv"
        )
        
        uploaded_file = st.file_uploader("Upload CSV File", type=['csv'])
        
        if uploaded_file:
            try:
                rainfall_df = pd.read_csv(uploaded_file)
                st.session_state.rainfall_df = rainfall_df
                st.success(f"✓ Loaded {len(rainfall_df)} years of rainfall data")
            except Exception as e:
                st.error(f"Error loading file: {e}")
        else:
            st.session_state.rainfall_df = sample_data
            st.info("Using sample Ratu Bridge rainfall data (1985-2020)")
    
    with col2:
        st.subheader("Rainfall Statistics")
        
        if 'rainfall_df' in st.session_state:
            df = st.session_state.rainfall_df
            rainfall_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            rainfall_data = df[rainfall_col].values
            
            st.metric("Years of Data", len(rainfall_data))
            st.metric("Mean Rainfall", f"{np.mean(rainfall_data):.2f} mm")
            st.metric("Max Rainfall", f"{np.max(rainfall_data):.2f} mm")
            st.metric("Min Rainfall", f"{np.min(rainfall_data):.2f} mm")
    
    st.markdown("---")
    
    if st.button("🔍 Run Frequency Analysis", type="primary"):
        if 'rainfall_df' in st.session_state:
            try:
                # Save to temporary file for analysis
                temp_path = Path("data/rainfall/temp_analysis.csv")
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                st.session_state.rainfall_df.to_csv(temp_path, index=False)
                
                rainfall_analysis = RainfallFrequencyAnalysis(str(temp_path))
                analysis_results = rainfall_analysis.full_analysis()
                
                st.session_state.rainfall_results = analysis_results
                
                # Store rainfall statistics for report
                st.session_state.rainfall_stats = {
                    'n_years': len(st.session_state.rainfall_df),
                    'mean': float(np.mean(rainfall_data)),
                    'max': float(np.max(rainfall_data)),
                    'min': float(np.min(rainfall_data)),
                    'std': float(np.std(rainfall_data))
                }
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.success(f"✓ Best Distribution: {analysis_results['best_distribution']}")
                with col2:
                    st.info(f"R100yr: {analysis_results['R100yr']:.2f} mm")
                with col3:
                    st.warning(f"Data Years: {len(st.session_state.rainfall_df)}")
                
            except Exception as e:
                st.error(f"Analysis error: {e}")
                st.session_state.rainfall_results = {'R100yr': 519.38}
        else:
            st.warning("Please upload rainfall data first")
    else:
        if st.session_state.rainfall_results is None:
            st.session_state.rainfall_results = {'R100yr': 519.38, 'best_distribution': 'Laplace (Report)'}
            st.info("Using Ratu Report R100yr value: 519.38 mm")

# ============== TAB 3: Analysis Results ==============
with tab3:
    st.header("📊 Peak Discharge Analysis Results")
    
    if st.button("🚀 Run All Discharge Methods", type="primary"):
        try:
            catchment = st.session_state.catchment_props
            R100yr = st.session_state.rainfall_results.get('R100yr', 519.38)
            
            calc = DischargeCalculator(
                area_km2=catchment['A_km2'],
                length_km=catchment['L_km'],
                lc_km=catchment['Lc_km'],
                hmax_m=catchment['Hmax_m'],
                hmin_m=catchment['Hmin_m']
            )
            
            results = calc.calculate_all_methods(
                rainfall_100yr_mm=R100yr,
                Ct=Ct,
                Cp=Cp
            )
            
            results['Adopted_Q100'] = max([
                results['WECS_100yr'],
                results['Dickens_100yr'],
                results['Richards_100yr'],
                results['Snyder_100yr']
            ])
            results['Design_Discharge'] = round(results['Adopted_Q100'] * climate_factor, 2)
            
            st.session_state.results = results
            
            st.success("✓ Discharge calculations completed!")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("WECS Method", f"{results['WECS_100yr']:.2f} m³/s")
            with col2:
                st.metric("Dickens Method", f"{results['Dickens_100yr']:.2f} m³/s")
            with col3:
                st.metric("Richards Method", f"{results['Richards_100yr']:.2f} m³/s")
            with col4:
                st.metric("Snyder Method", f"{results['Snyder_100yr']:.2f} m³/s")
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4;">
                    <h4>🎯 Adopted Q100</h4>
                    <h2>{results['Adopted_Q100']:.2f} m³/s</h2>
                    <p>Maximum of all methods</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background-color: #d4edda; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #28a745;">
                    <h4>✅ Design Discharge (Qdesign)</h4>
                    <h2>{results['Design_Discharge']:.2f} m³/s</h2>
                    <p>Q100 × {climate_factor} (Climate Change)</p>
                </div>
                """, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Calculation error: {e}")

# ============== TAB 4: Report Table 5 ==============
with tab4:
    st.header("📋 Summary Report (Table 5 Format)")
    
    if st.session_state.results:
        results = st.session_state.results
        catchment = st.session_state.catchment_props
        rainfall = st.session_state.rainfall_results
        
        table5_data = {
            'Parameter': [
                'Bridge Name',
                'Chainage',
                'Catchment Area (km²)',
                '24 hr rainfall of 100 y return period (R100yr), mm',
                'Ct',
                'Cp',
                'WECS Method',
                'Modified Dickens Method',
                'B.D. Richards Method',
                "Snyder's Method",
                'Adopted Q100',
                'Design Discharge (Qdesign)'
            ],
            'Value': [
                catchment.get('bridge_name', 'N/A'),
                catchment.get('chainage', 'N/A'),
                f"{catchment.get('A_km2', 0):.2f}",
                f"{rainfall.get('R100yr', 0):.2f}",
                f"{Ct}",
                f"{Cp}",
                f"{results.get('WECS_100yr', 0):.2f}",
                f"{results.get('Dickens_100yr', 0):.2f}",
                f"{results.get('Richards_100yr', 0):.2f}",
                f"{results.get('Snyder_100yr', 0):.2f}",
                f"{results.get('Adopted_Q100', 0):.2f}",
                f"{results.get('Design_Discharge', 0):.2f}"
            ]
        }
        
        table5_df = pd.DataFrame(table5_data)
        st.dataframe(table5_df, width='stretch', hide_index=True)
        
        csv_data = table5_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Table 5 (CSV)",
            data=csv_data,
            file_name=f"table5_{catchment.get('bridge_name', 'bridge')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ Please run discharge analysis in Tab 3 first")

# ============== TAB 5: Scour Calculation ==============
with tab5:
    st.header("🌊 Scour Depth Analysis")
    
    if st.session_state.results:
        st.subheader("📁 HEC-RAS Integration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            upload_method = st.radio(
                "Select Input Method:",
                ["📤 Upload HEC-RAS Output File", "📂 Link to HEC-RAS Project Folder"]
            )
        
        hec_ras_data = None
        
        # ─────────────────────────────────────────────────────────────
        # Method 1: Upload HEC-RAS Output File
        # ─────────────────────────────────────────────────────────────
        if upload_method == "📤 Upload HEC-RAS Output File":
            hec_ras_file = st.file_uploader(
                "Upload HEC-RAS Output (.hdf, .out, .O01, .csv, .txt)",
                type=['hdf', 'HDF', 'out', 'O01', 'txt', 'csv'],
                help="Upload HEC-RAS output file (HDF5 recommended for automation)"
            )
            
            if hec_ras_file:
                # Check file type
                filename = hec_ras_file.name.lower()
                
                if filename.endswith('.hdf'):
                    # HDF5 file - save temporarily and parse
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.hdf') as tmp:
                        tmp.write(hec_ras_file.read())
                        tmp_path = tmp.name
                    
                    with st.spinner("🔍 Parsing HDF5 file..."):
                        hec_ras_data = parse_hec_ras_hdf_file(tmp_path)
                    
                    # Clean up temp file
                    os.unlink(tmp_path)
                    
                else:
                    # Text or CSV file - use existing parser
                    with st.spinner("🔍 Parsing output file..."):
                        hec_ras_data = parse_hec_ras_file(hec_ras_file)
                
                if hec_ras_data:
                    st.success("✅ HEC-RAS file parsed successfully!")
                    st.session_state.hec_ras_data = hec_ras_data
                else:
                    st.error("❌ Could not parse HEC-RAS file. Please check file format.")
        
        # ─────────────────────────────────────────────────────────────
        # Method 2: Link to HEC-RAS Project Folder
        # ─────────────────────────────────────────────────────────────
        else:
            project_folder = st.text_input(
                "HEC-RAS Project Folder Path:",
                placeholder="C:\\Users\\user\\HEC-RAS\\Ratu_Bridge\\",
                help="Agent will auto-detect HDF5, text, or CSV files"
            )
            
            if project_folder:
                if os.path.exists(project_folder):
                    if st.button("🔍 Auto-Detect and Parse HEC-RAS Data"):
                        with st.spinner("🔍 Scanning project folder..."):
                            hec_ras_data = auto_parse_hec_ras(project_folder)
                            
                            if hec_ras_data:
                                st.success("✅ HEC-RAS data extracted successfully!")
                                st.session_state.hec_ras_data = hec_ras_data
                            else:
                                st.error("❌ Could not extract HEC-RAS data from folder")
                else:
                    st.error("❌ Folder path does not exist")
        
        # Display extracted HEC-RAS data
        if hec_ras_data:
            st.info(f"""
            **✅ Extracted from HEC-RAS:**
            - Water Surface Elevation (WSE/HFL): **{hec_ras_data.get('WSE', 'N/A')} m**
            - Total Discharge (Q): **{hec_ras_data.get('Q_total', 'N/A')} m³/s**
            - Bridge Discharge: **{hec_ras_data.get('Q_bridge', 'N/A')} m³/s**
            - Top Width: **{hec_ras_data.get('top_width', 'N/A')} m**
            - **Calculated q_avg: {hec_ras_data.get('q_avg', 'N/A')} m²/s**
            - **Calculated q_max: {hec_ras_data.get('q_max', 'N/A')} m²/s**
            """)
        
        st.subheader("Basic Parameters (Table 7)")
        
        # Auto-calculate Q_scour from Q100
        Q100 = st.session_state.results.get('Adopted_Q100', 0)
        Q_scour_auto = Q100 * 1.30
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"""
            **From Tab 3:**
            - Q100: {Q100:.2f} m³/s
            - Q_scour (×1.30): {Q_scour_auto:.2f} m³/s
            """)
            
            # Use HEC-RAS Q if available, otherwise use calculated
            default_Q = hec_ras_data.get('Q_bridge', Q_scour_auto) if hec_ras_data else Q_scour_auto
            
            Q_design = st.number_input(
                "Discharge for Scour Analysis Q (m³/s)",
                value=round(default_Q, 2),
                step=0.01,
                key="scour_Q_design"
            )
            
            L_bridge = st.number_input("Bridge Length (m)", value=226.17, step=0.01)
        
        with col2:
            dmean_mm = st.number_input("dmean (mm)", value=2.8, step=0.1)
            Ksf = st.number_input("Ksf (Silt Factor)", value=2.9, step=0.1)
        
        with col3:
            Blench_Fb = st.number_input("Blench Fb", value=0.8, step=0.1)
            freeboard = st.number_input("Freeboard (m)", value=1.5, step=0.1)
        
        # ═══════════════════════════════════════════════════════════════
        # Discharge Intensity - AUTO-CALCULATED (NOT MANUAL)
        # ═══════════════════════════════════════════════════════════════
        st.markdown("---")
        st.subheader("📊 Discharge Intensity (Auto-Calculated)")
        
        # Auto-calculate discharge intensity
        if hec_ras_data and hec_ras_data.get('q_avg'):
            # Use HEC-RAS extracted values
            q_avg_auto = hec_ras_data['q_avg']
            q_max_auto = hec_ras_data['q_max']
            HFL_auto = hec_ras_data['WSE']
            
            st.success(f"""
            **✅ Auto-Calculated from HEC-RAS:**
            - q_avg = Q_bridge / Top_Width = {hec_ras_data.get('Q_bridge', 0):.2f} / {hec_ras_data.get('top_width', 0):.2f} = **{q_avg_auto:.3f} m²/s**
            - q_max = q_avg × 1.4 = **{q_max_auto:.3f} m²/s**
            - HFL/WSE = **{HFL_auto:.2f} m**
            """)
            
            # Show option to override
            allow_override = st.checkbox("✏️ Allow manual override", value=False)
            
            if allow_override:
                q_avg = st.number_input("Average Discharge Intensity q_avg (m²/s)", 
                                       value=round(q_avg_auto, 3), step=0.001)
                q_max = st.number_input("Maximum Discharge Intensity q_max (m²/s)", 
                                       value=round(q_max_auto, 3), step=0.001)
                HFL = st.number_input("Water Surface Elevation (HFL/WSE) (m)", 
                                     value=round(HFL_auto, 2), step=0.01)
            else:
                q_avg = q_avg_auto
                q_max = q_max_auto
                HFL = HFL_auto
                
        elif st.session_state.results:
            # Calculate from design discharge if no HEC-RAS data
            Q_design_val = st.session_state.results.get('Design_Discharge', 0)
            L_bridge_val = L_bridge
            
            # Estimate q from Q and bridge length
            # q = Q / Width, assume Width ≈ 0.8 × L_bridge
            estimated_width = L_bridge_val * 0.8
            q_avg_auto = Q_design_val / estimated_width
            q_max_auto = q_avg_auto * 1.4
            
            st.warning(f"""
            **⚠️ No HEC-RAS data loaded. Auto-calculated from Q_design:**
            - q_avg = Q_design / (0.8 × L_bridge) = {Q_design_val:.2f} / {estimated_width:.2f} = **{q_avg_auto:.3f} m²/s**
            - q_max = q_avg × 1.4 = **{q_max_auto:.3f} m²/s**
            
            *Upload HEC-RAS output for more accurate values*
            """)
            
            # Show option to override
            allow_override = st.checkbox("✏️ Allow manual override", value=False)
            
            if allow_override:
                q_avg = st.number_input("Average Discharge Intensity q_avg (m²/s)", 
                                       value=round(q_avg_auto, 3), step=0.001)
                q_max = st.number_input("Maximum Discharge Intensity q_max (m²/s)", 
                                       value=round(q_max_auto, 3), step=0.001)
                HFL = st.number_input("Water Surface Elevation (HFL/WSE) (m)", 
                                     value=219.06, step=0.01)
            else:
                q_avg = q_avg_auto
                q_max = q_max_auto
                HFL = 219.06  # Default HFL
        else:
            # Fallback to manual entry
            st.error("⚠️ Please run discharge analysis in Tab 3 first!")
            q_avg = st.number_input("Average Discharge Intensity q_avg (m²/s)", value=5.21, step=0.001)
            q_max = st.number_input("Maximum Discharge Intensity q_max (m²/s)", value=7.70, step=0.001)
            HFL = st.number_input("Water Surface Elevation (HFL/WSE) (m)", value=219.06, step=0.01)
        
        # Calculate scour
        if st.button("🔍 Calculate Scour Depths", type="primary"):
            try:
                scour_calc = ScourCalculator(
                    Q_design=Q_design,
                    L_bridge=L_bridge,
                    dmean_mm=dmean_mm,
                    Ksf=Ksf,
                    Blench_Fb=Blench_Fb
                )
                
                # Calculate scour for single bridge section
                scour_results = scour_calc.full_scour_analysis(HFL, q_avg, q_max)
                
                # Display Table 8
                st.subheader("Mean Scour Calculation (Table 8)")
                scour_table = pd.DataFrame({
                    'Method': ["Lacey's (avg q)", "Lacey's (max q)", "Blench's", "Adopted"],
                    'Scour Depth (m)': [
                        scour_results['mean_scour']['D_lacey_avg'],
                        scour_results['mean_scour']['D_lacey_max'],
                        scour_results['mean_scour']['D_blench'],
                        scour_results['mean_scour']['D_adopted']
                    ]
                })
                st.dataframe(scour_table, width='stretch')
                
                # Display Table 9
                st.subheader("Scour Depth and Level Calculation (Table 9)")
                table9_data = {
                    'Parameter': [
                        'Adopted Mean Scour D (m)',
                        'Scour Depth - Abutment (m)',
                        'Scour Depth - Pier (m)',
                        'Scour Level - Abutment (m)',
                        'Scour Level - Pier (m)',
                        'Minimum Soffit Level (m)',
                        'Water Surface Elevation (HFL/WSE) (m)'
                    ],
                    'Value': [
                        scour_results['mean_scour']['D_adopted'],
                        scour_results['pier_abutment_scour']['D_abutment'],
                        scour_results['pier_abutment_scour']['D_pier'],
                        scour_results['scour_levels']['scour_level_abutment'],
                        scour_results['scour_levels']['scour_level_pier'],
                        scour_results['min_soffit_level'],
                        HFL
                    ]
                }
                table9_df = pd.DataFrame(table9_data)
                st.dataframe(table9_df, width='stretch')
                
                # Save to session state for report
                st.session_state.scour_results = {
                    'parameters': {
                        'Q_design': Q_design,
                        'Q100': Q100,
                        'L_bridge': L_bridge,
                        'dmean_mm': dmean_mm,
                        'Ksf': Ksf,
                        'Blench_Fb': Blench_Fb,
                        'q_avg': q_avg,
                        'q_max': q_max,
                        'HFL': HFL
                    },
                    'bridge_section': {
                        'mean_scour': {
                            'D_lacey_avg': scour_results['mean_scour']['D_lacey_avg'],
                            'D_lacey_max': scour_results['mean_scour']['D_lacey_max'],
                            'D_blench': scour_results['mean_scour']['D_blench'],
                            'D_adopted': scour_results['mean_scour']['D_adopted']
                        },
                        'pier_abutment_scour': {
                            'D_abutment': scour_results['pier_abutment_scour']['D_abutment'],
                            'D_pier': scour_results['pier_abutment_scour']['D_pier']
                        },
                        'scour_levels': {
                            'scour_level_abutment': scour_results['scour_levels']['scour_level_abutment'],
                            'scour_level_pier': scour_results['scour_levels']['scour_level_pier']
                        },
                        'min_soffit_level': scour_results['min_soffit_level'],
                        'HFL': HFL,
                        'q_avg': q_avg,
                        'q_max': q_max
                    }
                }
                
                st.success(f"✅ Scour calculation completed!")
                
            except Exception as e:
                st.error(f"❌ Scour calculation error: {e}")
                import traceback
                st.code(traceback.format_exc())
    else:
        st.warning("⚠️ Please run discharge analysis first (Tab 3)")

# ============== TAB 6: Export ==============
with tab6:
    st.header("💾 Export Results")
    
    if st.session_state.results:
        results = st.session_state.results
        catchment = st.session_state.catchment_props
        
        st.subheader("Download Options")
        
        # Option 1: HEC-RAS JSON
        hec_ras_input_data = {
            'project_info': {
                'bridge_name': catchment.get('bridge_name', 'Bridge'),
                'chainage': catchment.get('chainage', ''),
                'coordinates': {
                    'latitude': catchment.get('latitude', 0),
                    'longitude': catchment.get('longitude', 0)
                },
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'boundary_conditions': {
                'upstream_flow': results.get('Design_Discharge', 0),
                'flow_type': 'steady',
                'return_period': 100,
                'unit': 'm³/s'
            },
            'manning_coefficients': {
                'main_channel': 0.03,
                'overbank': 0.035
            }
        }
        
        json_data = json.dumps(hec_ras_input_data, indent=2)
        st.download_button(
            label="📥 Download HEC-RAS Input (JSON)",
            data=json_data,
            file_name=f"hec_ras_{catchment.get('bridge_name', 'bridge')}.json",
            mime="application/json"
        )
        
        # Option 2: Complete Hydrology Report (DOCX)
        st.markdown("---")
        st.subheader("📄 Complete Hydrology Report")
        
        if st.button("📊 Generate Complete Report (MS Word)", type="primary"):
            try:
                # Prepare rainfall data
                rainfall_stats = st.session_state.get('rainfall_stats', {})
                
                # Prepare scour data
                scour_data = st.session_state.get('scour_results', {})
                
                # Generate report
                report_gen = HydrologyReportGenerator(
                    catchment_data=catchment,
                    rainfall_data=rainfall_stats,
                    discharge_data=results,
                    scour_data=scour_data,
                    rainfall_analysis=st.session_state.get('rainfall_results', {})
                )
                
                # Save to temporary file
                report_path = f"hydrology_report_{catchment.get('bridge_name', 'bridge')}.docx"
                report_gen.generate_report(report_path)
                
                # Read file for download
                with open(report_path, 'rb') as f:
                    report_bytes = f.read()
                
                st.download_button(
                    label="📥 Download Report (DOCX)",
                    data=report_bytes,
                    file_name=report_path,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
                st.success("✅ Report generated successfully!")
                
            except Exception as e:
                st.error(f"Error generating report: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        st.markdown("---")
        st.success(f"**Upstream Boundary Condition for HEC-RAS: {results.get('Design_Discharge', 0):.2f} m³/s**")
        
        # Additional info
        st.info("""
        **Report Includes:**
        - ✅ Executive Summary
        - ✅ Catchment Characteristics (Table 1)
        - ✅ Rainfall Statistics & Frequency Analysis
        - ✅ Goodness-of-Fit Test Results (KS, Chi-Square, AD)
        - ✅ Return Period Rainfall (2, 5, 10, 20, 50, 100, 200 years)
        - ✅ Discharge Analysis (All 4 Methods - Table 5)
        - ✅ Scour Calculations (Tables 7, 8, 9)
        - ✅ Conclusions & Recommendations
        - ✅ Methodology & References
        """)
        
    else:
        st.warning("⚠️ Please run discharge analysis first (Tab 3)")

# Footer
st.markdown("---")
st.markdown("🌉 Bridge Hydrology Agent v1.0 | Based on DoR Nepal Guidelines ")