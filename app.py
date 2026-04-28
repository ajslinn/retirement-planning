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

st.sidebar.header("One-Off Splurges")
splurge_input = st.sidebar.text_input("Age:Amount (e.g., 60:10000, 70:20000)", value="")

# Convert text input into a dictionary {Age: Amount}
splurges = {}
if splurge_input:
    try:
        for item in splurge_input.split(","):
            age_str, amt_str = item.split(":")
            splurges[int(age_str.strip())] = float(amt_str.strip())
    except:
        st.sidebar.error("Format error! Use Age:Amount, Age:Amount")

st.sidebar.header("Market Assumptions")
growth_rate = st.sidebar.slider("Investment Growth (%)", 0.0, 10.0, 5.0) / 100
inflation_rate = st.sidebar.slider("Inflation (%)", 0.0, 5.0, 2.5) / 100

# --- 2. TAX CONSTANTS (2026/27 ESTIMATES) ---
PA_BASE = 12570
BASIC_RATE_LIMIT = 50270
TAPER_THRESHOLD = 100000
BASIC_RATE = 0.20
HIGHER_RATE = 0.40
LSA_LIMIT = 268275

# --- 3. THE CALCULATION ENGINE ---
data = []
temp_isa, temp_sipp = isa_bal, sipp_bal
temp_spend, temp_sp = annual_spend, state_pension_amt
lsa_used = 0

# Parse splurges from sidebar input
splurges = {}
if splurge_input:
    try:
        for item in splurge_input.split(","):
            age_str, amt_str = item.split(":")
            splurges[int(age_str.strip())] = float(amt_str.strip())
    except Exception:
        st.sidebar.error("Splurge format error! Use Age:Amount")

for age in range(current_age, 101):
    # 1. Annual Growth (applied at start of year)
    temp_isa *= (1 + growth_rate)
    temp_sipp *= (1 + growth_rate)
    
    # 2. Apply 25% Tax-Free Lump Sum (One-time move)
    if take_lump_sum and age == lump_sum_age:
        lump_sum_amt = min(temp_sipp * 0.25, LSA_LIMIT - lsa_used)
        temp_sipp -= lump_sum_amt
        temp_isa += lump_sum_amt
        lsa_used += lump_sum_amt

    # 3. Determine Spending Phase (Glide Path)
    if age < retirement_age:
        base_target_net = 0
    elif age >= phase_2_age:
        base_target_net = temp_spend * (1 - phase_1_drop) * (1 - phase_2_drop)
    elif age >= phase_1_age:
        base_target_net = temp_spend * (1 - phase_1_drop)
    else:
        base_target_net = temp_spend
        
    # 4. Add One-Off Splurge (not subject to phase drops, but adjusted for inflation if you prefer)
    # Here we keep the splurge amount exactly as entered in the text box
    current_splurge = splurges.get(age, 0)
    total_target_net = base_target_net + current_splurge
    
    # 5. Income Sourcing
    sp_rec = temp_sp if age >= state_pension_age else 0
    net_needed = max(0, total_target_net - sp_rec)
    
    # Draw from ISA first (Tax-Free)
    draw_isa = min(temp_isa, net_needed)
    temp_isa -= draw_isa
    net_final_gap = max(0, net_needed - draw_isa)
    
    # 6. SIPP Drawdown with Tax Band & 60% Trap Logic
    draw_sipp_gross = 0
    tax_paid = 0
    
    if net_final_gap > 0:
        # Solve for Gross withdrawal using Binary Search to handle the 60% Taper trap
        low, high = net_final_gap, net_final_gap * 3 
        for _ in range(20): 
            mid = (low + high) / 2
            test_gross = mid + sp_rec
            
            # Personal Allowance Taper Logic
            current_pa = PA_BASE
            if test_gross > TAPER_THRESHOLD:
                reduction = (test_gross - TAPER_THRESHOLD) / 2
                current_pa = max(0, PA_BASE - reduction)
            
            # Calculate Tax based on 2026/27 Bands
            tax = 0
            if test_gross > BASIC_RATE_LIMIT:
                tax += (BASIC_RATE_LIMIT - current_pa) * BASIC_RATE
                tax += (test_gross - BASIC_RATE_LIMIT) * HIGHER_RATE
            elif test_gross > current_pa:
                tax += (test_gross - current_pa) * BASIC_RATE
                
            if (mid - tax) < net_final_gap: 
                low = mid
            else: 
                high = mid
        
        draw_sipp_gross = min(temp_sipp, high)
        tax_paid = max(0, draw_sipp_gross - net_final_gap)
        temp_sipp -= draw_sipp_gross

    # 7. Record Year Data
    data.append({
        "Age": age, 
        "Total Wealth": round(temp_isa + temp_sipp),
        "ISA": round(temp_isa), 
        "SIPP": round(temp_sipp),
        "Target Spend": round(total_target_net),
        "ISA Draw": round(draw_isa), 
        "SIPP Draw (Net)": round(net_final_gap),
        "State Pension": round(sp_rec), 
        "Tax Paid": round(tax_paid),
        "Net Income Received": round(sp_rec + draw_isa + net_final_gap)
    })
    
    # 8. Inflation for next year's loop
    temp_spend *= (1 + inflation_rate)
    temp_sp *= (1 + inflation_rate)

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
