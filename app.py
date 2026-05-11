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
        "spend": 65000.0, "step1_age": 75, "step1_red": 20.0, "step2_age": 85, "step2_red": 10.0,
        "strategy": "ISA First", "use_ufpls": False, "triple_lock": True
    }

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("💾 Profile Management")
    uploaded_file = st.file_uploader("Upload Profile", type="json")
    if uploaded_file:
        loaded_data = json.load(uploaded_file)
        if "p1_age_drop" in loaded_data: loaded_data["step1_age"] = loaded_data.pop("p1_age_drop")
        if "p1_reduction" in loaded_data: loaded_data["step1_red"] = loaded_data.pop("p1_reduction")
        st.session_state.defaults.update(loaded_data)

    st.header("⚙️ Global Strategy")
    mode = st.radio("Mode", ["Single", "Joint"], index=0 if st.session_state.defaults["mode"] == "Single" else 1)
    strat = st.selectbox("Strategy", ["ISA First", "SIPP to Threshold"], index=0 if st.session_state.defaults["strategy"] == "ISA First" else 1)
    ufpls = st.toggle("Use UFPLS", value=st.session_state.defaults["use_ufpls"])
    t_lock = st.toggle("Triple Lock", value=st.session_state.defaults["triple_lock"])

    tabs = st.tabs(["Partner 1", "Partner 2", "Household"]) if mode == "Joint" else st.tabs(["User", "Household"])
    
    with tabs[0]:
        p1_age_start = st.number_input("P1 Age", value=int(st.session_state.defaults["p1_age"]))
        p1_acc_age = st.number_input("P1 SIPP Access Age", value=int(st.session_state.defaults["p1_access_age"]))
        p1_l_age = st.number_input("P1 Lump Sum Age", value=int(st.session_state.defaults["p1_lump_age"]))
        p1_sipp_init = st.number_input("P1 SIPP Balance", value=float(st.session_state.defaults["p1_sipp"]))
        p1_sp_amt = st.number_input("P1 State Pension", value=float(st.session_state.defaults["p1_sp_amt"]))
        p1_db_in = st.text_input("P1 DB (Age:Amt)", value=st.session_state.defaults["p1_db"])

    if mode == "Joint":
        with tabs[1]:
            p2_age_start = st.number_input("P2 Age", value=int(st.session_state.defaults["p2_age"]))
            p2_acc_age = st.number_input("P2 SIPP Access Age", value=int(st.session_state.defaults["p2_access_age"]))
            p2_l_age = st.number_input("P2 Lump Sum Age", value=int(st.session_state.defaults["p2_lump_age"]))
            p2_sipp_init = st.number_input("P2 SIPP Balance", value=float(st.session_state.defaults["p2_sipp"]))
            p2_sp_amt = st.number_input("P2 State Pension", value=float(st.session_state.defaults["p2_sp_amt"]))
            p2_db_in = st.text_input("P2 DB (Age:Amt)", value=st.session_state.defaults["p2_db"])
    else:
        p2_age_start, p2_acc_age, p2_l_age, p2_sipp_init, p2_sp_amt, p2_db_in = 0, 0, 0, 0, 0, ""

    with tabs[-1]:
        isa_init = st.number_input("ISA Balance", value=float(st.session_state.defaults["isa_bal"]))
        growth = st.slider("Growth (%)", 0.0, 10.0, float(st.session_state.defaults["growth"])) / 100
        infl = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults["inflation"])) / 100
        target_spend = st.number_input("Target Spend", value=float(st.session_state.defaults["spend"]))
        st.divider()
        s1_age = st.slider("Step 1 Age", 60, 95, int(st.session_state.defaults["step1_age"]))
        s1_red = st.slider("Step 1 Red %", 0, 50, int(st.session_state.defaults["step1_red"])) / 100

# --- 3. CALC ENGINE ---
PA, BR, TAPER, LSA_MAX = 12570, 50270, 100000, 268275

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
data_log = []
p1_s, p2_s, joint_i = p1_sipp_init, p2_sipp_init, isa_init
p1_lsa_taken, p2_lsa_taken = 0, 0
sp_growth = infl + 0.005 if t_lock else infl

