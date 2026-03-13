# 🌉 Bridge Hydrology Agent

**Automated Hydrological and Hydraulic Analysis for Bridge Design in Nepal**

Based on **Department of Roads (DoR) Nepal Guidelines** and validated against the **Ratu Bridge Hydrology Report**.

---

## 📋 Features

### ✅ Hydrological Analysis
- **4 Peak Discharge Estimation Methods:**
  - WECS (Water and Energy Commission Secretariat)
  - Modified Dicken's Method
  - B.D. Richards' Method
  - Snyder's Method (with regional Ct, Cp parameters)

### ✅ Rainfall Frequency Analysis
- **Distribution Fitting:**
  - GEV (Generalized Extreme Value)
  - Gumbel (Extreme Value Type I)
  - Log-Pearson Type III
  - Normal Distribution
  - Laplace Distribution
- **Goodness-of-Fit Tests:**
  - Kolmogorov-Smirnov Test
  - Chi-Square Test
  - Anderson-Darling Test (where applicable)

### ✅ Scour Calculation
- **Lacey's Formula**
- **Blench Zero Bed Factor Approach**
- **Pier and Abutment Scour Depths**
- **Foundation Level Calculations**

### ✅ Export Capabilities
- HEC-RAS boundary condition files (JSON/CSV)
- Summary reports (Table 5, 7, 8, 9 format)
- Catchment characteristics (Table 1)

---

## 🚀 Quick Start

### Local Installation

```bash
# Clone repository
git clone https://github.com/rupakmac123/hydrology_agent_fixed.git
cd hydrology_agent_fixed

# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run app.py