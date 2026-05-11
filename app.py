import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Retirement Planner Pro - Dev", layout="wide")

# Default values based on your uploaded profile
if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "mode": "Joint", "p1_age": 55, "p2_age": 55, "isa_bal": 580000.0,
        "p1_sipp": 1200000.0, "p2_sipp": 0.0, "growth": 5.0, "inflation": 2.5,
        "p1_sp_amt": 12548.0, "p2_sp_amt": 12548.0, "p1_db": "", "p2_db": "57:17000",
        "p1_lump_age": 55, "p2_lump_age": 55, "p1_access_age": 55, "p2_access_age": 55,
        "spend": 65000.0, "step1_age": 75, "step1_red": 20.0, "step2_age": 85, "step2_red": 10.0,
        "strategy": "ISA First", "use_ufpls": False, "triple_lock": True
    }

if 'last_loaded_file_id' not in st.session_state:
    st.session_state.last_loaded_file_id = None

# --- 2. SIDEBAR & PROFILE HANDLING ---
with st.sidebar:
    st.header("💾 Profile Management")
    uploaded_file = st.file_uploader("Upload Profile", type="json")
    
    if uploaded_file is not None:
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.last_loaded_file_id != file_id:
            try:
                loaded_data = json.load(uploaded_file)
                # Map legacy keys from your 'anon_08May' file format
                if "p1_age_drop" in loaded_data:
                    loaded_data["step1_age"] = loaded_data.pop("p1_age_drop")
                if "p1_reduction" in loaded_data:
                    loaded_data["step1_red"] = loaded_data.pop("p1_reduction")
                
                st.session_state.defaults.update(loaded_data)
                st.session_state.last_loaded_file_id = file_id
                st.rerun()
            except Exception as e: 
                st.error(f"Error loading profile: {e}")
    
    st.header("⚙️ Global Strategy")
    mode = st.radio("Mode", ["Single", "Joint"], index=0 if st.session_state.defaults.get("mode") == "Single" else 1)
    strat = st.selectbox("Strategy", ["ISA First", "SIPP to Threshold"], index=0 if st.session_state.defaults.get("strategy") == "ISA First" else 1)
    ufpls = st.toggle("Use UFPLS", value=st.session_state.defaults.get("use_ufpls", False))
    t_lock = st.toggle("Triple Lock", value=st.session_state.defaults.get("triple_lock", True))

    tabs = st.tabs(["Partner 1", "Partner 2", "Household"]) if mode == "Joint" else st.tabs(["User", "Household"])
    
    with tabs[0]:
        p1_age_start = st.number_input("P1 Age", value=int(st.session_state.defaults.get("p1_age", 55)))
        p1_acc_age = st.number_input("P1 Access Age", 50, 75, int(st.session_state.defaults.get("p1_access_age", 55)))
        p1_sipp_init = st.number_input("P1 SIPP Balance (£)", value=float(st.session_state.defaults.get("p1_sipp", 1200000)))
        p1_sp_amt = st.number_input("P1 State Pension (£)", value=float(st.session_state.defaults.get("p1_sp_amt", 12548)))
        p1_db_in = st.text_input("P1 DB (Age:Amt)", value=st.session_state.defaults.get("p1_db", ""))

    if mode == "Joint":
        with tabs[1]:
            p2_age_start = st.number_input("P2 Age", value=int(st.session_state.defaults.get("p2_age", 55)))
            p2_sipp_init = st.number_input("P2 SIPP Balance (£)", value=float(st.session_state.defaults.get("p2_sipp", 0)))
            p2_db_in = st.text_input("P2 DB (Age:Amt)", value=st.session_state.defaults.get("p2_db", "57:17000"))
    else: p2_age_start, p2_sipp_init, p2_db_in = 0, 0, ""

    with tabs[-1]:
        isa_joint_init = st.number_input("Joint ISA (£)", value=float(st.session_state.defaults.get("isa_bal", 580000)))
        growth = st.slider("Growth (%)", 0.0, 10.0, float(st.session_state.defaults.get("growth", 5.0))) / 100
        infl = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults.get("inflation", 2.5))) / 100
        target_spend = st.number_input("Target Spend (£)", value=float(st.session_state.defaults.get("spend", 65000)))
        st.divider()
        s1_age = st.slider("Step 1 Age", 60, 95, int(st.session_state.defaults.get("step1_age", 75)))
        s1_red = st.slider("Step 1 Reduction %", 0, 50, int(st.session_state.defaults.get("step1_red", 20))) / 100

