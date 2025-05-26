"""Department of Social Services – Family Tax Benefit Calculator (2024‑25)
=====================================================================

*Rates current at 20 March 2025 – supplements displayed separately.*

This Streamlit app calculates Family Tax Benefit Parts A & B in line with the
**Family Assistance Guide** (sections 3.1.1‑3.1.9) for the 2024‑25 year.  It
implements the two‑step ordinary‐income test for Part A (20 c taper to the
**base‑rate floor**, then a 30 c taper on the base rate) and applies child‑level
penalties for immunisation, Healthy‑Start, and maintenance action.

Styling retains the DSS navy/teal palette and the optional *Budget Beetle* 🐞.

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
# CONSTANTS & RATE TABLE (20 Mar 2025)
###############################################################################

PRIMARY = "#00558B"  # DSS navy
ACCENT  = "#009CA6"  # DSS teal

st.set_page_config(
    page_title="DSS – Family Tax Benefit Calculator 2024‑25",
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
st.markdown(f"<div class='dss-header'>{icon_html}<h1 style='display:inline'>Family Tax Benefit Calculator 2024‑25</h1></div>", unsafe_allow_html=True)

# — Rates — ---------------------------------------------------------------
RATES: Dict[str, object] = {
    "ftb_a": {
        "max_pf": {"0_12": 222.04, "13_15": 288.82, "16_19": 288.82},  # 16‑19 in study
        "base_pf": 71.26,  # per child (eldest ‑ simplified)
        "supplement": 916.15,
        "lower_ifa": 65_189,
        "higher_ifa": 115_997,
        "taper1": 0.20,
        "taper2": 0.30,
    },
    "ftb_b": {
        "max_pf": {"<5": 188.86, "5_18": 131.74},
        "supplement": 448.95,
        "secondary_free_area": 6_789,
        "primary_limit": 117_194,
        "taper": 0.20,
    },
    "compliance_pf": 34.44,
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
    return round(pf * 26, 2)


def child_max_rate_pf(child: Child) -> float:
    if child.age <= 12:
        return RATES["ftb_a"]["max_pf"]["0_12"]
    elif child.age <= 15:
        return RATES["ftb_a"]["max_pf"]["13_15"]
    else:
        return RATES["ftb_a"]["max_pf"]["16_19"]


def child_penalties_pf(child: Child) -> float:
    penalty = 0.0
    if not child.immunised:
        penalty += RATES["compliance_pf"]
    if 4 <= child.age <= 5 and not child.healthy_start:
        penalty += RATES["compliance_pf"]
    return penalty

###############################################################################
# CALCULATE FTB PART A (matches FAG 3.1.8.10 et seq.)
###############################################################################

def calc_ftb_part_a(fam: Family):
    rates = RATES["ftb_a"]
    # 1. Build per‑child adjusted max & base rates (applying penalties & maintenance test)
    child_records = []
    for ch in fam.children:
        max_pf = child_max_rate_pf(ch)
        base_pf = rates["base_pf"]
        penalty = child_penalties_pf(ch)
        # maintenance test – entitlement capped at base
        if not ch.maintenance_ok:
            max_pf = min(max_pf, base_pf)
        # apply penalties to both max & base amounts
        max_pf = max(max_pf - penalty, 0)
        base_pf = max(base_pf - penalty, 0)
        child_records.append((max_pf, base_pf))

    max_total_pf = sum(r[0] for r in child_records)
    base_total_pf = sum(r[1] for r in child_records)

    # 2. Ordinary income test
    if fam.on_income_support:
        payable_pf = max_total_pf  # full max if on IS
    else:
        income = fam.primary_income + fam.secondary_income
        if income <= rates["lower_ifa"]:
            payable_pf = max_total_pf
        elif income <= rates["higher_ifa"]:
            reduction = (income - rates["lower_ifa"]) * rates["taper1"]
            payable_pf = max(max_total_pf - reduction, base_total_pf)
        else:
            # above higher IFA – base‑rate only then tapered
            excess_high = income - rates["higher_ifa"]
            base_after_30 = max(base_total_pf - excess_high * rates["taper2"], 0)
            payable_pf = base_after_30

    annual_core = pf_to_annual(payable_pf)
    # End‑of‑year supplement only if family ATI ≤ $80 000 OR receiving income support
    fam_ati = fam.primary_income + fam.secondary_income
    supplement = rates["supplement"] if (payable_pf > 0 and (fam.on_income_support or fam_ati <= 80_000)) else 0.0

    return {
        "pf": round(payable_pf, 2),
        "annual": round(annual_core, 2),
        "supp": supplement,
        "annual_total": round(annual_core + supplement, 2),
    }

###############################################################################
# CALCULATE FTB PART B (unchanged logic)
###############################################################################

def calc_ftb_part_b(fam: Family):
    rb = RATES["ftb_b"]
    youngest = min(ch.age for ch in fam.children)
    base_pf = rb["max_pf"]["<5" if youngest < 5 else "5_18"]

    if fam.partnered:
        sec_red = max(fam.secondary_income - rb["secondary_free_area"], 0) * rb["taper"]
        core_pf = max(base_pf - sec_red, 0)
        if fam.primary_income > rb["primary_limit"]:
            core_pf = 0.0
    else:
        core_pf = base_pf

    annual = pf_to_annual(core_pf)
    supp = rb["supplement"] if core_pf > 0 else 0.0
    return {"pf": core_pf, "annual": annual, "supp": supp, "annual_total": annual + supp}

###############################################################################
# STREAMLIT SIDEBAR INPUTS
###############################################################################

st.sidebar.header("Household details")
partnered = st.sidebar.checkbox("Couple household", True)
primary_income = st.sidebar.number_input("Primary earner income ($ p.a.)", 0, 500_000, 0, 1_000, format="%d")
secondary_income = 0
if partnered:
    secondary_income = st.sidebar.number_input("Secondary earner income ($ p.a.)", 0, 500_000, 0, 1_000, format="%d")
receives_is = st.sidebar.checkbox("Receiving income support?")
num_kids = st.sidebar.number_input("Dependent children", 1, 10, 1, 1)

children: List[Child] = []
for i in range(int(num_kids)):
    with st.expander(f"Child {i+1} details"):
        age = st.slider("Age", 0, 19, 0, 1, key=f"age_{i}")
        immun = st.checkbox("Immunised", True, key=f"imm_{i}")
        hs = st.checkbox("Healthy‑Start check (age 4‑5)", True, key=f"hs_{i}")
        ma = st.checkbox("Maintenance action taken", True, key=f"ma_{i}")
    children.append(Child(age, immun, hs, ma))

fam = Family(partnered, primary_income, secondary_income, children, receives_is)

###############################################################################
# CALCULATE & DISPLAY
###############################################################################

if st.button("Calculate FTB"):
    a = calc_ftb_part_a(fam)
    b = calc_ftb_part_b(fam)
    st.success("Calculation complete!")

    colA, colB = st.columns(2)
    with colA:
        st.subheader("FTB Part A")
        st.write(f"**Fortnightly:** ${a['pf']:.2f}")
        st.write(f"**Annual (ex‑supp):** ${a['annual']:.2f}")
        st.write(f"**Supplement:** ${a['supp']:.2f}")
        st.write(f"**Annual incl. supp:** ${a['annual_total']:.2f}")
    with colB:
        st.subheader("FTB Part B")
        st.write(f"**Fortnightly:** ${b['pf']:.2f}")
        st.write(f"**Annual (ex‑supp):** ${b['annual']:.2f}")
        st.write(f"**Supplement:** ${b['supp']:.2f}")
        st.write(f"**Annual incl. supp:** ${b['annual_total']:.2f}")

    st.markdown("---")
    total = a['annual_total'] + b['annual_total']
    st.header(f"Total FTB (annual, after supplements): ${total:,.2f}")
