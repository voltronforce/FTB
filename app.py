"""Department of Social Services – Family Tax Benefit Calculator (2024‑25)
=====================================================================

*Rates current at 20 March 2025 – supplements displayed separately.*

This Streamlit app calculates Family Tax Benefit Parts A & B in line with the
**Family Assistance Guide** (sections 3.1.1‑3.1.9) for the 2024‑25 year.  It
implements the two‑step ordinary‐income test for Part A (20 c taper to the
**base‑rate floor**, then a 30 c taper on the base rate) and applies child‑level
penalties for immunisation, Healthy‑Start, and maintenance action.

Styling retains the DSS navy/teal palette and the optional *Budget Beetle* 🐞.

Run the app:
```bash
streamlit run ftb_streamlit_app_updated.py
```
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import streamlit as st
import os

###############################################################################
# CONSTANTS & RATE TABLE (20 Mar 2025)
###############################################################################

PRIMARY = "#00558B"  # DSS navy
ACCENT  = "#009CA6"  # DSS teal

st.set_page_config(
    page_title="DSS – Family Tax Benefit Calculator 2024‑25",
    page_icon="🐞",
    layout="centered",
)

st.markdown(
    f"""
    <style>
        :root {{ --primary: {PRIMARY}; --accent: {ACCENT}; }}
        .stApp {{ font-family: 'Helvetica Neue', Arial, sans-serif; }}
        h1, h2, h3, h4 {{ color: var(--primary); }}
        .stButton>button {{ background-color: var(--primary); color: #fff; border: none; }}
        .stButton>button:hover {{ background-color: var(--accent); }}
        .dss-header span.beetle {{ display:inline-block; filter:hue-rotate(90deg) saturate(3); }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Optional banners/icons
if os.path.exists("dss_logo.png"):
    st.image("dss_logo.png", width=180)
icon_html = (
    "<img src='green_beetle.png' width='32' style='vertical-align:middle;margin-right:8px;'>"
    if os.path.exists("green_beetle.png")
    else "<span class='beetle'>🐞</span>&nbsp;"
)
st.markdown(f"<div class='dss-header'>{icon_html}<h1 style='display:inline'>Family Tax Benefit Calculator 2024‑25</h1></div>", unsafe_allow_html=True)

# — Rates — ---------------------------------------------------------------
RATES: Dict[str, object] = {
    "ftb_a": {
        "max_pf": {"0_12": 222.04, "13_15": 288.82, "16_19": 288.82},  # 16‑19 in study
        "base_pf": {"0_12": 71.26, "13_plus": 71.26},  # base rate varies by age group
        "supplement": 916.15,
        "lower_ifa": 65_189,
        "higher_ifa": 115_997,
        "taper1": 0.20,
        "taper2": 0.30,
        "supplement_income_limit": 80_000,
    },
    "ftb_b": {
        "max_pf": {"under_5": 188.86, "5_to_18": 131.74},
        "supplement": 448.95,
        "secondary_free_area": 6_789,
        "primary_limit": 117_194,
        "taper": 0.20,
    },
    "compliance_penalty_pf": 34.44,
}

###############################################################################
# DATA CLASSES
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
    children: List[Child] = None
    on_income_support: bool = False

###############################################################################
# HELPER FUNCTIONS
###############################################################################

def pf_to_annual(pf: float) -> float:
    """Convert fortnightly payment to annual amount"""
    return round(pf * 26, 2)


def child_max_rate_pf(child: Child) -> float:
    """Get maximum fortnightly rate for a child based on age"""
    if child.age <= 12:
        return RATES["ftb_a"]["max_pf"]["0_12"]
    elif child.age <= 15:
        return RATES["ftb_a"]["max_pf"]["13_15"]
    else:  # 16-19 (must be in study)
        return RATES["ftb_a"]["max_pf"]["16_19"]


def child_base_rate_pf(child: Child) -> float:
    """Get base fortnightly rate for a child"""
    if child.age <= 12:
        return RATES["ftb_a"]["base_pf"]["0_12"]
    else:
        return RATES["ftb_a"]["base_pf"]["13_plus"]


def child_penalties_pf(child: Child) -> float:
    """Calculate compliance penalties for a child"""
    penalty = 0.0
    
    # Immunisation penalty applies to all children
    if not child.immunised:
        penalty += RATES["compliance_penalty_pf"]
    
    # Healthy Start penalty only applies to children aged 4-5
    if 4 <= child.age <= 5 and not child.healthy_start:
        penalty += RATES["compliance_penalty_pf"]
    
    return penalty

###############################################################################
# CALCULATE FTB PART A (Fixed calculation logic)
###############################################################################

def calc_ftb_part_a_method_1(fam: Family):
    """Calculate FTB Part A using Method 1 (higher maximum rates)"""
    rates = RATES["ftb_a"]
    
    # Step 1: Calculate per-child entitlements
    child_records = []
    for child in fam.children:
        # Method 1 uses higher maximum rates
        max_rate_pf = child_max_rate_pf(child)
        base_rate_pf = child_base_rate_pf(child)
        
        # Apply maintenance action test first (caps at base rate)
        if not child.maintenance_ok:
            max_rate_pf = min(max_rate_pf, base_rate_pf)
        
        # Apply compliance penalties
        penalty_pf = child_penalties_pf(child)
        max_rate_pf = max(max_rate_pf - penalty_pf, 0)
        base_rate_pf = max(base_rate_pf - penalty_pf, 0)
        
        child_records.append({
            'max_rate': max_rate_pf,
            'base_rate': base_rate_pf,
            'age': child.age
        })

    total_max_pf = sum(record['max_rate'] for record in child_records)
    total_base_pf = sum(record['base_rate'] for record in child_records)
    
    # Step 2: Apply Method 1 income test
    if fam.on_income_support:
        payable_pf = total_max_pf
    else:
        total_income = fam.primary_income + fam.secondary_income
        
        if total_income <= rates["lower_ifa"]:
            # Below lower threshold - full maximum rate
            payable_pf = total_max_pf
        elif total_income <= rates["higher_ifa"]:
            # Between thresholds - 20c taper down to base rate floor
            excess = total_income - rates["lower_ifa"]
            reduction = excess * rates["taper1"]
            payable_pf = max(total_max_pf - reduction, total_base_pf)
        else:
            # Above higher threshold - 30c taper from base rate
            excess_above_higher = total_income - rates["higher_ifa"]
            base_reduction = excess_above_higher * rates["taper2"]
            payable_pf = max(total_base_pf - base_reduction, 0)

    return {
        "payable_pf": payable_pf,
        "total_max_pf": total_max_pf,
        "total_base_pf": total_base_pf,
        "method": "Method 1"
    }


def calc_ftb_part_a_method_2(fam: Family):
    """Calculate FTB Part A using Method 2 (base rates only)"""
    rates = RATES["ftb_a"]
    
    # Step 1: Calculate per-child entitlements using base rates only
    child_records = []
    for child in fam.children:
        # Method 2 maximum rate = Method 1 base rate
        base_rate_pf = child_base_rate_pf(child)
        
        # Apply maintenance action test (not applicable for Method 2)
        # Apply compliance penalties
        penalty_pf = child_penalties_pf(child)
        base_rate_pf = max(base_rate_pf - penalty_pf, 0)
        
        child_records.append({
            'max_rate': base_rate_pf,  # Method 2 max = Method 1 base
            'base_rate': base_rate_pf,
            'age': child.age
        })

    total_max_pf = sum(record['max_rate'] for record in child_records)
    
    # Step 2: Apply Method 2 income test (30c taper from higher income free area)
    if fam.on_income_support:
        payable_pf = total_max_pf
    else:
        total_income = fam.primary_income + fam.secondary_income
        
        if total_income <= rates["higher_ifa"]:
            # Below higher threshold - full Method 2 maximum rate
            payable_pf = total_max_pf
        else:
            # Above higher threshold - 30c taper from Method 2 maximum
            excess_above_higher = total_income - rates["higher_ifa"]
            reduction = excess_above_higher * rates["taper2"]
            payable_pf = max(total_max_pf - reduction, 0)

    return {
        "payable_pf": payable_pf,
        "total_max_pf": total_max_pf,
        "total_base_pf": total_max_pf,  # Same for Method 2
        "method": "Method 2"
    }


def calc_ftb_part_a(fam: Family):
    """Calculate FTB Part A using both methods and return the higher rate"""
    rates = RATES["ftb_a"]
    
    # Calculate using both methods
    method_1_result = calc_ftb_part_a_method_1(fam)
    method_2_result = calc_ftb_part_a_method_2(fam)
    
    # Choose the higher of the two methods
    if method_1_result["payable_pf"] >= method_2_result["payable_pf"]:
        chosen_result = method_1_result
        payable_pf = method_1_result["payable_pf"]
    else:
        chosen_result = method_2_result  
        payable_pf = method_2_result["payable_pf"]

    # Calculate annual amounts
    annual_core = pf_to_annual(payable_pf)
    
    # Determine supplement eligibility
    family_ati = fam.primary_income + fam.secondary_income
    supplement_eligible = (
        payable_pf > 0 and 
        (fam.on_income_support or family_ati <= rates["supplement_income_limit"])
    )
    supplement = rates["supplement"] if supplement_eligible else 0.0

    return {
        "pf": round(payable_pf, 2),
        "annual": round(annual_core, 2),
        "supp": supplement,
        "annual_total": round(annual_core + supplement, 2),
        "debug": {
            "method_used": chosen_result["method"],
            "method_1_pf": round(method_1_result["payable_pf"], 2),
            "method_2_pf": round(method_2_result["payable_pf"], 2),
            "total_income": fam.primary_income + fam.secondary_income,
            "lower_ifa": rates["lower_ifa"],
            "higher_ifa": rates["higher_ifa"]
        }
    }

###############################################################################
# CALCULATE FTB PART B (Fixed calculation logic)
###############################################################################

def calc_ftb_part_b(fam: Family):
    """Calculate FTB Part B payment"""
    if not fam.children:
        return {"pf": 0, "annual": 0, "supp": 0, "annual_total": 0}
    
    rates = RATES["ftb_b"]
    
    # Find youngest child to determine rate
    youngest_age = min(child.age for child in fam.children)
    
    # Get base rate based on youngest child's age
    if youngest_age < 5:
        base_rate_pf = rates["max_pf"]["under_5"]
    else:
        base_rate_pf = rates["max_pf"]["5_to_18"]

    # Apply income tests
    if fam.partnered:
        # For couples: secondary earner test and primary earner limit
        if fam.secondary_income > rates["secondary_free_area"]:
            excess_secondary = fam.secondary_income - rates["secondary_free_area"]
            secondary_reduction = excess_secondary * rates["taper"]
            payable_pf = max(base_rate_pf - secondary_reduction, 0)
        else:
            payable_pf = base_rate_pf
        
        # Primary earner cut-off
        if fam.primary_income > rates["primary_limit"]:
            payable_pf = 0.0
    else:
        # Single parent - gets full rate
        payable_pf = base_rate_pf

    # Calculate annual amounts
    annual_core = pf_to_annual(payable_pf)
    supplement = rates["supplement"] if payable_pf > 0 else 0.0

    return {
        "pf": round(payable_pf, 2),
        "annual": round(annual_core, 2),
        "supp": supplement,
        "annual_total": round(annual_core + supplement, 2)
    }

###############################################################################
# STREAMLIT SIDEBAR INPUTS
###############################################################################

st.sidebar.header("Household details")
partnered = st.sidebar.checkbox("Couple household", True)
primary_income = st.sidebar.number_input("Primary earner income ($ p.a.)", 0, 500_000, 50_000, 1_000, format="%d")
secondary_income = 0
if partnered:
    secondary_income = st.sidebar.number_input("Secondary earner income ($ p.a.)", 0, 500_000, 0, 1_000, format="%d")
receives_is = st.sidebar.checkbox("Receiving income support?")
num_kids = st.sidebar.number_input("Dependent children", 1, 10, 1, 1)

st.sidebar.markdown("---")
st.sidebar.header("Children details")

children: List[Child] = []
for i in range(int(num_kids)):
    with st.sidebar.expander(f"Child {i+1} details", expanded=(i == 0)):
        age = st.slider("Age", 0, 19, 5, 1, key=f"age_{i}")
        immun = st.checkbox("Immunised", True, key=f"imm_{i}")
        hs_applicable = 4 <= age <= 5
        if hs_applicable:
            hs = st.checkbox("Healthy‑Start check completed", True, key=f"hs_{i}")
        else:
            hs = True
            if age < 4:
                st.caption("Healthy-Start check not applicable (under 4)")
            else:
                st.caption("Healthy-Start check not applicable (over 5)")
        ma = st.checkbox("Maintenance action taken (if applicable)", True, key=f"ma_{i}")
    children.append(Child(age, immun, hs, ma))

fam = Family(partnered, primary_income, secondary_income, children, receives_is)

###############################################################################
# CALCULATE & DISPLAY
###############################################################################

# Auto-calculate on input changes
a = calc_ftb_part_a(fam)
b = calc_ftb_part_b(fam)

st.markdown("---")
st.header("Family Tax Benefit Calculation Results")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🏠 FTB Part A")
    st.metric("Fortnightly payment", f"${a['pf']:.2f}")
    st.metric("Annual (ex-supplement)", f"${a['annual']:,.2f}")
    st.metric("Annual supplement", f"${a['supp']:,.2f}")
    st.metric("**Total Annual Part A**", f"${a['annual_total']:,.2f}")

with col2:
    st.subheader("👶 FTB Part B")
    st.metric("Fortnightly payment", f"${b['pf']:.2f}")
    st.metric("Annual (ex-supplement)", f"${b['annual']:,.2f}")
    st.metric("Annual supplement", f"${b['supp']:,.2f}")
    st.metric("**Total Annual Part B**", f"${b['annual_total']:,.2f}")

st.markdown("---")
total_annual = a['annual_total'] + b['annual_total']
st.markdown(f"### 💰 **Total Family Tax Benefit (Annual): ${total_annual:,.2f}**")

# Show breakdown for debugging
if st.checkbox("Show calculation details"):
    st.subheader("Calculation Breakdown")
    
    st.write("**FTB Part A Details:**")
    total_income = fam.primary_income + fam.secondary_income
    st.write(f"- Total family income: ${total_income:,.2f}")
    st.write(f"- Lower income threshold: ${RATES['ftb_a']['lower_ifa']:,.2f}")
    st.write(f"- Higher income threshold: ${RATES['ftb_a']['higher_ifa']:,.2f}")
    
    if 'debug' in a:
        st.write(f"- **Method used: {a['debug']['method_used']}**")
        st.write(f"- Method 1 would pay: ${a['debug']['method_1_pf']:.2f} per fortnight")
        st.write(f"- Method 2 would pay: ${a['debug']['method_2_pf']:.2f} per fortnight")
        st.write(f"- Higher rate selected: ${a['pf']:.2f} per fortnight")
        
        # Explain which method applies
        if total_income <= RATES['ftb_a']['higher_ifa']:
            st.info("💡 **Income below higher threshold:** Both methods calculated, higher rate selected")
        else:
            st.info("💡 **Income above higher threshold:** Method 2 automatically applies, but compared with adjusted Method 1")
    
    st.write("**FTB Part B Details:**")
    if fam.partnered:
        st.write(f"- Primary earner income: ${fam.primary_income:,.2f}")
        st.write(f"- Secondary earner income: ${fam.secondary_income:,.2f}")
        st.write(f"- Secondary earner free area: ${RATES['ftb_b']['secondary_free_area']:,.2f}")
        st.write(f"- Primary earner limit: ${RATES['ftb_b']['primary_limit']:,.2f}")
    else:
        st.write("- Single parent: Full rate applies (no income test)")

# Add method explanation
st.markdown("---")
with st.expander("ℹ️ How FTB Part A is calculated"):
    st.markdown("""
    **FTB Part A uses two calculation methods:**
    
    **Method 1 (Higher rates):**
    - Uses higher maximum rates for each child
    - Income test: 20¢ taper from lower threshold, then 30¢ taper above higher threshold  
    - Cannot go below base rate
    - Includes maintenance income test
    
    **Method 2 (Base rates):**
    - Maximum rate equals Method 1 base rate
    - Income test: 30¢ taper from higher income threshold only
    - No maintenance income test
    
    **The system calculates both methods and pays whichever is higher.**
    
    For families with income above the higher threshold ($115,997), the system:
    1. Calculates Method 2 rate
    2. Calculates adjusted Method 1 rate (with 30¢ taper above higher threshold)
    3. Pays the higher of the two
    """)

# Add information about the calculator
st.markdown("---")
st.info("""
**About this calculator:**
- Rates are current as of March 20, 2025 for the 2024-25 financial year
- Calculations follow the Family Assistance Guide methodology
- Part A uses a two-step income test with different taper rates
- Part B has separate tests for primary and secondary earners
- Compliance penalties apply for immunisation and health checks
- Supplements are paid annually if income conditions are met
""")

st.caption("This calculator is for estimation purposes only. Contact Services Australia for official calculations.")
