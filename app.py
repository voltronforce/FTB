"""Department of Social Services – Family Tax Benefit Calculator (2024‑25)
=====================================================================

*Rates current at 20 March 2025 – supplements displayed separately.*

This Streamlit app calculates Family Tax Benefit Parts A & B using official
rates and thresholds.  It incorporates the March 2025 updates and keeps the
original DSS‑style look‑and‑feel with:

* **DSS colour palette** (#00558B primary, #009CA6 accent).  
* **Logo banner** (optional – drop *dss_logo.png* in the same folder).  
* Clean two‑column layout with bold section dividers.  
* Primary action button styled in DSS teal.

Run with: `streamlit run ftb_streamlit_app_updated.py`
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import streamlit as st
import math
import os

###############################################################################
# BRANDING & PAGE CONFIG
###############################################################################

PRIMARY = "#00558B"  # DSS navy
ACCENT  = "#009CA6"  # DSS teal

st.set_page_config(
    page_title="DSS – Family Tax Benefit Calculator 2024‑25",
    page_icon="🧮",
    layout="centered",
    initial_sidebar_state="auto",
)

# Inject simple CSS to match DSS palette
st.markdown(
    f"""
    <style>
        :root {{ --primary: {PRIMARY}; --accent: {ACCENT}; }}
        .stApp {{ font-family: 'Helvetica Neue', Arial, sans-serif; }}
        h1, h2, h3, h4 {{ color: var(--primary); }}
        .stButton>button {{ background-color: var(--primary); color: #fff; border: none; }}
        .stButton>button:hover {{ background-color: var(--accent); }}
        .st-bb {{ color: var(--primary); }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Optional DSS logo banner
logo_path = "dss_logo.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=180)

st.markdown("<div class='dss-header'><h1>Family Tax Benefit Calculator 2024‑25</h1></div>", unsafe_allow_html=True)

###############################################################################
# RATE TABLE – 2024‑25 (Guide to Australian Government Payments, 20 Mar 2025)
###############################################################################

RATES_2025: Dict[str, object] = {
    "ftb_a": {
        "max_rate_pf": {"0_12": 222.04, "13_15": 288.82, "16_19_secondary": 288.82},
        "base_rate_pf": 71.26,
        "supplement_annual": 916.15,
        "lower_threshold": 65_189,
        "higher_threshold": 115_997,
        "primary_taper": 0.20,
        "secondary_taper": 0.30,
    },
    "ftb_b": {
        "max_rate_pf": {"<5": 188.86, "5_18": 131.74},
        "supplement_annual": 448.95,
        "secondary_earner_free_area": 6_789,
        "primary_earner_limit": 117_194,
        "taper": 0.20,
    },
    "compliance_reduction_pf": 34.44,
}

###############################################################################
# DATA STRUCTURES
###############################################################################

@dataclass
class Child:
    age: int
    immunised: bool = True
    healthy_start: bool = True
    maintenance_action_ok: bool = True

@dataclass
class Family:
    partnered: bool
    primary_income: float
    secondary_income: float = 0.0
    children: List[Child] = None
    receives_income_support: bool = False

###############################################################################
# CALCULATION HELPERS
###############################################################################

def pf_to_annual(amount_pf: float) -> float:
    return round(amount_pf * 26, 2)


def calc_ftb_a_child_pf(child: Child, fam_income: float, num_kids: int, on_income_support: bool) -> float:
    ra = RATES_2025["ftb_a"]
    # Core by age
    if child.age <= 12:
        core = ra["max_rate_pf"]["0_12"]
    elif child.age <= 15:
        core = ra["max_rate_pf"]["13_15"]
    else:
        core = ra["max_rate_pf"]["16_19_secondary"]

    # Income test
    if not on_income_support and fam_income > ra["lower_threshold"]:
        excess = fam_income - ra["lower_threshold"]
        if fam_income <= ra["higher_threshold"]:
            red = excess * ra["primary_taper"]
        else:
            red = (
                (ra["higher_threshold"] - ra["lower_threshold"]) * ra["primary_taper"] +
                (fam_income - ra["higher_threshold"]) * ra["secondary_taper"]
            )
        core = max(core - red / num_kids, 0)

    # Compliance penalties
    if not child.immunised:
        core -= RATES_2025["compliance_reduction_pf"]
    if 4 <= child.age <= 5 and not child.healthy_start:
        core -= RATES_2025["compliance_reduction_pf"]

    # Maintenance action test
    if not child.maintenance_action_ok:
        core = min(core, ra["base_rate_pf"])

    return max(core, 0)


def calc_ftb_a(fam: Family) -> Dict[str, float]:
    kids = len(fam.children)
    total_pf = sum(
        calc_ftb_a_child_pf(ch, fam.primary_income + fam.secondary_income, kids, fam.receives_income_support)
        for ch in fam.children
    )
    annual = pf_to_annual(total_pf)
    supp = RATES_2025["ftb_a"]["supplement_annual"] if total_pf > 0 else 0.0
    return {"pf": total_pf, "annual": annual, "supp": supp, "annual_total": annual + supp}


def calc_ftb_b(fam: Family) -> Dict[str, float]:
    rb = RATES_2025["ftb_b"]
    youngest = min(ch.age for ch in fam.children)
    base_pf = rb["max_rate_pf"]["<5" if youngest < 5 else "5_18"]

    if fam.partnered:
        sec_red = 0
        if fam.secondary_income > rb["secondary_earner_free_area"]:
            sec_red = (fam.secondary_income - rb["secondary_earner_free_area"]) * rb["taper"]
        core_pf = max(base_pf - sec_red, 0)
        if fam.primary_income > rb["primary_earner_limit"]:
            core_pf = 0
    else:
        core_pf = base_pf

    annual = pf_to_annual(core_pf)
    supp = rb["supplement_annual"] if core_pf > 0 else 0
    return {"pf": core_pf, "annual": annual, "supp": supp, "annual_total": annual + supp}

###############################################################################
# USER INTERFACE – INPUTS
###############################################################################

st.sidebar.header("Household Details")
partnered = st.sidebar.checkbox("Couple household", value=True)

pi = st.sidebar.number_input("Primary earner income ($ p.a.)", 0, 500000, 0, 1000, format="%d")
si = 0
if partnered:
    si = st.sidebar.number_input("Secondary earner income ($ p.a.)", 0, 500000, 0, 1000, format="%d")

receives_is = st.sidebar.checkbox("Receiving income support?", value=False)

num_kids = st.sidebar.number_input("Number of dependent children", 1, 10, 1, 1)

children: List[Child] = []
for i in range(int(num_kids)):
    with st.expander(f"Child {i+1} details"):
        age = st.slider("Age", 0, 19, 0, 1, key=f"age_{i}")
        immun = st.checkbox("Immunised", True, key=f"imm_{i}")
        hs = st.checkbox("Healthy‑Start check (age 4‑5)", True, key=f"hs_{i}")
        ma = st.checkbox("Maintenance action taken", True, key=f"ma_{i}")
    children.append(Child(age, immun, hs, ma))

fam = Family(partnered, pi, si, children, receives_is)

###############################################################################
# CALCULATE & DISPLAY RESULTS
###############################################################################

if st.button("Calculate FTB", key="calc_btn"):
    a = calc_ftb_a(fam)
    b = calc_ftb_b(fam)
    st.success("Calculation complete!")

    colA, colB = st.columns(2)
    with colA:
        st.subheader("FTB Part A")
        st.write(f"**Fortnightly:** ${a['pf']:.2f}")
        st.write(f"**Annual (ex‑supp):** ${a['annual']:.2f}")
        st.write(f"**Supplement:** ${a['supp']:.2f}")
        st.write(f"**Annual incl. supp:** ${a['annual_total']:.2f}")
    with colB:
        st.subheader("FTB Part B")
        st.write(f"**Fortnightly:** ${b['pf']:.2f}")
        st.write(f"**Annual (ex‑supp):** ${b['annual']:.2f}")
        st.write(f"**Supplement:** ${b['supp']:.2f}")
        st.write(f"**Annual incl. supp:** ${b['annual_total']:.2f}")

    st.markdown("---")
    total = a["annual_total"] + b["annual_total"]
    st.header(f"Total FTB (annual, after supplements): ${total:,.2f}")

###############################################################################
# RATE TABLE VIEWER (OPTIONAL)
###############################################################################

with st.expander("🔎 Show rate parameters (2024‑25)"):
    st.json(RATES_2025, expanded=False)
