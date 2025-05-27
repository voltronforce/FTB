# =============================================================================
# Family Tax Benefit (FTB) Calculator – 2024‑25 (Enhanced)
# =============================================================================
# This Streamlit application estimates Family Tax Benefit Part A & B payments
# for Australian families, including income‑test thresholds, validation, and
# contextual guidance. Styling follows Department of Social Services branding.
# =============================================================================

###############################################################################
# Streamlit Setup – MUST BE FIRST
###############################################################################
import streamlit as st

# Page configuration **must** be the first Streamlit command
st.set_page_config(
    page_title="Family Tax Benefit Calculator 2024‑25",
    page_icon="🐞",
    layout="wide",
    initial_sidebar_state="collapsed"
)

"""
Family Tax Benefit Calculator (2024‑25)
=======================================================================
"""

###############################################################################
# Imports & Setup
###############################################################################
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
import plotly.express as px
import numpy as np
import logging
import traceback

###############################################################################
# Logging & Error‑Handling Helpers
###############################################################################
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s – %(levelname)s – %(message)s",
)
logger = logging.getLogger(__name__)

def safe_calculate(func, *args, **kwargs):
    """Wrapper that logs exceptions and returns zeroed result dicts."""
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        logger.error(f"Calculation error in {func.__name__}: {exc}")
        logger.error(traceback.format_exc())
        st.error(f"❌ Calculation error: {exc}")
        return {"pf": 0, "annual": 0, "supp": 0, "annual_total": 0}

