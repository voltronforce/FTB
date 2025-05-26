from __future__ import annotations
"""
Department of Social Services – Family Tax Benefit Calculator (2024‑25)
=======================================================================
Streamlit application that estimates Family Tax Benefit (Parts A & B) for the
2024‑25 year in line with the Family Assistance Guide.

**Visual update (May 2025)**
* Uses a clean gradient banner and a single 🐞 “Budget Beetle” icon.
* Tabs: **Calculator • Income Buffer • Eligibility Thresholds** (plus extra info).
* Calculation logic follows DSS rates current at 20 Mar 2025.

Run with:
    streamlit run ftb_streamlit_app_updated.py
"""
###############################################################################
# Imports & Setup
###############################################################################
from dataclasses import dataclass
from typing import List, Dict
import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
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
    :root {{ --primary:{PRIMARY}; --accent:{ACCENT}; }}
    html,body{{font-family:Arial,Helvetica,sans-serif;background:#fafbfc;}}
    h1,h2,h3{{color:var(--primary);}}
    .stButton>button{{background-color:var(--primary);color:#fff;border:none;border-radius:12px;padding:0.6rem 1.6rem;font-weight:600;}}
    .stButton>button:hover{{background-color:var(--accent);}}

    /* Gradient banner */
    .banner{{background:linear-gradient(135deg,var(--primary) 0%,var(--accent) 100%);color:#fff;padding:1.4rem 1.8rem;border-radius:18px;display:flex;align-items:center;gap:20px;margin-bottom:1.6rem;box-shadow:0 4px 14px rgba(0,0,0,.12);}}
    .banner .beetle{{font-size:64px;filter:drop-shadow(0 4px 6px rgba(0,0,0,.25));}}
    .banner .title{{font-size:2.4rem;font-weight:600;}}

    /* Tabs */
    .stTabs [role="tab"]{{padding:10px 26px;font-weight:600;font-size:1rem;}}
    .stTabs [aria-selected="true"]{{color:var(--primary);}}

    /* Card */
    .card{{background:#fff;border-radius:16px;padding:1.8rem;margin-bottom:1.6rem;box-shadow:0 4px 12px rgba(0,0,0,.08);}}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
st.markdown("""
<div class='banner'>
  <span class='beetle'>🐞</span>
  <span class='title'>Family Tax Benefit Calculator 2024‑25</span>
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
# Dataclasses & Helpers
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

def pf_to_annual(pf:float)->float:
    return round(pf*26,2)

# --- child helpers ---

def child_max_rate_pf(c:Child)->float:
    return RATES["ftb_a"]["max_pf"]["0_12"] if c.age<=12 else (RATES["ftb_a"]["max_pf"]["13_15"] if c.age<=15 else RATES["ftb_a"]["max_pf"]["16_19"])

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
# FTB Part A – Method 1 & Method 2
###############################################################################

def calc_ftb_part_a(fam:Family)->Dict:
    rates=RATES["ftb_a"]
    total_max_pf,total_base_pf=0.0,0.0
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
    # Method 1
    if fam.on_income_support:
        m1_pf=total_max_pf
    else:
        if ati<=rates["lower_ifa"]:
            m1_pf=total_max_pf
        elif ati<=rates["higher_ifa"]:
            m1_pf=max(total_max_pf-(ati-rates["lower_ifa"])*rates["taper1"]/26,total_base_pf)
        else:
            m1_pf=max(total_base_pf-(ati-rates["higher_ifa"])*rates["taper2"]/26,0)
    # Method 2 – base only
    base_total_pf=sum(max(child_base_rate_pf(ch)-child_penalties_pf(ch),0) for ch in fam.children)
    if fam.on_income_support or ati<=rates["higher_ifa"]:
        m2_pf=base_total_pf
    else:
        m2_pf=max(base_total_pf-(ati-rates["higher_ifa"])*rates["taper2"]/26,0)

    best_pf=max(m1_pf,m2_pf)
    annual_core=pf_to_annual(best_pf)
    supp=rates["supplement"] if best_pf>0 and (fam.on_income_support or ati<=rates["supplement_income_limit"]) else 0
    return {"pf":round(best_pf,2),"annual":annual_core,"supp":supp,"annual_total":round(annual_core+supp,2)}

###############################################################################
# FTB Part B
###############################################################################

def calc_ftb_part_b(fam:Family,include_es:bool=False)->Dict:
    rates=RATES["ftb_b"]
    if not fam.children:
        return {k:0 for k in ("pf","annual","supp","energy","annual_total")}

    youngest=min(ch.age for ch in fam.children)
    std_pf=rates["max_pf"]["under_5"] if youngest<5 else rates["max_pf"]["5_to_18"]
    es_pf=rates["energy_pf"]["under_5"] if youngest<5 else rates["energy_pf"]["5_to_18"]

    if not fam.partnered:
        base_pf=std_pf if fam.primary_income<=rates["primary_limit"] else 0.0
    else:
        if youngest>=13:
            base_pf=0.0
        else:
            primary=max(fam.primary_income,fam.secondary_income)
            secondary=min(fam.primary_income,fam.secondary_income)
            if primary>rates["primary
