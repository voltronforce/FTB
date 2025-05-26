import streamlit as st

# --- Page Configuration and Styling ---
st.set_page_config(page_title="FTB Calculator (2024-25)", layout="wide")
# Use a simple sans-serif font for a modern government-style look
st.markdown("""
    <style>
    html, body {font-family: Arial, sans-serif;}
    .stTabs [role="tablist"] {margin-top: 1rem;}
    </style>
    """, unsafe_allow_html=True)

st.title("Family Tax Benefit Calculator (2024–25)")

# --- Constants based on Services Australia rates (24-25 financial year) ---
BASE_RATE_A = 71.26           # FTB Part A base rate per child per fortnight:contentReference[oaicite:15]{index=15}
MAX_RATE_A_UNDER13 = 222.04   # Max FTB Part A per child (0-12) per fortnight:contentReference[oaicite:16]{index=16}
MAX_RATE_A_13PLUS = 288.82    # Max FTB Part A per child (13-19 in full-time study):contentReference[oaicite:17]{index=17}
FTB_B_RATE_UNDER5 = 188.86    # Max FTB Part B per family per fortnight (youngest 0-4):contentReference[oaicite:18]{index=18}
FTB_B_RATE_5TO18 = 131.74     # Max FTB Part B per family per fortnight (youngest 5-18):contentReference[oaicite:19]{index=19}

# Income thresholds from official sites:
ITA_FREE_AREA = 65189        # Income free area for FTB Part A (full rate up to this ATI):contentReference[oaicite:20]{index=20}
ITA_UPPER_AREA = 115997       # Higher income free area (20% taper zone ends here):contentReference[oaicite:21]{index=21}
FTB_B_SINGLE_LIMIT = 117194   # Max ATI for any FTB Part B (single parent/full rate up to this):contentReference[oaicite:22]{index=22}

# Child age bands for Part B secondary income limit
FTB_B_SEC_LIMIT_YOUNG = 33653  # Secondary earner limit if youngest <5:contentReference[oaicite:23]{index=23}
FTB_B_SEC_LIMIT_5TO12 = 26207  # Secondary earner limit if youngest 5-12:contentReference[oaicite:24]{index=24}

# --- Helper Functions ---

def calc_ftb_part_a(annual_income, ages):
    """
    Calculate fortnightly FTB Part A based on combined annual income and list of child ages.
    Uses the 20%/30% tapers above the free areas. Returns (fortnightly_payment, annual_payment).
    """
    num_under13 = sum(1 for age in ages if age <= 12)
    num_over13 = len(ages) - num_under13
    # Compute the maximum possible FTB A per year at full rates:
    max_fortnight_total = num_under13*MAX_RATE_A_UNDER13 + num_over13*MAX_RATE_A_13PLUS
    max_annual_total = max_fortnight_total * 26

    # Determine income reduction:
    if annual_income <= ITA_FREE_AREA:
        # No reduction, get full max
        payment_annual = max_annual_total
    else:
        # Income above free area; start reducing
        excess = annual_income - ITA_FREE_AREA
        if annual_income <= ITA_UPPER_AREA:
            reduction = 0.20 * excess
        else:
            # For income beyond the upper area, first reduce 20% up to upper area, then 30% beyond
            reduction = 0.20 * (ITA_UPPER_AREA - ITA_FREE_AREA) + 0.30 * (annual_income - ITA_UPPER_AREA)
        payment_annual = max_annual_total - reduction

    # Floor at 0 if negative (no negative payments):
    payment_annual = max(payment_annual, 0)
    # Convert to fortnightly amount
    payment_fortnight = payment_annual / 26
    return payment_fortnight, payment_annual

