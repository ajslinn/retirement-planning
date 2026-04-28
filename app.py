class RetirementModel:
    def __init__(self, current_isa, current_sipp, annual_spend, growth_rate, inflation):
        self.isa = current_isa
        self.sipp = current_sipp
        self.annual_spend = annual_spend
        self.growth = growth_rate
        self.inflation = inflation

    def calculate_year(self):
        # Grow assets
        self.isa *= (1 + self.growth)
        self.sipp *= (1 + self.growth)
        
        # Withdraw strategy: ISA first
        if self.isa >= self.annual_spend:
            self.isa -= self.annual_spend
        else:
            remaining = self.annual_spend - self.isa
            self.isa = 0
            self.sipp -= remaining # Tax logic would be applied here
            
        # Adjust spend for next year
        self.annual_spend *= (1 + self.inflation)

import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="AJS Retirement Prototype", layout="wide")
st.title("🚀 AJS 2026 Retirement Calculator")
st.markdown("Automated wealth modeling including State Pension logic.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Current Financials")
current_age = st.sidebar.number_input("Current Age", value=55)
retirement_age = st.sidebar.number_input("Planned Retirement Age", value=60)
isa_bal = st.sidebar.number_input("Total ISA Balance (£)", value=100000)
sipp_bal = st.sidebar.number_input("Total SIPP Balance (£)", value=400000)

st.sidebar.header("State Pension")
state_pension_age = st.sidebar.slider("State Pension Age", 66, 68, 67)
# 2026/27 full rate is £12,548
state_pension_amt = st.sidebar.number_input("Annual State Pension (£)", value=12548)

st.sidebar.header("Assumptions")
annual_spend = st.sidebar.slider("Desired Annual Spend (£)", 20000, 100000, 35000)
growth_rate = st.sidebar.slider("Investment Growth (%)", 0.0, 10.0, 5.0) / 100
inflation_rate = st.sidebar.slider("Inflation (%)", 0.0, 5.0, 2.5) / 100

# --- CALCULATION ENGINE ---
# --- 2026/27 TAX CONSTANTS ---
PERSONAL_ALLOWANCE = 12570
BASIC_RATE_LIMIT = 50270  # (Allowance + 37,700)
BASIC_RATE = 0.20
HIGHER_RATE = 0.40

# --- UPDATED CALCULATION ENGINE ---
data = []
temp_isa = isa_bal
temp_sipp = sipp_bal
temp_spend = annual_spend
temp_state_pension = state_pension_amt

for age in range(current_age, 96):
    temp_isa *= (1 + growth_rate)
    temp_sipp *= (1 + growth_rate)
    
    state_pension_received = temp_state_pension if age >= state_pension_age else 0
    remaining_to_fund = temp_spend
    
    # 1. Use State Pension first (it's "income" that arrives automatically)
    remaining_to_fund = max(0, remaining_to_fund - state_pension_received)
    
    # 2. Use ISA next (Tax-Free Bridge - no tax calculation needed)
    draw_isa = min(temp_isa, remaining_to_fund)
    temp_isa -= draw_isa
    remaining_to_fund -= draw_isa
    
    # 3. Use SIPP for the final gap (Grossing up for Tax)
    draw_sipp = 0
    tax_paid = 0
    
    if remaining_to_fund > 0:
        # We need 'remaining_to_fund' as NET income.
        # We must calculate the GROSS withdrawal required to leave that NET amount.
        # This assumes State Pension has already used up some/all of the Personal Allowance.
        
        target_net = remaining_to_fund
        current_taxable_income = state_pension_received
        
        # Simple gross-up logic for Basic Rate (20%)
        # If total income stays below £50,270:
        if (current_taxable_income + (target_net / 0.8)) <= BASIC_RATE_LIMIT:
            # How much of the allowance is left?
            allowance_left = max(0, PERSONAL_ALLOWANCE - current_taxable_income)
            
            if target_net <= allowance_left:
                draw_sipp = target_net # No tax
            else:
                taxable_part_net = target_net - allowance_left
                gross_taxable_part = taxable_part_net / (1 - BASIC_RATE)
                draw_sipp = allowance_left + gross_taxable_part
                tax_paid = draw_sipp - target_net
        else:
            # If it hits Higher Rate, we'd need more complex math, 
            # but for this prototype, we'll cap at 20% or 40% estimation
            draw_sipp = target_net / (1 - BASIC_RATE) 
            tax_paid = draw_sipp - target_net

        temp_sipp -= draw_sipp

    # 4. Store Data
    data.append({
        "Age": age,
        "ISA": round(temp_isa),
        "SIPP": round(temp_sipp),
        "State Pension": round(state_pension_received),
        "Tax Paid": round(tax_paid),
        "Total Wealth": round(temp_isa + temp_sipp)
    })
    
    # Inflation adjustments
    temp_spend *= (1 + inflation_rate)
    temp_state_pension *= (1 + inflation_rate)



# --- VISUALIZATION ---
st.subheader("1. Wealth Projection (Total Capital)")
st.line_chart(df.set_index("Age")[["ISA", "SIPP", "Total Wealth"]])

st.subheader("2. Annual Income Sources (The 'Bridge' vs 'Pension')")
# We need to calculate how much was drawn from ISA and SIPP for this chart
# Let's add columns for better visualization
df['ISA Drawdown'] = df['ISA'].diff().fillna(0).abs()
df['SIPP Drawdown'] = df['SIPP'].diff().fillna(0).abs()

# This chart shows exactly where your spending money is coming from each year
st.bar_chart(df.set_index("Age")[["State Pension Rec'd", "ISA Drawdown", "SIPP Drawdown"]])
