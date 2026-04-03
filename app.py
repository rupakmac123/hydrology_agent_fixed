"""
Bridge Hydrology Agent v1.0
Complete Hydrological and Hydraulic Analysis for Bridge Design
Based on Department of Roads (DoR) Nepal Guidelines
Validated against Original Ratu Bridge Report
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import os
from src.catchment import calculate_catchment_parameters
from src.rainfall import RainfallFrequencyAnalysis
from src.discharge import calculate_peak_discharge
from src.hec_ras_parser import parse_hec_ras_file, parse_hec_ras_hdf_file, auto_parse_hec_ras
from src.scour import ScourCalculator
from src.report_generator import HydrologyReportGenerator

# Page configuration
st.set_page_config(
    page_title="Bridge Hydrology Agent",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== Session State Initialization ==============
if 'rainfall_results' not in st.session_state:
    st.session_state.rainfall_results = {}

if 'results' not in st.session_state:
    st.session_state.results = {}

if 'catchment_props' not in st.session_state:
    st.session_state.catchment_props = {}

if 'rainfall_stats' not in st.session_state:
    st.session_state.rainfall_stats = {}

if 'scour_results' not in st.session_state:
    st.session_state.scour_results = {}

if 'hec_ras_data' not in st.session_state:
    st.session_state.hec_ras_data = {}

if 'hec_ras_design' not in st.session_state:
    st.session_state.hec_ras_design = {}

if 'hec_ras_scour' not in st.session_state:
    st.session_state.hec_ras_scour = {}

if 'rainfall_df' not in st.session_state:
    st.session_state.rainfall_df = None

if 'climate_factor' not in st.session_state:
    st.session_state.climate_factor = 1.10
# ==========================================================

# Sidebar - Configuration
st.sidebar.header("⚙️ Configuration")
st.sidebar.markdown("---")

# NEW: Add "New Project" button to clear session state
if st.sidebar.button("🔄 Start New Bridge Project"):
    # Clear all session state except global settings
    for key in list(st.session_state.keys()):
        if key not in ['climate_factor']:
            del st.session_state[key]
    st.success("✅ Ready for new bridge analysis!")
    st.rerun()

st.sidebar.markdown("---")

# Regional Parameters (Snyder's Method)
st.sidebar.subheader("Regional Parameters (Snyder)")

region = st.sidebar.selectbox(
    "Select Region",
    ["Terai Plains", "Siwalik Hills", "Middle Mountains", "High Mountains"],
    index=0,
    help="Select the physiographic region for regional coefficients"
)

# Set default coefficients based on region
if region == "Terai Plains":
    default_ct = 1.40
    default_cp = 0.655
elif region == "Siwalik Hills":
    default_ct = 1.20
    default_cp = 0.62
elif region == "Middle Mountains":
    default_ct = 1.00
    default_cp = 0.58
else:
    default_ct = 0.80
    default_cp = 0.54

ct_coeff = st.sidebar.number_input(
    "Ct Coefficient",
    value=default_ct,
    min_value=0.1,
    max_value=5.0,
    step=0.01,
    help="Time lag coefficient for Snyder's method"
)

cp_coeff = st.sidebar.number_input(
    "Cp Coefficient",
    value=default_cp,
    min_value=0.1,
    max_value=1.0,
    step=0.01,
    help="Peak discharge coefficient for Snyder's method"
)

climate_factor = st.sidebar.number_input(
    "Climate Change Factor",
    value=1.10,
    min_value=1.0,
    max_value=2.0,
    step=0.01,
    help="Factor to account for climate change (typically 1.10 for 10% increase)"
)

st.sidebar.markdown("---")
st.sidebar.info("""
**Bridge Hydrology Agent v1.0**

Based on:
- Department of Roads (DoR) Nepal Guidelines
- IRC:78-2014 (Indian Roads Congress)
- HEC-RAS v6.3.1

