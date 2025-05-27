###############################################################################
# Streamlit Setup - MUST BE FIRST
###############################################################################
import streamlit as st

# Page configuration MUST be the very first Streamlit command
st.set_page_config(
    page_title="DSS – Family Tax Benefit Calculator 2024‑25",
    page_icon="🐞", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

"""
Department of Social Services – Family Tax Benefit Calculator (2024‑25)
=======================================================================
"""

###############################################################################
# Imports & Setup
###############################################################################
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os

# ---------------------------------------------------------------------------
# Enhanced CSS & Styling
# ---------------------------------------------------------------------------
PRIMARY = "#00558B"  # DSS navy
ACCENT  = "#009CA6"  # DSS teal
SECONDARY = "#4A90E2"  # Light blue
SUCCESS = "#28A745"   # Green
WARNING = "#FFC107"   # Amber
LIGHT_GRAY = "#F8F9FA"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {{ 
        --primary: {PRIMARY}; 
        --accent: {ACCENT}; 
        --secondary: {SECONDARY};
        --success: {SUCCESS};
        --warning: {WARNING};
        --light-gray: {LIGHT_GRAY};
    }}
    
    html, body {{ 
        font-family: 'Inter', Arial, Helvetica, sans-serif; 
        background-color: #fafbfc;
    }}
    
    .main .block-container {{ 
        padding-top: 1rem; 
        max-width: 1200px;
    }}
    
    h1, h2, h3 {{ 
        color: var(--primary); 
        font-weight: 600;
        letter-spacing: -0.025em;
        margin-bottom: 1rem;
    }}
    
    /* Enhanced Button Styling */
    .stButton>button {{ 
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
        color: #fff; 
        border: none; 
        border-radius: 8px;
        font-weight: 500;
        padding: 0.6rem 1.5rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(0,85,139,0.15);
        font-size: 0.95rem;
        min-height: 44px;
    }}
    
    .stButton>button:hover {{ 
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,85,139,0.25);
        background: linear-gradient(135deg, #003d5c 0%, #007580 100%);
    }}

    .stButton>button:active {{
        transform: translateY(0);
        box-shadow: 0 2px 6px rgba(0,85,139,0.2);
    }}

    /* Clean Banner Design */
    .hero-banner {{
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
        color: #fff;
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,.1);
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }}
    
    .hero-banner::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: radial-gradient(circle at 30% 20%, rgba(255,255,255,0.1) 0%, transparent 50%),
                    radial-gradient(circle at 70% 80%, rgba(255,255,255,0.08) 0%, transparent 50%);
        pointer-events: none;
    }}
    
    .hero-content {{
        position: relative;
        z-index: 1;
    }}
    
    .hero-banner .logo {{ 
        font-size: 3rem; 
        margin-bottom: 0.5rem;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
    }}
    
    .hero-banner .title {{ 
        font-size: 2.2rem; 
        font-weight: 700; 
        margin-bottom: 0.3rem;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        line-height: 1.2;
    }}
    
    .hero-banner .subtitle {{
        font-size: 1rem;
        opacity: 0.9;
        font-weight: 400;
        letter-spacing: 0.3px;
    }}

    /* Clean Tab Styling */
    .stTabs [role="tab"] {{ 
        padding: 12px 20px; 
        font-weight: 500;
        font-size: 0.95rem;
        background: #fff;
        border-radius: 8px 8px 0 0;
        margin-right: 2px;
        transition: all 0.2s ease;
        border: 1px solid #e9ecef;
        color: #6c757d;
    }}
    
    .stTabs [aria-selected="true"] {{ 
        color: var(--primary);
        background: #fff;
        border-bottom: 2px solid var(--primary);
        border-top: 2px solid var(--primary);
        font-weight: 600;
    }}
    
    .stTabs [role="tab"]:hover {{
        background: #f8f9fa;
        color: var(--primary);
    }}
    
    /* Card Styling */
    .calc-card {{
        background: #fff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-bottom: 1.5rem;
        border: 1px solid #e9ecef;
    }}
    
    .result-card {{
        background: linear-gradient(135deg, var(--success) 0%, #20c653 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(40,167,69,0.15);
        margin: 1rem 0;
    }}
    
    .info-card {{
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        color: var(--primary);
        padding: 1.2rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid var(--secondary);
    }}
    
    .warning-card {{
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        color: #856404;
        padding: 1.2rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid var(--warning);
    }}
    
    /* Form Input Styling */
    .stNumberInput > div > div > input {{
        border-radius: 6px;
        border: 1px solid #ced4da;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
        padding: 0.5rem 0.75rem;
    }}
    
    .stNumberInput > div > div > input:focus {{
        border-color: var(--primary);
        box-shadow: 0 0 0 2px rgba(0,85,139,0.1);
        outline: none;
    }}
    
    .stSelectbox > div > div {{
        border-radius: 6px;
    }}
    
    .stCheckbox > label {{
        font-size: 0.9rem;
        color: #495057;
    }}
    
    /* Metric Styling */
    .metric-container {{
        background: #fff;
        padding: 1.2rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border-left: 3px solid var(--accent);
    }}

    /* Expander Styling */
    .streamlit-expanderHeader {{
        font-weight: 500;
        color: var(--primary);
    }}

    /* Clean up spacing */
    .element-container {{
        margin-bottom: 0.8rem;
    }}

    /* Improve readability */
    .stMarkdown p {{
        margin-bottom: 0.8rem;
        line-height: 1.6;
    }}

    /* Better section headers */
    .section-header {{
        background: linear-gradient(90deg, var(--primary) 0%, var(--accent) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 1rem;
        display: block;
    }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Clean DSS Banner with Beetle Icon
# ---------------------------------------------------------------------------
st.markdown("""
<div class='hero-banner'>
    <div class='hero-content'>
        <div class='logo'>🐞</div>
        <div class='title'>Family Tax Benefit Calculator</div>
        <div class='subtitle'>2024‑25 • Department of Social Services</div>
    </div>
</div>
""", unsafe_allow_html=True)

###############################################################################
# 2024‑25 Constants & Rates (unchanged)
###############################################################################
RATES: Dict[str, Dict] = {
    "ftb_a": {
        "max_pf": {"0_12": 222.04, "13_15": 288.82, "16_19": 288.82},
        "base_pf": {"0_12": 71.26, "13_plus": 71.26},
        "supplement": 916.15,
        "lower_ifa": 65_189,
        "higher_ifa": 115_997,
        "taper1": 0.20,
        "taper2": 0.30,
        "supplement_income_limit": 80_000,
    },
    "ftb_b": {
        "max_pf": {"under_5": 188.86, "5_to_18": 131.74},
        "energy_pf": {"under_5": 2.80, "5_to_18": 1.96},
        "supplement": 448.95,
        "secondary_free_area": 6_789,
        "nil_secondary": {"under_5": 33_653, "5_to_12": 26_207},
        "primary_limit": 117_194,
        "taper": 0.20,
    },
    "compliance_penalty_pf": 34.44,
}

###############################################################################
# Dataclasses & helper functions (unchanged)
###############################################################################
@dataclass
class Child:
    age: int
    immunised: bool = True
    healthy_start: bool = True
    maintenance_ok: bool = True

@dataclass
class Family:
    partnered: bool
    primary_income: float
    secondary_income: float = 0.0
    children: List[Child] | None = None
    on_income_support: bool = False

def pf_to_annual(pf: float) -> float:
    return round(pf * 26, 2)

def child_max_rate_pf(c: Child) -> float:
    if c.age <= 12:
        return RATES["ftb_a"]["max_pf"]["0_12"]
    elif c.age <= 15:
        return RATES["ftb_a"]["max_pf"]["13_15"]
    return RATES["ftb_a"]["max_pf"]["16_19"]

def child_base_rate_pf(c: Child) -> float:
    return RATES["ftb_a"]["base_pf"]["0_12"] if c.age <= 12 else RATES["ftb_a"]["base_pf"]["13_plus"]

def child_penalties_pf(c: Child) -> float:
    pen = 0.0
    if not c.immunised:
        pen += RATES["compliance_penalty_pf"]
    if 4 <= c.age <= 5 and not c.healthy_start:
        pen += RATES["compliance_penalty_pf"]
    return pen

###############################################################################
# FTB Calculation Functions (unchanged logic)
###############################################################################

def calc_ftb_part_a(fam: Family) -> Dict:
    rates = RATES["ftb_a"]
    total_max_pf, total_base_pf = 0.0, 0.0
    for ch in fam.children:
        max_pf = child_max_rate_pf(ch)
        base_pf = child_base_rate_pf(ch)
        if not ch.maintenance_ok:
            max_pf = min(max_pf, base_pf)
        pen = child_penalties_pf(ch)
        max_pf = max(max_pf - pen, 0)
        base_pf = max(base_pf - pen, 0)
        total_max_pf += max_pf
        total_base_pf += base_pf

    ati = fam.primary_income + fam.secondary_income
    # Method 1
    if fam.on_income_support:
        m1_pf = total_max_pf
    else:
        if ati <= rates["lower_ifa"]:
            m1_pf = total_max_pf
        elif ati <= rates["higher_ifa"]:
            m1_pf = max(total_max_pf - (ati - rates["lower_ifa"]) * rates["taper1"] / 26, total_base_pf)
        else:
            m1_pf = max(total_base_pf - (ati - rates["higher_ifa"]) * rates["taper2"] / 26, 0)
    
    # Method 2
    base_total_pf = sum(max(child_base_rate_pf(ch) - child_penalties_pf(ch), 0) for ch in fam.children)
    if fam.on_income_support or ati <= rates["higher_ifa"]:
        m2_pf = base_total_pf
    else:
        m2_pf = max(base_total_pf - (ati - rates["higher_ifa"]) * rates["taper2"] / 26, 0)
    
    best_pf = max(m1_pf, m2_pf)
    annual_core = pf_to_annual(best_pf)
    supp = rates["supplement"] if best_pf > 0 and (fam.on_income_support or ati <= rates["supplement_income_limit"]) else 0
    return {"pf": round(best_pf, 2), "annual": annual_core, "supp": supp, "annual_total": round(annual_core + supp, 2)}

def calc_ftb_part_b(fam: Family, include_es: bool = False) -> Dict:
    rates = RATES["ftb_b"]
    if not fam.children:
        return {k: 0 for k in ("pf", "annual", "supp", "energy", "annual_total")}

    youngest = min(ch.age for ch in fam.children)
    std_pf = rates["max_pf"]["under_5"] if youngest < 5 else rates["max_pf"]["5_to_18"]
    energy_pf = rates["energy_pf"]["under_5"] if youngest < 5 else rates["energy_pf"]["5_to_18"]
    
    # Apply secondary income test
    if fam.secondary_income <= rates["secondary_free_area"]:
        secondary_reduction = 0
    else:
        excess = fam.secondary_income - rates["secondary_free_area"]
        secondary_reduction = excess * rates["taper"] / 26
    
    # Method 1 and Method 2 (simplified for this implementation)
    base_pf = max(std_pf - secondary_reduction, 0)
    
    # Primary income test
    if fam.primary_income > rates["primary_limit"]:
        base_pf = 0
    
    annual_core = pf_to_annual(base_pf)
    energy_annual = pf_to_annual(energy_pf) if include_es and base_pf > 0 else 0
    supp = rates["supplement"] if base_pf > 0 else 0
    
    return {
        "pf": round(base_pf, 2),
        "annual": annual_core,
        "supp": supp,
        "energy": energy_annual,
        "annual_total": round(annual_core + supp + energy_annual, 2)
    }

# ─────────────────────────────────────────────────────────────────────────────
#  Helpers – 365-day annualisation
# ─────────────────────────────────────────────────────────────────────────────
FTNS_PER_YEAR = 365 / 14           # 26.071428…  (official conversion)

def pf_to_annual(pf: float) -> float:
    """Convert a fortnightly rate to an annual amount using 365-day factor."""
    return pf * FTNS_PER_YEAR


# ─────────────────────────────────────────────────────────────────────────────
#  Revised FTB Part A income-cut-out calculator
# ─────────────────────────────────────────────────────────────────────────────
def find_ftb_a_cutoff(family_structure: Dict) -> Dict[str, int]:
    """
    Return three critical incomes for this family:
        • supplement eligibility cut-off ($80 000)
        • start of 30 ¢ taper ($115 997)
        • income where FTB A reaches $0 (higher of the two statutory tests)
    Implements the 2024-25 rules exactly as in the Guide to Payments.
    """
    rates = RATES["ftb_a"]

    # 1️⃣  Count children by age band
    n_0_12  = sum(1 for a in family_structure["child_ages"] if a <= 12)
    n_13_19 = len(family_structure["child_ages"]) - n_0_12

    # 2️⃣  “Testable” maximum annual rate (note: the pf rates ALREADY exclude
    #      supplements, so no $916.15 subtraction here!)
    max0_12_annual  = pf_to_annual(rates["max_pf"]["0_12"])   # 222.04 pf
    max13_19_annual = pf_to_annual(rates["max_pf"]["13_15"])  # 288.82 pf
    R_max = n_0_12 * max0_12_annual + n_13_19 * max13_19_annual

    # 3️⃣  Annual base rate (same for all ages)
    base_annual_per_child = pf_to_annual(rates["base_pf"]["0_12"])  # 71.26 pf
    R_base = (n_0_12 + n_13_19) * base_annual_per_child

    # 4️⃣  Fixed parameters of the income test
    lower_ifa   = rates["lower_ifa"]          # $65 189
    higher_ifa  = rates["higher_ifa"]         # $115 997
    k1, k2      = rates["taper1"], rates["taper2"]   # 0.20 / 0.30
    fixed_red   = k1 * (higher_ifa - lower_ifa)      # = 0.20 × 50 808

    # 5️⃣  Cut-out from Method 1 (maximum-rate test)
    X_cut_max  = higher_ifa + (R_max  - fixed_red) / k2

    # 6️⃣  Cut-out from Method 2 (base-rate test)
    X_cut_base = higher_ifa +  R_base / k2

    # 7️⃣  Final income limit = higher of the two
    zero_payment = round(max(X_cut_max, X_cut_base))  # Guide rounds to $1

    return {
        "supplement_cutoff": rates["supplement_income_limit"],  # $80 000
        "taper_start":       higher_ifa,                        # $115 997
        "zero_payment":      zero_payment                       # e.g. $140 014
    }

def find_ftb_b_cutoff(family_structure: Dict) -> Dict:
    """
    Return the income points at which FTB Part B payments are affected:
        • primary income limit where payment stops
        • secondary income free area
        • secondary income cutoff where payment reaches $0
    """
    rates = RATES["ftb_b"]
    
    # Get youngest child age to determine which rate applies
    youngest_age = min(family_structure["child_ages"]) if family_structure["child_ages"] else 5
    
    # Determine the nil rates based on youngest child's age
    if youngest_age < 5:
        secondary_cutoff = rates["nil_secondary"]["under_5"]
    else:
        secondary_cutoff = rates["nil_secondary"]["5_to_12"]
    
    return {
        "primary_limit": rates["primary_limit"],           # $117,194
        "secondary_free_area": rates["secondary_free_area"], # $6,789
        "secondary_cutoff": secondary_cutoff,              # $33,653 or $26,207
    }
###############################################################################
# Enhanced UI Components
###############################################################################

def render_child_input_section():
    """Render the child input section with enhanced styling"""
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">👶 Children Details</div>', unsafe_allow_html=True)
    
    if 'children_data' not in st.session_state:
        st.session_state.children_data = []
    
    col1, col2 = st.columns([2, 1])
    with col1:
        num_children = st.number_input("Number of children", min_value=0, max_value=10, value=len(st.session_state.children_data))
    with col2:
        st.write("")  # Add some spacing
        if st.button("Update Children Count"):
            st.session_state.children_data = [{"age": 5, "immunised": True, "healthy_start": True, "maintenance_ok": True} for _ in range(num_children)]
            st.rerun()
    
    children = []
    for i in range(num_children):
        if i >= len(st.session_state.children_data):
            st.session_state.children_data.append({"age": 5, "immunised": True, "healthy_start": True, "maintenance_ok": True})
        
        with st.expander(f"Child {i+1} Details", expanded=i < 2):  # Only expand first 2 by default
            col1, col2 = st.columns(2)
            with col1:
                age = st.number_input(f"Age", min_value=0, max_value=19, value=st.session_state.children_data[i]["age"], key=f"age_{i}")
                immunised = st.checkbox("Immunised", value=st.session_state.children_data[i]["immunised"], key=f"immunised_{i}")
            with col2:
                healthy_start = st.checkbox("Healthy Start Check (4-5 years)", value=st.session_state.children_data[i]["healthy_start"], key=f"healthy_start_{i}")
                maintenance_ok = st.checkbox("Maintenance Action Met", value=st.session_state.children_data[i]["maintenance_ok"], key=f"maintenance_ok_{i}")
            
            st.session_state.children_data[i] = {
                "age": age, "immunised": immunised, 
                "healthy_start": healthy_start, "maintenance_ok": maintenance_ok
            }
            children.append(Child(age, immunised, healthy_start, maintenance_ok))
    
    st.markdown('</div>', unsafe_allow_html=True)
    return children

def display_results(ftb_a_result: Dict, ftb_b_result: Dict):
    """Display calculation results with enhanced styling"""
    st.markdown('<div class="result-card">', unsafe_allow_html=True)
    st.markdown("### 💰 Your FTB Payment Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**FTB Part A**")
        st.metric("Fortnightly Payment", f"${ftb_a_result['pf']:.2f}")
        st.metric("Annual Core Payment", f"${ftb_a_result['annual']:,.2f}")
        st.metric("Annual Supplement", f"${ftb_a_result['supp']:,.2f}")
        st.metric("**Total Annual FTB A**", f"**${ftb_a_result['annual_total']:,.2f}**")
    
    with col2:
        st.markdown("**FTB Part B**")
        st.metric("Fortnightly Payment", f"${ftb_b_result['pf']:.2f}")
        st.metric("Annual Core Payment", f"${ftb_b_result['annual']:,.2f}")
        st.metric("Annual Supplement", f"${ftb_b_result['supp']:,.2f}")
        if ftb_b_result.get('energy', 0) > 0:
            st.metric("Energy Supplement", f"${ftb_b_result['energy']:,.2f}")
        st.metric("**Total Annual FTB B**", f"**${ftb_b_result['annual_total']:,.2f}**")
    
    # Combined totals
    total_fortnightly = ftb_a_result['pf'] + ftb_b_result['pf']
    total_annual = ftb_a_result['annual_total'] + ftb_b_result['annual_total']
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("**Combined Fortnightly**", f"**${total_fortnightly:.2f}**")
    with col2:
        st.metric("**Combined Annual Total**", f"**${total_annual:,.2f}**")
    
    st.markdown('</div>', unsafe_allow_html=True)

###############################################################################
# Main Application with Enhanced Tabs
###############################################################################

# Create clean tab layout
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧮 Calculator", 
    "🔄 Income Limits", 
    "📊 Payment Analysis", 
    "📋 Eligibility Guide",
    "📖 Rate Information"
])

with tab1:
    st.markdown("### Calculate your Family Tax Benefit payments")
    
    # Family structure inputs
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">👥 Family Structure</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        partnered = st.selectbox("Family Type", ["Single Parent", "Couple/Partnered"], index=0) == "Couple/Partnered"
        primary_income = st.number_input("Primary Income (annual)", min_value=0.0, value=50000.0, step=1000.0, format="%.0f")
    with col2:
        on_income_support = st.checkbox("Currently receiving income support payments")
        if partnered:
            secondary_income = st.number_input("Partner's Income (annual)", min_value=0.0, value=0.0, step=1000.0, format="%.0f")
        else:
            secondary_income = 0.0
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Children input
    children = render_child_input_section()
    
    # Calculate button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Calculate My FTB Payments", type="primary", use_container_width=True):
            if children:
                family = Family(partnered, primary_income, secondary_income, children, on_income_support)
                
                ftb_a_result = calc_ftb_part_a(family)
                ftb_b_result = calc_ftb_part_b(family, include_es=True)
                
                display_results(ftb_a_result, ftb_b_result)
            else:
                st.error("⚠️ Please add at least one child to calculate FTB payments.")

with tab2:
    st.markdown("### Find Income Thresholds for Your Family")
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**Income Limit Calculator**: Discover the income levels where your FTB payments begin to reduce or stop entirely.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">👥 Family Structure</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        reverse_partnered = st.selectbox("Family Type", ["Single Parent", "Couple/Partnered"], key="reverse_family", index=0) == "Couple/Partnered"
        reverse_num_children = st.number_input("Number of children", min_value=1, max_value=10, value=2, key="reverse_children")
    
    with col2:
        st.markdown("**Child Ages:**")
        reverse_child_ages = []
        for i in range(min(reverse_num_children, 4)):  # Limit display for cleaner UI
            age = st.number_input(f"Child {i+1} age", min_value=0, max_value=19, value=5+i*2, key=f"reverse_age_{i}")
            reverse_child_ages.append(age)
        
        # Add remaining children with default ages if more than 4
        for i in range(4, reverse_num_children):
            reverse_child_ages.append(5 + i*2)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("Calculate Income Thresholds", type="primary"):
        family_structure = {"child_ages": reverse_child_ages, "partnered": reverse_partnered}
        
        ftb_a_limits = find_ftb_a_cutoff(family_structure)
        ftb_b_limits = find_ftb_b_cutoff(family_structure)
        
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.markdown("### 💡 Income Threshold Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**FTB Part A Thresholds**")
            st.metric("Supplement Income Limit", f"${ftb_a_limits['supplement_cutoff']:,}")
            st.metric("Higher Taper Begins", f"${ftb_a_limits['taper_start']:,}")
            st.metric("Payment Stops", f"${ftb_a_limits['zero_payment']:,}")
        
        with col2:
            st.markdown("**FTB Part B Thresholds**")
            st.metric("Primary Income Limit", f"${ftb_b_limits['primary_limit']:,}")
            st.metric("Secondary Free Area", f"${ftb_b_limits['secondary_free_area']:,}")
            st.metric("Secondary Income Cutoff", f"${ftb_b_limits['secondary_cutoff']:,}")
        
        st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown("### Payment vs Income Analysis")
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**Payment Analysis**: Visualize how changes in income affect your FTB payments.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📈 Analysis Parameters</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        buffer_income = st.number_input("Base Income for Analysis", value=80000.0, step=5000.0, format="%.0f")
    with col2:
        buffer_range = st.slider("Income Range (+/-)", 5000, 50000, 20000, step=5000)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("Generate Payment Analysis", type="primary"):
        # Generate sample data for visualization
        incomes = np.arange(buffer_income - buffer_range, buffer_income + buffer_range + 1, 1000)
        
        # This is a simplified calculation for demonstration
        ftb_a_payments = []
        for income in incomes:
            if income <= 65189:
                payment = 5773  # Max payment example
            elif income <= 115997:
                payment = max(5773 - (income - 65189) * 0.2, 1853)
            else:
                payment = max(1853 - (income - 115997) * 0.3, 0)
            ftb_a_payments.append(payment)
        
        df = pd.DataFrame({
            'Income': incomes,
            'FTB_A_Annual': ftb_a_payments
        })
        
        fig = px.line(df, x='Income', y='FTB_A_Annual', 
                     title='FTB Part A Payment vs Income',
                     labels={'Income': 'Annual Income ($)', 'FTB_A_Annual': 'Annual FTB Part A ($)'})
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter, Arial, sans-serif"),
            title_font_size=16,
            showlegend=False,
            height=400
        )
        fig.update_traces(line_color=PRIMARY, line_width=3)
        fig.add_vline(x=buffer_income, line_dash="dash", line_color="red", 
                     annotation_text=f"Your Income: ${buffer_income:,.0f}")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show specific values
        current_idx = np.argmin(np.abs(incomes - buffer_income))
        current_payment = ftb_a_payments[current_idx]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("At Current Income", f"${current_payment:,.0f}")
        with col2:
            lower_payment = ftb_a_payments[max(0, current_idx - 5)]
            st.metric("$5K Less Income", f"${lower_payment:,.0f}", f"+${lower_payment - current_payment:,.0f}")
        with col3:
            higher_payment = ftb_a_payments[min(len(ftb_a_payments)-1, current_idx + 5)]
            st.metric("$5K More Income", f"${higher_payment:,.0f}", f"{higher_payment - current_payment:,.0f}")

