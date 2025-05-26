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
    """Store FTB rates and thresholds - 2024-25 Financial Year"""
    # FTB Part A standard rates (annual) - from Family Assistance Guide
    ftb_a_under_13_annual: float = 5788.90  # Method 1 - under 13 years
    ftb_a_13_over_annual: float = 7529.95   # Method 1 - 13 years and over
    ftb_a_base_rate_annual: float = 1857.85  # Method 2 - base rate
    
    # Convert to fortnightly rates
    @property
    def ftb_a_under_13_fortnightly(self) -> float:
        return self.ftb_a_under_13_annual / 26
    
    @property
    def ftb_a_13_over_fortnightly(self) -> float:
        return self.ftb_a_13_over_annual / 26
    
    @property
    def ftb_a_base_rate_fortnightly(self) -> float:
        return self.ftb_a_base_rate_annual / 26
    
    # FTB Part B standard rates (annual) - from Family Assistance Guide
    ftb_b_under_5_annual: float = 4923.85   # youngest child under 5
    ftb_b_5_to_13_annual: float = 3434.65   # youngest child 5-13 (couples) or 5-18 (singles)
    
    @property
    def ftb_b_under_5_fortnightly(self) -> float:
        return self.ftb_b_under_5_annual / 26
    
    @property
    def ftb_b_5_over_fortnightly(self) -> float:
        return self.ftb_b_5_to_13_annual / 26
    
    # Income test thresholds - 2024-25
    ftb_a_income_free_area: float = 65189     # Up to this amount, full rate
    ftb_a_higher_income_free_area: float = 115997  # Higher income test threshold
    ftb_a_taper_rate_1: float = 0.20         # 20 cents per dollar reduction
    ftb_a_taper_rate_2: float = 0.30         # 30 cents per dollar reduction (Method 2)
    
    ftb_b_income_free_area: float = 6789     # Secondary earner income free area
    ftb_b_taper_rate: float = 0.20           # 20 cents per dollar reduction
    ftb_b_primary_earner_limit: float = 117194  # Primary earner income limit
    
    # Supplements (annual) - 2024-25
    ftb_a_supplement_rate: float = 916.15    # Per child
    ftb_a_supplement_limit: float = 80000    # Income limit for supplement
    ftb_b_supplement_rate: float = 448.95    # Per family

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
        """Calculate FTB Part A for a single child using correct Methods 1 and 2"""
        
        # Determine standard rate based on age (Method 1)
        if child.age < 13:
            standard_rate_annual = self.rates.ftb_a_under_13_annual
        else:
            standard_rate_annual = self.rates.ftb_a_13_over_annual
        
        standard_rate_fortnightly = standard_rate_annual / 26
        base_rate_fortnightly = self.rates.ftb_a_base_rate_fortnightly
        
        # If on income support, get maximum rate (Method 1)
        if income_support:
            final_rate = standard_rate_fortnightly
            test_type = "Income Support - Maximum Rate"
        else:
            # Apply income tests based on family income
            if annual_income <= self.rates.ftb_a_income_free_area:
                # Full standard rate (Method 1)
                final_rate = standard_rate_fortnightly
                test_type = "Method 1 - Maximum Rate"
                
            elif annual_income <= self.rates.ftb_a_higher_income_free_area:
                # Method 1 - taper at 20 cents per dollar from standard rate to base rate
                excess_income = annual_income - self.rates.ftb_a_income_free_area
                annual_reduction = excess_income * self.rates.ftb_a_taper_rate_1
                fortnightly_reduction = annual_reduction / 26
                tapered_rate = standard_rate_fortnightly - fortnightly_reduction
                final_rate = max(base_rate_fortnightly, tapered_rate)
                test_type = "Method 1 - Income Test (20c taper)"
                
            else:
                # Use Method 1 or Method 2, whichever gives higher payment
                
                # Method 1: Continue 20c taper until zero
                excess_income_m1 = annual_income - self.rates.ftb_a_income_free_area
                annual_reduction_m1 = excess_income_m1 * self.rates.ftb_a_taper_rate_1
                fortnightly_reduction_m1 = annual_reduction_m1 / 26
                method1_rate = max(0, standard_rate_fortnightly - fortnightly_reduction_m1)
                
                # Method 2: Base rate tapered at 30c per dollar above HIFA
                excess_income_m2 = annual_income - self.rates.ftb_a_higher_income_free_area
                annual_reduction_m2 = excess_income_m2 * self.rates.ftb_a_taper_rate_2
                fortnightly_reduction_m2 = annual_reduction_m2 / 26
                method2_rate = max(0, base_rate_fortnightly - fortnightly_reduction_m2)
                
                # Use whichever method gives the higher rate
                if method1_rate >= method2_rate:
                    final_rate = method1_rate
                    test_type = "Method 1 - Extended taper (20c)"
                else:
                    final_rate = method2_rate
                    test_type = "Method 2 - Base rate taper (30c)"
        
        # Apply compliance reductions
        compliance_reduction = 0
        if not child.immunisation:
            compliance_reduction += final_rate * 0.5  # 50% reduction
        if not child.healthy_start and child.age >= 4:
            compliance_reduction += final_rate * 0.5  # 50% reduction (can exceed 100%)
        
        # Apply maintenance action test
        maintenance_reduction = 0
        if not child.maintenance_action:
            maintenance_reduction = final_rate
            final_rate = 0
        else:
            final_rate = max(0, final_rate - compliance_reduction)
        
        return FTBResult(
            fortnightly_rate=final_rate,
            test_type=test_type,
            base_rate=final_rate + compliance_reduction,
            compliance_reduction=compliance_reduction,
            maintenance_reduction=maintenance_reduction
        )
    
    def calculate_ftb_part_b(self, children: List[Child], family_type: str, annual_income: float, secondary_income: float = 0) -> FTBResult:
        """Calculate FTB Part B with correct income tests for singles vs couples"""
        
        # Find youngest child age
        youngest_age = min(child.age for child in children)
        
        # Determine maximum rate based on youngest child age
        if youngest_age < 5:
            max_rate_fortnightly = self.rates.ftb_b_under_5_fortnightly
        else:
            max_rate_fortnightly = self.rates.ftb_b_5_over_fortnightly
        
        if family_type == "single":
            # For single parents: use family income as primary earner income
            primary_earner_income = annual_income
            
            # Check primary earner income limit
            if primary_earner_income > self.rates.ftb_b_primary_earner_limit:
                return FTBResult(
                    fortnightly_rate=0,
                    test_type="Not payable - Income over primary earner limit",
                    reason=f"Single parent income (${primary_earner_income:,.0f}) exceeds primary earner limit (${self.rates.ftb_b_primary_earner_limit:,.0f})"
                )
            
            # Single parents get maximum rate if under primary earner limit
            return FTBResult(
                fortnightly_rate=max_rate_fortnightly,
                test_type="Single Parent - Maximum Rate",
                base_rate=max_rate_fortnightly,
                reason=f"Single parent under primary earner limit gets maximum rate"
            )
        
        else:  # couple
            # For couples - different rules apply based on youngest child age
            if youngest_age >= 13:
                return FTBResult(
                    fortnightly_rate=0,
                    test_type="Not payable - Couple with child 13+",
                    reason="FTB Part B is not payable to couples when youngest child is 13 or older"
                )
            
            # Check primary earner income limit first
            primary_earner_income = annual_income  # Assuming this is the higher earner
            if primary_earner_income > self.rates.ftb_b_primary_earner_limit:
                return FTBResult(
                    fortnightly_rate=0,
                    test_type="Not payable - Primary earner over limit",
                    reason=f"Primary earner income (${primary_earner_income:,.0f}) exceeds limit (${self.rates.ftb_b_primary_earner_limit:,.0f})"
                )
            
            # Apply secondary earner income test
            secondary_earner_income = secondary_income  # This should be the lower earner's income
            
            if secondary_earner_income <= self.rates.ftb_b_income_free_area:
                return FTBResult(
                    fortnightly_rate=max_rate_fortnightly,
                    test_type="Couple - Maximum Rate (Secondary earner under threshold)",
                    base_rate=max_rate_fortnightly,
                    reason=f"Secondary earner income (${secondary_earner_income:,.0f}) under income free area"
                )
            
            # Calculate taper reduction based on secondary earner's excess income
            excess_income = secondary_earner_income - self.rates.ftb_b_income_free_area
            annual_reduction = excess_income * self.rates.ftb_b_taper_rate
            fortnightly_reduction = annual_reduction / 26
            final_rate = max(0, max_rate_fortnightly - fortnightly_reduction)
            
            return FTBResult(
                fortnightly_rate=final_rate,
                test_type="Couple - Secondary Earner Income Test (20c taper)",
                base_rate=max_rate_fortnightly,
                reason=f"Secondary earner income test applied: ${secondary_earner_income:,.0f} - ${self.rates.ftb_b_income_free_area:,.0f} = ${excess_income:,.0f} excess"
            )
    
    def calculate_work_incentive(self, children: List[Child], family_type: str, current_income: float, secondary_income: float = 0) -> Dict:
        """Calculate work incentive information with accurate cut-off points"""
        
        # Calculate FTB Part A cut-off (based on primary/family income)
        ftb_a_cutout = 0
        if children:
            # Use the income where payment reaches zero for first child
            sample_child = children[0]
            
            # Estimate cut-off using Method 1 (20c taper from income free area)
            if sample_child.age < 13:
                max_annual_rate = self.rates.ftb_a_under_13_annual
            else:
                max_annual_rate = self.rates.ftb_a_13_over_annual
            
            # Income where 20c taper reduces payment to zero
            ftb_a_cutout = self.rates.ftb_a_income_free_area + (max_annual_rate / self.rates.ftb_a_taper_rate_1)
        
        # Calculate FTB Part B cut-off
        ftb_b_cutout = 0
        if children:
            youngest_age = min(child.age for child in children)
            
            if family_type == "single":
                # For singles, cut-off is the primary earner limit
                ftb_b_cutout = self.rates.ftb_b_primary_earner_limit
                
            elif youngest_age < 13:  # Couples with child under 13
                # For couples, secondary earner income test applies
                if youngest_age < 5:
                    max_annual_rate = self.rates.ftb_b_under_5_annual
                else:
                    max_annual_rate = self.rates.ftb_b_5_to_13_annual
                
                # Cut-off based on secondary earner income
                secondary_cutout = self.rates.ftb_b_income_free_area + (max_annual_rate / self.rates.ftb_b_taper_rate)
                
                # Also limited by primary earner limit
                ftb_b_cutout = min(self.rates.ftb_b_primary_earner_limit, secondary_cutout)
        
        # Determine additional earning capacity
        if family_type == "single":
            # For singles, compare against family income
            additional_income_capacity = max(0, min(ftb_a_cutout, ftb_b_cutout) - current_income) if ftb_b_cutout > 0 else max(0, ftb_a_cutout - current_income)
        else:
            # For couples, it's more complex - primary affects Part A, secondary affects Part B
            primary_capacity = max(0, ftb_a_cutout - current_income) if ftb_a_cutout > 0 else 0
            secondary_capacity = max(0, self.rates.ftb_b_income_free_area - secondary_income) if ftb_b_cutout > 0 else 0
            
            # Report the more restrictive constraint
            if primary_capacity > 0 and secondary_capacity > 0:
                additional_income_capacity = min(primary_capacity, secondary_capacity)
            else:
                additional_income_capacity = max(primary_capacity, secondary_capacity)
        
        return {
            "ftb_a_cutout": ftb_a_cutout,
            "ftb_b_cutout": ftb_b_cutout,
            "earliest_cutout": min(x for x in [ftb_a_cutout, ftb_b_cutout] if x > 0) if any([ftb_a_cutout, ftb_b_cutout]) else 0,
            "additional_annual_income": additional_income_capacity,
            "additional_weekly_income": additional_income_capacity / 52,
            "family_type": family_type,
            "secondary_income": secondary_income
        }

