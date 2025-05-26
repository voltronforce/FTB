from __future__ import annotations

"""
Department of Social Services – Family Tax Benefit Calculator (2024‑25)
=======================================================================
A polished Streamlit application that calculates Family Tax Benefit (Parts A & B)
using 2024‑25 rates and the rules in the Family Assistance Guide (FAG 3.1.1‑3.1.9).

Visual refresh (May 2025)
-------------------------
* Bold DSS banner (gradient navy→teal) with larger logo / beetle icon
* Sans‑serif typography and coloured tabs
* Three‑tab layout — **Calculator • Income Buffer • Eligibility Thresholds**
* Core calculation logic unchanged

Run with:
    streamlit run ftb_streamlit_app_updated.py
"""

###############################################################################
# Imports & Setup
###############################################################################
from dataclasses import dataclass
from typing import List, Dict
import streamlit as st
import os

# ---------------------------------------------------------------------------
# Page configuration & CSS
# ---------------------------------------------------------------------------
PRIMARY = "#00558B"  # DSS navy
ACCENT  = "#009CA6"  # DSS teal

st.set_page_config(page_title="DSS – Family Tax Benefit Calculator 2024‑25",
                   page_icon="🐞", layout="wide")

st.markdown(f"""
<style>
    :root {{ --primary: {PRIMARY}; --accent: {ACCENT}; }}
    html, body, label, span, input, select {{ font-family: Arial, Helvetica, sans-serif; }}
    h1, h2, h3 {{ color: var(--primary); }}
    .stButton>button {{ background-color: var(--primary); color:#fff; border:none; }}
    .stButton>button:hover {{ background-color: var(--accent); }}

    /* ---------- Banner styles ---------- */
    .banner {{
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
        color:#fff; padding:1rem 1.5rem; border-radius:14px; display:flex; align-items:center;
        box-shadow:0 4px 10px rgba(0,0,0,0.12); margin-bottom:1.5rem;
    }}
    .banner img, .banner span.beetle {{ width:56px; height:56px; margin-right:18px; }}
    .banner .title {{ font-size:2.2rem; font-weight:600; }}

    /* Tabs styling */
    .stTabs [role="tab"] {{ padding:8px 24px; font-weight:600; }}
    .stTabs [aria-selected="true"] {{ color:var(--primary); }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# DSS Banner (logo or beetle)
# ---------------------------------------------------------------------------
if os.path.exists("dss_logo.png"):
    icon_html = "<img src='dss_logo.png' alt='DSS logo'>"
elif os.path.exists("green_beetle.png"):
    icon_html = "<img src='green_beetle.png'>"
else:
    icon_html = "<span class='beetle'>🐞</span>"

st.markdown(f"""
<div class='banner'>
    {icon_html}
    <span class='title'>Family Tax Benefit Calculator&nbsp;2024‑25</span>
</div>
""", unsafe_allow_html=True)

###############################################################################
# 2024‑25 Constants & Rates
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
# Dataclasses & Helper functions
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

# ---------- Child‑level helpers ----------

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
# FTB Part A calculations (Method 1 & Method 2)
###############################################################################

def calc_ftb_part_a(fam: Family) -> Dict:
    rates = RATES["ftb_a"]
    # ---- Method 1 ----
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
    if fam.on_income_support:
        m1_pf = total_max_pf
    else:
        if ati <= rates["lower_ifa"]:
            m1_pf = total_max_pf
        elif ati <= rates["higher_ifa"]:
            m1_pf = max(total_max_pf - (ati - rates["lower_ifa"]) * rates["taper1"] / 26, total_base_pf)
        else:
            m1_pf = max(total_base_pf - (ati - rates["higher_ifa"]) * rates["taper2"] / 26, 0)

    # ---- Method 2 ----
    base_total_pf = sum(max(child_base_rate_pf(ch) - child_penalties_pf(ch), 0) for ch in fam.children)
    if fam.on_income_support or ati <= rates["higher_ifa"]:
        m2_pf = base_total_pf
    else:
        m2_pf = max(base_total_pf - (ati - rates["higher_ifa"]) * rates["taper2"] / 26, 0)

    best_pf = max(m1_pf, m2_pf)
    annual_core = pf_to_annual(best_pf)
    supp = rates["supplement"] if best_pf > 0 and (fam.on_income_support or ati <= rates["supplement_income_limit"]) else 0

    return {"pf": round(best_pf,2), "annual": annual_core, "supp": supp, "annual_total": round(annual_core + supp,2)}

###############################################################################
# FTB Part B calculation (Guide 3.1.9.10 / 3.1.9.20)
###############################################################################

def calc_ftb_part_b(fam: Family, include_es: bool=False) -> Dict:
    rates = RATES["ftb_b"]
    if not fam.children:
        return {k:0 for k in ("pf","annual","supp","energy","annual_total")}

    youngest = min(ch.age for ch in fam.children)
    std_pf = rates["max_pf"]["under_5"] if youngest < 5 else rates["max_pf"]["5_to_18"]
    es_pf  = rates["energy_pf"]["under_5"] if youngest < 5 else rates["energy_pf"]["5_to_18"]

    # ---- Method 1 (single) ----
    if not fam.partnered:
        payable_pf = std_pf if fam.primary_income <= rates["primary_limit"] else 0.0
    # ---- Method 2 (couple) ----
    else:
        if youngest >= 13:
            payable_pf = 0.0
        else:
            primary = max(fam.primary_income, fam.secondary_income)
            secondary = min(fam.primary_income, fam.secondary_income)
            if primary > rates["primary_limit"]:
                payable_pf = 0.0
            else:
                excess = max(0, secondary - rates["secondary_free_area"])
                payable_pf = std_pf - excess * rates["taper"] / 26
                if payable_pf < 0.01:
                    payable_pf = 0.0

    annual_core = pf_to_annual(payable_pf)
    supplement  = rates["supplement"] if payable_pf > 0 else 0.0
    energy      = pf_to_annual(es_pf) if include_es and payable_pf > 0 else 0.0

    return {"pf": round(payable_pf,2), "annual": annual_core, "supp": supplement, "energy": energy,
            "annual_total": round(annual_core + supplement + energy,2)}

###############################################################################
# Part A nil-rate ATI (selected look‑up table)
###############################################################################

def part_a_income_limit(n:int, u:int, o:int) -> float|None:
    limits = {
        (1,1,0):122_190,(1,0,1):122_190,
        (2,2,0):128_383,(2,1,1):128_383,(2,0
