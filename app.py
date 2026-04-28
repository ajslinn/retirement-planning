import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 1. CONFIG & INPUTS ---
st.set_page_config(page_title="AJS Retirement Prototype", layout="wide")
st.sidebar.header("Inputs")
current_age = st.sidebar.number_input("Current Age", value=55)
retirement_age = st.sidebar.number_input("Retirement Age", value=60)
isa_bal = st.sidebar.number_input("ISA Balance (£)", value=100000)
sipp_bal = st.sidebar.number_input("SIPP Balance (£)", value=400000)

st.sidebar.header("State Pension")
state_pension_age = st.sidebar.slider("State Pension Age", 66, 68, 67)
state_pension_amt = st.sidebar.number_input("Annual State Pension (£)", value=12548)

st.sidebar.header("Lump Sum Strategy")
lump_sum_age = st.sidebar.slider("Age to take 25% Tax-Free Cash", 55, 75, 60)
take_lump_sum = st.sidebar.checkbox("Apply 25% Tax-Free Lump Sum?", value=True)

st.sidebar.header("Assumptions")
annual_spend = st.sidebar.slider("Target Annual Spend (Net) (£)", 20000, 100000, 35000)
growth_rate = st.sidebar.slider("Growth (%)", 0.0, 10.0, 5.0) / 100
inflation_rate = st.sidebar.slider("Inflation (%)", 0.0, 5.0, 2.5) / 100

PERSONAL_ALLOWANCE = 12570
BASIC_RATE = 0.20
LSA_LIMIT = 268275 # Lifetime Lump Sum Allowance

# --- 2. THE CALCULATION LOOP ---
data = []
temp_isa, temp_sipp = isa_bal, sipp_bal
temp_spend, temp_sp = annual_spend, state_pension_amt
lsa_used = 0

for age in range(current_age, 101):
    # Growth
    temp_isa *= (1 + growth_rate)
    temp_sipp *= (1 + growth_rate)
    
    # Apply Lump Sum
    if take_lump_sum and age == lump_sum_age:
        lump_sum_amt = min(temp_sipp * 0.25, LSA_LIMIT - lsa_used)
        temp_sipp -= lump_sum_amt
        temp_isa += lump_sum_amt # Move it to the tax-free pot
        lsa_used += lump_sum_amt

    sp_rec = temp_sp if age >= state_pension_age else 0
    target_net = temp_spend if age >= retirement_age else 0
    
    # 1. State Pension 
    net_after_sp = max(0, target_net - sp_rec)
    
    # 2. ISA fills the gap (Now potentially boosted by Lump Sum)
    draw_isa = min(temp_isa, net_after_sp)
    temp_isa -= draw_isa
    net_after_isa = max(0, net_after_sp - draw_isa)
    
    # 3. SIPP fills the remaining gap (Taxable)
    draw_sipp_gross = 0
    tax_paid = 0
    
    if net_after_isa > 0:
        allowance_left = max(0, PERSONAL_ALLOWANCE - sp_rec)
        if net_after_isa <= allowance_left:
            draw_sipp_gross = net_after_isa
        else:
            taxable_net_needed = net_after_isa - allowance_left
            gross_taxable = taxable_net_needed / (1 - BASIC_RATE)
            draw_sipp_gross = allowance_left + gross_taxable
            tax_paid = draw_sipp_gross - net_after_isa
            
        draw_sipp_gross = min(temp_sipp, draw_sipp_gross)
        temp_sipp -= draw_sipp_gross

    data.append({
        "Age": age, "ISA": round(temp_isa), "SIPP": round(temp_sipp),
        "ISA Draw": round(draw_isa), "SIPP Draw (Net)": round(draw_sipp_gross - tax_paid),
        "State Pension": round(sp_rec), "Tax Paid": round(tax_paid),
        "Total Wealth": round(temp_isa + temp_sipp)
    })
    
    temp_spend *= (1 + inflation_rate)
    temp_sp *= (1 + inflation_rate)

df = pd.DataFrame(data)

# --- 3. THE PLOTLY CHART ---
st.subheader("Annual Income Stack vs Target Spend")
fig = go.Figure()
fig.add_trace(go.Bar(x=df['Age'], y=df['State Pension'], name='State Pension', marker_color='#2ca02c'))
fig.add_trace(go.Bar(x=df['Age'], y=df['ISA Draw'], name='ISA/Tax-Free Cash', marker_color='#1f77b4'))
fig.add_trace(go.Bar(x=df['Age'], y=df['SIPP Draw (Net)'], name='SIPP (Taxable)', marker_color='#ff7f0e'))
fig.add_trace(go.Scatter(x=df['Age'], y=df['Tax Paid'], name='Tax Paid (HMRC)', line=dict(color='#d62728', width=2)))

fig.update_layout(barmode='stack', xaxis_title="Age", yaxis_title="£ Amount")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Wealth Over Time")
# Show how the Lump Sum move affects the pots
st.line_chart(df.set_index("Age")[["ISA", "SIPP", "Total Wealth"]])
