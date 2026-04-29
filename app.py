import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 1. CONFIG & INPUTS ---
st.set_page_config(page_title="AJS Retirement Ultimate", layout="wide")
st.title("🚀 AJS Ultimate Retirement Prototype (2026/27)")

# User Guide Expander
with st.expander("❓ How to use this model (User Guide)"):
    st.markdown("""
    ### 1. The Income Waterfall
    The model draws income in this order: **DB Pensions > State Pension > Tax-Free Cash > Taxable SIPP**. 
    This sequence is designed to keep your taxable income as low as possible for as long as possible.

    ### 2. Smart Tax Logic
    We've modeled the **2026/27 Tax Year**, including:
    * **Personal Allowance:** £12,570 (frozen).
    * **The 60% Trap:** Your allowance tapers away between £100k - £125,140.
    * **LSA Cap:** Total tax-free lump sums are capped at £268,275.

    ### 3. Tax-Free Cash vs ISA
    Note: While the model moves 25% of your SIPP into a 'Tax-Free Pot', it does not assume this enters an ISA (which has a £20k annual limit). It simply treats this capital as available to spend without further tax.
    """)

with st.sidebar:
    st.header("1. Assets & Growth")
    current_age = st.number_input("Current Age", value=55)
    retirement_age = st.number_input("Retirement Age", value=60)
    isa_bal = st.number_input("Existing ISA/Cash Balance (£)", value=100000)
    sipp_bal = st.number_input("SIPP Balance (£)", value=400000)
    growth_rate = st.slider("Investment Growth (%)", 0.0, 10.0, 5.0) / 100
    inflation_rate = st.slider("Inflation (%)", 0.0, 5.0, 2.5) / 100

    st.header("2. Guaranteed Income")
    state_pension_age = st.slider("State Pension Age", 66, 68, 67)
    state_pension_amt = st.number_input("Annual State Pension (£)", value=12548)
    db_input = st.text_input("DB Pensions (Age:Amount, Age:Amount)", value="")

    st.header("3. Strategy & Splurges")
    take_lump_sum = st.checkbox("Take 25% Tax-Free Cash?", value=True)
    lump_sum_age = st.slider("Age to take Tax-Free Cash", 55, 75, 60)
    splurge_input = st.text_input("Splurges (Age:Amount)", value="")

    st.header("4. Spending Phases")
    annual_spend = st.number_input("Initial Target Net Spend (£)", value=35000)
    phase_1_age = st.slider("Phase 1 Drop Age", 60, 95, 75)
    phase_1_drop = st.slider("Phase 1 Drop (%)", 0, 50, 10) / 100
    phase_2_age = st.slider("Phase 2 Drop Age", 70, 100, 85)
    phase_2_drop = st.slider("Phase 2 Drop (%)", 0, 50, 10) / 100

# --- 2. CONSTANTS & PARSING ---
PA_BASE = 12570
BASIC_RATE_LIMIT = 50270
TAPER_THRESHOLD = 100000
BASIC_RATE = 0.20
HIGHER_RATE = 0.40
LSA_LIMIT = 268275

def parse_input(text):
    d = {}
    if text:
        try:
            for item in text.split(","):
                k, v = item.split(":")
                d[int(k.strip())] = float(v.strip())
        except: st.sidebar.error(f"Format error in: {text}")
    return d

db_schemes = parse_input(db_input)
splurges = parse_input(splurge_input)

# --- 3. THE CALCULATION ENGINE ---
data = []
temp_tax_free_pot, temp_sipp = isa_bal, sipp_bal
temp_spend, temp_sp = annual_spend, state_pension_amt
lsa_used = 0