def calc_ftb_part_b(annual_income, ages, partnered):
    """
    Calculate fortnightly FTB Part B based on incomes and ages.
    If partnered=True, expects annual_income as (primary_income, secondary_income) tuple.
    Returns (fortnightly_payment, annual_payment).
    """
    # Determine youngest child and corresponding max rate
    if ages:
        youngest = min(ages)
    else:
        youngest = None
    if youngest is None:
        return 0.0, 0.0
    if youngest <= 4:
        max_rate = FTB_B_RATE_UNDER5
    else:
        max_rate = FTB_B_RATE_5TO18

    # If single parent, treat annual_income as single income:
    if not partnered:
        primary_income = annual_income
        secondary_income = 0
        # Single parent part B: full rate if income ≤ limit, else 0
        if primary_income <= FTB_B_SINGLE_LIMIT:
            payment_annual = max_rate * 26
        else:
            payment_annual = 0.0
    else:
        # Partnered case: annual_income is a tuple (income1, income2)
        income1, income2 = annual_income
        primary = max(income1, income2)
        secondary = min(income1, income2)
        # Couple is eligible only if youngest child <13 and primary ≤ limit
        if youngest >= 13 or primary > FTB_B_SINGLE_LIMIT:
            payment_annual = 0.0
        else:
            # Compute secondary taper:
            if secondary <= 6789:
                payment_annual = max_rate * 26
            else:
                # Determine secondary earner cutoff based on child's age
                if youngest <= 4:
                    sec_limit = FTB_B_SEC_LIMIT_YOUNG
                else:
                    sec_limit = FTB_B_SEC_LIMIT_5TO12
                if secondary >= sec_limit:
                    payment_annual = 0.0
                else:
                    reduction = 0.20 * (secondary - 6789)
                    payment_annual = max_rate * 26 - reduction
                    payment_annual = max(payment_annual, 0.0)
    payment_fortnight = payment_annual / 26
    return payment_fortnight, payment_annual

# Function to lookup FTB Part A cutoff (income at which FTB A falls to zero) based on composition
def ftb_part_a_income_limit(num_children, num_under13, num_over13):
    """
    Return the annual income limit where FTB Part A goes to zero, based on number of children 
    and their age composition. Uses official DSS tables for up to 6 children.
    If combination not explicitly in table, returns None.
    """
    # Hardcoded income limits from Services Australia tables:contentReference[oaicite:25]{index=25}:
    # Format: {(num_under13, num_over13): limit}
    limits = {
        # 1 child
        (1,0): 122190, (0,1): 122190,
        # 2 children
        (2,0): 128383, (1,1): 128383, (0,2): 132325,
        # 3 children
        (3,0): 140014, (2,1): 145818, (1,2): 151621, (0,3): 157425,
        # 4 children (selected combos given)
        (3,1): 165114, (2,2): 170918, (1,3): 176721,
        # 5 children (selected)
        (3,2): 190214, (2,3): 196018,
        # 6 children (given combination)
        (3,3): 215314
    }
    # For fewer children, pad with zeros
    key = (num_under13, num_over13)
    return limits.get(key, None)

# Create tabs
tab1, tab2, tab3 = st.tabs(["FTB Calculator", "Income Buffer", "Eligibility Thresholds"])