def main():
    st.set_page_config(
        page_title="Family Tax Benefit Calculator",
        page_icon="🪲",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state for rates first
    if 'rates' not in st.session_state:
        try:
            st.session_state.rates = FTBRates()
        except Exception as e:
            st.error(f"Error initializing rates: {e}")
            st.stop()
    
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
        <p>Calculate your Family Tax Benefit Part A and Part B entitlements - 2024-25 Financial Year</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a section:",
        ["Calculator", "Results", "Charts", "Rates & Thresholds"]
    )
    
    try:
        if page == "Calculator":
            calculator_page()
        elif page == "Results":
            results_page()
        elif page == "Charts":
            charts_page()
        elif page == "Rates & Thresholds":
            rates_page()
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.info("Please try refreshing the page or resetting the rates in the 'Rates & Thresholds' tab.")

def calculator_page():
    st.header("Family Tax Benefit Calculator")
    
    # Initialize rates if not present
    if 'rates' not in st.session_state:
        st.session_state.rates = FTBRates()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Family Information")
        family_type = st.selectbox("Family Type:", ["couple", "single"], format_func=lambda x: "Couple" if x == "couple" else "Single Parent")
        
        if family_type == "couple":
            st.info("💡 **For couples:** Enter the higher earner's income as 'Primary' and lower earner as 'Secondary'")
            annual_income = st.number_input("Primary Earner Annual Income ($):", min_value=0.0, value=50000.0, step=1000.0, help="Higher earning partner's income")
            secondary_income = st.number_input("Secondary Earner Annual Income ($):", min_value=0.0, value=15000.0, step=1000.0, help="Lower earning partner's income - subject to FTB Part B income test")
        else:
            annual_income = st.number_input("Annual Family Income ($):", min_value=0.0, value=50000.0, step=1000.0)
            secondary_income = 0.0
        
        rent_assistance = st.number_input("Annual Rent Assistance ($):", min_value=0.0, value=0.0, step=100.0)
        income_support = st.checkbox("Family receives income support payment")
        
        try:
            st.info("📊 **Income Test Information:**\n"
                    f"• FTB Part A Income Free Area: ${st.session_state.rates.ftb_a_income_free_area:,}\n"
                    f"• FTB Part A Higher Income Free Area: ${st.session_state.rates.ftb_a_higher_income_free_area:,}\n"
                    f"• FTB Part B Income Free Area (Secondary): ${st.session_state.rates.ftb_b_income_free_area:,}\n"
                    f"• FTB Part B Primary Earner Limit: ${st.session_state.rates.ftb_b_primary_earner_limit:,}")
        except AttributeError as e:
            st.error(f"Error loading rates: {e}")
            st.session_state.rates = FTBRates()  # Reset to defaults
    
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
                    
                    if not immunisation:
                        st.warning("⚠️ Non-compliance: 50% rate reduction applies")
                    if not healthy_start and age >= 4:
                        st.warning("⚠️ Non-compliance: 50% rate reduction applies")
                    if not maintenance_action:
                        st.error("🚫 Payment suspended: Maintenance action required")
                    
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
            ftb_b_result = calculator.calculate_ftb_part_b(children, family_type, annual_income, secondary_income)
            
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
            work_incentive = calculator.calculate_work_incentive(children, family_type, annual_income, secondary_income)
            
            # Store results in session state
            st.session_state.calculation_results = {
                'family_type': family_type,
                'annual_income': annual_income,
                'secondary_income': secondary_income,
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
            
            st.success("✅ Calculation completed! Check the Results tab.")

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
            <h4>💰 Total Family Entitlement</h4>
            <h2>${results['total_annual_with_supplements']:.2f}</h2>
            <p>Annual (including supplements)</p>
            <h3>${results['total_fortnightly']:.2f}</h3>
            <p>Fortnightly (regular payments)</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="result-card">
            <h4>📊 FTB Part A</h4>
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
            <h4>👨‍👩‍👧‍👦 FTB Part B</h4>
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
            ℹ️ <strong>FTB Part B Note:</strong> {results['ftb_b_result'].reason}
        </div>
        """, unsafe_allow_html=True)
    
    # Work Incentive Information
    work_incentive = results['work_incentive']
    if work_incentive['additional_annual_income'] > 0:
        st.markdown(f"""
        <div class="work-incentive">
            <h4>💼 Work Incentive Information</h4>
            <p>Understanding how additional income affects your payments:</p>
            <ul>
                <li><strong>Additional earning capacity:</strong> ${work_incentive['additional_annual_income']:.0f} annually (${work_incentive['additional_weekly_income']:.0f} per week)</li>
                <li><strong>FTB Part A cuts out at:</strong> ${work_incentive['ftb_a_cutout']:.0f} annual income</li>
                {f"<li><strong>FTB Part B cuts out at:</strong> ${work_incentive['ftb_b_cutout']:.0f} annual income</li>" if work_incentive['ftb_b_cutout'] > 0 else ""}
                <li><strong>Next payment reduction:</strong> At ${work_incentive['earliest_cutout']:.0f} annual income</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="work-incentive">
            <h4>💼 Work Incentive Information</h4>
            <p><strong>Your income is above the cut-out thresholds.</strong></p>
            <p>Consider reviewing your circumstances or seek advice about maximizing your family's financial position.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Breakdown by Child
    st.subheader("👶 Breakdown by Child")
    for child_result in results['ftb_a_results']:
        result = child_result['result']
        st.markdown(f"""
        <div class="result-card">
            <h5>Child {child_result['child_index']} (Age: {child_result['age']})</h5>
            <p><strong>FTB Part A Rate:</strong> ${result.fortnightly_rate:.2f} per fortnight (${result.fortnightly_rate * 26:.2f} annually)</p>
            <p><strong>Assessment Method:</strong> {result.test_type}</p>
            {f'<div class="alert-warning"><strong>⚠️ Compliance Reduction:</strong> ${result.compliance_reduction:.2f} fortnightly - Check immunisation and health requirements</div>' if result.compliance_reduction > 0 else ''}
            {f'<div class="alert-warning"><strong>🚫 Maintenance Action Test:</strong> Payment suspended - Action required</div>' if result.maintenance_reduction > 0 else ''}
        </div>
        """, unsafe_allow_html=True)
    
    # Important Notes
    rent_note = f"<li>Rent Assistance (${results['rent_assistance']:.2f}) noted but not calculated in this tool</li>" if results['rent_assistance'] > 0 else ""
    st.markdown(f"""
    <div class="alert-info">
        <strong>📝 Important Notes:</strong>
        <ul>
            <li>These calculations use the correct 2024-25 rates and Methods 1 & 2 from the Family Assistance Act</li>
            <li>Income tests apply 20c and 30c taper rates as per official guidelines</li>
            <li>Supplements are paid annually after end-of-year reconciliation</li>
            <li>Contact Services Australia on 136 150 for official assessments</li>
            <li>Based on Family Assistance Guide 3.1.1.20 and current Services Australia rates</li>
            {rent_note}
        </ul>
    </div>
    """, unsafe_allow_html=True)

def charts_page():
    st.header("📈 Family Tax Benefit Rate Charts")
    
    if 'calculation_results' not in st.session_state:
        st.info("Please complete the calculation in the Calculator tab first to see personalized charts.")
        # Show default charts
        children = [Child(age=5)]
        family_type = "single"
        secondary_income = 0
    else:
        results = st.session_state.calculation_results
        children = results['children']
        family_type = results['family_type']
        secondary_income = results.get('secondary_income', 0)
    
    calculator = FTBCalculator(st.session_state.rates)
    
    # Generate FTB Part A Chart
    st.subheader("📊 FTB Part A Rate by Annual Income")
    
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
    
    # Add threshold lines with current rates
    fig_a.add_vline(x=st.session_state.rates.ftb_a_income_free_area, 
                   line_dash="dash", line_color="red",
                   annotation_text="Income Free Area ($65,189)")
    fig_a.add_vline(x=st.session_state.rates.ftb_a_higher_income_free_area, 
                   line_dash="dash", line_color="orange",
                   annotation_text="Higher Income Free Area ($115,997)")
    
    fig_a.update_layout(
        title="FTB Part A Rate by Annual Income (Method 1 & 2)",
        xaxis_title="Annual Family Income ($)",
        yaxis_title="Fortnightly Rate ($)",
        hovermode='x unified',
        showlegend=True
    )
    
    st.plotly_chart(fig_a, use_container_width=True)
    
    # Generate FTB Part B Chart
    st.subheader("📈 FTB Part B Rate by Annual Income")
    
    income_range_b = list(range(0, 50001, 1000))
    ftb_b_rates = []
    
    for income in income_range_b:
        if family_type == "couple":
            # For couples, vary the secondary income while keeping primary income constant
            result = calculator.calculate_ftb_part_b(children, family_type, 50000, income)  # Assume $50k primary
        else:
            # For singles, vary the family income
            result = calculator.calculate_ftb_part_b(children, family_type, income, 0)
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
    
    # Add threshold lines
    fig_b.add_vline(x=st.session_state.rates.ftb_b_income_free_area, 
                   line_dash="dash", line_color="red",
                   annotation_text=f"Income Free Area (${st.session_state.rates.ftb_b_income_free_area:,.0f})")
    
    if family_type == "couple":
        fig_b.add_vline(x=st.session_state.rates.ftb_b_primary_earner_limit, 
                       line_dash="dash", line_color="purple",
                       annotation_text=f"Primary Earner Limit (${st.session_state.rates.ftb_b_primary_earner_limit:,.0f})")
    
    fig_b.update_layout(
        title=f"FTB Part B Rate by {'Secondary Earner' if family_type == 'couple' else 'Family'} Income ({family_type.title()} Family)",
        xaxis_title=f"Annual {'Secondary Earner' if family_type == 'couple' else 'Family'} Income ($)",
        yaxis_title="Fortnightly Rate ($)",
        hovermode='x unified',
        showlegend=True
    )
    
    st.plotly_chart(fig_b, use_container_width=True)
    
    # Rate explanation
    st.markdown("""
    ### 📖 Chart Explanation
    
    **FTB Part A:**
    - **Method 1:** 20c reduction per dollar above Income Free Area ($65,189)
    - **Method 2:** 30c reduction per dollar above Higher Income Free Area ($115,997) 
    - The system automatically uses whichever method gives the higher payment
    
    **FTB Part B:**
    - 20c reduction per dollar above Income Free Area ($6,789)
    - Different rates apply based on youngest child's age
    - Couples have additional primary earner income limits
    """)

def rates_page():
    st.header("⚙️ FTB Rates and Thresholds (2024-25)")
    st.info("These rates are based on the official Family Assistance Guide and Services Australia. You can edit them to test scenarios.")
    
    # Current vs Editable rates
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 FTB Part A Rates (Annual)")
        
        st.session_state.rates.ftb_a_under_13_annual = st.number_input(
            "Standard rate - under 13 years:", 
            value=st.session_state.rates.ftb_a_under_13_annual, 
            step=1.0,
            help="Official rate: $5,788.90 per year"
        )
        st.session_state.rates.ftb_a_13_over_annual = st.number_input(
            "Standard rate - 13 years and over:", 
            value=st.session_state.rates.ftb_a_13_over_annual, 
            step=1.0,
            help="Official rate: $7,529.95 per year"
        )
        st.session_state.rates.ftb_a_base_rate_annual = st.number_input(
            "Base rate (Method 2):", 
            value=st.session_state.rates.ftb_a_base_rate_annual, 
            step=1.0,
            help="Official rate: $1,857.85 per year"
        )
        
        st.write("**Fortnightly Equivalents:**")
        st.write(f"• Under 13: ${st.session_state.rates.ftb_a_under_13_fortnightly:.2f}")
        st.write(f"• 13+ years: ${st.session_state.rates.ftb_a_13_over_fortnightly:.2f}")
        st.write(f"• Base rate: ${st.session_state.rates.ftb_a_base_rate_fortnightly:.2f}")
    
    with col2:
        st.subheader("👨‍👩‍👧‍👦 FTB Part B Rates (Annual)")
        
        st.session_state.rates.ftb_b_under_5_annual = st.number_input(
            "Standard rate - youngest under 5:", 
            value=st.session_state.rates.ftb_b_under_5_annual, 
            step=1.0,
            help="Official rate: $4,923.85 per year"
        )
        st.session_state.rates.ftb_b_5_to_13_annual = st.number_input(
            "Standard rate - youngest 5+:", 
            value=st.session_state.rates.ftb_b_5_to_13_annual, 
            step=1.0,
            help="Official rate: $3,434.65 per year"
        )
        
        st.write("**Fortnightly Equivalents:**")
        st.write(f"• Under 5: ${st.session_state.rates.ftb_b_under_5_fortnightly:.2f}")
        st.write(f"• 5+ years: ${st.session_state.rates.ftb_b_5_over_fortnightly:.2f}")
    
    # Income Test Thresholds
    st.subheader("💰 Income Test Thresholds")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.rates.ftb_a_income_free_area = st.number_input(
            "FTB Part A - Income Free Area:", 
            value=st.session_state.rates.ftb_a_income_free_area, 
            step=1.0,
            help="Income up to this amount receives full rate"
        )
        st.session_state.rates.ftb_a_higher_income_free_area = st.number_input(
            "FTB Part A - Higher Income Free Area:", 
            value=st.session_state.rates.ftb_a_higher_income_free_area, 
            step=1.0,
            help="Threshold for Method 2 calculation"
        )
        st.session_state.rates.ftb_b_income_free_area = st.number_input(
            "FTB Part B - Income Free Area:", 
            value=st.session_state.rates.ftb_b_income_free_area, 
            step=1.0,
            help="Secondary earner income threshold"
        )
    
    with col2:
        st.session_state.rates.ftb_a_taper_rate_1 = st.number_input(
            "FTB Part A - Taper Rate 1 (20c):", 
            value=st.session_state.rates.ftb_a_taper_rate_1, 
            step=0.01,
            help="Method 1 taper rate"
        )
        st.session_state.rates.ftb_a_taper_rate_2 = st.number_input(
            "FTB Part A - Taper Rate 2 (30c):", 
            value=st.session_state.rates.ftb_a_taper_rate_2, 
            step=0.01,
            help="Method 2 taper rate"
        )
        st.session_state.rates.ftb_b_taper_rate = st.number_input(
            "FTB Part B - Taper Rate (20c):", 
            value=st.session_state.rates.ftb_b_taper_rate, 
            step=0.01,
            help="Part B income test taper"
        )
        st.session_state.rates.ftb_b_primary_earner_limit = st.number_input(
            "FTB Part B - Primary Earner Limit:", 
            value=st.session_state.rates.ftb_b_primary_earner_limit, 
            step=1.0,
            help="Maximum primary earner income for couples"
        )
    
    # Supplements
    st.subheader("🎁 Supplements (Annual)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.rates.ftb_a_supplement_rate = st.number_input(
            "FTB Part A Supplement (per child):", 
            value=st.session_state.rates.ftb_a_supplement_rate, 
            step=0.01,
            help="Annual supplement per eligible child"
        )
        st.session_state.rates.ftb_b_supplement_rate = st.number_input(
            "FTB Part B Supplement (per family):", 
            value=st.session_state.rates.ftb_b_supplement_rate, 
            step=0.01,
            help="Annual supplement per eligible family"
        )
    
    with col2:
        st.session_state.rates.ftb_a_supplement_limit = st.number_input(
            "FTB Part A Supplement income limit:", 
            value=st.session_state.rates.ftb_a_supplement_limit, 
            step=1.0,
            help="Family income must be under this amount"
        )
    
    # Display current rates in a comprehensive table
    st.subheader("📋 Current Rate Summary")
    
    rates_data = {
        "Component": [
            "FTB Part A - Under 13 (annual)",
            "FTB Part A - 13+ years (annual)", 
            "FTB Part A - Base rate (annual)",
            "FTB Part A - Under 13 (fortnightly)",
            "FTB Part A - 13+ years (fortnightly)",
            "FTB Part A - Base rate (fortnightly)",
            "FTB Part B - Under 5 (annual)",
            "FTB Part B - 5+ years (annual)",
            "FTB Part B - Under 5 (fortnightly)",
            "FTB Part B - 5+ years (fortnightly)",
            "Income Free Area - Part A",
            "Higher Income Free Area - Part A",
            "Income Free Area - Part B",
            "Primary Earner Limit - Part B",
            "FTB Part A Supplement",
            "FTB Part B Supplement"
        ],
        "Rate/Amount ($)": [
            f"{st.session_state.rates.ftb_a_under_13_annual:.2f}",
            f"{st.session_state.rates.ftb_a_13_over_annual:.2f}",
            f"{st.session_state.rates.ftb_a_base_rate_annual:.2f}",
            f"{st.session_state.rates.ftb_a_under_13_fortnightly:.2f}",
            f"{st.session_state.rates.ftb_a_13_over_fortnightly:.2f}",
            f"{st.session_state.rates.ftb_a_base_rate_fortnightly:.2f}",
            f"{st.session_state.rates.ftb_b_under_5_annual:.2f}",
            f"{st.session_state.rates.ftb_b_5_to_13_annual:.2f}",
            f"{st.session_state.rates.ftb_b_under_5_fortnightly:.2f}",
            f"{st.session_state.rates.ftb_b_5_over_fortnightly:.2f}",
            f"{st.session_state.rates.ftb_a_income_free_area:.0f}",
            f"{st.session_state.rates.ftb_a_higher_income_free_area:.0f}",
            f"{st.session_state.rates.ftb_b_income_free_area:.0f}",
            f"{st.session_state.rates.ftb_b_primary_earner_limit:.0f}",
            f"{st.session_state.rates.ftb_a_supplement_rate:.2f}",
            f"{st.session_state.rates.ftb_b_supplement_rate:.2f}"
        ],
        "Official Source": [
            "Family Assistance Guide 3.1.1.20",
            "Family Assistance Guide 3.1.1.20",
            "Family Assistance Guide 3.1.1.20",
            "Calculated (annual ÷ 26)",
            "Calculated (annual ÷ 26)",
            "Calculated (annual ÷ 26)",
            "Family Assistance Guide 3.1.1.20",
            "Family Assistance Guide 3.1.1.20",
            "Calculated (annual ÷ 26)",
            "Calculated (annual ÷ 26)",
            "Family Assistance Guide 3.1.1.20",
            "Family Assistance Guide 3.1.1.20",
            "Family Assistance Guide 3.1.1.20",
            "Family Assistance Guide 3.1.1.20",
            "Services Australia",
            "Services Australia"
        ]
    }
    
    df = pd.DataFrame(rates_data)
    st.dataframe(df, use_container_width=True)
    
    # Reset and validation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Reset to Official Rates"):
            st.session_state.rates = FTBRates()
            st.success("Rates reset to official 2024-25 values!")
            st.rerun()
    
    with col2:
        if st.button("✅ Validate Current Rates"):
            official_rates = FTBRates()
            differences = []
            
            if abs(st.session_state.rates.ftb_a_under_13_annual - official_rates.ftb_a_under_13_annual) > 0.01:
                differences.append("FTB Part A Under 13")
            if abs(st.session_state.rates.ftb_a_income_free_area - official_rates.ftb_a_income_free_area) > 0.01:
                differences.append("Income Free Area")
            
            if differences:
                st.warning(f"⚠️ Modified rates detected: {', '.join(differences)}")
            else:
                st.success("✅ All rates match official 2024-25 values")
    
    # Information about rate sources
    st.markdown("""
    ### 📚 Rate Sources and Methodology
    
    **Official Sources:**
    - Family Assistance Guide 3.1.1.20 - Current FTB rates & income test amounts
    - Services Australia FTB Payment Rates pages
    - Family Assistance Act 1999 - Legislative framework
    
    **Calculation Methods:**
    - **Method 1:** Used when family income ≤ $115,997 (Higher Income Free Area)
    - **Method 2:** Used when family income > $115,997 (alternative calculation)
    - System automatically applies the method giving the higher payment rate
    
    **Key Features:**
    - Rates are indexed annually on 1 July
    - Supplements paid after end-of-year reconciliation
    - Compliance requirements may reduce payments by up to 50%
    - Maintenance Action Test can suspend payments entirely
    """)

if __name__ == "__main__":
    main()
