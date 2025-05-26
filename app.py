from __future__ import annotations

"""
Department of Social Services – Family Tax Benefit Calculator (2024‑25)
======================================================================

Streamlit application that calculates Family Tax Benefit Parts A & B using
2024‑25 rates and the rules in the Family Assistance Guide (FAG 3.1.1‑3.1.9).

New in this build (May 2025)
---------------------------
* Tabbed interface (Calculator • Income Buffer • Eligibility Thresholds)
* Corrected FTB Part B logic per FAG 3.1.9.10/20 (Method 1 & Method 2)
* Optional Energy Supplement toggle
* ‘Income buffer’ and ‘Eligibility limit’ tools
* Clean DSS navy/teal styling, optional “Budget Beetle” 🐞

Run with:
    streamlit run ftb_streamlit_app_updated.py
"""

###############################################################################
# Imports & Setup
###############################################################################
from dataclasses import dataclass
from typing import List, Dict, Tuple
import streamlit as st
import os

# --- Page configuration & basic CSS -------------------------------------------------
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
    .stTabs [role="tablist"] {{ margin-top: 1rem; }}
</style>
""", unsafe_allow_html=True)

if os.path.exists("dss_logo.png"):
    st.image("dss_logo.png", width=180)
icon_html = (
    "<img src='green_beetle.png' width='28' style='vertical-align:middle;margin-right:6px;'>"
    if os.path.exists("green_beetle.png") else "🐞 "
)
st.markdown(f"<h1>{icon_html}Family Tax Benefit Calculator 2024‑25</h1>", unsafe_allow_html=True)

###############################################################################
# Constants & 2024‑25 Rates
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
# Dataclasses
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

###############################################################################
# Helper functions
###############################################################################

def pf_to_annual(pf: float) -> float:
    """Fortnightly → annual (×26)."""
    return round(pf * 26, 2)


def child_max_rate_pf(child: Child) -> float:
    if child.age <= 12:
        return RATES["ftb_a"]["max_pf"]["0_12"]
    elif child.age <= 15:
        return RATES["ftb_a"]["max_pf"]["13_15"]
    else:
        return RATES["ftb_a"]["max_pf"]["16_19"]


def child_base_rate_pf(child: Child) -> float:
    return RATES["ftb_a"]["base_pf"]["0_12"] if child.age <= 12 else RATES["ftb_a"]["base_pf"]["13_plus"]


def child_penalties_pf(child: Child) -> float:
    pen = 0.0
    if not child.immunised:
        pen += RATES["compliance_penalty_pf"]
    if 4 <= child.age <= 5 and not child.healthy_start:
        pen += RATES["compliance_penalty_pf"]
    return pen

###############################################################################
# Calculation – FTB Part A
###############################################################################

def calc_ftb_part_a_method_1(fam: Family) -> Dict:
    rates = RATES["ftb_a"]
    total_max_pf, total_base_pf = 0.0, 0.0
    for ch in fam.children or []:
        max_pf = child_max_rate_pf(ch)
        base_pf = child_base_rate_pf(ch)
        if not ch.maintenance_ok:
            max_pf = min(max_pf, base_pf)
        pen = child_penalties_pf(ch)
        max_pf = max(max_pf - pen, 0)
        base_pf = max(base_pf - pen, 0)
        total_max_pf += max_pf
        total_base_pf += base_pf

    if fam.on_income_support:
        payable_pf = total_max_pf
    else:
        ati = fam.primary_income + fam.secondary_income
        if ati <= rates["lower_ifa"]:
            payable_pf = total_max_pf
        elif ati <= rates["higher_ifa"]:
            red = (ati - rates["lower_ifa"]) * rates["taper1"] / 26
            payable_pf = max(total_max_pf - red, total_base_pf)
        else:
            base_red = (ati - rates["higher_ifa"]) * rates["taper2"] / 26
            payable_pf = max(total_base_pf - base_red, 0)

    return {
        "pf": round(payable_pf, 2),
        "annual": pf_to_annual(payable_pf),
    }


def calc_ftb_part_a(fam: Family) -> Dict:
    """Higher of Method 1 or Method 2 (Method 2 = base‑rate only)."""
    m1 = calc_ftb_part_a_method_1(fam)

    # Method 2: same as Method 1 but start from base rates only and 30¢ taper above higher_ifa
    rates = RATES["ftb_a"]
    base_total_pf = sum(max(child_base_rate_pf(ch) - child_penalties_pf(ch), 0) for ch in fam.children)
    ati = fam.primary_income + fam.secondary_income
    if fam.on_income_support:
        m2_pf = base_total_pf
    else:
        if ati <= rates["higher_ifa"]:
            m2_pf = base_total_pf
        else:
            m2_pf = max(base_total_pf - (ati - rates["higher_ifa"]) * rates["taper2"] / 26, 0)
    m2 = {"pf": round(m2_pf, 2), "annual": pf_to_annual(m2_pf)}

    best = m1 if m1["pf"] >= m2["pf"] else m2
    supp_eligible = best["pf"] > 0 and (fam.on_income_support or ati <= rates["supplement_income_limit"])
    supp = rates["supplement"] if supp_eligible else 0.0
    best.update({"supp": supp, "annual_total": round(best["annual"] + supp, 2)})
    return best

###############################################################################
# Calculation – FTB Part B (Guide 3.1.9.10 & 3.1.9.20)
###############################################################################

def calc_ftb_part_b(fam: Family, include_es: bool = False) -> Dict:
    rates = RATES["ftb_b"]
    if not fam.children:
        return {k: 0 for k in ("pf", "annual", "supp", "energy", "annual_total")}

    youngest = min(ch.age for ch in fam.children)
    std_pf = rates["max_pf"]["under_5"] if youngest < 5 else rates["max_pf"]["5_to_18"]
    es_pf  = rates["energy_pf"]["under_5"] if youngest < 5 else rates["energy_pf"]["5_to_18"]

    # ---------------- Method 1 – Single parent -----------------
    if not fam.partnered:
        if fam.primary_income > rates["primary_limit"]:
            payable_pf = 0.0
        else:
            payable_pf = std_pf
    # ---------------- Method 2 – Couple ------------------------
    else:
        if youngest >= 13:
            payable_pf = 0.0  # no eligibility if youngest 13+
        else:
            primary = max(fam.primary_income, fam.secondary_income)
            secondary = min(fam.primary_income, fam.secondary_income)
            if primary > rates["primary_limit"]:
                payable_pf = 0.0
            else:
                excess = max(0, secondary - rates["secondary_free_area"])
                payable_pf = std_pf - (excess * rates["taper"] / 26)
                if payable_pf < 0.01:
                    payable_pf = 0.0

    annual_core = pf_to_annual(payable_pf)
    supplement  = rates["supplement"] if payable_pf > 0 else 0.0
    energy      = pf_to_annual(es_pf) if include_es and payable_pf > 0 else 0.0

    return {
        "pf": round(payable_pf, 2),
        "annual": round(annual_core, 2),
        "supp": supplement,
        "energy": round(energy, 2),
        "annual_total": round(annual_core + supplement + energy, 2),
    }

###############################################################################
# Helper – lookup Part A nil-rate ATI (selected combos)
###############################################################################

def part_a_income_limit(num_children: int, num_under13: int, num_over13: int) -> float | None:
    """Return ATI cutoff at which FTB Part A → $0. From SA published tables (up to 6 kids)."""
    limits = {
        (1,0,1): 122_190, (1,1,0): 122_190,
        (2,0,2): 128_383, (2,1,1): 128_383, (2,2,0): 132_325,
        (3,0,3): 140_014, (3,1,2): 145_818, (3,2,1): 151_621, (3,3,0): 157_425,
        (4,3,1): 165_114, (4,2,2): 170_918, (4,1,3): 176_721,
        (5,3,2): 190_214, (5,2,3): 196_018,
        (6,3,3): 215_314,
    }
    return limits.get((num_children, num_under13, num_over13))

###############################################################################
# Streamlit UI – Tabs
###############################################################################

tab_calc, tab_buffer, tab_limits = st.tabs(["FTB Calculator", "Income Buffer", "Eligibility Thresholds"])

# ---------------------------------------------------------------------------
# TAB 1 : Calculator
# ---------------------------------------------------------------------------
with tab_calc:
    st.subheader("Estimate your fortnightly FTB payments")

    # -- Inputs ---------------------------------------------------------
    col1, col2 = st.columns(2)
    with col1:
        partnered = st.radio("Family status", ("Single", "Partnered")) == "Partnered"
        income_primary = st.number_input("Primary earner ATI ($ p.a.)", min_value=0.0, step=1000.0)
        income_secondary = 0.0
        if partnered:
            income_secondary = st.number_input("Secondary earner ATI ($ p.a.)", min_value=0.0, step=1000.0)
    with col2:
        num_kids = st.slider("Number of dependent children", 0, 6, 1)
        children: List[Child] = []
        for i in range(num_kids):
            age = st.slider(f"Child {i+1} age", 0, 18, 5, key=f"age_{i}")
            children.append(Child(age))
        include_es = st.checkbox("Receive Energy Supplement (pre‑2016 recipients)")

    fam = Family(partnered, income_primary, income_secondary, children)

    # -- Calculations ----------------------------------------------------
    result_a = calc_ftb_part_a(fam)
    result_b = calc_ftb_part_b(fam, include_es=include_es)

    # -- Display ---------------------------------------------------------
    st.markdown("### Results")
    colA, colB = st.columns(2)
    with colA:
        st.metric("FTB Part A (ftn)", f"${result_a['pf']:.2f}")
        st.metric("Annual incl. supp", f"${result_a['annual_total']:,.0f}")
    with colB:
        st.metric("FTB Part B (ftn)", f"${result_b['pf']:.2f}")
        st.metric("Annual incl. supp", f"${result_b['annual_total']:,.0f}")

    total = result_a['annual_total'] + result_b['annual_total']
    st.success(f"**Total annual FTB: ${total:,.0f}**")

    if st.checkbox("Show details"):
        st.json({"Part A": result_a, "Part B": result_b}, expanded=False)

# ---------------------------------------------------------------------------
# TAB 2 : Income buffer
# ---------------------------------------------------------------------------
with tab_buffer:
    st.subheader("How much more can I earn before FTB stops?")
    col1b, col2b = st.columns(2)
    with col1b:
        partnered_b = st.radio("Family status", ("Single", "Partnered"), key="fsb") == "Partnered"
        inc_pri_b = st.number_input("Primary earner current ATI ($ p.a.)", min_value=0.0, step=1000.0, key="pri_b")
        inc_sec_b = 0.0
        if partnered_b:
            inc_sec_b = st.number_input("Secondary earner current ATI ($ p.a.)", min_value=0.0, step=1000.0, key="sec_b")
    with col2b:
        num_kids_b = st.slider("Children", 0, 6, 1, key="kids_b")
        ages_b: List[int] = []
        for i in range(num_kids_b):
            ages_b.append(st.slider(f"Age child {i+1}", 0, 18, 5, key=f"ageb_{i}"))

    # --- Part A buffer --------------------------------------------------
    num_under13 = sum(a <= 12 for a in ages_b)
    num_over13  = len(ages_b) - num_under13
    limit_a = part_a_income_limit(len(ages_b), num_under13, num_over13)
    fam_income_b = inc_pri_b + inc_sec_b

    st.markdown("#### FTB Part A")
    if limit_a is None:
        st.info("No official nil‑rate point published for this child mix.")
    else:
        if fam_income_b >= limit_a:
            st.warning(f"Your income (${fam_income_b:,.0f}) is already above the Part A cut‑off (${limit_a:,.0f}).")
        else:
            st.success(f"You can earn **${limit_a - fam_income_b:,.0f}** more before Part A ceases (cut‑off ${limit_a:,.0f}).")

    # --- Part B buffer --------------------------------------------------
    st.markdown("#### FTB Part B")
    youngest_b = min(ages_b) if ages_b else None
    if partnered_b:
        if youngest_b is None or youngest_b >= 13:
            st.info("Couple not eligible for Part B if youngest child is 13 or older.")
        else:
            prim_buf = max(0, RATES['ftb_b']['primary_limit'] - inc_pri_b)
            if youngest_b < 5:
                sec_cut = RATES['ftb_b']['nil_secondary']['under_5']
            else:
                sec_cut = RATES['ftb_b']['nil_secondary']['5_to_12']
            sec_buf = max(0, sec_cut - inc_sec_b)
            st.write(f"Primary earner can earn **${prim_buf:,.0f}** more (limit ${RATES['ftb_b']['primary_limit']:,.0f}).")
            st.write(f"Secondary earner can earn **${sec_buf:,.0f}** more (limit ${sec_cut:,.0f}).")
    else:
        prim_buf = max(0, RATES['ftb_b']['primary_limit'] - inc_pri_b)
        st.write(f"You can earn **${prim_buf:,.0f}** more before hitting the Part B cut‑off (${RATES['ftb_b']['primary_limit']:,.0f}).")

# ---------------------------------------------------------------------------
# TAB 3 : Eligibility Thresholds
# ---------------------------------------------------------------------------
with tab_limits:
    st.subheader("Maximum ATI for any FTB eligibility")
    col1c, col2c = st.columns(2)
    with col1c:
        partnered_c = st.radio("Family status", ("Single", "Partnered"), key="fsc") == "Partnered"
        num_kids_c = st.slider("Number of children", 0, 6, 1, key="kids_c")
    with col2c:
        ages_c: List[int] = []
        for i in range(num_kids_c):
            ages_c.append(st.slider(f"Age child {i+1}", 0, 18, 5, key=f"agec_{i}"))

    num_u_c = sum(a <= 12 for a in ages_c)
    num_o_c = len(ages_c) - num_u_c
    limit_a_c = part_a_income_limit(len(ages_c), num_u_c, num_o_c)

    st.markdown("### FTB Part A")
    if len(ages_c) == 0:
        st.write("Not eligible (no children).")
    elif limit_a_c:
        st.write(f"Nil‑rate cutoff: **${limit_a_c:,.0f}** ATI.")
    else:
        st.write("No published cutoff for this child mix.")

    st.markdown("### FTB Part B")
    if not ages_c:
        st.write("Not eligible (no children).")
    else:
        youngest_c = min(ages_c)
        if not partnered_c:
            st.write(f"Single parent: eligible to ATI **${RATES['ftb_b']['primary_limit']:,.0f}**.")
        else:
            if youngest_c >= 13:
                st.write("Couples with youngest child ≥13: not eligible for Part B.")
            else:
                st.write(f"Primary earner must be ≤ **${RATES['ftb_b']['primary_limit']:,.0f}**.")
                sec_lim = RATES['ftb_b']['nil_secondary']['under_5'] if youngest_c < 5 else RATES['ftb_b']['nil_secondary']['five_to_12'] if 'five_to_12' in RATES['ftb_b']['nil_secondary'] else RATES['ftb_b']['nil_secondary']['5_to_12']
                st.write(f"Secondary earner nil‑rate cutoff: **${sec_lim:,.0f}** (payment tapers above $6 