with tab1:
    st.header("FTB Payment Calculator")
    st.write("Enter your family details to estimate your fortnightly FTB Part A and Part B payments.")
    colA, colB = st.columns(2)
    with colA:
        # Family status
        status = st.radio("Family status:", ("Single parent", "Partnered parents"), help="Select whether you have a partner.")
        if status == "Partnered parents":
            in1 = st.number_input("Annual income (you)", min_value=0.0, help="Your annual adjusted taxable income")
            in2 = st.number_input("Annual income (partner)", min_value=0.0, help="Your partner's annual adjusted taxable income")
        else:
            in1 = st.number_input("Annual income (you)", min_value=0.0, help="Your annual adjusted taxable income")
            in2 = 0.0
    with colB:
        # Children inputs
        num_kids = st.slider("Number of dependent children", 0, 6, help="Enter total number of eligible children.")
        ages = []
        for i in range(int(num_kids)):
            age = st.slider(f"Age of child #{i+1}", 0, 18, help="Enter age of child (0-18).")
            ages.append(age)
    # Perform calculations
    family_income = (in1, in2) if status == "Partnered parents" else in1
    ftbA_fortnight, ftbA_year = calc_ftb_part_a(in1 + in2, ages)
    ftbB_fortnight, ftbB_year = calc_ftb_part_b(family_income, ages, partnered=(status == "Partnered parents"))
    # Display results
    st.subheader("Estimated Payments:")
    st.write(f"**FTB Part A:** ${ftbA_fortnight:,.2f} per fortnight  " 
             f"(${ftbA_year:,.0f} per year) based on {int(num_kids)} child(ren)")
    st.write(f"**FTB Part B:** ${ftbB_fortnight:,.2f} per fortnight  "
             f"(${ftbB_year:,.0f} per year)")
    st.write("_Note: Actual payments may vary due to share of care, child support, and other rules._")

with tab2:
    st.header("Income Buffer Before Eligibility Loss")
    st.write("Enter your current income and family composition to see how much more you could earn before losing FTB Part A or Part B eligibility.")
    colA2, colB2 = st.columns(2)
    with colA2:
        status2 = st.radio("Family status:", ("Single parent", "Partnered parents"), key="status2")
        if status2 == "Partnered parents":
            current_primary = st.number_input("Current primary earner income", min_value=0.0, key="curr1",
                                              help="Higher income earner in your family")
            current_secondary = st.number_input("Current secondary earner income", min_value=0.0, key="curr2",
                                                help="Lower income earner (or 0 if none)")
        else:
            current_primary = st.number_input("Your current income", min_value=0.0, key="curr_single",
                                              help="Your annual adjusted taxable income")
            current_secondary = 0.0
    with colB2:
        num_kids2 = st.slider("Number of dependent children", 0, 6, key="kids2")
        ages2 = []
        for i in range(int(num_kids2)):
            age = st.slider(f"Age of child #{i+1}", 0, 18, key=f"age2_{i}",
                            help="Enter age of child (0-18).")
            ages2.append(age)

    # Compute Part A loss threshold
    num_u = sum(1 for age in ages2 if age <= 12)
    num_o = len(ages2) - num_u
    limit_ftbA = ftb_part_a_income_limit(num_kids2, num_u, num_o)
    additionalA = (limit_ftbA - (current_primary + current_secondary)) if limit_ftbA is not None else None

    # Compute Part B buffer
    youngest2 = min(ages2) if ages2 else None
    bufB_msgs = []
    if status2 == "Single parent":
        # Single: threshold is FTB_B_SINGLE_LIMIT
        if current_primary >= FTB_B_SINGLE_LIMIT:
            bufB_primary = 0.0
        else:
            bufB_primary = FTB_B_SINGLE_LIMIT - current_primary
        bufB_msgs.append(f"Single parent: can earn up to **${FTB_B_SINGLE_LIMIT:,.0f}** (breaks eligibility):contentReference[oaicite:26]{index=26}. " +
                         (f"You can earn **${bufB_primary:,.0f}** more." if bufB_primary > 0 else "Already above threshold."))
    else:
        # Partnered case
        if not ages2 or youngest2 >= 13:
            bufB_msgs.append("Partnered: *No FTB Part B eligibility* (youngest child ≥13).")
        else:
            # Primary buffer
            bufB_primary = max(0.0, FTB_B_SINGLE_LIMIT - current_primary)
            bufB_msgs.append(f"Partnered: primary earner limit is **${FTB_B_SINGLE_LIMIT:,.0f}**:contentReference[oaicite:27]{index=27}; " +
                             (f"${bufB_primary:,.0f}** more can be earned." if bufB_primary > 0 else "already at/above limit."))
            # Secondary buffer
            if youngest2 <= 4:
                sec_limit = FTB_B_SEC_LIMIT_YOUNG
            else:
                sec_limit = FTB_B_SEC_LIMIT_5TO12
            if current_secondary >= sec_limit:
                bufB_msgs.append(f"Secondary earner is already above the Part B cutoff of **${sec_limit:,.0f}**:contentReference[oaicite:28]{index=28}.")
            else:
                bufB_msgs.append(f"Secondary earner limit is **${sec_limit:,.0f}**; you can earn **${(sec_limit - current_secondary):,.0f}** more.")
    # Display buffers
    st.subheader("FTB Part A Buffer:")
    if limit_ftbA is not None:
        st.write(f"You stop receiving **FTB Part A** when family income reaches **${limit_ftbA:,.0f}** (for this family composition):contentReference[oaicite:29]{index=29}.")
        if additionalA is not None:
            if additionalA > 0:
                st.write(f"At current income ${current_primary+current_secondary:,.0f}, you could earn **${additionalA:,.0f}** more before losing FTB Part A.")
            else:
                st.write("You are already at or above the Part A cutoff; no further income can be earned without losing Part A eligibility.")
    else:
        st.write("FTB Part A limit not available for this combination of children.")
    st.subheader("FTB Part B Buffer:")
    for msg in bufB_msgs:
        st.write("- " + msg)

