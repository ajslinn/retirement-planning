import streamlit as st
import pandas as pd

# --- 1. APP CONFIGURATION ---
st.set_page_config(page_title="AJS Retirement Prototype", layout="wide")
st.title("🚀 AJS 2026 Retirement Calculator")
st.markdown("Automated wealth and tax modeling based on 2026/27 UK tax references.")

# --- 2. SIDEBAR INPUTS ---
st.sidebar.header("Current Financials")
current_age = st.sidebar.number_input("Current Age", value=55)
retirement_age = st.sidebar.number_input("Planned Retirement Age", value=60)
isa_bal = st.sidebar.number_input("Total ISA Balance (£)", value=100000)
sipp_bal = st.sidebar.number_input("Total SIPP Balance (£)", value=400000)

st.sidebar.header("State Pension")
state_pension_age = st.sidebar.slider("State Pension Age", 66, 68, 67)
# 2026/27 forecast is £241.30/week (~£12,548/year)
state_pension_amt = st.sidebar.number_input("Annual State Pension (£)", value=12548)

st.sidebar.header("Assumptions")
annual_spend = st.sidebar.slider("Target Annual Spend (£)", 20000, 100000, 35000)
growth_rate = st.sidebar.slider("Investment Growth (%)", 0.0, 10.0, 5.0) / 100
inflation_rate = st.sidebar.slider("Inflation (%)", 0.0, 5.0, 2.5) / 100

# --- 3. TAX CONSTANTS (2026/27) ---
PERSONAL_ALLOWANCE = 12570
BASIC_RATE = 0.20

# --- 4. CALCULATION ENGINE ---
data = []
temp_isa = isa_bal
temp_sipp = sipp_bal
temp_spend = annual_spend
temp_state_pension = state_pension_amt

for age in range(current_age, 100):
    # Grow Assets
    temp_isa *= (1 + growth_rate)
    temp_sipp *= (1 + growth_rate)
    
    state_pension_received = temp_state_pension if age >= state_pension_age else 0
    net_needed = temp_spend
    
    # Logic: State Pension hits the bank account first
    net_needed = max(0, net_needed - state_pension_received)
    
    # Logic: ISA fills the gap next (Tax-Free)
    draw_isa = min(temp_isa, net_needed)
    temp_isa -= draw_isa
    net_needed -= draw_isa
    
    # Logic: SIPP fills remaining gap (Taxable)
    draw_sipp = 0
    tax_paid = 0
    
    if net_needed > 0:
        # We need to withdraw enough to cover the tax bill
        # State Pension usually eats up the Personal Allowance first
        taxable_income_so_far = state_pension_received
        
        # How much tax-free allowance is left?
        allowance_left = max(0, PERSONAL_ALLOWANCE - taxable_income_so_far)
        
        if net_needed <= allowance_left:
            draw_sipp = net_needed
        else:
            taxable_portion_net = net_needed - allowance_left
            # Gross up for 20% basic rate tax
            gross_taxable = taxable_portion_net / (1 - BASIC_RATE)
            draw_sipp = allowance_left + gross_taxable
            tax_paid = draw_sipp - net_needed
            
        temp_sipp -= draw_sipp

    # Append results
    data.append({
        "Age": age,
        "ISA": round(temp_isa),
        "SIPP": round(temp_sipp),
        "State Pension": round(state_pension_received),
        "Tax Paid": round(tax_paid),
        "Net Spend": round(temp_spend),
        "Total Wealth": round(temp_isa + temp_sipp)
    })
    
    # Adjust for inflation for next loop
    temp_spend *= (1 + inflation_rate)
    temp_state_pension *= (1 + inflation_rate)

# --- 5. VISUALIZATIONS ---
df = pd.DataFrame(data)

st.subheader("1. Wealth Projection (Total Capital)")
st.line_chart(df.set_index("Age")[["ISA", "SIPP", "Total Wealth"]])

st.subheader("2. Annual Income Flow (Including Tax Hit)")
# Show the components of your spending money + the tax paid to HMRC
st.bar_chart(df.set_index("Age")[["State Pension", "Tax Paid"]])

st.subheader("3. Data Breakdown")
st.dataframe(df, use_container_width=True)