###############################################################################
# Branding – CSS
###############################################################################
PRIMARY = "#00558B"   # DSS navy
ACCENT  = "#009CA6"   # DSS teal
SECONDARY = "#4A90E2" # Light blue
SUCCESS = "#28A745"   # Green
WARNING = "#FFC107"   # Amber
LIGHT_GRAY = "#F8F9FA"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    :root {{ --primary:{PRIMARY}; --accent:{ACCENT}; --secondary:{SECONDARY}; --success:{SUCCESS}; --warning:{WARNING}; --light-gray:{LIGHT_GRAY}; }}
    html,body {{ font-family:'Inter',sans-serif;background:#fafbfc; }}
    .main .block-container {{ padding-top:1rem;max-width:1200px; }}
    h1,h2,h3 {{ color:var(--primary);font-weight:600;letter-spacing:-0.025em;margin-bottom:1rem; }}
    /* Buttons */
    .stButton>button {{ background:linear-gradient(135deg,var(--primary)0%,var(--accent)100%);color:#fff;border:none;border-radius:8px;font-weight:500;padding:0.6rem 1.5rem;transition:0.2s;box-shadow:0 2px 8px rgba(0,85,139,0.15);font-size:0.95rem;min-height:44px; }}
    .stButton>button:hover {{ transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,85,139,0.25);background:linear-gradient(135deg,#003d5c 0%,#007580 100%); }}
    .stButton>button:active {{ transform:translateY(0);box-shadow:0 2px 6px rgba(0,85,139,0.2); }}
    /* Cards */
    .calc-card {{ background:#fff;padding:1.5rem;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.06);margin-bottom:1.5rem;border:1px solid #e9ecef; }}
    .result-card {{ background:linear-gradient(135deg,var(--success)0%,#20c653 100%);color:#fff;padding:1.5rem;border-radius:12px;box-shadow:0 4px 16px rgba(40,167,69,0.15);margin:1rem 0; }}
    .info-card {{ background:linear-gradient(135deg,#e3f2fd 0%,#bbdefb 100%);color:var(--primary);padding:1.2rem;border-radius:10px;margin:1rem 0;border-left:4px solid var(--secondary); }}
    .warning-card {{ background:linear-gradient(135deg,#fff3cd 0%,#ffeaa7 100%);color:#856404;padding:1.2rem;border-radius:10px;margin:1rem 0;border-left:4px solid var(--warning); }}
    /* Metrics */
    .metric-container {{ background:#fff;padding:1.2rem;border-radius:10px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.04);border-left:3px solid var(--accent); }}
</style>
""", unsafe_allow_html=True)

###############################################################################
# Hero Banner
###############################################################################
st.markdown(
    """
    <div class='hero-banner' style='background:linear-gradient(135deg,var(--primary)0%,var(--accent)100%);color:#fff;padding:2rem;border-radius:12px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.1);margin-bottom:2rem;'>
        <div class='logo' style='font-size:3rem;margin-bottom:0.5rem;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.1));'>🐞</div>
        <div class='title' style='font-size:2.2rem;font-weight:700;margin-bottom:0.3rem;'>Family Tax Benefit Calculator</div>
        <div class='subtitle' style='font-size:1rem;font-weight:400;opacity:0.9;'>2024‑25</div>
    </div>
    """,
    unsafe_allow_html=True,
)

###############################################################################
# Constants – Rates (2024‑25)
###############################################################################
RATES: Dict[str, Dict] = {
    "ftb_a": {
        "max_pf": {"0_12":222.04,"13_15":288.82,"16_19":288.82},
        "base_pf":{"0_12":71.26,"13_plus":71.26},
        "supplement":916.15,
        "lower_ifa":65_189,
        "higher_ifa":115_997,
        "taper1":0.20,
        "taper2":0.30,
        "supplement_income_limit":80_000,
    },
    "ftb_b": {
        "max_pf":{"under_5":188.86,"5_to_18":131.74},
        "energy_pf":{"under_5":2.80,"5_to_18":1.96},
        "supplement":448.95,
        "secondary_free_area":6_789,
        "nil_secondary":{"under_5":33_653,"5_to_12":26_207},
        "primary_limit":117_194,
        "taper":0.20,
    },
    "compliance_penalty_pf":34.44,
}

###############################################################################
# Data Models
###############################################################################
@dataclass
class Child:
    age:int
    immunised:bool=True
    healthy_start:bool=True
    maintenance_ok:bool=True

@dataclass
class Family:
    partnered:bool
    primary_income:float
    secondary_income:float=0.0
    children:List[Child]|None=None
    on_income_support:bool=False

###############################################################################
# Helper Utilities
###############################################################################

def pf_to_annual(pf:float)->float: return round(pf*26,2)

def child_max_rate_pf(c:Child)->float:
    if c.age<=12: return RATES["ftb_a"]["max_pf"]["0_12"]
    if c.age<=15: return RATES["ftb_a"]["max_pf"]["13_15"]
    return RATES["ftb_a"]["max_pf"]["16_19"]

def child_base_rate_pf(c:Child)->float:
    return RATES["ftb_a"]["base_pf"]["0_12"] if c.age<=12 else RATES["ftb_a"]["base_pf"]["13_plus"]

def child_penalties_pf(c:Child)->float:
    pen=0.0
    if not c.immunised:
        pen+=RATES["compliance_penalty_pf"]
    if 4<=c.age<=5 and not c.healthy_start:
        pen+=RATES["compliance_penalty_pf"]
    return pen

###############################################################################
# FTB Calculation Functions
###############################################################################

def calc_ftb_part_a(fam:Family)->Dict:
    r=RATES["ftb_a"]
    total_max_pf=total_base_pf=0.0
    for ch in fam.children:
        max_pf=child_max_rate_pf(ch)
        base_pf=child_base_rate_pf(ch)
        if not ch.maintenance_ok:
            max_pf=min(max_pf,base_pf)
        pen=child_penalties_pf(ch)
        max_pf=max(max_pf-pen,0)
        base_pf=max(base_pf-pen,0)
        total_max_pf+=max_pf
        total_base_pf+=base_pf
    ati=fam.primary_income+fam.secondary_income
    if fam.on_income_support or ati<=r["lower_ifa"]:
        m1_pf=total_max_pf
    elif ati<=r["higher_ifa"]:
        m1_pf=max(total_max_pf-(ati-r["lower_ifa"])*r["taper1"]/26,total_base_pf)
    else:
        m1_pf=max(total_base_pf-(ati-r["higher_ifa"])*r["taper2"]/26,0)
    # Method 2 – base rate only
    base_total_pf=sum(max(child_base_rate_pf(ch)-child_penalties_pf(ch),0) for ch in fam.children)
    if fam.on_income_support or ati<=r["higher_ifa"]:
        m2_pf=base_total_pf
    else:
        m2_pf=max(base_total_pf-(ati-r["higher_ifa"])*r["taper2"]/26,0)
    best_pf=max(m1_pf,m2_pf)
    annual_core=pf_to_annual(best_pf)
    supp=r["supplement"] if best_pf>0 and (fam.on_income_support or ati<=r["supplement_income_limit"]) else 0
    return {"pf":round(best_pf,2),"annual":annual_core,"supp":supp,"annual_total":round(annual_core+supp,2)}

def calc_ftb_part_b(fam:Family,include_es:bool=False)->Dict:
    r=RATES["ftb_b"]
    if not fam.children:
        return {k:0 for k in ("pf","annual","supp","energy","annual_total")}
    youngest=min(ch.age for ch in fam.children)
    std_pf=r["max_pf"]["under_5"] if youngest<5 else r["max_pf"]["5_to_18"]
    energy_pf=r["energy_pf"]["under_5"] if youngest<5 else r["energy_pf"]["5_to_18"]
    # Secondary income test
    if fam.secondary_income<=r["secondary_free_area"]:
        sec_red=0
    else:
        sec_red=(fam.secondary_income-r["secondary_free_area"])*r["taper"]/26
    base_pf=max(std_pf-sec_red,0)
    # Primary income test
    if fam.primary_income>r["primary_limit"]:
        base_pf=0
    annual_core=pf_to_annual(base_pf)
    energy_annual=pf_to_annual(energy_pf) if include_es and base_pf>0 else 0
    supp=r["supplement"] if base_pf>0 else 0
    return {"pf":round(base_pf,2),"annual":annual_core,"supp":supp,"energy":energy_annual,"annual_total":round(annual_core+supp+energy_annual,2)}

###############################################################################
# **Fixed** income‑limit calculation for FTB Part A
###############################################################################

def find_ftb_a_cutoff(family_structure:Dict)->Dict:
    r=RATES["ftb_a"]
    total_max_pf=total_base_pf=0.0
    for age in family_structure["child_ages"]:
        if age<=12:
            max_pf=r["max_pf"]["0_12"]; base_pf=r["base_pf"]["0_12"]
        elif age<=15:
            max_pf=r["max_pf"]["13_15"]; base_pf=r["base_pf"]["13_plus"]
        else:
            max_pf=r["max_pf"]["16_19"]; base_pf=r["base_pf"]["13_plus"]
        total_max_pf+=max_pf
        total_base_pf+=base_pf
    # Stage 1 – within 20 % taper
    diff_pf=total_max_pf-total_base_pf
    diff_ann=diff_pf*26
    stage1_inc_needed=diff_ann/r["taper1"]
    stage1_range=r["higher_ifa"]-r["lower_ifa"]
    stage1_inc_used=min(stage1_inc_needed,stage1_range)
    stage1_reduction=stage1_inc_used*r["taper1"]
    pay_after_stage1=(total_max_pf*26)-stage1_reduction
    remaining_pf=max(pay_after_stage1/26,total_base_pf)
    # Stage 2 – within 30 % taper
    stage2_inc_needed=(remaining_pf*26)/r["taper2"]
    zero_income=r["lower_ifa"]+stage1_inc_used+stage2_inc_needed
    return {"supplement_cutoff":r["supplement_income_limit"],"taper_start":r["higher_ifa"],"zero_payment":round(zero_income)}

###############################################################################
# FTB Part B thresholds
###############################################################################

def find_ftb_b_cutoff(family_structure:Dict)->Dict:
    r=RATES["ftb_b"]
    youngest=min(family_structure["child_ages"]) if family_structure["child_ages"] else 5
    secondary_cutoff=r["nil_secondary"]["under_5"] if youngest<5 else r["nil_secondary"]["5_to_12"]
    return {"primary_limit":r["primary_limit"],"secondary_free_area":r["secondary_free_area"],"secondary_cutoff":secondary_cutoff}

###############################################################################
# Validation & Warnings
###############################################################################

def validate_and_show_warnings(family:Family):
    warnings=[]
    total_income=family.primary_income+family.secondary_income
    if total_income>300_000:
        warnings.append("⚠️ Very high income – FTB payments likely $0")
    for i,ch in enumerate(family.children,1):
        if ch.age>19:
            warnings.append(f"⚠️ Child {i} over 19 – may not be eligible for FTB")
        elif 16<=ch.age<=19:
            warnings.append(f"ℹ️ Child {i} aged 16‑19 – study requirements apply")
    non_compliant=[]
    for i,ch in enumerate(family.children,1):
        if not ch.immunised:
            non_compliant.append(f"Child {i} (immunisation)")
        if 4<=ch.age<=5 and not ch.healthy_start:
            non_compliant.append(f"Child {i} (health check)")
    if non_compliant:
        warnings.append("⚠️ Compliance penalties apply: "+", ".join(non_compliant))
    if warnings:
        st.markdown('<div class="warning-card">',unsafe_allow_html=True)
        st.markdown("**Important Notes:**")
        for w in warnings:
            st.markdown(f"• {w}")
        st.markdown('</div>',unsafe_allow_html=True)

###############################################################################
# UI Helpers
###############################################################################

def render_child_input_section():
    st.markdown('<div class="calc-card">',unsafe_allow_html=True)
    st.markdown('<div class="section-header">👶 Children Details</div>',unsafe_allow_html=True)
    if 'children_data' not in st.session_state:
        st.session_state.children_data=[]
    col1,col2=st.columns([2,1])
    with col1:
        num_children=st.number_input("Number of children",0,10,len(st.session_state.children_data))
    with col2:
        st.write("")
        if st.button("Update Children Count"):
            st.session_state.children_data=[{"age":5,"immunised":True,"healthy_start":True,"maintenance_ok":True} for _ in range(num_children)]
            st.rerun()
    children=[]
    for i in range(num_children):
        if i>=len(st.session_state.children_data):
            st.session_state.children_data.append({"age":5,"immunised":True,"healthy_start":True,"maintenance_ok":True})
        with st.expander(f"Child {i+1} Details",expanded=i<2):
            col1,col2=st.columns(2)
            with col1:
                age=st.number_input("Age",0,19,st.session_state.children_data[i]["age"],key=f"age_{i}")
                immunised=st.checkbox("Immunised",st.session_state.children_data[i]["immunised"],key=f"imm_{i}")
            with col2:
                healthy_start=st.checkbox("Healthy Start (4‑5 yrs)",st.session_state.children_data[i]["healthy_start"],key=f"hs_{i}")
                maintenance_ok=st.checkbox("Maintenance Action Met",st.session_state.children_data[i]["maintenance_ok"],key=f"maint_{i}")
            st.session_state.children_data[i]={"age":age,"immunised":immunised,"healthy_start":healthy_start,"maintenance_ok":maintenance_ok}
            children.append(Child(age,immunised,healthy_start,maintenance_ok))
    st.markdown('</div>',unsafe_allow_html=True)
    return children


def display_results(ftb_a:Dict,ftb_b:Dict):
    """Enhanced results card with context."""
    st.markdown('<div class="result-card">',unsafe_allow_html=True)
    st.markdown("### 💰 Your FTB Payment Summary")
    col1,col2=st.columns(2)
    with col1:
        st.markdown("**FTB Part A**")
        st.metric("Fortnightly",f"${ftb_a['pf']:.2f}")
        st.metric("Annual Core",f"${ftb_a['annual']:,.2f}")
        st.metric("Annual Supplement",f"${ftb_a['supp']:,.2f}")
        st.metric("**Total Annual**",f"**${ftb_a['annual_total']:,.2f}**")
    with col2:
        st.markdown("**FTB Part B**")
        st.metric("Fortnightly",f"${ftb_b['pf']:.2f}")
        st.metric("Annual Core",f"${ftb_b['annual']:,.2f}")
        st.metric("Annual Supplement",f"${ftb_b['supp']:,.2f}")
        if ftb_b.get('energy',0)>0:
            st.metric("Energy Supplement",f"${ftb_b['energy']:,.2f}")
        st.metric("**Total Annual**",f"**${ftb_b['annual_total']:,.2f}**")
    st.markdown('---')
    tot_pf=ftb_a['pf']+ftb_b['pf']
    tot_ann=ftb_a['annual_total']+ftb_b['annual_total']
    col1,col2=st.columns(2)
    with col1:
        st.metric("**Combined Fortnightly**",f"**${tot_pf:.2f}**")
    with col2:
        st.metric("**Combined Annual Total**",f"**${tot_ann:,.2f}**")
    st.markdown('</div>',unsafe_allow_html=True)
    # Context
    if tot_ann>0:
        st.markdown('<div class="info-card">',unsafe_allow_html=True)
        st.markdown("**💡 Important Information:**")
        st.markdown("• Payments are estimates based on current rates and your inputs")
        st.markdown("• FTB A supplement is paid as a lump‑sum after tax‑time")
        if ftb_b['pf']>0:
            st.markdown("• FTB B is only payable to single parents or where one partner earns <$6,789")
        st.markdown('</div>',unsafe_allow_html=True)

###############################################################################
# Main Application – Tabs
###############################################################################

tab_calc,tab_limits,tab_analysis,tab_guide,tab_rates=st.tabs([
    "🧮 Calculator","🔄 Income Limits","📊 Payment Analysis","📋 Eligibility Guide","📖 Rate Information"])

# ---------------------------------------------------------------------------
# Tab 1 – Calculator
# ---------------------------------------------------------------------------
with tab_calc:
    st.markdown("### Calculate your Family Tax Benefit payments")
    st.markdown('<div class="calc-card">',unsafe_allow_html=True)
    st.markdown('<div class="section-header">👥 Family Structure</div>',unsafe_allow_html=True)
    col1,col2=st.columns(2)
    with col1:
        partnered=st.selectbox("Family Type",["Single Parent","Couple/Partnered"],0)=="Couple/Partnered"
        primary_income=st.number_input("Primary Income (annual)",0.0,300_000.0,50_000.0,step=1_000.0,format="%.0f")
    with col2:
        on_income_support=st.checkbox("Receiving income‑support payment")
        secondary_income=st.number_input("Partner's Income (annual)",0.0,300_000.0,0.0,step=1_000.0,format="%.0f") if partnered else 0.0
    st.markdown('</div>',unsafe_allow_html=True)

    children=render_child_input_section()

    # --- Calculate Button ---
    st.markdown('---')
    col1,col2,col3=st.columns([1,2,1])
    with col2:
        if st.button("Calculate My FTB Payments",type="primary",use_container_width=True):
            if not children:
                st.error("⚠️ Add at least one child to calculate FTB payments.")
            else:
                family=Family(partnered,primary_income,secondary_income,children,on_income_support)
                validate_and_show_warnings(family)
                ftb_a=safe_calculate(calc_ftb_part_a,family)
                ftb_b=safe_calculate(calc_ftb_part_b,family,include_es=True)
                if ftb_a['pf']<0 or ftb_b['pf']<0:
                    st.error("⚠️ Calculation error detected. Please check inputs.")
                else:
                    display_results(ftb_a,ftb_b)
                    tot_ann=ftb_a['annual_total']+ftb_b['annual_total']
                    if tot_ann==0:
                        st.info("💡 No FTB entitlement based on provided incomes.")
                    elif tot_ann<1_000:
                        st.info("💡 Low payment amount – verify child details and income.")

# ---------------------------------------------------------------------------
# Tab 2 – Income Limits
# ---------------------------------------------------------------------------
with tab_limits:
    st.markdown("### Find Income Thresholds for Your Family")
    st.markdown('<div class="info-card">',unsafe_allow_html=True)
    st.markdown("**Income‑Limit Calculator**: Discover where your FTB begins to reduce or stops.")
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('<div class="calc-card">',unsafe_allow_html=True)
    st.markdown('<div class="section-header">👥 Family Structure</div>',unsafe_allow_html=True)
    col1,col2=st.columns(2)
    with col1:
        rev_partnered=st.selectbox("Family Type",["Single Parent","Couple/Partnered"],key="rev_ft",index=0)=="Couple/Partnered"
        rev_children_num=st.number_input("Number of children",1,10,2,key="rev_nc")
    with col2:
        st.markdown("**Child Ages:**")
        rev_ages=[st.number_input(f"Child {i+1} age",0,19,5+i*2,key=f"rev_age_{i}") for i in range(rev_children_num)]
    st.markdown('</div>',unsafe_allow_html=True)
    if st.button("Calculate Income Thresholds",type="primary"):
        family_structure={"child_ajes":rev_partnered,"child_ages":rev_ages}
        try:
            ftb_a_lim=find_ftb_a_cutoff({"child_ages":rev_ages})
            ftb_b_lim=find_ftb_b_cutoff({"child_ages":rev_ages})
            st.markdown('<div class="result-card">',unsafe_allow_html=True)
            st.markdown("### 💡 Income Threshold Analysis")
            col1,col2=st.columns(2)
            with col1:
                st.markdown("**FTB Part A Thresholds**")
                st.metric("Supplement Income Limit",f"${ftb_a_lim['supplement_cutoff']:,}")
                st.metric("Higher Taper Begins",f"${ftb_a_lim['taper_start']:,}")
                st.metric("Payment Stops",f"${ftb_a_lim['zero_payment']:,}")
            with col2:
                st.markdown("**FTB Part B Thresholds**")
                st.metric("Primary Income Limit",f"${ftb_b_lim['primary_limit']:,}")
                st.metric("Secondary Free Area",f"${ftb_b_lim['secondary_free_area']:,}")
                st.metric("Secondary Income Cutoff",f"${ftb_b_lim['secondary_cutoff']:,}")
            st.markdown('</div>',unsafe_allow_html=True)
            st.markdown('<div class="info-card">',unsafe_allow_html=True)
            st.markdown("**Understanding Your Thresholds:**")
            st.markdown(f"• Below ${ftb_a_lim['supplement_cutoff']:,}: Full FTB A incl. supplement")
            st.markdown(f"• ${ftb_a_lim['supplement_cutoff']:,}‑${ftb_a_lim['taper_start']:,}: Full FTB A, no supplement")
            st.markdown(f"• ${ftb_a_lim['taper_start']:,}‑${ftb_a_lim['zero_payment']:,}: Reduced FTB A")
            st.markdown(f"• Above ${ftb_a_lim['zero_payment']:,}: No FTB A")
            st.markdown('</div>',unsafe_allow_html=True)
        except Exception as exc:
            st.error(f"Error calculating thresholds: {exc}")
            logger.error(traceback.format_exc())

# ---------------------------------------------------------------------------
# Tab 3 – Payment Analysis (simplified – unchanged)
# ---------------------------------------------------------------------------
with tab_analysis:
    st.markdown("### Payment vs Income Analysis")
    st.markdown('<div class="info-card">',unsafe_allow_html=True)
    st.markdown("Visualise how income changes affect FTB Part A payments (illustrative).")
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('<div class="calc-card">',unsafe_allow_html=True)
    st.markdown('<div class="section-header">📈 Analysis Parameters</div>',unsafe_allow_html=True)
    col1,col2=st.columns(2)
    with col1:
        base_income=st.number_input("Base income",0.0,200_000.0,80_000.0,step=5_000.0,format="%.0f")
    with col2:
        income_range=st.slider("Income range (+/‑)",5_000,50_000,20_000,step=5_000)
    st.markdown('</div>',unsafe_allow_html=True)
    if st.button("Generate Payment Analysis",type="primary"):
        incomes=np.arange(base_income-income_range,base_income+income_range+1,1_000)
        payments=[max(5773-(max(i-65_189,0))*0.20,max(1853-(max(i-115_997,0))*0.30,0)) for i in incomes]
        df=pd.DataFrame({"Income":incomes,"FTB_A_Annual":payments})
        fig=px.line(df,x="Income",y="FTB_A_Annual",title="FTB A vs Income",labels={"Income":"Annual Income ($)","FTB_A_Annual":"Annual FTB A ($)"})
        fig.update_traces(line_color=PRIMARY,line_width=3)
        st.plotly_chart(fig,use_container_width=True)

# Tabs 4 & 5 remain identical to earlier version – omitted for brevity in this snippet
# (Eligibility guide and rate tables – copy from the previous script.)

###############################################################################
# Session State Initialisation
###############################################################################
if 'app_initialized' not in st.session_state:
    st.session_state.app_initialized=True
    st.session_state.children_data=[]
