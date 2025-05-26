"""Department of Social Services – Family Tax Benefit Calculator (2024‑25)
=====================================================================

*Rates current at 20 March 2025 – supplements displayed separately.*

This Streamlit app calculates Family Tax Benefit Parts A & B using official
rates and thresholds.  It maintains the DSS look‑and‑feel while adding a quirky
**green beetle icon** (nick‑named *Budget Beetle*) requested by the user.

Highlights
---------
* **DSS colour palette** – navy #00558B & teal #009CA6.  
* **Optional DSS banner** → place `dss_logo.png` beside the script.  
* **Optional beetle logo** → place `green_beetle.png`; otherwise a CSS‑tinted 🐞.
* Clean two‑column layout & teal primary action button.

Run with:
```
streamlit run ftb_streamlit_app_updated.py
```
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional
import streamlit as st
import os

###############################################################################
# BRANDING & PAGE CONFIG
###############################################################################

PRIMARY = "#00558B"  # DSS navy
ACCENT  = "#009CA6"  # DSS teal

st.set_page_config(
    page_title="DSS – Family Tax Benefit Calculator 2024‑25",
    page_icon="🐞",  # CSS‑tinted when no PNG provided
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

###############################################################################
# HEADER WITH LOGOS / ICONS
###############################################################################

if os.path.exists("dss_logo.png"):
    st.image("dss_logo.png", width=180)

if os.path.exists("green_beetle.png"):
    beetle_html = "<img src='green_beetle.png' width='32' style='vertical-align:middle;margin-right:8px;'>"
else:
    beetle_html = "<span class='beetle'>🐞</span>&nbsp;"

st.markdown(
    f"<div class='dss-header'>{beetle_html}<h1 style='display:inline'>Family Tax Benefit Calculator 2024‑25</h1></div>",
    unsafe_allow_html=True,
)

###############################################################################
# RATE TABLE – 2024‑25 (Guide to Australian Government Payments, 20 Mar 2025)
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
# DATA CLASSES
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
    children: Optional[List[Child]] = None
    receives_income_support: bool = False

###############################################################################
# CALCULATION HELPERS
###############################################################################

def pf_to_annual(amount_pf: float) -> float:
    """Convert a fortnightly amount to annual (26 fortnights)."""
    return round(amount_pf * 26, 2)


def calc_ftb_a_child_pf(child: Child, fam_income: float, kids: int, on_is: bool) -> float:
    ra = RATES_2025["ftb_a"]
    # Core by age
    if child.age <= 12:
        core = ra["max_rate_pf"]["0_12"]
    elif child.age <= 15:
        core = ra["max_rate_pf"]["13_15"]
    else:
        core = ra["max_rate_pf"]["16_19_secondary"]

    # Income test (skip if on income support)
    if not on_is and fam_income > ra["lower_threshold"]:
        excess = fam_income - ra["lower_threshold"]
        if fam_income <= ra["higher_threshold"]:
            reduction = excess * ra["primary_taper"]
        else:
            reduction = (
                (ra["higher_threshold"] - ra["lower_threshold"]) * ra["primary_taper"] +
                (fam_income - ra["higher_threshold"]) * ra["secondary_taper"]
            )
        core = max(core - reduction / kids, 0)

    # Compliance penalties (flat $34.44 pf each)
    if not child.immunised:
        core -= RATES_2025["compliance_reduction_pf"]
    if 4 <= child.age <= 5 and not child.healthy_start:
        core -= RATES_2025["compliance_reduction_pf"]

    # Maintenance action test → limit to base rate if not taken reasonable action
    if not child.maintenance_action_ok:
        core = min(core, ra["base_rate_pf"])

    return max(core, 0)


def calc_ftb_a(fam: Family) -> Dict[str, float]:
    if not fam.children:
        return {"pf": 0.0, "annual": 0.0, "supp": 0.0, "annual_total": 0.0}
    
    kids = len(fam.children)
    total_pf = sum(
        calc_ftb_a_child_pf(ch, fam.primary_income + fam.secondary_income, kids, fam.receives_income_support)
        for ch in fam.children
    )
    annual = pf_to_annual(total_pf)
    supp = RATES_2025["ftb_a"]["supplement_annual"] if total_pf > 0 else 0.0
    return {"pf": total_pf, "annual": annual, "supp": supp, "annual_total": annual + supp}


def calc_ftb_b(fam: Family) -> Dict[str, float]:
    if not fam.children:
        return {"pf": 0.0, "annual": 0.0, "supp": 0.0, "annual_total": 0.0}
    
    rb = RATES_2025["ftb_b"]
    youngest = min(ch.age for ch in fam.children)
    base_pf = rb["max_rate_pf"]["<5" if youngest < 5 else "5_18"]

    if fam.partnered:
        sec_red = max(fam.secondary_income - rb["secondary_earner_free_area"], 0) * rb["taper"]
        core_pf = max(base_pf - sec_red, 0)
        if fam.primary_income > rb["primary_earner_limit"]:
            core_pf = 0.0
    else:
        core_pf = base_pf

    annual = pf_to_annual(core_pf)
    supp = rb["supplement_annual"] if core_pf > 0 else 0.0
    return {"pf": core_pf, "annual": annual, "supp": supp, "annual_total": annual + supp}

###############################################################################
# SIDEBAR INPUTS
###############################################################################

st.sidebar.header("Household details")
partnered = st.sidebar.checkbox("Couple household", value=True)
primary_income = st.sidebar.number_input("Primary earner income ($ p.a.)", 0, 500_000, 0, 1_000, format="%d")
secondary_income = 0
if partnered:
    secondary_income = st.sidebar.number_input("Secondary earner income ($ p.a.)", 0, 500_000, 0, 1_000, format="%d")
receives_is = st.sidebar.checkbox("Receiving income support?", value=False)
num_kids = st.sidebar.number_input("Number of dependent children", 1, 10, 1, 1)

children: List[Child] = []
for i in range(int(num_kids)):
    with st.expander(f"Child {i+1} details"):
        age = st.slider("Age", 0, 19, 0, 1, key=f"age_{i}")
        immun = st.checkbox("Immunised", True, key=f"imm_{i}")
        hs = st.checkbox("Healthy‑Start check (age 4‑5)", True, key=f"hs_{i}")
        ma = st.checkbox("Maintenance action taken", True, key=f"ma_{i}")
    children.append(Child(age, immun, hs, ma))

fam = Family(partnered, primary_income, secondary_income, children, receives_is)

###############################################################################
# CALCULATE & DISPLAY RESULTS
###############################################################################

if st.button("Calculate FTB"):
    part_a = calc_ftb_a(fam)
    part_b = calc_ftb_b(fam)
    st.success("Calculation complete!")

    colA, colB = st.columns(2)
    with colA:
        st.subheader("FTB Part A")
        st.write(f"**Fortnightly:** ${part_a['pf']:.2f}")
        st.write(f"**Annual (ex‑supp):** ${part_a['annual']:.2f}")
        st.write(f"**Supplement:** ${part_a['supp']:.2f}")
        st.write(f"**Annual incl. supp:** ${part_a['annual_total']:.2f}")

    with colB:
        st.subheader("FTB Part B")
        st.write(f"**Fortnightly:** ${part_b['pf']:.2f}")
        st.write(f"**Annual (ex‑supp):** ${part_b['annual']:.2f}")
        st.write(f"**Supplement:** ${part_b['supp']:.2f}")
        st.write(f"**Annual incl. supp:** ${part_b['annual_total']:.2f}")

    # Summary
    st.markdown("---")
    st.subheader("Total Benefits")
    total_pf = part_a['pf'] + part_b['pf']
    total_annual = part_a['annual_total'] + part_b['annual_total']
    
    st.write(f"**Total fortnightly:** ${total_pf:.2f}")
    st.write(f"**Total annual:** ${total_annual:.2f}")
    
    # Additional information
    st.markdown("---")
    st.info("💡 **Note:** These calculations are estimates based on current rates. Actual payments may vary based on individual circumstances and changes to government policy.")
    
    # Show breakdown by child for Part A if applicable
    if part_a['pf'] > 0:
        with st.expander("Part A breakdown by child"):
            for i, child in enumerate(children):
                child_rate = calc_ftb_a_child_pf(
                    child, 
                    fam.primary_income + fam.secondary_income, 
                    len(children), 
                    fam.receives_income_support
                )
                st.write(f"**Child {i+1} (age {child.age}):** ${child_rate:.2f} per fortnight")

###############################################################################
# FOOTER
###############################################################################

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
    Australian Government Department of Social Services<br>
    Family Tax Benefit Calculator 2024-25<br>
    <em>For information purposes only</em>
    </div>
    """,
    unsafe_allow_html=True
)
