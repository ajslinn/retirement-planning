import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Retirement Planner Pro", layout="wide")

if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "mode": "Joint", "p1_age": 55, "p2_age": 55, "isa_bal": 580000.0,
        "p1_sipp": 1200000.0, "p2_sipp": 0.0, "growth": 5.0, "inflation": 2.5,
        "p1_sp_amt": 12548.0, "p2_sp_amt": 12548.0, "p1_db": "", "p2_db": "57:17000",
        "p1_lump_age": 55, "p2_lump_age": 55, "p1_access_age": 55, "p2_access_age": 55,
        "spend": 65000.0, "step1_age": 75, "step1_red": 20.0, "strategy": "ISA First",
        "use_ufpls": False, "triple_lock": True
    }

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("💾 Profile Management")
    uploaded_file = st.file_uploader("Upload Profile", type="json")
    if uploaded_file:
        loaded_data = json.load(uploaded_file)
        # Handle legacy names from your anon file
        if "p1_age_drop" in loaded_data: loaded_data["step1_age"] = loaded_data.pop("p1_age_drop")
        if "p1_reduction" in loaded_data: loaded_data["step1_red"] = loaded_data.pop("p1_reduction")
        st.session_state.defaults.update(loaded_data)

    st.header("⚙️ Global Strategy")
    mode = st.radio("Mode", ["Single", "Joint"], index=0 if st.session_state.defaults["mode"] == "Single" else 1)
    strat = st.selectbox("Strategy", ["ISA First", "SIPP to Threshold"], index=0 if st.session_state.defaults["strategy"] == "ISA First" else 1)
    ufpls = st.toggle("Use UFPLS", value=st.session_state.defaults["use_ufpls"])
    t_lock = st.toggle("Triple Lock", value=st.session_state.defaults["triple_lock"])

    p1_age_start = st.number_input("P1 Age", value=int(st.session_state.defaults["p1_age"]))
    p1_sipp_init = st.number_input("P1 SIPP", value=float(st.session_state.defaults["p1_sipp"]))
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
p1_s, joint_i = p1_sipp_init, isa_init
growth, infl = st.session_state.defaults["growth"]/100, st.session_state.defaults["inflation"]/100
sp_growth = infl + 0.005 if t_lock else infl

for year in range(41):
    p1_a = p1_age_start + year
    p1_s *= (1+growth); joint_i *= (1+growth)
    
    # Calculate Guaranteed Income
    p1_sp = (st.session_state.defaults["p1_sp_amt"] * ((1+sp_growth)**year)) if p1_a >= 67 else 0
    p2_db = (17000 * ((1+infl)**year)) if p1_a >= 57 else 0
    fixed_inc = p1_sp + p2_db
    
    # SIPP Draw Logic (Fixing the minus figures)
    if strat == "SIPP to Threshold":
        # Only draw if fixed income hasn't already pushed you over the threshold
        p1_draw = max(0, min(p1_s, BR - fixed_inc))
    else:
        # ISA First logic - draw enough to cover allowance or threshold
        p1_draw = max(0, min(p1_s, PA - fixed_inc)) if p1_a < 67 else 0

    p1_s -= p1_draw
    p1_tax = calc_tax(fixed_inc + p1_draw)
    
    # ISA coverage
    goal = target_spend * ((1+infl)**year)
    if p1_a >= st.session_state.defaults["step1_age"]: goal *= (1 - st.session_state.defaults["step1_red"]/100)
    
    net_inc = (fixed_inc + p1_draw) - p1_tax
    isa_draw = max(0, goal - net_inc)
    joint_i -= isa_draw

    data_log.append({
        "Age": p1_a,
        "P1 SP": round(p1_sp),
        "P2 DB": round(p2_db),
        "P1 SIPP Draw": round(p1_draw),
        "P1 Tax": round(p1_tax),
        "ISA Draw": round(isa_draw),
        "Total Tax Line": round(p1_tax), # This name MUST match the chart trace below
        "Total Wealth": round(p1_s + joint_i)
    })

df = pd.DataFrame(data_log)

# --- 4. DISPLAY ---
st.subheader("Income & Tax Forecast")
fig = go.Figure()

# Bars
fig.add_trace(go.Bar(x=df['Age'], y=df['P1 SP'], name="P1 State Pension", marker_color="#4A148C"))
fig.add_trace(go.Bar(x=df['Age'], y=df['P2 DB'], name="P2 DB Pension", marker_color="#388E3C"))
fig.add_trace(go.Bar(x=df['Age'], y=df['P1 SIPP Draw'], name="P1 SIPP Draw", marker_color="#9C27B0"))
fig.add_trace(go.Bar(x=df['Age'], y=df['ISA Draw'], name="ISA Draw", marker_color="#1F77B4"))

# The Red Tax Line (Pinned to 'Total Tax Line')
fig.add_trace(go.Scatter(
    x=df['Age'], 
    y=df['Total Tax Line'], 
    name="Total Tax Paid",
    line=dict(color='red', width=4),
    mode='lines+markers'
))

fig.update_layout(barmode='stack', hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Yearly Breakdown")
st.dataframe(df, use_container_width=True)