for age in range(current_age, 101):
    temp_tax_free_pot *= (1 + growth_rate)
    temp_sipp *= (1 + growth_rate)
    
    if take_lump_sum and age == lump_sum_age:
        lump_amt = min(temp_sipp * 0.25, LSA_LIMIT - lsa_used)
        temp_sipp -= lump_amt
        temp_tax_free_pot += lump_amt
        lsa_used += lump_amt

    # Phase-based Spending
    target_net = temp_spend if age >= retirement_age else 0
    if age >= phase_2_age: target_net *= (1 - phase_1_drop) * (1 - phase_2_drop)
    elif age >= phase_1_age: target_net *= (1 - phase_1_drop)
    target_net += splurges.get(age, 0)
    
    # 1. DB Pensions & State Pension (Taxable base)
    db_income = sum(amt * ((1 + inflation_rate)**(age - current_age)) 
                    for start_age, amt in db_schemes.items() if age >= start_age)
    sp_rec = temp_sp if age >= state_pension_age else 0
    total_taxable_fixed = db_income + sp_rec
    
    net_needed = max(0, target_net - total_taxable_fixed)
    
    # 2. Tax-Free Pot Draw (ISA & Lump Sum)
    draw_tax_free = min(temp_tax_free_pot, net_needed)
    temp_tax_free_pot -= draw_tax_free
    net_final_gap = max(0, net_needed - draw_tax_free)
    
    # 3. SIPP Draw (Taxable)
    draw_sipp_gross = 0
    tax_paid = 0
    if net_final_gap > 0:
        low, high = net_final_gap, net_final_gap * 4
        for _ in range(20):
            mid = (low + high) / 2
            total_taxable = mid + total_taxable_fixed
            pa = max(0, PA_BASE - (max(0, total_taxable - TAPER_THRESHOLD) / 2))
            tax = 0
            if total_taxable > BASIC_RATE_LIMIT:
                tax += (BASIC_RATE_LIMIT - pa) * BASIC_RATE
                tax += (total_taxable - BASIC_RATE_LIMIT) * HIGHER_RATE
            elif total_taxable > pa:
                tax += (total_taxable - pa) * BASIC_RATE
            if (mid - tax) < net_final_gap: low = mid
            else: high = mid
        
        draw_sipp_gross = min(temp_sipp, high)
        tax_paid = max(0, draw_sipp_gross - net_final_gap)
        temp_sipp -= draw_sipp_gross

    data.append({
        "Age": age, "Total Wealth": round(temp_tax_free_pot + temp_sipp),
        "Tax-Free Pot": round(temp_tax_free_pot), "SIPP": round(temp_sipp),
        "DB Income": round(db_income), "State Pension": round(sp_rec),
        "Tax-Free Draw": round(draw_tax_free), "SIPP (Net)": round(net_final_gap),
        "Tax Paid": round(tax_paid), "Target Net": round(target_net)
    })
    temp_spend *= (1 + inflation_rate); temp_sp *= (1 + inflation_rate)

df = pd.DataFrame(data)

# --- 4. METRICS & VISUALS ---
m1, m2, m3 = st.columns(3)
m1.metric("Final Wealth (Age 100)", f"£{df['Total Wealth'].iloc[-1]:,}")
m2.metric("Total Tax Bill", f"£{df['Tax Paid'].sum():,}")
m3.metric("Plan Status", "SECURE" if df['Total Wealth'].iloc[-1] > 0 else "EXHAUSTED", 
          delta_color="normal" if df['Total Wealth'].iloc[-1] > 0 else "inverse")

st.subheader("Annual Income Stack vs Tax Drag")
fig = go.Figure()
fig.add_trace(go.Bar(x=df['Age'], y=df['DB Income'], name='DB Pension', marker_color='#9467bd'))
fig.add_trace(go.Bar(x=df['Age'], y=df['State Pension'], name='State Pension', marker_color='#2ca02c'))
fig.add_trace(go.Bar(x=df['Age'], y=df['Tax-Free Draw'], name='Tax-Free Cash Draw', marker_color='#1f77b4'))
fig.add_trace(go.Bar(x=df['Age'], y=df['SIPP (Net)'], name='SIPP (Net)', marker_color='#ff7f0e'))
fig.add_trace(go.Scatter(x=df['Age'], y=df['Tax Paid'], name='Tax (HMRC)', line=dict(color='#d62728', width=2)))
fig.update_layout(barmode='stack', hovermode="x unified", xaxis_title="Age", yaxis_title="£ Amount")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Asset Depletion")
st.line_chart(df.set_index("Age")[["Tax-Free Pot", "SIPP", "Total Wealth"]])
st.dataframe(df)
