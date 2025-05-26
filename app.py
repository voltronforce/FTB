"""Family Tax Benefit & Rent Assistance Calculator
==================================================

Updated: 26 May 2025 (rates effective 20 Mar 2025)

Key changes
-----------
* All maximum/base rates and thresholds brought into line with the *Guide to Australian Government Payments – 20 March 2025*.
* Immunisation / Health‑start compliance penalties now apply a **$34.44 per‑fortnight** reduction (indexed each 1 July).
* Maintenance‑action test now reduces the rate to **Base Rate** rather than zero.
* Rates & thresholds moved to a JSON‑like structure (`RATES_2025`) for easier annual indexation.

Notes
-----
* Annual amounts below exclude end‑of‑year supplements unless explicitly noted.
* Supplements (`ftb_a_supplement`, `ftb_b_supplement`) are added at the end of the financial year if eligible.
* All monetary amounts are stored in *dollars* (AUD).
"""

from __future__ import annotations
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple

import streamlit as st

###############################################################################
# 2024‑25 RATES & THRESHOLDS
###############################################################################

RATES_2025: Dict[str, object] = {
    "ftb_a": {
        # Fortnightly core amounts (ex‑supplement)
        "max_rate_pf": {
            "0_12": 222.04,   # children aged 0‑12
            "13_15": 288.82,  # children aged 13‑15
            "16_19_secondary": 288.82,  # 16‑19 yo in secondary study
        },
        "base_rate_pf": 71.26,
        # Supplements (paid after reconciliation)
        "supplement_annual": 916.15,
        # Income test
        "lower_threshold": 65_189,
        "higher_threshold": 115_997,
        "primary_taper": 0.20,   # 20c per $ over lower threshold
        "secondary_taper": 0.30, # 30c per $ over higher threshold
    },
    "ftb_b": {
        # Fortnightly core amounts (ex‑supplement)
        "max_rate_pf": {
            "<5": 188.86,
            "5_18": 131.74,
        },
        "supplement_annual": 448.95,
        # Income test
        "secondary_earner_free_area": 6_789,
        "primary_earner_limit": 117_194,
        "taper": 0.20,  # 20c per $ over free area for secondary earner
    },
    "compliance_reduction_pf": 34.44,  # per unmet requirement per child
}

###############################################################################
# DATA CLASSES
###############################################################################

from dataclasses import dataclass

@dataclass
class Child:
    age: int
    immunised: bool = True
    healthy_start: bool = True
    maintenance_action_ok: bool = True  # Has parent taken reasonable maintenance action?


@dataclass
class Family:
    partnered: bool
    primary_income: float
    secondary_income: float = 0.0
    children: List[Child] = None
    receives_income_support: bool = False
    rent_pf: float = 0.0  # Fortnightly rent
    receives_rent_assistance: bool = False


###############################################################################
# HELPER FUNCTIONS
###############################################################################

def fortnightly_to_annual(amount_pf: float) -> float:
    return round(amount_pf * 26, 2)


def calc_ftb_a_child_rate_pf(child: Child, family_income: float, family: Family) -> Tuple[float, float]:
    """Return (core_rate_pf_after_income_test, compliance_reduction_pf)."""
    rates_a = RATES_2025["ftb_a"]

    # Determine max or base core rate for age
    if child.age <= 12:
        core_pf = rates_a["max_rate_pf"]["0_12"]
    elif child.age <= 15:
        core_pf = rates_a["max_rate_pf"]["13_15"]
    else:
        core_pf = rates_a["max_rate_pf"]["16_19_secondary"]

    # Apply income test unless family receives an income support payment
    if not family.receives_income_support and family_income > rates_a["lower_threshold"]:
        excess = family_income - rates_a["lower_threshold"]
        if family_income <= rates_a["higher_threshold"]:
            reduction = excess * rates_a["primary_taper"]
        else:
            red1 = (rates_a["higher_threshold"] - rates_a["lower_threshold"]) * rates_a["primary_taper"]
            red2 = (family_income - rates_a["higher_threshold"]) * rates_a["secondary_taper"]
            reduction = red1 + red2
        core_pf = max(core_pf - (reduction / len(family.children)), 0)

    # Compliance reductions (flat dollar) – applied *after* income test
    compliance_pf = 0.0
    if not child.immunised:
        compliance_pf += RATES_2025["compliance_reduction_pf"]
    if not child.healthy_start and 4 <= child.age <= 5:
        compliance_pf += RATES_2025["compliance_reduction_pf"]

    core_pf = max(core_pf - compliance_pf, 0)

    # Maintenance action test: if failed, limit to base rate
    if not child.maintenance_action_ok:
        core_pf = min(core_pf, rates_a["base_rate_pf"])

    return core_pf, compliance_pf


def calc_ftb_part_a(family: Family) -> Dict[str, float]:
    """Return a dict with fortnightly & annual totals incl. supplements."""
    total_pf = 0.0
    comp_pf_total = 0.0
    combined_income = family.primary_income + family.secondary_income

    for child in family.children:
        child_pf, comp_pf = calc_ftb_a_child_rate_pf(child, combined_income, family)
        total_pf += child_pf
        comp_pf_total += comp_pf

    annual_core = fortnightly_to_annual(total_pf)
    supplement = RATES_2025["ftb_a"]["supplement_annual"] if total_pf > 0 else 0.0

    return {
        "core_pf": round(total_pf, 2),
        "core_annual": round(annual_core, 2),
        "supplement": supplement,
        "annual_with_supplement": round(annual_core + supplement, 2),
        "compliance_reduction_pf": round(comp_pf_total, 2),
    }


def calc_ftb_part_b(family: Family) -> Dict[str, float]:
    rates_b = RATES_2025["ftb_b"]

    if family.partnered:
        secondary_income = family.secondary_income
        if secondary_income <= rates_b["secondary_earner_free_area"]:
            secondary_reduction = 0.0
        else:
            secondary_reduction = (secondary_income - rates_b["secondary_earner_free_area"]) * rates_b["taper"]
        core_pf = (
            rates_b["max_rate_pf"]["<5"] if min(child.age for child in family.children) < 5
            else rates_b["max_rate_pf"]["5_18"]
        )
        core_pf = max(core_pf - secondary_reduction, 0)
        if family.primary_income > rates_b["primary_earner_limit"]:
            core_pf = 0.0
    else:
        # Single parent: secondary earner test doesn't apply
        core_pf = (
            rates_b["max_rate_pf"]["<5"] if min(child.age for child in family.children) < 5
            else rates_b["max_rate_pf"]["5_18"]
        )

    annual_core = fortnightly_to_annual(core_pf)
    supplement = rates_b["supplement_annual"] if core_pf > 0 else 0.0

    return {
        "core_pf": round(core_pf, 2),
        "core_annual": round(annual_core, 2),
        "supplement": supplement,
        "annual_with_supplement": round(annual_core + supplement, 2),
    }


###############################################################################
# STREAMLIT UI
###############################################################################

st.set_page_config(page_title="Family Tax Benefit Calculator (2025‑26)",
                   page_icon=":money_with_wings:",
                   layout="centered")

st.title("👶 Family Tax Benefit Calculator")
st.caption("Rates effective 20 March 2025 – excludes end‑of‑year supplements until reconciliation.")

with st.expander("⚙️ Rate parameters"):
    st.json(RATES_2025, expanded=False)

# Basic user inputs -----------------------------------------------------------

st.header("Household Details")

col1, col2 = st.columns(2)
partnered = col1.checkbox("Partnered / Couple?", value=True)
primary_income = col1.number_input("Primary earner taxable income ($ p.a.)", 0, 500_000