with tab4:
    st.markdown("### Eligibility Requirements & Thresholds")
    
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📋 FTB Part A - 2024-25 Rates</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Income Thresholds:**")
        st.markdown(f"• Lower income free area: **${RATES['ftb_a']['lower_ifa']:,}**")
        st.markdown(f"• Higher income free area: **${RATES['ftb_a']['higher_ifa']:,}**")
        st.markdown(f"• Supplement income limit: **${RATES['ftb_a']['supplement_income_limit']:,}**")
        
        st.markdown("**Taper Rates:**")
        st.markdown(f"• First taper rate: **{RATES['ftb_a']['taper1']*100:.0f}¢** per dollar")
        st.markdown(f"• Second taper rate: **{RATES['ftb_a']['taper2']*100:.0f}¢** per dollar")
    
    with col2:
        st.markdown("**Maximum Fortnightly Rates:**")
        st.markdown(f"• Ages 0-12: **${RATES['ftb_a']['max_pf']['0_12']:.2f}**")
        st.markdown(f"• Ages 13-15: **${RATES['ftb_a']['max_pf']['13_15']:.2f}**")
        st.markdown(f"• Ages 16-19: **${RATES['ftb_a']['max_pf']['16_19']:.2f}**")
        
        st.markdown("**Base Fortnightly Rates:**")
        st.markdown(f"• Ages 0-12: **${RATES['ftb_a']['base_pf']['0_12']:.2f}**")
        st.markdown(f"• Ages 13+: **${RATES['ftb_a']['base_pf']['13_plus']:.2f}**")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📋 FTB Part B - 2024-25 Rates</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Income Thresholds:**")
        st.markdown(f"• Primary income limit: **${RATES['ftb_b']['primary_limit']:,}**")
        st.markdown(f"• Secondary free area: **${RATES['ftb_b']['secondary_free_area']:,}**")
        st.markdown(f"• Taper rate: **{RATES['ftb_b']['taper']*100:.0f}¢** per dollar")
        
        st.markdown("**Payment Ceases When Secondary Income Reaches:**")
        st.markdown(f"• Family with child under 5: **${RATES['ftb_b']['nil_secondary']['under_5']:,}**")
        st.markdown(f"• Family with children 5-12: **${RATES['ftb_b']['nil_secondary']['5_to_12']:,}**")
    
    with col2:
        st.markdown("**Maximum Fortnightly Rates:**")
        st.markdown(f"• Youngest child under 5: **${RATES['ftb_b']['max_pf']['under_5']:.2f}**")
        st.markdown(f"• Youngest child 5-18: **${RATES['ftb_b']['max_pf']['5_to_18']:.2f}**")
        
        st.markdown("**Energy Supplement (fortnightly):**")
        st.markdown(f"• Youngest child under 5: **${RATES['ftb_b']['energy_pf']['under_5']:.2f}**")
        st.markdown(f"• Youngest child 5-18: **${RATES['ftb_b']['energy_pf']['5_to_18']:.2f}**")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="warning-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">⚠️ Compliance Requirements</div>', unsafe_allow_html=True)
    st.markdown(f"**Penalty per child (fortnightly): ${RATES['compliance_penalty_pf']:.2f}**")
    st.markdown("• **Immunisation**: Children must be fully immunised or have approved exemption")
    st.markdown("• **Healthy Start**: 4-5 year olds must complete health check requirements")
    st.markdown("• **Maintenance Action**: Appropriate maintenance action must be taken where required")
    st.markdown('</div>', unsafe_allow_html=True)

