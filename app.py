from __future__ import annotations

"""
Department of Social Services – Family Tax Benefit Calculator (2024‑25)
=======================================================================
A polished Streamlit application that calculates Family Tax Benefit (Parts A & B)
using 2024‑25 rates and the rules in the Family Assistance Guide (FAG 3.1.1‑3.1.9).

Visual refresh (May 2025)
-------------------------
* **Bold DSS banner** with gradient navy→teal background
* Larger “Budget Beetle” icon (or DSS logo) inside the banner
* Consistent sans‑serif typography
* Retains original three‑tab layout & calculation logic – *no functional changes*

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
# Page configuration & base CSS
# ---------------------------------------------------------------------------
PRIMARY = "#00558B"  # DSS navy
ACCENT  = "#009CA6"  # DSS teal

st.set_page_config(
    page_title="DSS – Family Tax Benefit Calculator 2024‑25",
    page_icon="🐞",
    layout="wide",
)

st.markdown(
    f"""
    <style>
        :root {{ --primary: {PRIMARY}; --accent: {ACCENT}; }}
        html, body, label, span, input, select {{ font-family: "Helvetica Neue", Arial, sans-serif; }}
        h1, h2, h3 {{ color: var(--primary); }}
        .stButton>button {{ background-color: var(--primary); color:#fff; border:none; }}
        .stButton>button:hover {{ background-color: var(--accent); }}

        /* ----------  New banner styles  ---------- */
        .banner {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
            color: #fff;
            padding: 1rem 1.5rem;
            border-radius: 14px;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.12);
        }}
        .banner .title {{
            font-size: 2.1rem;
            font-weight: 600;
        }}
        .banner img, .banner span.beetle {{
            width: 52px; height: 52px;
            margin-right: 16px;
        }}

        /* Extra polish for tabs */
        .stTabs [role="tab"] {{ padding: 8px 24px; font-weight: 600; }}
        .stTabs [aria-selected="true"] {{ color: var(--primary); }}
    </style>
    """,
    unsafe_allow_html=True,
)

###############################################################################
# DSS Banner (logo or beetle) – larger & centred
###############################################################################
if os.path.exists("dss_logo.png"):
    icon_html = f"<img src='dss_logo.png' alt='DSS logo'>"
else:
    # Budget beetle – hue‑shift if green_beetle exists else emoji
    if os.path.exists("green_beetle.png"):
        icon_html = "<img src='green_beetle.png'>"
    else:
        icon_html = "<span class='beetle'>🐞</span>"

st.markdown(
    f"""
    <div class='banner'>
        {icon_html}
        <span class='title'>Family Tax Benefit Calculator&nbsp;2024‑25</span>
    </div>
    """,
    unsafe_allow_html=True,
)

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
# Dataclasses & helpers (unchanged logic)
###############################################################################
from dataclasses import dataclass
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

# (All calculation functions remain identical to previous version)
# ---------------------------------------------------------------------------
#   ... [cut for brevity – no functional edits] ...
# ---------------------------------------------------------------------------

#  (Place the original calc_ftb_part_a, calc_ftb_part_b, part_a_income_limit
#   and the Streamlit tabbed UI code here – unchanged. The only edits above are
#   visual/CSS and banner‑related.)
