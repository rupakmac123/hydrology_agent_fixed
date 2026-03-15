"""
Hydrology Agent - Streamlit Web Interface
Based on Ratu Bridge Hydrology Report (DoR Nepal)
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.discharge import DischargeCalculator
from src.rainfall import RainfallFrequencyAnalysis
from src.reporter import ReportGenerator
from src.scour import ScourCalculator  # ADD THIS LINE

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

# Main Content - Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📍 Location & Catchment",
    "🌧️ Rainfall Data",
    "📊 Analysis Results",
    "📋 Report Table 5",
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
                temp_path = Path("data/rainfall/temp_analysis.csv")
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                st.session_state.rainfall_df.to_csv(temp_path, index=False)
                
                rainfall_analysis = RainfallFrequencyAnalysis(str(temp_path))
                analysis_results = rainfall_analysis.full_analysis()
                
                st.session_state.rainfall_results = analysis_results
                
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

# ============== TAB 5: Export ==============
with tab5:
    st.header("💾 Export Results")
    
    if st.session_state.results:
        results = st.session_state.results
        catchment = st.session_state.catchment_props
        
        hec_ras_data = {
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
        
        json_data = json.dumps(hec_ras_data, indent=2)
        st.download_button(
            label="📥 Download HEC-RAS Input (JSON)",
            data=json_data,
            file_name=f"hec_ras_{catchment.get('bridge_name', 'bridge')}.json",
            mime="application/json"
        )
        
        st.markdown("---")
        st.success(f"**Upstream Boundary Condition for HEC-RAS: {results.get('Design_Discharge', 0):.2f} m³/s**")
        
    else:
        st.warning("⚠️ Please run analysis first to export results")

# ============== TAB 6: Scour Calculation ==============
# ============== TAB 6: Scour Calculation ==============
with tab5:  # Or create new tab: with st.expander("🌊 Scour Calculation (Tables 7, 8, 9)"):
    st.header("🌊 Scour Depth Analysis")
    
    if st.session_state.results:
        st.subheader("Basic Parameters (Table 7)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            Q_design = st.number_input(
                "Design Discharge Q (m³/s)",
                value=st.session_state.results['Design_Discharge'],
                step=0.01,
                key="scour_Q_design",
                help="Design discharge from Tab 3 (Q100 × 1.10)"
            )
            L_bridge = st.number_input("Bridge Length (m)", value=226.17, step=0.01)
        
        with col2:
            dmean_mm = st.number_input("dmean (mm)", value=2.8, step=0.1, help="Mean diameter of bed material")
            Ksf = st.number_input("Ksf (Silt Factor)", value=2.9, step=0.1, help="Ksf = 1.76 × √(dmean)")
        
        with col3:
            Blench_Fb = st.number_input("Blench Fb", value=0.8, step=0.1, help="Blench's Zero Bed Factor")
            freeboard = st.number_input("Freeboard (m)", value=1.5, step=0.1)
        
        # ═══════════════════════════════════════════════════════════════
        # AUTO-CALCULATE discharge intensity from Q_design
        # ═══════════════════════════════════════════════════════════════
        st.markdown("---")
        st.subheader("📊 Discharge Intensity (Auto-Calculated from Q_design)")
        
        # Effective width for discharge distribution (typically 70-90% of bridge length)
        width_factor = st.slider(
            "Effective Width Factor",
            min_value=0.5,
            max_value=1.0,
            value=0.8,
            step=0.05,
            help="Fraction of bridge length used for flow distribution"
        )
        
        effective_width = L_bridge * width_factor
        q_auto = Q_design / effective_width
        
        st.info(f"""
        **📈 Auto-Calculated Values:**
        - Effective Width: {effective_width:.2f} m ({width_factor*100:.0f}% of bridge length)
        - Average Discharge Intensity (q_avg): **{q_auto:.3f} m²/s**
        - Scour Discharge (Q_scour = Q_design × 1.3/1.1): **{Q_design * (1.3/1.1):.2f} m³/s**
        """)
        
        # Option to use auto-calculated or manual values
        use_auto_q = st.checkbox("✅ Use auto-calculated q values from Q_design", value=True)
        
        st.subheader("Cross-Section Analysis (Table 8 & 9)")
        
        # Upstream section
        st.markdown("**Upstream Section**")
        col1, col2 = st.columns(2)
        with col1:
            HFL_US = st.number_input("HFL US (m)", value=219.06, step=0.01)
            if use_auto_q:
                q_avg_US = st.number_input(
                    "q avg US (m²/s)", 
                    value=round(q_auto * 0.9, 2),
                    step=0.01,
                    key="q_avg_US"
                )
            else:
                q_avg_US = st.number_input("q avg US (m²/s)", value=5.21, step=0.01, key="q_avg_US_manual")
        with col2:
            if use_auto_q:
                q_max_US = st.number_input(
                    "q max US (m²/s)", 
                    value=round(q_auto * 1.3, 2),
                    step=0.01,
                    key="q_max_US"
                )
            else:
                q_max_US = st.number_input("q max US (m²/s)", value=7.7, step=0.01, key="q_max_US_manual")
        
        # Existing bridge section
        st.markdown("**Existing Bridge Section**")
        col1, col2 = st.columns(2)
        with col1:
            HFL_EX = st.number_input("HFL EX (m)", value=218.6, step=0.01)
            if use_auto_q:
                q_avg_EX = st.number_input(
                    "q avg EX (m²/s)", 
                    value=round(q_auto, 2),
                    step=0.01,
                    key="q_avg_EX"
                )
            else:
                q_avg_EX = st.number_input("q avg EX (m²/s)", value=5.28, step=0.01, key="q_avg_EX_manual")
        with col2:
            if use_auto_q:
                q_max_EX = st.number_input(
                    "q max EX (m²/s)", 
                    value=round(q_auto * 1.4, 2),
                    step=0.01,
                    key="q_max_EX"
                )
            else:
                q_max_EX = st.number_input("q max EX (m²/s)", value=8.1, step=0.01, key="q_max_EX_manual")
        
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
                
                # Upstream
                scour_US = scour_calc.full_scour_analysis(HFL_US, q_avg_US, q_max_US)
                
                # Existing
                scour_EX = scour_calc.full_scour_analysis(HFL_EX, q_avg_EX, q_max_EX)
                
                # Display results (Table 8)
                st.subheader("Mean Scour Calculation (Table 8)")
                
                scour_table = pd.DataFrame({
                    'Section': ['Upstream', 'Existing Bridge'],
                    'D_lacey_avg': [scour_US['mean_scour']['D_lacey_avg'], 
                                   scour_EX['mean_scour']['D_lacey_avg']],
                    'D_lacey_max': [scour_US['mean_scour']['D_lacey_max'],
                                   scour_EX['mean_scour']['D_lacey_max']],
                    'D_blench': [scour_US['mean_scour']['D_blench'],
                                scour_EX['mean_scour']['D_blench']],
                    'D_adopted': [scour_US['mean_scour']['D_adopted'],
                                 scour_EX['mean_scour']['D_adopted']]
                })
                
                st.dataframe(scour_table, width='stretch')
                
                # Display results (Table 9)
                st.subheader("Scour Depth and Level Calculation (Table 9)")
                
                table9_data = {
                    'Parameter': [
                        'Adopted Mean Scour D (m)',
                        'Scour Depth Abutment (m)',
                        'Scour Depth Pier (m)',
                        'Scour Level Abutment (m)',
                        'Scour Level Pier (m)',
                        'Min Soffit Level (m)'
                    ],
                    'Upstream': [
                        scour_US['mean_scour']['D_adopted'],
                        scour_US['pier_abutment_scour']['D_abutment'],
                        scour_US['pier_abutment_scour']['D_pier'],
                        scour_US['scour_levels']['scour_level_abutment'],
                        scour_US['scour_levels']['scour_level_pier'],
                        scour_US['min_soffit_level']
                    ],
                    'Existing': [
                        scour_EX['mean_scour']['D_adopted'],
                        scour_EX['pier_abutment_scour']['D_abutment'],
                        scour_EX['pier_abutment_scour']['D_pier'],
                        scour_EX['scour_levels']['scour_level_abutment'],
                        scour_EX['scour_levels']['scour_level_pier'],
                        scour_EX['min_soffit_level']
                    ]
                }
                
                table9_df = pd.DataFrame(table9_data)
                st.dataframe(table9_df, width='stretch')
                
                # Show impact of Q_design changes
                st.markdown("---")
                st.success(f"""
                ✅ **Scour calculation completed!**
                
                **Key Results:**
                - Design Discharge: {Q_design:.2f} m³/s
                - Effective Width: {effective_width:.2f} m
                - Average q: {q_auto:.3f} m²/s
                - Upstream Adopted Scour: {scour_US['mean_scour']['D_adopted']:.2f} m
                - Existing Adopted Scour: {scour_EX['mean_scour']['D_adopted']:.2f} m
                """)
                
            except Exception as e:
                st.error(f"❌ Scour calculation error: {e}")
                import traceback
                st.code(traceback.format_exc())
    else:
        st.warning("⚠️ Please run discharge analysis first (Tab 3)")
# Footer
st.markdown("---")
st.markdown("🌉 Bridge Hydrology Agent v1.0 | Based on DoR Nepal Guidelines | Ratu Bridge Hydrology Report")
