import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import base64

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
END_YEAR_SUPPLEMENT = 916.15

st.set_page_config(page_title="Family Tax Benefit Calculator", layout="wide")
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
        }
        .stTabs [role="tab"] {
            background: #f0f2f6;
            padding: 0.75rem;
            margin-right: 0.5rem;
            border-radius: 5px;
            font-weight: bold;
        }
        .stTabs [role="tab"][aria-selected="true"] {
            background: #0066cc;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

st.title("💡 Family Tax Benefit Calculator")
st.caption("Updated for 2025 thresholds — including Part A, Part B, Rent Assistance, and Supplements")

# Tabs
income_tab, children_tab, results_tab = st.tabs(["🏠 Income & Rent", "👶 Children", "📊 Results"])

with income_tab:
    st.subheader("Family Income and Rent")
    income1 = st.number_input("Annual Income - Parent 1", min_value=0, step=1000)
    income2 = st.number_input("Annual Income - Parent 2 (if couple)", min_value=0, step=1000)
    rent_fortnight = st.number_input("Fortnightly Rent Paid", min_value=0.0, step=10.0)
    total_income = income1 + income2

with children_tab:
    st.subheader("Child Details")
    num_children = st.number_input("Number of children", min_value=0, step=1)
    child_ages = []
    for i in range(int(num_children)):
        age = st.slider(f"Age of Child {i+1}", 0, 19, 5)
        child_ages.append(age)

# Benefit calculations
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

# Calculate primary scenario
ftb_a = calc_ftb_part_a(total_income, len(child_ages))
status_a = "Maximum" if total_income <= FTB_A_THRESHOLD_MAX_RATE else ("Reduced" if ftb_a > 0 else "Ineligible")

is_couple = income2 > 0
if len(child_ages) >= 1 and (not is_couple or income2 <= FTB_B_PARTNER_INCOME_LIMIT):
    ftb_b = FTB_B_MAX_RATE_ANNUAL
    status_b = "Entitled"
else:
    ftb_b = 0
    status_b = "None"

if rent_fortnight > RA_THRESHOLD_FT:
    ra = min(RA_MAX_RATE_FT, (rent_fortnight - RA_THRESHOLD_FT) * 0.75)
else:
    ra = 0
ra_annual = ra * 26
supplements = END_YEAR_SUPPLEMENT * len(child_ages)

total_payment = ftb_a + ftb_b + ra_annual + supplements

with results_tab:
    st.subheader("Benefit Summary")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**FTB Part A:** `{status_a}`")
        st.markdown(f"**FTB Part B:** `{status_b}`")
        st.markdown(f"**Rent Assistance:** `{'Yes' if ra > 0 else 'No'}`")
        st.markdown(f"**Supplements:** `{len(child_ages)} × ${END_YEAR_SUPPLEMENT:.2f}`")
    with col2:
        st.success(f"**Total Annual Payment:** ${total_payment:,.2f}")
        st.info(f"**Fortnightly Estimate:** ${total_payment / 26:,.2f}")

    st.subheader("Payment Breakdown")
    st.write({
        "FTB Part A": f"${ftb_a:,.2f}",
        "FTB Part B": f"${ftb_b:,.2f}",
        "Rent Assistance": f"${ra_annual:,.2f}",
        "Supplements": f"${supplements:,.2f}"
    })

    st.subheader("📈 FTB Part A vs Income (1 Child)")
    x = np.linspace(0, 140000, 300)
    y = [calc_ftb_part_a(i, 1) for i in x]
    fig, ax = plt.subplots()
    ax.plot(x, y, label="FTB Part A (1 child)", color="#3399cc")
    ax.axvline(FTB_A_THRESHOLD_MAX_RATE, color='green', linestyle='--', label="Max Rate Threshold")
    ax.axvline(FTB_A_THRESHOLD_TAPER_END, color='orange', linestyle='--', label="Base Rate Threshold")
    ax.set_xlabel("Household Income")
    ax.set_ylabel("FTB Part A Annual Payment")
    ax.legend()
    st.pyplot(fig)

    st.subheader("🧮 Compare Scenarios")
    compare_income = st.slider("Compare different household incomes", 0, 140000, [30000, 80000, 120000], step=10000)
    compare_data = {
        f"${i:,}": {
            "FTB Part A": calc_ftb_part_a(i, len(child_ages)),
            "FTB Part B": FTB_B_MAX_RATE_ANNUAL if len(child_ages) and (not is_couple or income2 <= FTB_B_PARTNER_INCOME_LIMIT) else 0,
            "Rent Assist": ra_annual,
            "Supplements": supplements
        } for i in compare_income
    }
    compare_df = pd.DataFrame(compare_data).T
    st.dataframe(compare_df.style.format("${:,.2f}"))

    # CSV download
    csv = compare_df.to_csv().encode('utf-8')
    st.download_button("⬇️ Download scenario comparison as CSV", data=csv, file_name="ftb_scenario_comparison.csv", mime="text/csv")