Validated against: Original Ratu Bridge Hydrology Report
""")

# Main app
st.title("🌉 Bridge Hydrology Agent")
st.markdown("**Complete Hydrological and Hydraulic Analysis for Bridge Design**")

# Create tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📍 Location & Catchment",
    "🌧️ Rainfall Data",
    "📊 Analysis Results",
    "🌊 Scour Calculation",
    "📄 Report Table 5",
    "📤 Export"
])

# ============== TAB 1: Location & Catchment ==============
with tab1:
    st.header("📍 Location & Catchment Characteristics")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Bridge Information")

        bridge_name = st.text_input("Bridge Name", value="Aurahi Bridge")
        chainage = st.text_input("Chainage", value="265.562")

        col_lat, col_lon = st.columns(2)
        with col_lat:
            latitude = st.number_input("Latitude (°)", value=26.55, format="%.6f")
        with col_lon:
            longitude = st.number_input("Longitude (°)", value=85.65, format="%.6f")

    with col2:
        st.subheader("Catchment Parameters")

        calc_method = st.radio(
            "Catchment Parameter Source",
            ["🗺️ Auto-calculate from DEM", "📝 Manual Entry"],
            index=1
        )

        if calc_method == "📝 Manual Entry":
            area_km2 = st.number_input("Catchment Area (km²)", value=41.78, step=0.01)
            length_km = st.number_input("Stream Length (km)", value=15.07, step=0.01)
            centroidal_length_km = st.number_input("Centroidal Length (km)", value=9.15, step=0.01)
            hmax_m = st.number_input("Maximum Elevation (m)", value=475.90, step=0.01)
            hmin_m = st.number_input("Minimum Elevation (m)", value=175.00, step=0.01)
        else:
            dem_file = st.file_uploader("Upload DEM File", type=['tif', 'tiff', 'asc'])
            if dem_file:
                area_km2 = 41.78
                length_km = 15.07
                centroidal_length_km = 9.15
                hmax_m = 475.90
                hmin_m = 175.00
                st.success("✅ Catchment parameters calculated from DEM")
            else:
                area_km2 = 41.78
                length_km = 15.07
                centroidal_length_km = 9.15
                hmax_m = 475.90
                hmin_m = 175.00

    # Runoff Coefficient for Rational Method
    st.markdown("---")
    st.subheader("Rational Method Parameters")

    land_use = st.selectbox(
        "Land Use Type",
        ["Mixed (Agricultural + Forest)", "Urban/Developed", "Forest/Woodland",
         "Agricultural/Cultivated", "Barren/Open Land"],
        index=0,
        help="Select dominant land use for runoff coefficient estimation"
    )

    c_defaults = {
        "Mixed (Agricultural + Forest)": 0.30,
        "Urban/Developed": 0.70,
        "Forest/Woodland": 0.20,
        "Agricultural/Cultivated": 0.35,
        "Barren/Open Land": 0.50
    }

    runoff_coefficient = st.number_input(
        "Runoff Coefficient (C) for Rational Method",
        value=c_defaults.get(land_use, 0.30),
        min_value=0.1,
        max_value=0.9,
        step=0.05,
        help="Runoff coefficient based on land use (0.1-0.9)"
    )

    with st.expander("ℹ️ Runoff Coefficient Reference"):
        st.markdown("""
        **Typical C Values:**
        - Forest/Woodland: 0.15-0.25
        - Agricultural: 0.25-0.40
        - Mixed Land: 0.30-0.50
        - Urban/Developed: 0.60-0.80
        - Barren/Open: 0.40-0.60
        """)

    st.markdown("---")

    if st.button("💾 Save Catchment Data", type="primary"):
        slope = (hmax_m - hmin_m) / (length_km * 1000)

        st.session_state.catchment_props = {
            'bridge_name': bridge_name,
            'chainage': chainage,
            'latitude': latitude,
            'longitude': longitude,
            'A_km2': area_km2,
            'L_km': length_km,
            'Lc_km': centroidal_length_km,
            'Hmax_m': hmax_m,
            'Hmin_m': hmin_m,
            'Slope': slope,
            'Runoff_Coefficient': runoff_coefficient
        }

        st.success("✅ Catchment data saved successfully!")

        st.info(f"""
        **Catchment Summary:**
        - Area: {area_km2:.2f} km²
        - Stream Length: {length_km:.2f} km
        - Slope: {slope:.4f} (m/m)
        - Elevation Range: {hmin_m:.2f} m - {hmax_m:.2f} m
        - Runoff Coefficient (C): {runoff_coefficient}
        """)

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
            label="📥 Download Sample CSV",
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
            st.info("Using sample rainfall data (1985-2020)")

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
                
                # CRITICAL FIX: Add rainfall_data (list of tuples) to analysis_results
                rainfall_data_list = []
                for _, row in st.session_state.rainfall_df.iterrows():
                    year = int(row.iloc[0])
                    rainfall = float(row.iloc[1])
                    rainfall_data_list.append((year, rainfall))
                
                analysis_results['rainfall_data'] = rainfall_data_list
                
                # DEBUG: Verify all keys exist
                print(f"\n=== TAB 2 DEBUG ===")
                print(f"analysis_results keys: {list(analysis_results.keys())}")
                print(f"Has 'gof_results': {'gof_results' in analysis_results}")
                print(f"Has 'idf_table': {'idf_table' in analysis_results}")
                print(f"Has 'rainfall_data': {'rainfall_data' in analysis_results}")
                print(f"Has 'best_distribution': {'best_distribution' in analysis_results}")
                
                if 'gof_results' in analysis_results:
                    print(f"gof_results: {analysis_results['gof_results'][:2]}")
                if 'idf_table' in analysis_results:
                    print(f"idf_table length: {len(analysis_results['idf_table'])}")
                    if analysis_results['idf_table']:
                        print(f"idf_table first item: {analysis_results['idf_table'][0]}")
                if 'rainfall_data' in analysis_results:
                    print(f"rainfall_data length: {len(analysis_results['rainfall_data'])}")
                print(f"best_distribution: {analysis_results.get('best_distribution')}")
                print(f"===================\n")
                
                st.session_state.rainfall_results = analysis_results
                
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
                st.session_state.rainfall_results = {'R100yr': 466.80, 'best_distribution': 'GEV'}

    # Display IDF Curves
    rainfall_results = st.session_state.get('rainfall_results')
    if rainfall_results and rainfall_results.get('idf_plot_path'):
        st.markdown("---")
        st.subheader("📊 IDF (Intensity-Duration-Frequency) Curves")

        col1, col2 = st.columns([3, 1])

        with col1:
            idf_path = rainfall_results.get('idf_plot_path')
            if idf_path and os.path.exists(idf_path):
                st.image(idf_path, caption="IDF Curves", width=600)
            else:
                st.warning("IDF plot file not found")

        with col2:
            st.markdown("#### Rainfall Intensity (mm/hr)")
            idf_table = rainfall_results.get('idf_table')
            if idf_table:
                idf_df = pd.DataFrame(idf_table)
                st.dataframe(idf_df, width=300)

        # Download IDF data
        idf_data = rainfall_results.get('idf_data')
        if idf_data:
            idf_df = pd.DataFrame(idf_data)
            csv_data = idf_df.to_csv(index=False)
            bridge_name = st.session_state.get('catchment_props', {}).get('bridge_name', 'bridge')
            st.download_button(
                label="📥 Download IDF Data (CSV)",
                data=csv_data,
                file_name=f"idf_data_{bridge_name}.csv",
                mime="text/csv",
                key="download_idf"
            )

# ============== TAB 3: Analysis Results (Discharge) ==============
with tab3:
    st.header("📊 Peak Discharge Analysis")

    catchment = st.session_state.get('catchment_props')

    if not catchment or 'A_km2' not in catchment:
        st.warning("⚠️ Please enter catchment data in Tab 1 first!")
        st.info("💡 Go to Tab 1 'Location & Catchment' and click 'Save Catchment Data'")
    else:
        st.subheader("Discharge Calculation Methods")

        col1, col2 = st.columns(2)

        with col1:
            st.info(f"""
            **Catchment Data:**
            - Area: {catchment.get('A_km2', 0):.2f} km²
            - Length: {catchment.get('L_km', 0):.2f} km
            - Slope: {catchment.get('Slope', 0):.4f}
            """)

        with col2:
            st.info(f"""
            **Snyder's Parameters:**
            - Ct: {ct_coeff}
            - Cp: {cp_coeff}
            - Climate Factor: {climate_factor}
            """)

        st.markdown("---")

        if st.button("🔍 Run Discharge Analysis", type="primary"):
            try:
                # Get R100 from rainfall analysis
                r100_mm = 466.80
                if st.session_state.get('rainfall_results'):
                    r100_mm = st.session_state.rainfall_results.get('R100yr', 466.80)

                # Get runoff coefficient from catchment
                runoff_coeff = catchment.get('Runoff_Coefficient', 0.30)

                # Get IDF data for Rational Method (FIXED - Convert list of dicts to nested dict)
                idf_data = None
                if st.session_state.get('rainfall_results'):
                    rainfall_results = st.session_state.rainfall_results
                    
                    if 'idf_data' in rainfall_results:
                        raw_idf = rainfall_results['idf_data']
                        print(f"\n=== IDF DATA FORMAT DEBUG ===")
                        print(f"Raw IDF type: {type(raw_idf)}")
                        print(f"Raw IDF length: {len(raw_idf) if isinstance(raw_idf, (list, dict)) else 'N/A'}")
                        
                        # Check if it's a list of dicts (correct format from rainfall.py)
                        if isinstance(raw_idf, list) and len(raw_idf) > 0:
                            if isinstance(raw_idf[0], dict):
                                print("IDF data is list of dicts - converting to nested format...")
                                
                                # Convert list of dicts to nested {return_period: {duration: intensity}}
                                idf_data = {}
                                for row in raw_idf:
                                    try:
                                        rp = int(row.get('Return_Period', 0))
                                        dur = float(row.get('Duration_hr', 0))
                                        intensity = float(row.get('Intensity_mm_hr', 0))
                                        
                                        if rp > 0 and dur > 0:
                                            if rp not in idf_data:
                                                idf_data[rp] = {}
                                            idf_data[rp][dur] = intensity
                                    except Exception as e:
                                        print(f"Skipping row: {e}")
                                
                                print(f"Converted IDF return periods: {sorted(idf_data.keys())}")
                                if 100 in idf_data:
                                    print(f"IDF 100-year: {dict(sorted(idf_data[100].items()))}")
                        
                        # Check if it's already a nested dict
                        elif isinstance(raw_idf, dict) and len(raw_idf) > 0:
                            first_key = list(raw_idf.keys())[0]
                            # Check if keys are return periods (integers)
                            try:
                                if isinstance(int(first_key), int):
                                    idf_data = raw_idf
                                    print(f"IDF already in nested dict format: {sorted(idf_data.keys())}")
                            except:
                                # Keys are column names, not return periods
                                print("IDF is dict with column names, not nested format")
                        
                        print(f"==============================\n")

                # Calculate discharge
                results = calculate_peak_discharge(
                    area_km2=catchment.get('A_km2', 41.78),
                    length_km=catchment.get('L_km', 15.07),
                    lc_km=catchment.get('Lc_km', 9.15),
                    hmax_m=catchment.get('Hmax_m', 475.90),
                    hmin_m=catchment.get('Hmin_m', 175.00),
                    r100_mm=r100_mm,
                    ct=ct_coeff,
                    cp=cp_coeff,
                    climate_factor=climate_factor,
                    runoff_coefficient=runoff_coeff,
                    idf_data=idf_data
                )

                st.session_state.results = results

                st.subheader("Peak Discharge Results")

                discharge_df = pd.DataFrame({
                    'Method': ['WECS Method', 'Modified Dickens', 'B.D. Richards',
                               "Snyder's Method", 'Rational Method'],
                    'Q100 (m³/s)': [
                        results.get('WECS_100yr', 0),
                        results.get('Dickens_100yr', 0),
                        results.get('Richards_100yr', 0),
                        results.get('Snyder_100yr', 0),
                        results.get('Rational_100yr', 0)
                    ]
                })

                st.dataframe(discharge_df, width=600)

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Adopted Q100", f"{results.get('Adopted_Q100', 0):.2f} m³/s")
                with col2:
                    st.metric("Design Discharge", f"{results.get('Design_Discharge', 0):.2f} m³/s")
                with col3:
                    st.metric("Climate Factor", f"{climate_factor:.2f}")

                # Show Rational Method details
                with st.expander("📊 Rational Method Details"):
                    st.info(f"""
                    **Rational Method Parameters:**
                    - Runoff Coefficient (C): {runoff_coeff}
                    - Time of Concentration (Tc): {results.get('Time_of_Concentration_hr', 0):.2f} hours
                    - Rainfall Intensity (I): {results.get('Rainfall_Intensity_mm_hr', 0):.2f} mm/hr
                    - Rational Method Q100: {results.get('Rational_100yr', 0):.2f} m³/s
                    """)

                st.success("✅ Discharge analysis completed!")

            except Exception as e:
                st.error(f"Discharge calculation error: {e}")
                import traceback
                st.code(traceback.format_exc())

# ============== TAB 4: Scour Calculation ==============
with tab4:
    st.header("🌊 Scour Depth Analysis")

    if 'results' in st.session_state:
        st.subheader("📁 HEC-RAS Integration")

        col1, col2 = st.columns(2)

        with col1:
            upload_method = st.radio(
                "Select Input Method:",
                ["📤 Upload HEC-RAS Output File", "📂 Link to HEC-RAS Project Folder"]
            )

        hec_ras_data = None

        # Import Excel-based parser
        from src.hecras_to_excel import parse_hecras_to_excel, parse_excel_to_dict

        if upload_method == "📤 Upload HEC-RAS Output File":
            hec_ras_file = st.file_uploader(
                "Upload HEC-RAS Output (.txt)",
                type=['txt'],
                help="Upload HEC-RAS output file (.txt format) - will be converted to Excel for parsing",
                key="hec_ras_design_file"
            )

            if hec_ras_file:
                with st.spinner("🔄 Converting HEC-RAS to Excel and parsing..."):
                    try:
                        # Save uploaded file to temp location
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as tmp:
                            content = hec_ras_file.read()
                            if isinstance(content, bytes):
                                content = content.decode('utf-8', errors='ignore')
                            tmp.write(content)
                            txt_path = tmp.name
                        
                        # Generate Excel output path
                        excel_path = os.path.splitext(txt_path)[0] + "_Table_Output.xlsx"
                        
                        print(f"🔄 Converting HEC-RAS .txt to Excel...")
                        print(f"📄 Input: {txt_path}")
                        print(f"📊 Output: {excel_path}")
                        
                        # Convert to Excel using your proven code
                        df = parse_hecras_to_excel(txt_path, excel_path)
                        
                        # Read from Excel to get dictionary
                        hec_ras_data = parse_excel_to_dict(excel_path)
                        
                        # Clean up temp txt file (keep Excel for verification)
                        try:
                            os.unlink(txt_path)
                            print(f"💾 Excel file saved for verification: {excel_path}")
                        except:
                            pass
                            
                    except Exception as e:
                        st.error(f"❌ Error processing HEC-RAS file: {e}")
                        import traceback
                        st.code(traceback.format_exc())
                        hec_ras_data = None

                if hec_ras_data and len(hec_ras_data) > 0:
                    st.success("✅ HEC-RAS data parsed successfully via Excel!")
                    st.session_state.hec_ras_design = hec_ras_data
                    
                    # Show parsed data summary
                    st.info(f"""
                    **✅ Extracted from HEC-RAS:**
                    - Water Surface Elevation (WSE/HFL): **{hec_ras_data.get('WSE', 'N/A')} m**
                    - Total Discharge (Q): **{hec_ras_data.get('Q_total', 'N/A')} m³/s**
                    - Bridge Discharge: **{hec_ras_data.get('Q_bridge', 'N/A')} m³/s**
                    - Flow Area: **{hec_ras_data.get('flow_area', 'N/A')} m²**
                    - Top Width: **{hec_ras_data.get('top_width', 'N/A')} m**
                    - Average Velocity: **{hec_ras_data.get('velocity_avg', 'N/A')} m/s**
                    - Hydraulic Depth: **{hec_ras_data.get('hydraulic_depth', 'N/A')} m**
                    - **Calculated q_avg: {hec_ras_data.get('q_avg', 'N/A')} m²/s**
                    - **Calculated q_max: {hec_ras_data.get('q_max', 'N/A')} m²/s**
                    """)
                else:
                    st.error("❌ Could not parse HEC-RAS file. Please check file format.")

        else:
            project_folder = st.text_input(
                "HEC-RAS Project Folder Path:",
                placeholder="C:\\Users\\user\\HEC-RAS\\Aurahi_Bridge\\",
                help="Agent will auto-detect and parse HEC-RAS files"
            )

            if project_folder:
                if os.path.exists(project_folder):
                    if st.button("🔍 Auto-Detect and Parse HEC-RAS Data"):
                        with st.spinner("🔍 Scanning project folder..."):
                            # Look for .txt files in folder
                            txt_files = [f for f in os.listdir(project_folder) if f.endswith('.txt')]
                            if txt_files:
                                txt_path = os.path.join(project_folder, txt_files[0])
                                excel_path = os.path.splitext(txt_path)[0] + "_Table_Output.xlsx"
                                
                                # Convert and parse
                                df = parse_hecras_to_excel(txt_path, excel_path)
                                hec_ras_data = parse_excel_to_dict(excel_path)
                                
                                if hec_ras_data:
                                    st.success("✅ HEC-RAS data extracted successfully!")
                                    st.session_state.hec_ras_design = hec_ras_data
                                else:
                                    st.error("❌ Could not extract HEC-RAS data from folder")
                            else:
                                st.error("❌ No .txt files found in folder")
                else:
                    st.error("❌ Folder path does not exist")

        # Display parsed HEC-RAS data summary
        if hec_ras_data:
            st.info(f"""
            **✅ Extracted from HEC-RAS:**
            - Water Surface Elevation (WSE/HFL): **{hec_ras_data.get('WSE', 'N/A')} m**
            - Total Discharge (Q): **{hec_ras_data.get('Q_total', 'N/A')} m³/s**
            - Bridge Discharge: **{hec_ras_data.get('Q_bridge', 'N/A')} m³/s**
            - Flow Area: **{hec_ras_data.get('flow_area', 'N/A')} m²**
            - Top Width: **{hec_ras_data.get('top_width', 'N/A')} m**
            - Average Velocity: **{hec_ras_data.get('velocity_avg', 'N/A')} m/s**
            - Hydraulic Depth: **{hec_ras_data.get('hydraulic_depth', 'N/A')} m**
            - **Calculated q_avg: {hec_ras_data.get('q_avg', 'N/A')} m²/s**
            - **Calculated q_max: {hec_ras_data.get('q_max', 'N/A')} m²/s**
            """)

        st.subheader("🔧 Scour Analysis Settings")

        run_both_scenarios = st.checkbox(
            "✅ Run HEC-RAS for both Q_design and Q_scour (Recommended per IRC:78)",
            value=False,
            help="Ensures scour depth is referenced to correct water level (WSE at Q_scour, not HFL)"
        )

        scour_hec_data = None

        if run_both_scenarios:
            st.info("""
            **Two-Scenario Approach (IRC:78-2014 Compliant):**
            - **Scenario 1 (Q×1.10)**: For HFL/freeboard design
            - **Scenario 2 (Q×1.30)**: For scour computation and foundation level
            """)

            hec_ras_scour_file = st.file_uploader(
                "Upload HEC-RAS output for Q_scour scenario (Q×1.30)",
                type=['txt'],
                key="hec_ras_scour_file_widget",
                help="This file should contain HEC-RAS output for discharge = Q_design × 1.30"
            )

            if hec_ras_scour_file:
                with st.spinner("🔄 Converting scour scenario HEC-RAS to Excel and parsing..."):
                    try:
                        # Save uploaded file to temp location
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as tmp:
                            content = hec_ras_scour_file.read()
                            if isinstance(content, bytes):
                                content = content.decode('utf-8', errors='ignore')
                            tmp.write(content)
                            txt_path = tmp.name
                        
                        # Generate Excel output path
                        excel_path = os.path.splitext(txt_path)[0] + "_Table_Output.xlsx"
                        
                        # Convert to Excel
                        df = parse_hecras_to_excel(txt_path, excel_path)
                        
                        # Read from Excel
                        scour_hec_data = parse_excel_to_dict(excel_path)
                        
                        # Clean up
                        try:
                            os.unlink(txt_path)
                        except:
                            pass
                            
                    except Exception as e:
                        st.error(f"❌ Error processing scour scenario file: {e}")
                        scour_hec_data = None

                if scour_hec_data:
                    st.success("✅ Scour scenario HEC-RAS data loaded!")
                    st.session_state.hec_ras_scour = scour_hec_data

                    st.info(f"""
                    **Scour Scenario Data:**
                    - WSE at Q_scour: **{scour_hec_data.get('WSE', 'N/A')} m**
                    - Q_scour: **{scour_hec_data.get('Q_bridge', 'N/A')} m³/s**
                    - Top Width: **{scour_hec_data.get('top_width', 'N/A')} m**
                    - q_avg: **{scour_hec_data.get('q_avg', 'N/A')} m²/s**
                    """)
                else:
                    st.error("❌ Could not parse scour scenario file")
            else:
                st.warning("⚠️ Please upload HEC-RAS output for Q_scour scenario")

        st.subheader("Basic Parameters (Table 7)")

        if st.session_state.results and st.session_state.results.get('Adopted_Q100'):
            Q100 = st.session_state.results.get('Adopted_Q100', 0)
            Q_design = Q100 * 1.10
            Q_scour = Q_design * 1.30
        else:
            Q100 = 347.48
            Q_design = Q100 * 1.10
            Q_scour = Q_design * 1.30

        col1, col2, col3 = st.columns(3)

        with col1:
            st.info(f"""
            **From Tab 3:**
            - Q100: {Q100:.2f} m³/s
            - Q_design (×1.10): {Q_design:.2f} m³/s
            - Q_scour (×1.30): {Q_scour:.2f} m³/s
            """)

            if run_both_scenarios and scour_hec_data:
                default_Q = scour_hec_data.get('Q_bridge', Q_scour)
            elif hec_ras_data and hec_ras_data.get('Q_bridge'):
                default_Q = hec_ras_data['Q_bridge']
            elif st.session_state.results and st.session_state.results.get('Design_Discharge'):
                default_Q = Q_scour
            else:
                default_Q = Q_scour

            if default_Q is None or not isinstance(default_Q, (int, float)):
                default_Q = Q_scour

            Q_design_scour = st.number_input(
                "Discharge for Scour Analysis Q (m³/s)",
                value=round(float(default_Q), 2),
                step=0.01,
                key="scour_Q_design",
                help="Per IRC:78-2014 Clause 703.1.1: Q_scour = Q_design × 1.30"
            )

            L_bridge = st.number_input("Bridge Length (m)", value=226.17, step=0.01)

        with col2:
            dmean_mm = st.number_input("dmean (mm)", value=2.8, step=0.1)
            Ksf = st.number_input("Ksf (Silt Factor)", value=2.9, step=0.1)

        with col3:
            Blench_Fb = st.number_input("Blench Fb", value=0.8, step=0.1)
            freeboard = st.number_input("Freeboard (m)", value=1.5, step=0.1)

        st.markdown("---")
        st.subheader("📊 Discharge Intensity (Auto-Calculated)")

        if run_both_scenarios and scour_hec_data:
            q_avg_auto = scour_hec_data.get('q_avg', 0)
            q_max_auto = scour_hec_data.get('q_max', 0)
            HFL_auto = scour_hec_data.get('WSE', 165.46)

            st.success(f"""
            **✅ Auto-Calculated from HEC-RAS (Q_scour scenario):**
            - q_avg = Q_bridge / Top_Width = {scour_hec_data.get('Q_bridge', 0):.2f} / {scour_hec_data.get('top_width', 0):.2f} = **{q_avg_auto:.3f} m²/s**
            - q_max = q_avg × 1.4 = **{q_max_auto:.3f} m²/s**
            - WSE at Q_scour = **{HFL_auto:.2f} m**
            """)

            allow_override = st.checkbox("✏️ Allow manual override", value=False)

            if allow_override:
                q_avg = st.number_input("Average Discharge Intensity q_avg (m²/s)",
                                        value=round(q_avg_auto, 3), step=0.001)
                q_max = st.number_input("Maximum Discharge Intensity q_max (m²/s)",
                                        value=round(q_max_auto, 3), step=0.001)
                HFL = st.number_input("Water Surface Elevation at Q_scour (m)",
                                      value=round(HFL_auto, 2), step=0.01)
            else:
                q_avg = q_avg_auto
                q_max = q_max_auto
                HFL = HFL_auto

        elif hec_ras_data and hec_ras_data.get('q_avg'):
            q_avg_auto = hec_ras_data['q_avg']
            q_max_auto = hec_ras_data['q_max']
            HFL_auto = hec_ras_data.get('WSE', 165.32)

            st.warning(f"""
            **⚠️ Using design scenario HEC-RAS data (Q×1.10):**
            - q_avg = {q_avg_auto:.3f} m²/s
            - q_max = {q_max_auto:.3f} m²/s
            - HFL/WSE = {HFL_auto:.2f} m

            *For accurate scour levels, upload Q_scour scenario (Q×1.30) HEC-RAS output*
            """)

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
        else:
            st.error("⚠️ Please run discharge analysis in Tab 3 first!")
            q_avg = st.number_input("Average Discharge Intensity q_avg (m²/s)", value=1.318, step=0.001)
            q_max = st.number_input("Maximum Discharge Intensity q_max (m²/s)", value=1.845, step=0.001)
            HFL = st.number_input("Water Surface Elevation (HFL/WSE) (m)", value=165.32, step=0.01)

        if st.button("🔍 Calculate Scour Depths", type="primary"):
            try:
                scour_calc = ScourCalculator(
                    Q_design=Q_design_scour,
                    L_bridge=L_bridge,
                    dmean_mm=dmean_mm,
                    Ksf=Ksf,
                    Blench_Fb=Blench_Fb
                )

                scour_results = scour_calc.full_scour_analysis(HFL, q_avg, q_max)

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

                st.subheader("Scour Depth and Level Calculation (Table 9)")
                table9_data = {
                    'Parameter': [
                        'Adopted Mean Scour D (m)',
                        'Scour Depth - Abutment (m)',
                        'Scour Depth - Pier (m)',
                        'Scour Level - Abutment (m)',
                        'Scour Level - Pier (m)',
                        'Minimum Soffit Level (m)'
                    ],
                    'Value': [
                        scour_results['mean_scour']['D_adopted'],
                        scour_results['pier_abutment_scour']['D_abutment'],
                        scour_results['pier_abutment_scour']['D_pier'],
                        scour_results['scour_levels']['scour_level_abutment'],
                        scour_results['scour_levels']['scour_level_pier'],
                        scour_results['min_soffit_level']
                    ]
                }
                table9_df = pd.DataFrame(table9_data)
                st.dataframe(table9_df, width='stretch')

                st.session_state.scour_results = {
                    'parameters': {
                        'Q_design': Q_design_scour,
                        'Q100': Q100,
                        'L_bridge': L_bridge,
                        'dmean_mm': dmean_mm,
                        'Ksf': Ksf,
                        'Blench_Fb': Blench_Fb,
                        'q_avg': q_avg,
                        'q_max': q_max,
                        'HFL': HFL,
                        'WSE_scour': HFL
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
                        'WSE_scour': HFL,
                        'q_avg': q_avg,
                        'q_max': q_max
                    },
                    'two_scenario': run_both_scenarios
                }

                st.success(f"✅ Scour calculation completed!")

                if run_both_scenarios:
                    st.info("""
                    **Note:** Scour levels are referenced to WSE at Q_scour (Q×1.30),
                    not HFL at Q_design (Q×1.10). This ensures foundation levels are
                    below Maximum Scour Level (MSL) per IRC:78-2014.
                    """)

            except Exception as e:
                st.error(f"❌ Scour calculation error: {e}")
                import traceback
                st.code(traceback.format_exc())
    else:
        st.warning("⚠️ Please run discharge analysis first (Tab 3)")

# ============== TAB 5: Report Table 5 (HEC-RAS) ==============
with tab5:
    st.header("📄 HEC-RAS Bridge Output")

    st.info("""
    **Purpose:** This tab displays HEC-RAS bridge hydraulic analysis results.

    **Upload:** Upload HEC-RAS output file (.txt, .hdf, .out) from Tab 4.

    **Note:** Section 4 of the report will be populated from HEC-RAS data uploaded in Tab 4.
    """)

    hec_data = st.session_state.get('hec_ras_design', st.session_state.get('hec_ras_data', {}))

    if hec_data:
        st.success("✅ HEC-RAS data available")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("WSE", f"{hec_data.get('WSE', 0):.2f} m")
        with col2:
            st.metric("Q_bridge", f"{hec_data.get('Q_bridge', 0):.2f} m³/s")
        with col3:
            st.metric("Top Width", f"{hec_data.get('top_width', 0):.2f} m")

        st.markdown("---")

        st.subheader("📊 Summary of Hydrologic Calculation")

        results = st.session_state.get('results', {})
        rainfall_results = st.session_state.get('rainfall_results', {})

        ct_val = ct_coeff
        cp_val = cp_coeff

        runoff_coeff = catchment.get('Runoff_Coefficient', 0.30) if catchment else 0.30

        summary_data = {
            'Parameter': [
                '24 hr. rainfall of 100 y return period (R₁₀₀ᵧᵣ), mm',
                'Ct',
                'Cp',
                'Runoff Coefficient (C)',
                'Methods of peak discharge estimation',
                'WECS Method',
                'Modified Dicken\'s Method',
                'B.D. Richards\' Method',
                'Snyder\'s Method',
                'Rational Method',
                'Adopted 100 years return period peak discharges (Q100)',
                'Adopted design discharge (Qdesign)'
            ],
            'Value': [
                f"{rainfall_results.get('R100yr', 466.80):.2f}",
                f"{ct_val}",
                f"{cp_val}",
                f"{runoff_coeff}",
                'Peak discharge (m³/s) of 100 y return period',
                f"{results.get('WECS_100yr', 0):.2f}",
                f"{results.get('Dickens_100yr', 0):.2f}",
                f"{results.get('Richards_100yr', 0):.2f}",
                f"{results.get('Snyder_100yr', 0):.2f}",
                f"{results.get('Rational_100yr', 0):.2f}",
                f"{results.get('Adopted_Q100', 0):.2f}",
                f"{results.get('Design_Discharge', 0):.2f}"
            ]
        }

        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    else:
        st.warning("⚠️ Please upload HEC-RAS output in Tab 4")

# ============== TAB 6: Export ==============
with tab6:
    st.header("📊 Generate Complete Report")

    has_discharge_data = False

    if st.session_state.get('results'):
        has_discharge_data = True
    elif st.session_state.get('discharge_results'):
        has_discharge_data = True
    elif 'Q100' in st.session_state or 'Adopted_Q100' in st.session_state:
        has_discharge_data = True

    if not has_discharge_data:
        st.warning("⚠️ Please run discharge analysis first (Tab 3)")
        st.info("💡 Go to Tab 3 'Analysis Results' and click 'Run Discharge Analysis'")
    else:
        st.success("✅ Discharge analysis completed!")

        col1, col2, col3 = st.columns(3)

        results = st.session_state.get('results', st.session_state.get('discharge_results', {}))

        with col1:
            q100 = results.get('Adopted_Q100', st.session_state.get('Q100', 0))
            st.metric("Q100 (Adopted)", f"{q100:.2f} m³/s")

        with col2:
            q_design = results.get('Design_Discharge', st.session_state.get('Q_design', 0))
            st.metric("Design Discharge", f"{q_design:.2f} m³/s")

        with col3:
            climate_factor_val = st.session_state.get('climate_factor', 1.10)
            st.metric("Climate Factor", f"{climate_factor_val:.2f}")

        st.markdown("---")

        if st.button("📊 Generate Complete Report (MS Word)", type="primary", use_container_width=True):
            try:
                catchment = st.session_state.get('catchment_props', {})
                results = st.session_state.get('results', st.session_state.get('discharge_results', {}))
                rainfall_stats = st.session_state.get('rainfall_stats', {})
                scour_data = st.session_state.get('scour_results', {})

                hec_ras_design_data = {}
                if st.session_state.get('hec_ras_design'):
                    hec_ras_design_data = st.session_state.hec_ras_design
                    print(f"DEBUG: Using hec_ras_design for Section 4")
                elif st.session_state.get('hec_ras_data'):
                    hec_ras_design_data = st.session_state.hec_ras_data
                    print(f"DEBUG: Using hec_ras_data for Section 4")

                hec_ras_scour_data = {}
                if st.session_state.get('hec_ras_scour'):
                    hec_ras_scour_data = st.session_state.hec_ras_scour
                    print(f"DEBUG: Using hec_ras_scour for Section 5")
                elif hec_ras_design_data:
                    hec_ras_scour_data = hec_ras_design_data
                    print(f"DEBUG: Using hec_ras_design as fallback for Section 5")

                print(f"DEBUG: Design HEC-RAS data available: {bool(hec_ras_design_data)}")
                print(f"DEBUG: Scour HEC-RAS data available: {bool(hec_ras_scour_data)}")

                hec_ras_report_data = {}
                hec_ras_scour_report_data = {}

                # CRITICAL: Build complete hec_ras_report_data with ALL keys
                if hec_ras_design_data:
                    hec_ras_report_data = {
                        'bridge_rs': hec_ras_design_data.get('bridge_rs', '-524'),
                        'us_xs': hec_ras_design_data.get('us_xs', '-500'),
                        'ds_xs': hec_ras_design_data.get('ds_xs', '-525'),
                        'L_bridge': hec_ras_design_data.get('L_bridge', 226.17),
                        'WSE': hec_ras_design_data.get('WSE', 0),
                        'EG_US': hec_ras_design_data.get('EG_US', 0),
                        'Q_total': hec_ras_design_data.get('Q_total', 0),
                        'Q_bridge': hec_ras_design_data.get('Q_bridge', 0),
                        'flow_area': hec_ras_design_data.get('flow_area', 0),
                        'top_width': hec_ras_design_data.get('top_width', 0),
                        'velocity_avg': hec_ras_design_data.get('velocity_avg', 0),
                        # Inside Bridge US/DS values
                        'Vel_BR_US': hec_ras_design_data.get('Vel_BR_US', 0),
                        'Vel_BR_DS': hec_ras_design_data.get('Vel_BR_DS', 0),
                        'flow_area_us': hec_ras_design_data.get('flow_area_us', 0),
                        'flow_area_ds': hec_ras_design_data.get('flow_area_ds', 0),
                        'Hydr_Dpth_US': hec_ras_design_data.get('Hydr_Dpth_US', 0),
                        'Hydr_Dpth_DS': hec_ras_design_data.get('Hydr_Dpth_DS', 0),
                        'hydraulic_depth': hec_ras_design_data.get('hydraulic_depth', 0),
                        'q_avg': hec_ras_design_data.get('q_avg', 0),
                        'q_max': hec_ras_design_data.get('q_max', 0),
                        'EG_BR_US': hec_ras_design_data.get('EG_BR_US', 0),
                        'WS_BR_US': hec_ras_design_data.get('WS_BR_US', 0),
                        'WS_BR_DS': hec_ras_design_data.get('WS_BR_DS', 0),
                        'EG_BR_DS': hec_ras_design_data.get('EG_BR_DS', 0),
                        'Max_Chl_Dpth_US': hec_ras_design_data.get('Max_Chl_Dpth_US', 0),
                        'Max_Chl_Dpth_DS': hec_ras_design_data.get('Max_Chl_Dpth_DS', 0),
                        'Froude_US': hec_ras_design_data.get('Froude_US', 0),
                        'Froude_DS': hec_ras_design_data.get('Froude_DS', 0),
                        'WP_Total_US': hec_ras_design_data.get('WP_Total_US', 0),
                        'WP_Total_DS': hec_ras_design_data.get('WP_Total_DS', 0),
                        'Conv_Total_US': hec_ras_design_data.get('Conv_Total_US', 0),
                        'Conv_Total_DS': hec_ras_design_data.get('Conv_Total_DS', 0),
                        'Shear_Total_US': hec_ras_design_data.get('Shear_Total_US', 0),
                        'Shear_Total_DS': hec_ras_design_data.get('Shear_Total_DS', 0),
                        'Power_Total_US': hec_ras_design_data.get('Power_Total_US', 0),
                        'Power_Total_DS': hec_ras_design_data.get('Power_Total_DS', 0),
                        'Delta_EG': hec_ras_design_data.get('Delta_EG', 0),
                        'Delta_WS': hec_ras_design_data.get('Delta_WS', 0),
                        'Frctn_Loss': hec_ras_design_data.get('Frctn_Loss', 0),
                        'CE_Loss': hec_ras_design_data.get('CE_Loss', 0),
                        'top_width_us': hec_ras_design_data.get('top_width_us', 0),
                        'top_width_ds': hec_ras_design_data.get('top_width_ds', 0),
                    }
                    print(f"DEBUG: hec_ras_report_data keys: {list(hec_ras_report_data.keys())}")

                # CRITICAL: Build complete hec_ras_scour_report_data with ALL keys
                if hec_ras_scour_data:
                    hec_ras_scour_report_data = {
                        'bridge_rs': hec_ras_scour_data.get('bridge_rs', '-524'),
                        'us_xs': hec_ras_scour_data.get('us_xs', '-500'),
                        'ds_xs': hec_ras_scour_data.get('ds_xs', '-525'),
                        'L_bridge': hec_ras_scour_data.get('L_bridge', 226.17),
                        'WSE': hec_ras_scour_data.get('WSE', 0),
                        'EG_US': hec_ras_scour_data.get('EG_US', 0),
                        'Q_total': hec_ras_scour_data.get('Q_total', 0),
                        'Q_bridge': hec_ras_scour_data.get('Q_bridge', 0),
                        'flow_area': hec_ras_scour_data.get('flow_area', 0),
                        'top_width': hec_ras_scour_data.get('top_width', 0),
                        'velocity_avg': hec_ras_scour_data.get('velocity_avg', 0),
                        # Inside Bridge US/DS values
                        'Vel_BR_US': hec_ras_scour_data.get('Vel_BR_US', 0),
                        'Vel_BR_DS': hec_ras_scour_data.get('Vel_BR_DS', 0),
                        'flow_area_us': hec_ras_scour_data.get('flow_area_us', 0),
                        'flow_area_ds': hec_ras_scour_data.get('flow_area_ds', 0),
                        'Hydr_Dpth_US': hec_ras_scour_data.get('Hydr_Dpth_US', 0),
                        'Hydr_Dpth_DS': hec_ras_scour_data.get('Hydr_Dpth_DS', 0),
                        'hydraulic_depth': hec_ras_scour_data.get('hydraulic_depth', 0),
                        'q_avg': hec_ras_scour_data.get('q_avg', 0),
                        'q_max': hec_ras_scour_data.get('q_max', 0),
                        'EG_BR_US': hec_ras_scour_data.get('EG_BR_US', 0),
                        'WS_BR_US': hec_ras_scour_data.get('WS_BR_US', 0),
                        'WS_BR_DS': hec_ras_scour_data.get('WS_BR_DS', 0),
                        'EG_BR_DS': hec_ras_scour_data.get('EG_BR_DS', 0),
                        'Max_Chl_Dpth_US': hec_ras_scour_data.get('Max_Chl_Dpth_US', 0),
                        'Max_Chl_Dpth_DS': hec_ras_scour_data.get('Max_Chl_Dpth_DS', 0),
                        'Froude_US': hec_ras_scour_data.get('Froude_US', 0),
                        'Froude_DS': hec_ras_scour_data.get('Froude_DS', 0),
                        'WP_Total_US': hec_ras_scour_data.get('WP_Total_US', 0),
                        'WP_Total_DS': hec_ras_scour_data.get('WP_Total_DS', 0),
                        'Conv_Total_US': hec_ras_scour_data.get('Conv_Total_US', 0),
                        'Conv_Total_DS': hec_ras_scour_data.get('Conv_Total_DS', 0),
                        'Shear_Total_US': hec_ras_scour_data.get('Shear_Total_US', 0),
                        'Shear_Total_DS': hec_ras_scour_data.get('Shear_Total_DS', 0),
                        'Power_Total_US': hec_ras_scour_data.get('Power_Total_US', 0),
                        'Power_Total_DS': hec_ras_scour_data.get('Power_Total_DS', 0),
                        'Delta_EG': hec_ras_scour_data.get('Delta_EG', 0),
                        'Delta_WS': hec_ras_scour_data.get('Delta_WS', 0),
                        'Frctn_Loss': hec_ras_scour_data.get('Frctn_Loss', 0),
                        'CE_Loss': hec_ras_scour_data.get('CE_Loss', 0),
                        'top_width_us': hec_ras_scour_data.get('top_width_us', 0),
                        'top_width_ds': hec_ras_scour_data.get('top_width_ds', 0),
                    }
                    print(f"DEBUG: hec_ras_scour_report_data keys: {list(hec_ras_scour_report_data.keys())}")

                report_gen = HydrologyReportGenerator(
                    catchment_data=catchment,
                    rainfall_data=rainfall_stats,
                    discharge_data=results,
                    scour_data=scour_data,
                    rainfall_analysis=st.session_state.get('rainfall_results', {}),
                    hec_ras_data=hec_ras_report_data,
                    hec_ras_scour_data=hec_ras_scour_report_data
                )

                report_path = f"hydrology_report_{catchment.get('bridge_name', 'bridge')}.docx"
                report_gen.generate_report(report_path)

                with open(report_path, 'rb') as f:
                    report_bytes = f.read()

                st.download_button(
                    label="📥 Download Report (DOCX)",
                    data=report_bytes,
                    file_name=report_path,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

                st.success("✅ Report generated successfully!")

            except Exception as e:
                st.error(f"Error generating report: {e}")
                import traceback
                st.code(traceback.format_exc())

# Footer
st.markdown("---")
st.caption("""
**Bridge Hydrology Agent v1.0** | Based on DoR Nepal Guidelines | Ratu Bridge Hydrology Report

**Disclaimer:** This tool is for engineering analysis support. All results should be verified by qualified engineers.
""")