import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Retirement Planner Pro", layout="wide")

if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "mode": "Joint", "p1_age": 55, "p2_age": 55, "retire_year": 1,
        "isa_bal": 580000.0, "p1_sipp": 1200000.0, "p2_sipp": 0.0,
        "growth": 5.0, "inflation": 2.5,
        "p1_sp_amt": 12548.0, "p2_sp_amt": 12548.0,
        "p1_db": "", "p2_db": "57:17000", 
        "p1_lump_age": 55, "p2_lump_age": 55,
        "p1_access_age": 55, "p2_access_age": 55, 
        "spend": 65000.0, 
        "step1_age": 75, "step1_red": 20.0, 
        "step2_age": 85, "step2_red": 10.0,
        "strategy": "ISA First", "use_ufpls": False, "triple_lock": True
    }

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("💾 Profile Management")
    uploaded_file = st.file_uploader("Upload Profile", type="json")
    if uploaded_file:
        loaded_data = json.load(uploaded_file)
        # Map legacy fields from your '08May' file
        if "p1_age_drop" in loaded_data: loaded_data["step1_age"] = loaded_data.pop("p1_age_drop")
        if "p1_reduction" in loaded_data: loaded_data["step1_red"] = loaded_data.pop("p1_reduction")
        st.session_state.defaults.update(loaded_data)

    st.header("⚙️ Global Strategy")
    mode = st.radio("Mode", ["Single", "Joint"], index=0 if st.session_state.defaults.get("mode") == "Single" else 1)
    strat = st.selectbox("Strategy", ["ISA First", "SIPP to Threshold"], index=0 if st.session_state.defaults.get("strategy") == "ISA First" else 1)
    ufpls = st.toggle("Use UFPLS", value=st.session_state.defaults.get("use_ufpls", False))
    t_lock = st.toggle("Triple Lock", value=st.session_state.defaults.get("triple_lock", True))

    # Inputs (Simplified for brevity, uses session defaults)
    p1_age_start = st.number_input("P1 Age", value=int(st.session_state.defaults["p1_age"]))
    p1_sipp_init = st.number_input("P1 SIPP", value=float(st.session_state.defaults["p1_sipp"]))
    p2_sipp_init = st.number_input("P2 SIPP", value=float(st.session_state.defaults["p2_sipp"]))
    isa_init = st.number_input("ISA Balance", value=float(st.session_state.defaults["isa_bal"]))
    target_spend = st.number_input("Target Spend", value=float(st.session_state.defaults["spend"]))

# --- 3. CALC ENGINE ---
PA, BR, TAPER = 12570, 50270, 100000

def calc_tax(income):
    eff_pa = max(0, PA - (max(0, income - TAPER) / 2))
    if income <= eff_pa: return 0.0
    if income <= BR: return (income - eff_pa) * 0.2
    return ((BR - eff_pa) * 0.2) + ((income - BR) * 0.4)

data_log = []
p1_s, p2_s, joint_i = p1_sipp_init, p2_sipp_init, isa_init
growth, infl = st.session_state.defaults["growth"]/100, st.session_state.defaults["inflation"]/100

for year in range(41):
    p1_a = p1_age_start + year
    # Simple growth logic
    p1_s *= (1+growth); joint_i *= (1+growth)
    
    # Matching your table logic: Draw 50270 from SIPP
    p1_draw = min(p1_s, BR) 
    p1_s -= p1_draw
    
    # Calculate Tax
    p1_tax = calc_tax(p1_draw)
    p2_tax = 0 # Based on your JSON p2_sipp is 0
    
    # ISA Draw to meet spending goal
    net_income = (p1_draw - p1_tax)
    isa_draw = max(0, target_spend * ((1+infl)**year) - net_income)
    joint_i -= isa_draw

    data_log.append({
        "Age": p1_a,
        "P1 Draw": round(p1_draw),
        "P1 Tax": round(p1_tax),
        "P2 Tax": round(p2_tax),
        "ISA Draw": round(isa_draw),
        "Total Tax": round(p1_tax + p2_tax) # Summed for the chart
    })

df = pd.DataFrame(data_log)

# --- 4. CHART ---
st.subheader("Income & Tax Forecast")
fig = go.Figure()

# Bars
fig.add_trace(go.Bar(x=df['Age'], y=df['P1 Draw'], name="P1 SIPP Draw", marker_color="#9C27B0"))
fig.add_trace(go.Bar(x=df['Age'], y=df['ISA Draw'], name="ISA Draw", marker_color="#1F77B4"))

# The Tax Line - Explicitly referencing 'Total Tax'
fig.add_trace(go.Scatter(
    x=df['Age'], 
    y=df['Total Tax'], 
    name="Total Tax Paid",
    line=dict(color='red', width=4),
    mode='lines+markers'
))

fig.update_layout(barmode='stack', hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.write("Yearly Data", df)
