from __future__ import annotations
"""
Department of Social Services – Family Tax Benefit Calculator (2024‑25)
=======================================================================
Streamlit application that estimates Family Tax Benefit (Parts A & B) for the
2024‑25 year in line with the Family Assistance Guide.

**Visual update (May 2025)**
* Retains modern gradient banner but now shows a single **🐞 “Budget Beetle”** icon
  (no government or money emoji) for a lighter look.
* Typography, tab layout, and calculator logic unchanged.

Run with:
    streamlit run ftb_streamlit_app_updated.py
"""
###############################################################################
# Imports & Setup
###############################################################################
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
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
    :root {{ --primary:{PRIMARY}; --accent:{ACCENT}; }}
    html,body{{font-family:Arial,Helvetica,sans-serif;}}
    h1,h2,h3{{color:var(--primary);}}
    .stButton>button{{background-color:var(--primary);color:#fff;border:none;}}
    .stButton>button:hover{{background-color:var(--accent);}}

    /* Gradient banner */
    .banner{{
        background:linear-gradient(135deg,var(--primary) 0%,var(--accent) 100%);
        color:#fff;padding:1.2rem 1.6rem;border-radius:16px;
        display:flex;align-items:center;gap:18px;margin-bottom:1.6rem;
        box-shadow:0 4px 12px rgba(0,0,0,.12);
    }}
    .banner .beetle{{font-size:60px;filter:drop-shadow(0 4px 6px rgba(0,0,0,.25));}}
    .banner .title{{font-size:2.3rem;font-weight:600;line-height:1;}}

    /* Tabs */
    .stTabs [role="tab"]{padding:8px 24px;font-weight:600;}
    .stTabs [aria-selected="true"]{color:var(--primary);}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# DSS Banner – always show beetle icon (no govt / money emojis)
# ---------------------------------------------------------------------------
icon_html = "<span class='beetle'>🐞</span>"

st.markdown(f"""
<div class='banner'>
    {icon_html}
    <span class='title'>Family Tax Benefit Calculator 2024‑25</span>
</div>
""", unsafe_allow_html=True)

###############################################################################
# 2024‑25 Constants & Rates  (unchanged)
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
# Dataclasses & helpers (logic unchanged)
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
    if c.age<=12:
        return RATES["ftb_a"]["max_pf"]["0_12"]
    elif c.age<=15:
        return RATES["ftb_a"]["max_pf"]["13_15"]
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
# Calculation functions (unchanged logic) – abbreviated here for brevity
# (calc_ftb_part_a, calc_ftb_part_b, etc. remain exactly as previously)
###############################################################################
# ...  [keep existing functions unchanged] ...

###############################################################################
# UI – keep existing tab layout and components (unchanged)
###############################################################################
# ...  [rest of the UI code remains the same] ...
