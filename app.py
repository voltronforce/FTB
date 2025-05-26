import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import json

# Configuration and Constants
@dataclass
class FTBRates:
    """Store FTB rates and thresholds"""
    # FTB Part A rates (fortnightly)
    base_rate_under_13: float = 66.34
    base_rate_13_over: float = 86.60
    max_rate_under_13: float = 197.96
    max_rate_13_over: float = 257.46
    
    # FTB Part B rates (fortnightly)
    ftb_b_max_under_5: float = 171.14
    ftb_b_max_5_over: float = 119.24
    
    # Income test thresholds
    ftb_a_higher_threshold: float = 58108
    ftb_a_higher_taper: float = 0.20
    ftb_a_base_threshold: float = 103368
    ftb_a_base_taper: float = 0.30
    ftb_b_threshold: float = 6497
    ftb_b_taper: float = 0.20
    
    # Supplements (annual)
    ftb_a_supplement_rate: float = 842.64
    ftb_a_supplement_limit: float = 80000
    ftb_b_supplement_rate: float = 421.32

@dataclass
class Child:
    """Store individual child information"""
    age: int
    immunisation: bool = True
    healthy_start: bool = True
    maintenance_action: bool = True

@dataclass
class FTBResult:
    """Store calculation results"""
    fortnightly_rate: float
    test_type: str
    base_rate: float = 0
    compliance_reduction: float = 0
    maintenance_reduction: float = 0
    reason: str = ""

class FTBCalculator:
    """Main calculator class for Family Tax Benefit calculations"""
    
    def __init__(self, rates: FTBRates):
        self.rates = rates
    
    def calculate_ftb_part_a(self, child: Child, annual_income: float, income_support: bool) -> FTBResult:
        """Calculate FTB Part A for a single child"""
        # Determine base rates based on age
        max_rate = self.rates.max_rate_under_13 if child.age < 13 else self.rates.max_rate_13_over
        base_rate = self.rates.base_rate_under_13 if child.age < 13 else self.rates.base_rate_13_over
        
        # Apply compliance reductions
        compliance_reduction = 0
        if not child.immunisation:
            compliance_reduction += max_rate * 0.5  # 50% reduction
        if not child.healthy_start and child.age >= 4:
            compliance_reduction += max_rate * 0.5  # 50% reduction
        
        # If on income support, get maximum rate
        if income_support:
            return FTBResult(
                fortnightly_rate=max(0, max_rate - compliance_reduction),
                test_type="Income Support - Maximum Rate",
                base_rate=max_rate,
                compliance_reduction=compliance_reduction
            )
        
        # Calculate rate based on income test
        if annual_income <= self.rates.ftb_a_higher_threshold:
            # Maximum rate
            rate = max_rate
            test_type = "Maximum Rate Income Test"
        elif annual_income <= self.rates.ftb_a_base_threshold:
            # Higher income test - taper from max to base
            excess = annual_income - self.rates.ftb_a_higher_threshold
            annual_reduction = excess * self.rates.ftb_a_higher_taper
            fortnightly_reduction = annual_reduction / 26
            rate = max(base_rate, max_rate - fortnightly_reduction)
            test_type = "Higher Income Test"
        else:
            # Base rate test - taper from base rate
            excess = annual_income - self.rates.ftb_a_base_threshold
            annual_reduction = excess * self.rates.ftb_a_base_taper
            fortnightly_reduction = annual_reduction / 26
            rate = max(0, base_rate - fortnightly_reduction)
            test_type = "Base Rate Income Test"
        
        # Apply maintenance action test
        maintenance_reduction = 0
        if not child.maintenance_action:
            maintenance_reduction = rate
            rate = 0
        
        return FTBResult(
            fortnightly_rate=max(0, rate - compliance_reduction),
            test_type=test_type,
            base_rate=rate,
            compliance_reduction=compliance_reduction,
            maintenance_reduction=maintenance_reduction
        )
    
    def calculate_ftb_part_b(self, children: List[Child], family_type: str, annual_income: float) -> FTBResult:
        """Calculate FTB Part B"""
        if family_type == "couple":
            return FTBResult(
                fortnightly_rate=0,
                test_type="Not payable - Couple",
                reason="FTB Part B is generally not payable to couples"
            )
        
        # Find youngest child
        youngest_age = min(child.age for child in children)
        max_rate = self.rates.ftb_b_max_under_5 if youngest_age < 5 else self.rates.ftb_b_max_5_over
        
        # Apply income test
        if annual_income <= self.rates.ftb_b_threshold:
            return FTBResult(
                fortnightly_rate=max_rate,
                test_type="Under Income Threshold",
                base_rate=max_rate
            )
        
        # Calculate taper
        excess = annual_income - self.rates.ftb_b_threshold
        annual_reduction = excess * self.rates.ftb_b_taper
        fortnightly_reduction = annual_reduction / 26
        final_rate = max(0, max_rate - fortnightly_reduction)
        
        return FTBResult(
            fortnightly_rate=final_rate,
            test_type="Income Test Applied",
            base_rate=max_rate
        )
    
    def calculate_work_incentive(self, children: List[Child], family_type: str, current_income: float) -> Dict:
        """Calculate work incentive information"""
        # Calculate income where FTB Part A cuts out
        ftb_a_cutout = 0
        if children:
            base_rate = self.rates.base_rate_under_13 if children[0].age < 13 else self.rates.base_rate_13_over
            annual_base_rate = base_rate * 26
            ftb_a_cutout = self.rates.ftb_a_base_threshold + (annual_base_rate / self.rates.ftb_a_base_taper)
        
        # Calculate income where FTB Part B cuts out
        ftb_b_cutout = 0
        if family_type == "single" and children:
            youngest_age = min(child.age for child in children)
            max_rate = self.rates.ftb_b_max_under_5 if youngest_age < 5 else self.rates.ftb_b_max_5_over
            annual_max_rate = max_rate * 26
            ftb_b_cutout = self.rates.ftb_b_threshold + (annual_max_rate / self.rates.ftb_b_taper)
        
        earliest_cutout = min(x for x in [ftb_a_cutout, ftb_b_cutout] if x > 0) if any([ftb_a_cutout, ftb_b_cutout]) else 0
        additional_income_capacity = max(0, earliest_cutout - current_income)
        
        return {
            "ftb_a_cutout": ftb_a_cutout,
            "ftb_b_cutout": ftb_b_cutout,
            "earliest_cutout": earliest_cutout,
            "additional_annual_income": additional_income_capacity,
            "additional_weekly_income": additional_income_capacity / 52
        }