# --- 3. CALCULATION ENGINE ---
PA, BR, TAPER = 12570, 50270, 100000

def parse_kv(text):
    d = {}
    if text:
        try:
            for item in text.split(","):
                k, v = item.split(":"); d[int(k.strip())] = float(v.strip())
        except: pass
    return d

def calc_tax(income):
    eff_pa = max(0, PA - (max(0, income - TAPER) / 2))
    if income <= eff_pa: return 0.0
    if income <= BR: return (income - eff_pa) * 0.2
    return ((BR - eff_pa) * 0.2) + ((income - BR) * 0.4)

p1_db_map, p2_db_map = parse_kv(p1_db_in), parse_kv(p2_db_in)
data_log, p1_s, p2_s, joint_i = [], p1_sipp_init, p2_sipp_init, isa_joint_init
sp_growth = (infl + 0.005) if t_lock else infl

for year in range(41):
    p1_a, p2_a = p1_age_start + year, p2_age_start + year
    p1_s *= (1+growth); p2_s *= (1+growth); joint_i *= (1+growth)
    
    # 1. Guaranteed Income
    p1_sp = (p1_sp_amt * ((1+sp_growth)**year)) if p1_a >= 67 else 0
    p1_db = sum(v*((1+infl)**year) for k,v in p1_db_map.items() if p1_a >= k)
    p2_db = sum(v*((1+infl)**year) for k,v in p2_db_map.items() if p2_a >= k)
    fixed_inc = p1_sp + p1_db + p2_db

    # 2. SIPP Draw Strategy
    if strat == "SIPP to Threshold":
        p1_draw = max(0, min(p1_s, BR - fixed_inc))
    else:
        p1_draw = max(0, min(p1_s, PA - fixed_inc)) if p1_a >= 55 else 0

    p1_s -= p1_draw
    annual_tax = calc_tax(fixed_inc + p1_draw)
    
    # 3. ISA Coverage
    goal = target_spend * ((1+infl)**year)
    if p1_a >= s1_age: goal *= (1 - s1_red)
    
    net_non_isa = (fixed_inc + p1_draw) - annual_tax
    isa_draw = max(0, goal - net_non_isa)
    joint_i -= isa_draw

    data_log.append({
        "Age": p1_a,
        "Pension Income": round(fixed_inc),
        "SIPP Draw": round(p1_draw),
        "ISA Draw": round(isa_draw),
        "Total Wealth": round(p1_s + p2_s + joint_i),
        "TAX_VAL": round(annual_tax)
    })

df = pd.DataFrame(data_log)

# --- 4. VISUALIZATION ---
st.title(f"Retirement Forecast: {strat}")

# We use subplots with a secondary Y-axis to ensure the Tax Line is visible
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Add Stacks
fig.add_trace(go.Bar(x=df['Age'], y=df['Pension Income'], name="Pension (SP/DB)", marker_color="#4A148C"), secondary_y=False)
fig.add_trace(go.Bar(x=df['Age'], y=df['SIPP Draw'], name="SIPP Draw", marker_color="#9C27B0"), secondary_y=False)
fig.add_trace(go.Bar(x=df['Age'], y=df['ISA Draw'], name="ISA Draw", marker_color="#1F77B4"), secondary_y=False)

# Add Tax Line on Secondary Axis (prevents it being squashed at the bottom)
fig.add_trace(go.Scatter(
    x=df['Age'], y=df['TAX_VAL'], name="Annual Tax",
    line=dict(color='red', width=4), mode='lines+markers'
), secondary_y=True)

fig.update_layout(barmode='stack', hovermode="x unified", title="Income Mix vs Annual Tax")
fig.update_yaxes(title_text="Income / Spend (£)", secondary_y=False)
fig.update_yaxes(title_text="Tax Paid (£)", secondary_y=True, color="red")

st.plotly_chart(fig, use_container_width=True)

st.subheader("Asset Depletion")
st.line_chart(df.set_index("Age")["Total Wealth"])

st.subheader("Yearly Breakdown")
st.dataframe(df, use_container_width=True)
