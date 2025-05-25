import streamlit as st

# Configurable parameters
FTB_A_THRESHOLD_MAX_RATE = 65189
FTB_A_THRESHOLD_TAPER_END = 115997
FTB_A_MAX_RATE_ANNUAL = 6705.05
FTB_A_TAPER_RATE1 = 0.20
FTB_A_TAPER_RATE2 = 0.30
FTB_A_BASE_RATE_ANNUAL = 2774.00
FTB_B_PARTNER_INCOME_LIMIT = 11233
FTB_B_MAX_RATE_ANNUAL = 163.40 * 26
RA_THRESHOLD_FT = 196.42
RA_MAX_RATE_FT = 249.20

st.set_page_config(page_title="Family Tax Benefit Calculator", layout="centered")
st.title("Family Tax Benefit Calculator")
st.markdown("""This tool estimates your **Family Tax Benefit (FTB)** including Part A, Part B, and Rent Assistance.
Updated for 2025 thresholds.""")

# Inputs
st.header("Family Income and Rent")
income1 = st.number_input("Annual Income - Parent 1", min_value=0, step=1000)
income2 = st.number_input("Annual Income - Parent 2 (if couple)", min_value=0, step=1000)
rent_fortnight = st.number_input("Fortnightly Rent Paid", min_value=0.0, step=10.0)

st.header("Children")
num_children = st.number_input("Number of eligible children", min_value=0, step=1)

# Calculations
total_income = income1 + income2

def calc_ftb_part_a(income, children):
    if income <= FTB_A_THRESHOLD_MAX_RATE:
        amt1 = FTB_A_MAX_RATE_ANNUAL * children
    elif income <= FTB_A_THRESHOLD_TAPER_END:
        red = (income - FTB_A_THRESHOLD_MAX_RATE) * FTB_A_TAPER_RATE1
        amt1 = max(0, FTB_A_MAX_RATE_ANNUAL * children - red)
    else:
        red1 = (FTB_A_THRESHOLD_TAPER_END - FTB_A_THRESHOLD_MAX_RATE) * FTB_A_TAPER_RATE1
        red2 = (income - FTB_A_THRESHOLD_TAPER_END) * FTB_A_TAPER_RATE2
        amt1 = max(0, FTB_A_MAX_RATE_ANNUAL * children - red1 - red2)

    if income <= FTB_A_THRESHOLD_TAPER_END:
        amt2 = FTB_A_BASE_RATE_ANNUAL * children
    else:
        redb = (income - FTB_A_THRESHOLD_TAPER_END) * FTB_A_TAPER_RATE2
        amt2 = max(0, FTB_A_BASE_RATE_ANNUAL * children - redb)
    return max(amt1, amt2)

ftb_a = calc_ftb_part_a(total_income, num_children)
status_a = "Maximum" if total_income <= FTB_A_THRESHOLD_MAX_RATE else ("Reduced" if ftb_a > 0 else "Ineligible")

# FTB Part B
is_couple = income2 > 0
if num_children >= 1 and (not is_couple or income2 <= FTB_B_PARTNER_INCOME_LIMIT):
    ftb_b = FTB_B_MAX_RATE_ANNUAL
    status_b = "Entitled"
else:
    ftb_b = 0
    status_b = "None"

# Rent Assistance
if rent_fortnight > RA_THRESHOLD_FT:
    ra = min(RA_MAX_RATE_FT, (rent_fortnight - RA_THRESHOLD_FT) * 0.75)
else:
    ra = 0
ra_annual = ra * 26

# Output
st.header("Results")
status_color = {"Maximum": "green", "Reduced": "orange", "Ineligible": "red"}.get(status_a, "black")
st.markdown(f"**FTB Part A:** <span style='color:{status_color}'>{status_a}</span>", unsafe_allow_html=True)
st.markdown(f"**FTB Part B:** {status_b}")
st.markdown(f"**Rent Assistance:** {'Yes' if ra > 0 else 'No'}")

ftb_total = ftb_a + ftb_b + ra_annual
st.markdown(f"**Total Annual Payment:** ${ftb_total:,.2f}")
st.markdown(f"**Fortnightly Estimate:** ${ftb_total/26:,.2f}")

st.subheader("Breakdown")
st.write({
    "FTB Part A": f"${ftb_a:,.2f}",
    "FTB Part B": f"${ftb_b:,.2f}",
    "Rent Assistance": f"${ra_annual:,.2f}"
})