def main():
    st.set_page_config(
        page_title="Family Tax Benefit Calculator",
        page_icon="🪲",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #2E8B57, #228B22);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .beetle-logo {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .result-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #2E8B57;
        margin: 1rem 0;
    }
    .work-incentive {
        background: linear-gradient(135deg, #17a2b8, #138496);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .alert-warning {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .alert-info {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <div class="beetle-logo">🪲</div>
        <h1>Family Tax Benefit Calculator</h1>
        <p>Calculate your Family Tax Benefit Part A and Part B entitlements</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state for rates
    if 'rates' not in st.session_state:
        st.session_state.rates = FTBRates()
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a section:",
        ["Calculator", "Results", "Charts", "Rates & Thresholds"]
    )
    
    if page == "Calculator":
        calculator_page()
    elif page == "Results":
        results_page()
    elif page == "Charts":
        charts_page()
    elif page == "Rates & Thresholds":
        rates_page()

def calculator_page():
    st.header("Family Tax Benefit Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Family Information")
        family_type = st.selectbox("Family Type:", ["couple", "single"], format_func=lambda x: "Couple" if x == "couple" else "Single Parent")
        annual_income = st.number_input("Annual Family Income ($):", min_value=0.0, value=50000.0, step=1000.0)
        rent_assistance = st.number_input("Annual Rent Assistance ($):", min_value=0.0, value=0.0, step=100.0)
        income_support = st.checkbox("Family receives income support payment")
    
    with col2:
        st.subheader("Children Information")
        num_children = st.number_input("Number of Children:", min_value=0, max_value=10, value=2)
        
        children = []
        if num_children > 0:
            for i in range(num_children):
                with st.expander(f"Child {i+1} Details", expanded=True):
                    age = st.number_input(f"Age of Child {i+1}:", min_value=0, max_value=25, value=5, key=f"age_{i}")
                    immunisation = st.checkbox(f"Immunisation requirements met", value=True, key=f"imm_{i}")
                    healthy_start = st.checkbox(f"Healthy Start for School requirements met", value=True, key=f"health_{i}")
                    maintenance_action = st.checkbox(f"Maintenance Action Test passed", value=True, key=f"maint_{i}")
                    
                    children.append(Child(
                        age=age,
                        immunisation=immunisation,
                        healthy_start=healthy_start,
                        maintenance_action=maintenance_action
                    ))
    
    # Store calculation inputs in session state
    if st.button("Calculate FTB", type="primary"):
        if num_children == 0:
            st.error("Please enter at least one child to calculate FTB.")
        else:
            calculator = FTBCalculator(st.session_state.rates)
            
            # Calculate FTB Part A for each child
            ftb_a_results = []
            for i, child in enumerate(children):
                result = calculator.calculate_ftb_part_a(child, annual_income, income_support)
                ftb_a_results.append({
                    'child_index': i + 1,
                    'age': child.age,
                    'result': result
                })
            
            # Calculate FTB Part B
            ftb_b_result = calculator.calculate_ftb_part_b(children, family_type, annual_income)
            
            # Calculate totals
            total_ftb_a_fortnightly = sum(r['result'].fortnightly_rate for r in ftb_a_results)
            total_ftb_b_fortnightly = ftb_b_result.fortnightly_rate
            total_fortnightly = total_ftb_a_fortnightly + total_ftb_b_fortnightly
            total_annual = total_fortnightly * 26
            
            # Calculate supplements
            ftb_a_supplement = 0
            ftb_b_supplement = 0
            
            if total_ftb_a_fortnightly > 0 and annual_income <= st.session_state.rates.ftb_a_supplement_limit:
                ftb_a_supplement = st.session_state.rates.ftb_a_supplement_rate * len(children)
            
            if total_ftb_b_fortnightly > 0:
                ftb_b_supplement = st.session_state.rates.ftb_b_supplement_rate
            
            total_annual_with_supplements = total_annual + ftb_a_supplement + ftb_b_supplement
            
            # Calculate work incentive
            work_incentive = calculator.calculate_work_incentive(children, family_type, annual_income)
            
            # Store results in session state
            st.session_state.calculation_results = {
                'family_type': family_type,
                'annual_income': annual_income,
                'rent_assistance': rent_assistance,
                'income_support': income_support,
                'children': children,
                'ftb_a_results': ftb_a_results,
                'ftb_b_result': ftb_b_result,
                'total_ftb_a_fortnightly': total_ftb_a_fortnightly,
                'total_ftb_b_fortnightly': total_ftb_b_fortnightly,
                'total_fortnightly': total_fortnightly,
                'total_annual': total_annual,
                'ftb_a_supplement': ftb_a_supplement,
                'ftb_b_supplement': ftb_b_supplement,
                'total_annual_with_supplements': total_annual_with_supplements,
                'work_incentive': work_incentive
            }
            
            st.success("Calculation completed! Check the Results tab.")

def results_page():
    st.header("Calculation Results")
    
    if 'calculation_results' not in st.session_state:
        st.info("Please complete the calculation in the Calculator tab first.")
        return
    
    results = st.session_state.calculation_results
    
    # Summary cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="result-card">
            <h4>Total Family Entitlement</h4>
            <h2>${results['total_annual_with_supplements']:.2f}</h2>
            <p>Annual (including supplements)</p>
            <h3>${results['total_fortnightly']:.2f}</h3>
            <p>Fortnightly (regular payments)</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="result-card">
            <h4>FTB Part A</h4>
            <h2>${(results['total_ftb_a_fortnightly'] * 26 + results['ftb_a_supplement']):.2f}</h2>
            <p>Annual (inc. supplement: ${results['ftb_a_supplement']:.2f})</p>
            <h3>${results['total_ftb_a_fortnightly']:.2f}</h3>
            <p>Fortnightly</p>
            <p><strong>Assessment:</strong> {results['ftb_a_results'][0]['result'].test_type if results['ftb_a_results'] else 'N/A'}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="result-card">
            <h4>FTB Part B</h4>
            <h2>${(results['total_ftb_b_fortnightly'] * 26 + results['ftb_b_supplement']):.2f}</h2>
            <p>Annual (inc. supplement: ${results['ftb_b_supplement']:.2f})</p>
            <h3>${results['total_ftb_b_fortnightly']:.2f}</h3>
            <p>Fortnightly</p>
            <p><strong>Assessment:</strong> {results['ftb_b_result'].test_type}</p>
        </div>
        """, unsafe_allow_html=True)
    
    if results['ftb_b_result'].reason:
        st.markdown(f"""
        <div class="alert-warning">
            {results['ftb_b_result'].reason}
        </div>
        """, unsafe_allow_html=True)
    
    # Work Incentive Information
    work_incentive = results['work_incentive']
    if work_incentive['additional_annual_income'] > 0:
        st.markdown(f"""
        <div class="work-incentive">
            <h4>Work Incentive Information</h4>
            <p>Understanding how additional income affects your payments:</p>
            <ul>
                <li>You can earn up to <strong>${work_incentive['additional_annual_income']:.0f}</strong> more annually (<strong>${work_incentive['additional_weekly_income']:.0f}</strong> per week) before losing eligibility</li>
                <li>FTB Part A cuts out at: <strong>${work_incentive['ftb_a_cutout']:.0f}</strong> annual income</li>
                {f"<li>FTB Part B cuts out at: <strong>${work_incentive['ftb_b_cutout']:.0f}</strong> annual income</li>" if work_incentive['ftb_b_cutout'] > 0 else ""}
            </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="work-incentive">
            <h4>Work Incentive Information</h4>
            <p><strong>Your income is above the cut-out thresholds.</strong></p>
            <p>Consider reviewing your circumstances or seek advice about maximizing your family's financial position.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Breakdown by Child
    st.subheader("Breakdown by Child")
    for child_result in results['ftb_a_results']:
        result = child_result['result']
        st.markdown(f"""
        <div class="result-card">
            <h5>Child {child_result['child_index']} (Age: {child_result['age']})</h5>
            <p><strong>FTB Part A Rate:</strong> ${result.fortnightly_rate:.2f} per fortnight</p>
            <p><strong>Assessment Type:</strong> {result.test_type}</p>
            {f'<div class="alert-warning"><strong>Compliance Reduction:</strong> ${result.compliance_reduction:.2f} - Check immunisation and health requirements</div>' if result.compliance_reduction > 0 else ''}
            {f'<div class="alert-warning"><strong>Maintenance Action Test:</strong> Payment suspended - Action required</div>' if result.maintenance_reduction > 0 else ''}
        </div>
        """, unsafe_allow_html=True)
    
    # Important Notes
    rent_note = f"<li>Rent Assistance has been noted but not calculated in this tool</li>" if results['rent_assistance'] > 0 else ""
    st.markdown(f"""
    <div class="alert-info">
        <strong>Important Notes:</strong>
        <ul>
            <li>These calculations are estimates based on current rates and your inputs</li>
            <li>Actual payments may vary based on your specific circumstances</li>
            <li>Supplements are paid annually after reconciliation</li>
            <li>Contact Services Australia for official assessments and advice</li>
            {rent_note}
        </ul>
    </div>
    """, unsafe_allow_html=True)

def charts_page():
    st.header("Family Tax Benefit Rate Charts")
    
    if 'calculation_results' not in st.session_state:
        st.info("Please complete the calculation in the Calculator tab first to see personalized charts.")
        # Show default charts
        children = [Child(age=5)]
        family_type = "single"
    else:
        results = st.session_state.calculation_results
        children = results['children']
        family_type = results['family_type']
    
    calculator = FTBCalculator(st.session_state.rates)
    
    # Generate FTB Part A Chart
    st.subheader("FTB Part A Rate by Annual Income")
    
    income_range = list(range(0, 150001, 2000))
    ftb_a_rates = []
    
    for income in income_range:
        total_rate = 0
        for child in children:
            result = calculator.calculate_ftb_part_a(child, income, False)
            total_rate += result.fortnightly_rate
        ftb_a_rates.append(total_rate)
    
    fig_a = go.Figure()
    fig_a.add_trace(go.Scatter(
        x=income_range,
        y=ftb_a_rates,
        mode='lines',
        name='FTB Part A ($/fortnight)',
        line=dict(color='#2E8B57', width=3),
        fill='tonexty'
    ))
    
    # Add threshold lines
    fig_a.add_vline(x=st.session_state.rates.ftb_a_higher_threshold, 
                   line_dash="dash", line_color="red",
                   annotation_text="Higher Income Test Threshold")
    fig_a.add_vline(x=st.session_state.rates.ftb_a_base_threshold, 
                   line_dash="dash", line_color="orange",
                   annotation_text="Base Rate Test Threshold")
    
    fig_a.update_layout(
        title="FTB Part A Rate by Annual Income",
        xaxis_title="Annual Family Income ($)",
        yaxis_title="Fortnightly Rate ($)",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_a, use_container_width=True)
    
    # Generate FTB Part B Chart
    st.subheader("FTB Part B Rate by Annual Income")
    
    income_range_b = list(range(0, 50001, 1000))
    ftb_b_rates = []
    
    for income in income_range_b:
        result = calculator.calculate_ftb_part_b(children, family_type, income)
        ftb_b_rates.append(result.fortnightly_rate)
    
    fig_b = go.Figure()
    fig_b.add_trace(go.Scatter(
        x=income_range_b,
        y=ftb_b_rates,
        mode='lines',
        name='FTB Part B ($/fortnight)',
        line=dict(color='#17a2b8', width=3),
        fill='tonexty'
    ))
    
    # Add threshold line
    fig_b.add_vline(x=st.session_state.rates.ftb_b_threshold, 
                   line_dash="dash", line_color="red",
                   annotation_text="Income Test Threshold")
    
    fig_b.update_layout(
        title="FTB Part B Rate by Annual Income",
        xaxis_title="Annual Family Income ($)",
        yaxis_title="Fortnightly Rate ($)",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_b, use_container_width=True)

def rates_page():
    st.header("FTB Rates and Thresholds (2024-25)")
    st.info("These rates are editable. Changes will update the calculator automatically.")
    
    # FTB Part A Rates
    st.subheader("FTB Part A Rates (per fortnight)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.rates.base_rate_under_13 = st.number_input(
            "Base rate - under 13:", 
            value=st.session_state.rates.base_rate_under_13, 
            step=0.01
        )
        st.session_state.rates.max_rate_under_13 = st.number_input(
            "Maximum rate - under 13:", 
            value=st.session_state.rates.max_rate_under_13, 
            step=0.01
        )
    
    with col2:
        st.session_state.rates.base_rate_13_over = st.number_input(
            "Base rate - 13 and over:", 
            value=st.session_state.rates.base_rate_13_over, 
            step=0.01
        )
        st.session_state.rates.max_rate_13_over = st.number_input(
            "Maximum rate - 13 and over:", 
            value=st.session_state.rates.max_rate_13_over, 
            step=0.01
        )
    
    # FTB Part B Rates
    st.subheader("FTB Part B Rates (per fortnight)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.rates.ftb_b_max_under_5 = st.number_input(
            "Maximum rate - under 5:", 
            value=st.session_state.rates.ftb_b_max_under_5, 
            step=0.01
        )
    
    with col2:
        st.session_state.rates.ftb_b_max_5_over = st.number_input(
            "Maximum rate - 5 and over:", 
            value=st.session_state.rates.ftb_b_max_5_over, 
            step=0.01
        )
    
    # Income Test Thresholds
    st.subheader("Income Test Thresholds")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.rates.ftb_a_higher_threshold = st.number_input(
            "FTB Part A - Higher income test threshold:", 
            value=st.session_state.rates.ftb_a_higher_threshold, 
            step=1.0
        )
        st.session_state.rates.ftb_a_base_threshold = st.number_input(
            "FTB Part A - Base rate test threshold:", 
            value=st.session_state.rates.ftb_a_base_threshold, 
            step=1.0
        )
        st.session_state.rates.ftb_b_threshold = st.number_input(
            "FTB Part B - Income test threshold:", 
            value=st.session_state.rates.ftb_b_threshold, 
            step=1.0
        )
    
    with col2:
        st.session_state.rates.ftb_a_higher_taper = st.number_input(
            "FTB Part A - Higher taper rate:", 
            value=st.session_state.rates.ftb_a_higher_taper, 
            step=0.01
        )
        st.session_state.rates.ftb_a_base_taper = st.number_input(
            "FTB Part A - Base taper rate:", 
            value=st.session_state.rates.ftb_a_base_taper, 
            step=0.01
        )
        st.session_state.rates.ftb_b_taper = st.number_input(
            "FTB Part B - Taper rate:", 
            value=st.session_state.rates.ftb_b_taper, 
            step=0.01
        )
    
    # Supplements
    st.subheader("Supplements (Annual)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.rates.ftb_a_supplement_rate = st.number_input(
            "FTB Part A Supplement rate:", 
            value=st.session_state.rates.ftb_a_supplement_rate, 
            step=0.01
        )
        st.session_state.rates.ftb_b_supplement_rate = st.number_input(
            "FTB Part B Supplement rate:", 
            value=st.session_state.rates.ftb_b_supplement_rate, 
            step=0.01
        )
    
    with col2:
        st.session_state.rates.ftb_a_supplement_limit = st.number_input(
            "FTB Part A Supplement income limit:", 
            value=st.session_state.rates.ftb_a_supplement_limit, 
            step=1.0
        )
    
    # Display current rates in a table
    st.subheader("Current Rate Summary")
    
    rates_data = {
        "Component": [
            "Base rate - under 13",
            "Base rate - 13 and over",
            "Maximum rate - under 13",
            "Maximum rate - 13 and over",
            "FTB B - under 5",
            "FTB B - 5 and over",
            "Higher income threshold",
            "Base rate threshold",
            "FTB B threshold",
            "FTB A supplement",
            "FTB B supplement"
        ],
        "Rate/Amount ($)": [
            f"{st.session_state.rates.base_rate_under_13:.2f}",
            f"{st.session_state.rates.base_rate_13_over:.2f}",
            f"{st.session_state.rates.max_rate_under_13:.2f}",
            f"{st.session_state.rates.max_rate_13_over:.2f}",
            f"{st.session_state.rates.ftb_b_max_under_5:.2f}",
            f"{st.session_state.rates.ftb_b_max_5_over:.2f}",
            f"{st.session_state.rates.ftb_a_higher_threshold:.0f}",
            f"{st.session_state.rates.ftb_a_base_threshold:.0f}",
            f"{st.session_state.rates.ftb_b_threshold:.0f}",
            f"{st.session_state.rates.ftb_a_supplement_rate:.2f}",
            f"{st.session_state.rates.ftb_b_supplement_rate:.2f}"
        ],
        "Type": [
            "Fortnightly",
            "Fortnightly",
            "Fortnightly",
            "Fortnightly",
            "Fortnightly",
            "Fortnightly",
            "Annual",
            "Annual",
            "Annual",
            "Annual",
            "Annual"
        ]
    }
    
    df = pd.DataFrame(rates_data)
    st.dataframe(df, use_container_width=True)
    
    if st.button("Reset to Default Rates"):
        st.session_state.rates = FTBRates()
        st.success("Rates reset to default values!")
        st.experimental_rerun()

if __name__ == "__main__":
    main()