with tab5:
    st.markdown("### Rate Details & Calculation Information")
    
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🔍 How FTB Part A is Calculated</div>', unsafe_allow_html=True)
    
    st.markdown("""
    **Method 1 (Standard Calculation):**
    1. Start with maximum rate for each child's age group
    2. Apply maintenance action and compliance penalties
    3. Apply income test using two-tier taper system:
       - 20¢ per dollar above $65,189 (lower threshold)
       - 30¢ per dollar above $115,997 (higher threshold)
    4. Payment cannot fall below base rate in first tier
    
    **Method 2 (Base Rate Calculation):**
    1. Start with base rate for each child
    2. Apply compliance penalties only
    3. Apply 30¢ per dollar taper above $115,997
    4. Used when it gives a higher result than Method 1
    
    **Final Payment = Higher of Method 1 or Method 2**
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🔍 How FTB Part B is Calculated</div>', unsafe_allow_html=True)
    
    st.markdown("""
    **Primary Income Test:**
    - Payment ceases when primary earner income exceeds $117,194
    
    **Secondary Income Test:**
    - Free area: $6,789 (no reduction)
    - Taper: 20¢ per dollar above free area
    - Payment ceases at different thresholds based on youngest child's age
    
    **Energy Supplement:**
    - Additional payment for eligible families
    - Separate rate for under 5 vs 5-18 age groups
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Rate comparison table
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📊 Rate Comparison Tables</div>', unsafe_allow_html=True)
    
    # Create comparison DataFrame
    st.markdown("**FTB Part A Rates by Age Group:**")
    rate_data = {
        'Age Group': ['0-12 years', '13-15 years', '16-19 years'],
        'Maximum ($/fortnight)': [222.04, 288.82, 288.82],
        'Maximum ($/year)': [5773.04, 7509.32, 7509.32],
        'Base ($/fortnight)': [71.26, 71.26, 71.26],
        'Base ($/year)': [1852.76, 1852.76, 1852.76]
    }
    
    df_rates = pd.DataFrame(rate_data)
    st.dataframe(df_rates, use_container_width=True, hide_index=True)
    
    st.markdown("**FTB Part B Rates by Age Group:**")
    ftb_b_data = {
        'Age Group': ['Youngest under 5', 'Youngest 5-18'],
        'Standard ($/fortnight)': [188.86, 131.74],
        'Standard ($/year)': [4910.36, 3425.24],
        'Energy Supplement ($/fortnight)': [2.80, 1.96],
        'Energy Supplement ($/year)': [72.80, 50.96]
    }
    
    df_ftb_b = pd.DataFrame(ftb_b_data)
    st.dataframe(df_ftb_b, use_container_width=True, hide_index=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Clean Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6c757d; padding: 1.5rem; background: #f8f9fa; border-radius: 8px; margin-top: 2rem;'>
    <p style='margin-bottom: 0.5rem;'><strong>Department of Social Services - Family Tax Benefit Calculator 2024-25</strong></p>
    <p style='font-size: 0.9rem; margin-bottom: 0.5rem;'>This calculator provides estimates based on current rates and thresholds. 
    Actual payments may vary based on individual circumstances.</p>
    <p style='font-size: 0.85rem; margin: 0;'><em>For official advice, contact Services Australia or visit servicesaustralia.gov.au</em></p>
</div>
""", unsafe_allow_html=True)

###############################################################################
# Session State Management
###############################################################################
if 'app_initialized' not in st.session_state:
    st.session_state.app_initialized = True
    st.session_state.children_data = []
