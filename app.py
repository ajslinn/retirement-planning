import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 1. CONFIG & INPUTS ---
st.set_page_config(page_title="AJS Retirement Prototype", layout="wide")
st.title("🚀 AJS 2026 Retirement Calculator (Ultimate)")

st.sidebar.header("Current Assets")
current_age = st.sidebar.number_input("Current Age", value=55)
retirement_age = st.sidebar.number_input("Retirement Age", value=60)
isa_bal = st.sidebar.number_input("ISA Balance (£)", value=100000)
sipp_bal = st.sidebar.number_input("SIPP Balance (£)", value=400000)

st.sidebar.header("State Pension")
state_pension_age = st.sidebar.slider("State Pension Age", 66, 68, 67)
state_pension_amt = st.sidebar.number_input("Annual State Pension (£)", value=12548)

st.sidebar.header("Lump Sum Strategy")
take_lump_sum = st.sidebar.checkbox("Apply 25% Tax-Free Lump Sum?", value=True)
lump_sum_age = st.sidebar.slider("Age to take Lump Sum", 55, 75, 60)

st.sidebar.header("Spending Phases")
annual_spend = st.sidebar.number_input("Initial Target Net Spend (£)", value=35000)
phase_1_age = st.sidebar.slider("Age for Phase 1 Drop", 60, 95, 75)
phase_1_drop = st.sidebar.slider("Phase 1 Drop (%)", 0, 50, 10) / 100
phase_2_age = st.sidebar.slider("Age for Phase 2 Drop", 70, 100, 85)
phase_2_drop = st.sidebar.slider("Phase 2 Drop (%)", 0, 50, 10) / 100

st.sidebar.header("Market Assumptions")
growth_rate = st.sidebar.slider("Investment Growth (%)", 0.0, 10.0, 5.0) / 100
inflation_rate = st.sidebar.slider("Inflation (%)", 0.0, 5.0, 2.5) / 100

# --- 2. TAX CONSTANTS (2026/27 ESTIMATES) ---
PA_BASE = 12570
BASIC_RATE_LIMIT = 50270
TAPER_THRESHOLD = 100000
BASIC_RATE = 0.20
HIGHER_RATE = 0.40

# --- 3. THE CALCULATION ENGINE ---
data = []
temp_isa, temp_sipp = isa_bal, sipp_bal
temp_spend, temp_sp = annual_spend, state_pension_amt
lsa_used = 0

for age in range(current_age, 101):
    temp_isa *= (1 + growth_rate)
    temp_sipp *= (1 + growth_rate)
    
    # Apply 25% Tax-Free Lump Sum
    if take_lump_sum and age == lump_sum_age:
        lump_sum_amt = min(temp_sipp * 0.25, 268275 - lsa_used)
        temp_sipp -= lump_sum_amt
        temp_isa += lump_sum_amt
        lsa_used += lump_sum_amt

    # Phase-based Spending Logic
    target_net = temp_spend
    if age < retirement_age:
        target_net = 0
    elif age >= phase_2_age:
        target_net = temp_spend * (1 - phase_1_drop) * (1 - phase_2_drop)
    elif age >= phase_1_age:
        target_net = temp_spend * (1 - phase_1_drop)
        
    sp_rec = temp_sp if age >= state_pension_age else 0
    net_needed = max(0, target_net - sp_rec)
    
    # Draw from ISA (Tax-Free)
    draw_isa = min(temp_isa, net_needed)
    temp_isa -= draw_isa
    net_final_gap = max(0, net_needed - draw_isa)
    
    # Calculate SIPP Gross Withdrawal (With Tax Bands & 60% Trap)
    draw_sipp_gross = 0
    tax_paid = 0
    
    if net_final_gap > 0:
        # We solve for Gross withdrawal using a step-climb approach
        low, high = net_final_gap, net_final_gap * 3 # Search range for gross
        for _ in range(20): # Binary search for precision
            mid = (low + high) / 2
            test_gross = mid + sp_rec
            
            # Calculate Personal Allowance Taper
            current_pa = PA_BASE
            if test_gross > TAPER_THRESHOLD:
                reduction = (test_gross - TAPER_THRESHOLD) / 2
                current_pa = max(0, PA_BASE - reduction)
            
            # Calculate Tax
            tax = 0
            if test_gross > BASIC_RATE_LIMIT:
                tax += (BASIC_RATE_LIMIT - current_pa) * BASIC_RATE
                tax += (test_gross - BASIC_RATE_LIMIT) * HIGHER_RATE
            elif test_gross > current_pa:
                tax += (test_gross - current_pa) * BASIC_RATE
                
            if (mid - tax) < net_final_gap: low = mid
            else: high = mid
        
        draw_sipp_gross = min(temp_sipp, high)
        tax_paid = draw_sipp_gross - net_final_gap
        temp_sipp -= draw_sipp_gross

    data.append({
        "Age": age, "Total Wealth": round(temp_isa + temp_sipp),
        "ISA": round(temp_isa), "SIPP": round(temp_sipp),
        "ISA Draw": round(draw_isa), "SIPP Draw (Net)": round(net_final_gap),
        "State Pension": round(sp_rec), "Tax Paid": round(tax_paid),
        "Net Income": round(sp_rec + draw_isa + net_final_gap)
    })
    temp_spend *= (1 + inflation_rate); temp_sp *= (1 + inflation_rate)

df = pd.DataFrame(data)

# --- 4. VISUALIZATION ---
st.subheader("Annual Income Strategy")
fig = go.Figure()
fig.add_trace(go.Bar(x=df['Age'], y=df['State Pension'], name='State Pension', marker_color='#2ca02c'))
fig.add_trace(go.Bar(x=df['Age'], y=df['ISA Draw'], name='ISA/Lump Sum', marker_color='#1f77b4'))
fig.add_trace(go.Bar(x=df['Age'], y=df['SIPP Draw (Net)'], name='SIPP (Net)', marker_color='#ff7f0e'))
fig.add_trace(go.Scatter(x=df['Age'], y=df['Tax Paid'], name='Tax (HMRC)', line=dict(color='#d62728', width=2)))
fig.update_layout(barmode='stack', hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Asset Depletion")
st.line_chart(df.set_index("Age")[["ISA", "SIPP", "Total Wealth"]])
st.dataframe(df)