for year in range(41):
    p1_a, p2_a = p1_age_start + year, p2_age_start + year
    p1_s *= (1+growth); p2_s *= (1+growth); joint_i *= (1+growth)
    
    # Lump Sum Logic
    if not ufpls:
        if p1_a == p1_l_age and p1_a >= p1_acc_age:
            lump = min(p1_s * 0.25, LSA_MAX - p1_lsa_taken)
            p1_s -= lump; joint_i += lump; p1_lsa_taken += lump
        if mode == "Joint" and p2_a == p2_l_age and p2_a >= p2_acc_age:
            lump = min(p2_s * 0.25, LSA_MAX - p2_lsa_taken)
            p2_s -= lump; joint_i += lump; p2_lsa_taken += lump

    # Guaranteed Income
    p1_sp = (p1_sp_amt * ((1+sp_growth)**year)) if p1_a >= 67 else 0
    p1_db = sum(v*((1+infl)**year) for k,v in p1_db_map.items() if p1_a >= k)
    p2_sp = (p2_sp_amt * ((1+sp_growth)**year)) if (mode=="Joint" and p2_a >= 67) else 0
    p2_db = sum(v*((1+infl)**year) for k,v in p2_db_map.items() if p2_a >= k)
    
    # SIPP Draw
    if strat == "SIPP to Threshold":
        p1_draw = max(0, min(p1_s, BR - (p1_sp + p1_db))) if p1_a >= p1_acc_age else 0
        p2_draw = max(0, min(p2_s, BR - (p2_sp + p2_db))) if (mode=="Joint" and p2_a >= p2_acc_age) else 0
    else:
        p1_draw = max(0, min(p1_s, PA - (p1_sp + p1_db))) if p1_a >= p1_acc_age else 0
        p2_draw = max(0, min(p2_s, PA - (p2_sp + p2_db))) if (mode=="Joint" and p2_a >= p2_acc_age) else 0

    p1_s -= p1_draw; p2_s -= p2_draw
    p1_tax = calc_tax(p1_sp + p1_db + p1_draw)
    p2_tax = calc_tax(p2_sp + p2_db + p2_draw)
    
    # ISA Draw
    goal = target_spend * ((1+infl)**year)
    if p1_a >= s1_age: goal *= (1 - s1_red)
    
    net_inc = (p1_sp + p1_db + p1_draw - p1_tax) + (p2_sp + p2_db + p2_draw - p2_tax)
    isa_draw = max(0, goal - net_inc)
    joint_i -= isa_draw

    data_log.append({
        "P1 Age": p1_a, "P1 SP": round(p1_sp), "P1 DB": round(p1_db), "P1 Draw": round(p1_draw), "P1 Tax": round(p1_tax), "P1 SIPP Balance": round(p1_s),
        "P2 Age": p2_a, "P2 SP": round(p2_sp), "P2 DB": round(p2_db), "P2 Draw": round(p2_draw), "P2 Tax": round(p2_tax), "P2 SIPP Balance": round(p2_s),
        "ISA Draw": round(isa_draw), "ISA Balance": round(joint_i), "Total Tax": round(p1_tax + p2_tax), "Total Wealth": round(p1_s + p2_s + joint_i)
    })

df = pd.DataFrame(data_log)

# --- 4. DISPLAY ---
st.subheader(f"Retirement Forecast: {strat}")
fig = go.Figure()
for col in ["P1 SP", "P1 DB", "P1 Draw", "P2 SP", "P2 DB", "P2 Draw", "ISA Draw"]:
    fig.add_trace(go.Bar(x=df['P1 Age'], y=df[col], name=col))
fig.add_trace(go.Scatter(x=df['P1 Age'], y=df['Total Tax'], name="Total Tax", line=dict(color='red', width=3)))
fig.update_layout(barmode='stack', hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Yearly Breakdown")
st.dataframe(df, use_container_width=True)
