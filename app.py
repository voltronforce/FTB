"""Family Tax Benefit & Rent Assistance Calculator
================================================

Updated: 26 May 2025 (rates effective 20 Mar 2025)

This single‑file Streamlit app reflects the latest guidance and fixes the
*"All numerical arguments must be of the same type"* error by ensuring that
`value`, `min_value`, `max_value`, and `step` are **all of the same type** for
_every_ numerical widget.

——————————————————————————————————————————————————————————
Run with →  `streamlit run ftb_streamlit_app_updated.py`
——————————————————————————————————————————————————————————
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple

import streamlit as st

###############################################################################
# RATE TABLE ─ 2024‑25 (Guide to Australian Government Payments, 20 Mar 2025)
###############################################################################

RATES_2025: Dict[str, object] = {
    "ftb_a": {
        # Fortnightly core (ex‑supplement)
        "max_rate_pf": {"0_12": 222.04, "13_15": 288.82, "16_19_secondary": 288.82},
        "base_rate_pf": 71.26,
        "supplement_annual": 916.15,
        # Income test
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
    "compliance_reduction_pf": 34.44,  # flat reduction per unmet requirement
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
    children: List[Child] = None
    receives_income_support: bool = False
    rent_pf: float = 0.0

###############################################################################
# CALC HELPERS
###############################################################################

def pf_to_annual(amount_pf: float) -> float:
    return round(amount_pf * 26, 2)


def calc_ftb_a_child_pf(child: Child, family_income: float, kids: int, income_support: bool) -> float:
    ra = RATES_2025["ftb_a"]
    # base amount by age
    core = (
        ra["max_rate_pf"]["0_12"] if child.age <= 12 else ra["max_rate_pf"]["13_15"]
        if child.age <= 15 else ra["max_rate_pf"]["16_19_secondary"]
    )
    # income test (unless on income support)
    if not income_support and family_income > ra["lower_threshold"]:
        excess = family_income - ra["lower_threshold"]
        if family_income <= ra["higher_threshold"]:
            red = excess * ra["primary_taper"]
        else:
            red = (
                (ra["higher_threshold"] - ra["lower_threshold"]) * ra["primary_taper"]
                + (family_income - ra["higher_threshold"]) * ra["secondary_taper"]
            )
        core = max(core - red / kids, 0)
    # compliance penalties
    if not child.immunised:
        core -= RATES_2025["compliance_reduction_pf"]
    if 4 <= child.age <= 5 and not child.healthy_start:
        core -= RATES_2025["compliance_reduction_pf"]
    # maintenance action test
    if not child.maintenance_action_ok:
        core = min(core, ra["base_rate_pf"])
    return max(core, 0)


def calc_ftb_a(fam: Family) -> Dict[str, float]:
    kids = len(fam.children)
    rate_pf = sum(
        calc_ftb_a_child_pf(ch, fam.primary_income + fam.secondary_income, kids, fam.receives_income_support)
        for ch in fam.children
    )
    annual = pf_to_annual(rate_pf)
    supp = RATES_2025["ftb_a"]["supplement_annual"] if rate_pf > 0 else 0.0
    return {"pf": rate_pf, "annual": annual, "supp": supp, "annual_total": annual + supp}


def calc_ftb_b(fam: Family) -> Dict[str, float]:
    rb = RATES_2025["ftb_b"]
    youngest_age = min(ch.age for ch in fam.children)
    base_pf = rb["max_rate_pf"]["<5" if youngest_age < 5 else "5_18"]

    if fam.partnered:
        # secondary earner test
        sec_red = 0.0
        if fam.secondary_income > rb["secondary_earner_free_area"]:
            sec_red = (fam.secondary_income - rb["secondary_earner_free_area"]) * rb["taper"]
        core_pf = max(base_pf - sec_red, 0)
        # primary earner limit
        if fam.primary_income > rb["primary_earner_limit"]:
            core_pf = 0.0
    else:
        core_pf = base_pf

    annual = pf_to_annual(core_pf)
    supp = rb["supplement_annual"] if core_pf > 0 else 0.0
    return {"pf": core_pf, "annual": annual, "supp": supp, "annual_total": annual + supp}

###############################################################################
# STREAMLIT UI
###############################################################################

st.set_page_config("Family Tax Benefit Calculator 2024‑25", ":money_with_wings:")

st.title("👶 Family Tax Benefit Calculator – 2024‑25")
st.caption("Figures current at 20 March 2025. Supplements are shown separately.")

with st.expander("🔧 Rate parameters (2024‑25)"):
    st.json(RATES_2025, expanded=False)

# ─── Household details ───────────────────────────────────────────────────────
partnered = st.checkbox("Partnered / Couple household", value=True)

col_pi, col_si = st.columns(2 if partnered else 1)
primary_income = col_pi.number_input(
    "Primary earner taxable income ($ p.a.)",
    min_value=0,
    max_value=500_000,
    value=0,
    step=1_000,
    format="%d",
)
secondary_income = 0
if partnered:
    secondary_income = col_si.number_input(
        "Secondary earner taxable income ($ p.a.)",
        min_value=0,
        max_value=500_000,
        value=0,
        step=1_000,
        format="%d",
    )

rent_pf = st.number_input(
    "Fortnightly rent ($)",
    min_value=0.0,
    max_value=5_000.0,
    value=0.0,
    step=10.0,
    format="%0.2f",
)

receives_is = st.checkbox("Receiving an income support payment? (e.g. JobSeeker)")

# ─── Children details ────────────────────────────────────────────────────────
num_kids = st.number_input(
    "Number of dependent children (max 10)",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    format="%d",
)

children: List[Child] = []
for i in range(int(num_kids)):
    st.subheader(f"Child {i+1}")
    c1, c2, c3, c4 = st.columns(4)
    age = c1.slider("Age", 0, 19, 0, step=1, key=f"age_{i}")
    immun = c2.checkbox("Immunised", value=True, key=f"imm_{i}")
    hs = c3.checkbox("Healthy‑Start check (if age 4‑5)", value=True, key=f"hs_{i}")
    mact = c4.checkbox("Maintenance action ok", value=True, key=f"ma_{i}")
    children.append(Child(age, immun, hs, mact))

# ─── Calculate ───────────────────────────────────────────────────────────────
family = Family(
    partnered=partnered,
    primary_income=primary_income,
    secondary_income=secondary_income,
    children=children,
    receives_income_support=receives_is,
    rent_pf=rent_pf,
)

if st.button("Calculate FTB"):
    a = calc_ftb_a(family)
    b = calc_ftb_b(family)

    st.success("Calculation complete 🎉")
    st.subheader("FTB Part A")
    st.write(f"Fortnightly: **${a['pf']:.2f}**")
    st.write(f"Annual (ex‑supplement): **${a['annual']:.2f}**")
    st.write(f"End‑of‑year supplement: **${a['supp']:.2f}**")
    st.write(f"Annual incl. supplement: **${a['annual_total']:.2f}**")

    st.subheader("FTB Part B")
    st.write(f"Fortnightly: **${b['pf']:.2f}**")
    st.write(f"Annual (ex‑supplement): **${b['annual']:.2f}**")
    st.write(f"End‑of‑year supplement: **${b['supp']:.2f}**")
    st.write(f"Annual incl. supplement: **${b['annual_total']:.2f}**")

    total_annual = a["annual_total"] + b["annual_total"]
    st.header(f"Total FTB annual (after supplements): ${total_annual:,.2f}")
