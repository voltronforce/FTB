from __future__ import annotations

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
    
    .main .block-container {{ padding-top: 1rem; }}
    
    h1, h2, h3 {{ 
        color: var(--primary); 
        font-weight: 600;
        letter-spacing: -0.025em;
    }}
    
    .stButton>button {{ 
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
        color: #fff; 
        border: none; 
        border-radius: 12px;
        font-weight: 500;
        padding: 0.75rem 2rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,85,139,0.2);
    }}
    
    .stButton>button:hover {{ 
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,85,139,0.3);
    }}

    /* ---------- Enhanced Banner styles ---------- */
    .hero-banner {{
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 50%, var(--accent) 100%);
        color: #fff;
        padding: 2.5rem 2rem;
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,.15);
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
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="white" opacity="0.1"/><circle cx="75" cy="75" r="1" fill="white" opacity="0.1"/><circle cx="50" cy="10" r="0.5" fill="white" opacity="0.1"/><circle cx="10" cy="60" r="0.5" fill="white" opacity="0.1"/><circle cx="90" cy="40" r="0.5" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
        pointer-events: none;
    }}
    
    .hero-content {{
        position: relative;
        z-index: 1;
    }}
    
    .hero-banner .logo {{ 
        font-size: 5rem; 
        margin-bottom: 1rem;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2));
    }}
    
    .hero-banner .title {{ 
        font-size: 3rem; 
        font-weight: 700; 
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        line-height: 1.1;
    }}
    
    .hero-banner .subtitle {{
        font-size: 1.2rem;
        opacity: 0.9;
        font-weight: 300;
        letter-spacing: 0.5px;
    }}

    /* Enhanced Tabs styling */
    .stTabs [role="tab"] {{ 
        padding: 12px 28px; 
        font-weight: 600;
        font-size: 1rem;
        background: white;
        border-radius: 12px 12px 0 0;
        margin-right: 4px;
        transition: all 0.3s ease;
    }}
    
    .stTabs [aria-selected="true"] {{ 
        color: var(--primary);
        background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }}
    
    .stTabs [role="tab"]:hover {{
        background: #f8f9fa;
    }}
    
    /* Card styling */
    .calc-card {{
        background: white;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
        border: 1px solid #e9ecef;
    }}
    
    .result-card {{
        background: linear-gradient(135deg, var(--success) 0%, #34ce57 100%);
        color: white;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 6px 25px rgba(40,167,69,0.2);
        margin: 1rem 0;
    }}
    
    .info-card {{
        background: linear-gradient(135deg, var(--secondary) 0%, #6ba3f5 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
    }}
    
    .warning-card {{
        background: linear-gradient(135deg, var(--warning) 0%, #ffd93d 100%);
        color: #333;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
    }}
    
    /* Number input styling */
    .stNumberInput > div > div > input {{
        border-radius: 8px;
        border: 2px solid #e9ecef;
        transition: border-color 0.3s ease;
    }}
    
    .stNumberInput > div > div > input:focus {{
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(0,85,139,0.1);
    }}
    
    /* Selectbox styling */
    .stSelectbox > div > div {{
        border-radius: 8px;
    }}
    
    /* Metric styling */
    .metric-container {{
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border-left: 4px solid var(--accent);
    }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Enhanced DSS Banner - Let's make it even more prominent
# ---------------------------------------------------------------------------
st.markdown("""
<div class='hero-banner'>
    <div class='hero-content'>
        <div class='logo'>🏛️💰</div>
        <div class='title'>Enhanced FTB Calculator</div>
        <div class='subtitle'>2024‑25 • Department of Social Services • ENHANCED VERSION</div>
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

###############################################################################
# Reverse Calculator Functions
###############################################################################

def find_ftb_a_cutoff(family_structure: Dict) -> Dict:
    """Find the income where FTB Part A reduces to zero"""
    rates = RATES["ftb_a"]
    
    # Calculate base amounts for the family
    total_base_pf = 0.0
    for child_age in family_structure["child_ages"]:
        if child_age <= 12:
            total_base_pf += rates["base_pf"]["0_12"]
        else:
            total_base_pf += rates["base_pf"]["13_plus"]
    
    # Calculate cutoff income (where payment goes to zero)
    cutoff_income = rates["higher_ifa"] + (total_base_pf * 26) / rates["taper2"]
    
    return {
        "supplement_cutoff": rates["supplement_income_limit"],
        "taper_start": rates["higher_ifa"],
        "zero_payment": round(cutoff_income, 2)
    }

def find_ftb_b_cutoff(family_structure: Dict) -> Dict:
    """Find the income where FTB Part B reduces to zero"""
    rates = RATES["ftb_b"]
    
    youngest_age = min(family_structure["child_ages"])
    max_pf = rates["max_pf"]["under_5"] if youngest_age < 5 else rates["max_pf"]["5_to_18"]
    
    # Secondary income cutoff
    secondary_cutoff = rates["secondary_free_area"] + (max_pf * 26) / rates["taper"]
    
    return {
        "primary_limit": rates["primary_limit"],
        "secondary_free_area": rates["secondary_free_area"],
        "secondary_cutoff": round(secondary_cutoff, 2)
    }

###############################################################################
# Enhanced UI Components
###############################################################################

def render_child_input_section():
    """Render the child input section with enhanced styling"""
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.subheader("👶 Children Details")
    
    if 'children_data' not in st.session_state:
        st.session_state.children_data = []
    
    col1, col2 = st.columns([3, 1])
    with col1:
        num_children = st.number_input("Number of children", min_value=0, max_value=10, value=len(st.session_state.children_data))
    with col2:
        if st.button("Update Children", type="primary"):
            st.session_state.children_data = [{"age": 5, "immunised": True, "healthy_start": True, "maintenance_ok": True} for _ in range(num_children)]
    
    children = []
    for i in range(num_children):
        if i >= len(st.session_state.children_data):
            st.session_state.children_data.append({"age": 5, "immunised": True, "healthy_start": True, "maintenance_ok": True})
        
        with st.expander(f"Child {i+1}", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                age = st.number_input(f"Age", min_value=0, max_value=19, value=st.session_state.children_data[i]["age"], key=f"age_{i}")
            with col2:
                immunised = st.checkbox("Immunised", value=st.session_state.children_data[i]["immunised"], key=f"immunised_{i}")
            with col3:
                healthy_start = st.checkbox("Healthy Start", value=st.session_state.children_data[i]["healthy_start"], key=f"healthy_start_{i}")
            with col4:
                maintenance_ok = st.checkbox("Maintenance OK", value=st.session_state.children_data[i]["maintenance_ok"], key=f"maintenance_ok_{i}")
            
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
    st.subheader("💰 Calculation Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### FTB Part A")
        st.metric("Fortnightly Payment", f"${ftb_a_result['pf']:.2f}")
        st.metric("Annual Core Payment", f"${ftb_a_result['annual']:.2f}")
        st.metric("Annual Supplement", f"${ftb_a_result['supp']:.2f}")
        st.metric("**Total Annual FTB A**", f"**${ftb_a_result['annual_total']:.2f}**")
    
    with col2:
        st.markdown("### FTB Part B")
        st.metric("Fortnightly Payment", f"${ftb_b_result['pf']:.2f}")
        st.metric("Annual Core Payment", f"${ftb_b_result['annual']:.2f}")
        st.metric("Annual Supplement", f"${ftb_b_result['supp']:.2f}")
        if ftb_b_result.get('energy', 0) > 0:
            st.metric("Energy Supplement", f"${ftb_b_result['energy']:.2f}")
        st.metric("**Total Annual FTB B**", f"**${ftb_b_result['annual_total']:.2f}**")
    
    # Combined totals
    total_fortnightly = ftb_a_result['pf'] + ftb_b_result['pf']
    total_annual = ftb_a_result['annual_total'] + ftb_b_result['annual_total']
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("**Combined Fortnightly**", f"**${total_fortnightly:.2f}**")
    with col2:
        st.metric("**Combined Annual Total**", f"**${total_annual:.2f}**")
    
    st.markdown('</div>', unsafe_allow_html=True)

###############################################################################
# Main Application with Enhanced Tabs
###############################################################################

# Create enhanced tab layout
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧮 Calculator", 
    "🔄 Reverse Calculator", 
    "📊 Income Buffer Analysis", 
    "📋 Eligibility Thresholds",
    "📖 Rate Details"
])

with tab1:
    st.markdown("### Calculate your Family Tax Benefit payments")
    
    # Family structure inputs
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.subheader("👥 Family Structure")
    
    col1, col2 = st.columns(2)
    with col1:
        partnered = st.selectbox("Family Type", ["Single", "Partnered/Couple"]) == "Partnered/Couple"
        primary_income = st.number_input("Primary Income (annual $)", min_value=0.0, value=50000.0, step=1000.0)
    with col2:
        on_income_support = st.checkbox("Receiving Income Support")
        secondary_income = st.number_input("Secondary Income (annual $)", min_value=0.0, value=0.0, step=1000.0) if partnered else 0.0
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Children input
    children = render_child_input_section()
    
    if st.button("Calculate FTB Payments", type="primary"):
        if children:
            family = Family(partnered, primary_income, secondary_income, children, on_income_support)
            
            ftb_a_result = calc_ftb_part_a(family)
            ftb_b_result = calc_ftb_part_b(family, include_es=True)
            
            display_results(ftb_a_result, ftb_b_result)
        else:
            st.warning("Please add at least one child to calculate FTB payments.")

with tab2:
    st.markdown("### Find Income Limits for Your Family")
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**Reverse Calculator**: Enter your family structure to find the income thresholds where FTB payments reduce or cease.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.subheader("👥 Family Structure for Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        reverse_partnered = st.selectbox("Family Type", ["Single", "Partnered/Couple"], key="reverse_family") == "Partnered/Couple"
        reverse_num_children = st.number_input("Number of children", min_value=1, max_value=10, value=2, key="reverse_children")
    
    with col2:
        st.markdown("**Child Ages:**")
        reverse_child_ages = []
        for i in range(reverse_num_children):
            age = st.number_input(f"Child {i+1} age", min_value=0, max_value=19, value=5, key=f"reverse_age_{i}")
            reverse_child_ages.append(age)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("Calculate Income Limits", type="primary"):
        family_structure = {"child_ages": reverse_child_ages, "partnered": reverse_partnered}
        
        ftb_a_limits = find_ftb_a_cutoff(family_structure)
        ftb_b_limits = find_ftb_b_cutoff(family_structure)
        
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.subheader("💡 Income Limit Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### FTB Part A Limits")
            st.metric("Supplement Income Limit", f"${ftb_a_limits['supplement_cutoff']:,.0f}")
            st.metric("Higher Taper Starts", f"${ftb_a_limits['taper_start']:,.0f}")
            st.metric("Payment Ceases", f"${ftb_a_limits['zero_payment']:,.0f}")
        
        with col2:
            st.markdown("### FTB Part B Limits")
            st.metric("Primary Income Limit", f"${ftb_b_limits['primary_limit']:,.0f}")
            st.metric("Secondary Free Area", f"${ftb_b_limits['secondary_free_area']:,.0f}")
            st.metric("Secondary Income Cutoff", f"${ftb_b_limits['secondary_cutoff']:,.0f}")
        
        st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown("### Income Buffer Analysis")
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**Buffer Analysis**: See how small changes in income affect your FTB payments.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # This would show a chart of how payments change with income
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.subheader("📈 Payment vs Income Chart")
    
    buffer_income = st.number_input("Base Income for Analysis", value=80000.0, step=5000.0)
    buffer_range = st.slider("Income Range (+/-)", 5000, 50000, 20000, step=5000)
    
    if st.button("Generate Buffer Analysis", type="primary"):
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
            showlegend=False
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
    
    st.markdown('</div>', unsafe_allow_html=True)

with tab4:
    st.markdown("### Eligibility Thresholds & Requirements")
    
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.subheader("📋 FTB Part A Thresholds (2024-25)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Income Thresholds:**")
        st.markdown(f"- Lower income free area: **${RATES['ftb_a']['lower_ifa']:,}**")
        st.markdown(f"- Higher income free area: **${RATES['ftb_a']['higher_ifa']:,}**")
        st.markdown(f"- Supplement income limit: **${RATES['ftb_a']['supplement_income_limit']:,}**")
        
        st.markdown("**Taper Rates:**")
        st.markdown(f"- First taper rate: **{RATES['ftb_a']['taper1']*100}%** per dollar")
        st.markdown(f"- Second taper rate: **{RATES['ftb_a']['taper2']*100}%** per dollar")
    
    with col2:
        st.markdown("**Maximum Fortnightly Rates:**")
        st.markdown(f"- 0-12 years: **${RATES['ftb_a']['max_pf']['0_12']:.2f}**")
        st.markdown(f"- 13-15 years: **${RATES['ftb_a']['max_pf']['13_15']:.2f}**")
        st.markdown(f"- 16-19 years: **${RATES['ftb_a']['max_pf']['16_19']:.2f}**")
        
        st.markdown("**Base Fortnightly Rates:**")
        st.markdown(f"- 0-12 years: **${RATES['ftb_a']['base_pf']['0_12']:.2f}**")
        st.markdown(f"- 13+ years: **${RATES['ftb_a']['base_pf']['13_plus']:.2f}**")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.subheader("📋 FTB Part B Thresholds (2024-25)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Income Thresholds:**")
        st.markdown(f"- Primary income limit: **${RATES['ftb_b']['primary_limit']:,}**")
        st.markdown(f"- Secondary free area: **${RATES['ftb_b']['secondary_free_area']:,}**")
        st.markdown(f"- Taper rate: **{RATES['ftb_b']['taper']*100}%** per dollar")
        
        st.markdown("**Nil Rate Thresholds:**")
        st.markdown(f"- Under 5: **${RATES['ftb_b']['nil_secondary']['under_5']:,}**")
        st.markdown(f"- 5-12 years: **${RATES['ftb_b']['nil_secondary']['5_to_12']:,}**")
    
    with col2:
        st.markdown("**Maximum Fortnightly Rates:**")
        st.markdown(f"- Under 5: **${RATES['ftb_b']['max_pf']['under_5']:.2f}**")
        st.markdown(f"- 5-18 years: **${RATES['ftb_b']['max_pf']['5_to_18']:.2f}**")
        
        st.markdown("**Energy Supplement (fortnightly):**")
        st.markdown(f"- Under 5: **${RATES['ftb_b']['energy_pf']['under_5']:.2f}**")
        st.markdown(f"- 5-18 years: **${RATES['ftb_b']['energy_pf']['5_to_18']:.2f}**")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="warning-card">', unsafe_allow_html=True)
    st.markdown("### ⚠️ Compliance Requirements")
    st.markdown(f"**Penalty per child (fortnightly): ${RATES['compliance_penalty_pf']:.2f}**")
    st.markdown("- Children must be immunised (or have approved exemption)")
    st.markdown("- 4-5 year olds must complete healthy start checks")
    st.markdown("- Maintenance action requirements must be met")
    st.markdown('</div>', unsafe_allow_html=True)

with tab5:
    st.markdown("### Rate Details & Calculation Methods")
    
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.subheader("🔍 FTB Part A Calculation Methods")
    
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
    
    **Final Payment = MAX(Method 1, Method 2)**
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="calc-card">', unsafe_allow_html=True)
    st.subheader("🔍 FTB Part B Calculation")
    
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
    st.subheader("📊 Rate Comparison Table")
    
    # Create comparison DataFrame
    rate_data = {
        'Age Group': ['0-12 years', '13-15 years', '16-19 years'],
        'FTB A Maximum ($/fortnight)': [222.04, 288.82, 288.82],
        'FTB A Maximum ($/year)': [5773.04, 7509.32, 7509.32],
        'FTB A Base ($/fortnight)': [71.26, 71.26, 71.26],
        'FTB A Base ($/year)': [1852.76, 1852.76, 1852.76]
    }
    
    df_rates = pd.DataFrame(rate_data)
    st.dataframe(df_rates, use_container_width=True)
    
    # FTB B rates
    ftb_b_data = {
        'Age Group': ['Under 5', '5-18 years'],
        'FTB B Maximum ($/fortnight)': [188.86, 131.74],
        'FTB B Maximum ($/year)': [4910.36, 3425.24],
        'Energy Supplement ($/fortnight)': [2.80, 1.96],
        'Energy Supplement ($/year)': [72.80, 50.96]
    }
    
    df_ftb_b = pd.DataFrame(ftb_b_data)
    st.dataframe(df_ftb_b, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><strong>Department of Social Services - Family Tax Benefit Calculator 2024-25</strong></p>
    <p>This calculator provides estimates based on current rates and thresholds. 
    Actual payments may vary based on individual circumstances and additional factors not captured in this tool.</p>
    <p><em>For official advice, contact Services Australia or visit servicesaustralia.gov.au</em></p>
</div>
""", unsafe_allow_html=True)

###############################################################################
# Session State Management
###############################################################################
if 'app_initialized' not in st.session_state:
    st.session_state.app_initialized = True
    st.session_state.children_data = []
