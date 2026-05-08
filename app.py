import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Retirement Planner Pro 2026", layout="wide")

if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "mode": "Joint", "p1_age": 55, "p2_age": 55, "retire_year": 1,
        "isa_bal": 43000, "p1_sipp": 1750000, "p2_sipp": 18415,
        "growth": 5.0, "inflation": 2.5,
        "p1_sp_age": 67, "p1_sp_amt": 12548, "p2_sp_age": 67, "p2_sp_amt": 12548,
        "p1_db": "", "p2_db": "60:2336, 65:5633, 67:6292", 
        "p1_lump_age": 55, "p2_lump_age": 55,
        "spend": 80000, "p1_age_drop": 75, "p1_reduction": 20, 
        "strategy": "ISA First", "use_ufpls": False, "triple_lock": True
    }

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("💾 Profile & Strategy")
    uploaded_file = st.file_uploader("Upload Profile (.json)", type="json")
    if uploaded_file is not None:
        try:
            loaded_data = json.load(uploaded_file)
            if any(st.session_state.defaults.get(k) != v for k, v in loaded_data.items()):
                st.session_state.defaults.update(loaded_data)
                st.rerun()
        except Exception: st.error("Error loading JSON.")

    strat = st.selectbox("Strategy", ["ISA First", "SIPP to Threshold"], index=0 if st.session_state.defaults["strategy"] == "ISA First" else 1)
    ufpls = st.toggle("Use UFPLS", value=st.session_state.defaults["use_ufpls"])
    t_lock = st.toggle("Triple Lock", value=st.session_state.defaults.get("triple_lock", True))

    tabs = st.tabs(["P1", "P2", "Settings"])
    with tabs[0]:
        p1_age_in = st.number_input("P1 Age", value=int(st.session_state.defaults["p1_age"]))
        p1_sipp_in = st.number_input("P1 SIPP", value=float(st.session_state.defaults["p1_sipp"]))
        p1_sp_amt_in = st.number_input("P1 SP", value=float(st.session_state.defaults["p1_sp_amt"]))
        p1_db_in = st.text_input("P1 DB", value=st.session_state.defaults["p1_db"])
    with tabs[1]:
        p2_age_in = st.number_input("P2 Age", value=int(st.session_state.defaults["p2_age"]))
        p2_sipp_in = st.number_input("P2 SIPP", value=float(st.session_state.defaults["p2_sipp"]))
        p2_sp_amt_in = st.number_input("P2 SP", value=float(st.session_state.defaults["p2_sp_amt"]))
        p2_db_in = st.text_input("P2 DB", value=st.session_state.defaults["p2_db"])
    with tabs[2]:
        isa_bal_in = st.number_input("ISA", value=float(st.session_state.defaults["isa_bal"]))
        growth_rate = st.slider("Growth %", 0.0, 10.0, 5.0) / 100
        infl_rate = st.slider("Inflation %", 0.0, 5.0, 2.5) / 100
        spend_target = st.number_input("Target Spend", value=float(st.session_state.defaults["spend"]))

# --- 3. ENGINE ---
PA, BR_LIMIT, TAPER, LSA, MIN_AGE = 12570, 50270, 100000, 268275, 55

def parse_kv(text):
    d = {}
    if text:
        try:
            for item in text.split(","):
                k, v = item.split(":")
                d[int(k.strip())] = float(v.strip())
        except: pass
    return d

def calc_tax(income):
    eff_pa = max(0, PA - (max(0, income - TAPER) / 2))
    if income <= eff_pa: return 0.0
    if income <= BR_LIMIT: return (income - eff_pa) * 0.20
    return ((BR_LIMIT - eff_pa) * 0.20) + ((income - BR_LIMIT) * 0.40)

p1_db_map, p2_db_map = parse_kv(p1_db_in), parse_kv(p2_db_in)
data_log = []
p1_s, p2_s, joint_i = p1_sipp_in, p2_sipp_in, isa_bal_in
p1_lsa, p2_lsa = 0, 0
sp_growth = infl_rate + 0.005 if t_lock else infl_rate

for year in range(41):
    p1_a, p2_a = p1_age_in + year, p2_age_in + year
    p1_s *= (1 + growth_rate); p2_s *= (1 + growth_rate); joint_i *= (1 + growth_rate)
    
    if not ufpls:
        if p1_a == 55:
            amt = min(p1_s * 0.25, LSA - p1_lsa); p1_s -= amt; joint_i += amt; p1_lsa += amt
        if p2_a == 55:
            amt = min(p2_s * 0.25, LSA - p2_lsa); p2_s -= amt; joint_i += amt; p2_lsa += amt

    goal = spend_target * ((1 + infl_rate) ** year)
    p1_guar = (p1_sp_amt_in * ((1 + sp_growth) ** year)) if p1_a >= 67 else 0
    p1_guar += sum(v * ((1 + infl_rate) ** year) for k, v in p1_db_map.items() if p1_a >= k)
    p2_guar = (p2_sp_amt_in * ((1 + sp_growth) ** year)) if p2_a >= 67 else 0
    p2_guar += sum(v * ((1 + infl_rate) ** year) for k, v in p2_db_map.items() if p2_a >= k)

    p1_pa_draw = min(p1_s, max(0, PA - p1_guar) / (0.75 if ufpls else 1.0)) if p1_a >= MIN_AGE else 0
    p1_s -= p1_pa_draw
    p2_pa_draw = min(p2_s, max(0, PA - p2_guar) / (0.75 if ufpls else 1.0)) if p2_a >= MIN_AGE else 0
    p2_s -= p2_pa_draw

    net_fixed = p1_guar + p2_guar + p1_pa_draw + p2_pa_draw
    gap = max(0, goal - net_fixed)
    p1_draw, p2_draw = 0, 0

    if strat == "SIPP to Threshold":
        for p_idx in [1, 2]:
            fixed = (p1_guar + p1_pa_draw*0.75 if ufpls else p1_pa_draw) if p_idx==1 else (p2_guar + p2_pa_draw*0.75 if ufpls else p2_pa_draw)
            gross = min((p1_s if p_idx==1 else p2_s), (BR_LIMIT - fixed) / (0.75 if ufpls else 1.0))
            tax = calc_tax(fixed + gross*0.75 if ufpls else gross) - calc_tax(fixed)
            if p_idx==1: p1_draw = gross; p1_s -= gross
            else: p2_draw = gross; p2_s -= gross
            net_fixed += (gross - tax)
        joint_i -= (goal - net_fixed)
    else:
        i_draw = min(joint_i, gap); joint_i -= i_draw; gap -= i_draw
        if gap > 0:
            p1_draw = min(p1_s, gap / 0.8); p1_s -= p1_draw

    data_log.append({"Age": p1_a, "P1 Pension": round(p1_guar), "P2 Pension": round(p2_guar), "SIPP Draw": round(p1_pa_draw + p1_draw + p2_pa_draw + p2_draw), "Tax": round(calc_tax(p1_guar + p1_draw)), "Total Wealth": round(p1_s + p2_s + joint_i)})

df = pd.DataFrame(data_log)
st.title(f"Plan: {strat}")
st.plotly_chart(go.Figure(data=[go.Bar(x=df['Age'], y=df[c], name=c) for c in ["P1 Pension", "P2 Pension", "SIPP Draw"]]))
st.line_chart(df.set_index("Age")["Total Wealth"])