with tab3:
    st.header("Eligibility Income Limits by Family")
    st.write("Enter family status and children to see the maximum annual incomes for FTB Part A and B eligibility.")
    colA3, colB3 = st.columns(2)
    with colA3:
        status3 = st.radio("Family status:", ("Single parent", "Partnered parents"), key="status3")
    with colB3:
        num_kids3 = st.slider("Number of dependent children", 0, 6, key="kids3")
        ages3 = []
        for i in range(int(num_kids3)):
            age = st.slider(f"Age of child #{i+1}", 0, 18, key=f"age3_{i}")
            ages3.append(age)

    # FTB Part A eligibility limit:
    num_u3 = sum(1 for age in ages3 if age <= 12)
    num_o3 = len(ages3) - num_u3
    limitA3 = ftb_part_a_income_limit(num_kids3, num_u3, num_o3)
    st.subheader("FTB Part A Income Limit:")
    if num_kids3 == 0:
        st.write("No children, not eligible for FTB Part A.")
    else:
        if limitA3:
            st.write(f"With {num_kids3} child(ren) (ages {', '.join(map(str, ages3))}), you stop receiving FTB Part A at **${limitA3:,.0f}**:contentReference[oaicite:30]{index=30}.")
        else:
            st.write("Exact income limit not listed for this child age combination.")

    # FTB Part B eligibility limit:
    st.subheader("FTB Part B Income Limits:")
    youngest3 = min(ages3) if ages3 else None
    if not ages3:
        st.write("No children, not eligible for FTB Part B.")
    else:
        if status3 == "Single parent":
            st.write(f"As a single parent, you are eligible for FTB Part B if your income is ≤ **${FTB_B_SINGLE_LIMIT:,.0f}**:contentReference[oaicite:31]{index=31}.")
        else:
            if youngest3 is None or youngest3 >= 13:
                st.write("Partnered parents with youngest child ≥13 are *not* eligible for FTB Part B.")
            else:
                st.write(f"Primary earner must have ≤ **${FTB_B_SINGLE_LIMIT:,.0f}**:contentReference[oaicite:32]{index=32}. ", end='')
                if youngest3 <= 4:
                    st.write(f"Secondary earner must have ≤ **${FTB_B_SEC_LIMIT_YOUNG:,.0f}**:contentReference[oaicite:33]{index=33}.")
                else:
                    st.write(f"Secondary earner must have ≤ **${FTB_B_SEC_LIMIT_5TO12:,.0f}**:contentReference[oaicite:34]{index=34}.")
