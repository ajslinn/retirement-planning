import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Retirement Planner Pro 2026", layout="wide")

# Persistent defaults reflecting 2026/27 UK Tax Year rates
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
            # Prevent infinite loop by checking for actual changes
            if any(st.session_state.defaults.get(k) != v for k, v in loaded_data.items()):
                st.session_state.defaults.update(loaded_data)
                st.rerun()
        except Exception: 
            st.error("Error loading JSON.")

    strat = st.selectbox("Drawdown Strategy", ["ISA First", "SIPP to Threshold"], 
                         index=0 if st.session_state.defaults["strategy"] == "ISA First" else 1)
    ufpls = st.toggle("Use UFPLS (Tax-Free Trickle)", value=st.session_state.defaults["use_ufpls"])
    t_lock = st.toggle("Apply Triple Lock (+0.5% over infl.)", value=st.session_state.defaults.get("triple_lock", True))

    tabs = st.tabs(["Partner 1", "Partner 2", "Settings"])
    
    with tabs[0]:
        p1_age_in = st.number_input("P1 Age", value=int(st.session_state.defaults["p1_age"]))
        p1_sipp_in = st.number_input("P1 SIPP (£)", value=float(st.session_state.defaults["p1_sipp"]))
        p1_sp_amt_in = st.number_input("P1 State Pension", value=float(st.session_state.defaults["p1_sp_amt"]))
        p1_db_in = st.text_input("P1 DB (Age:Amt)", value=st.session_state.defaults["p1_db"])

    with tabs[1]:
        p2_age_in = st.number_input("P2 Age", value=int(st.session_state.defaults["p2_age"]))
        p2_sipp_in = st.number_input("P2 SIPP (£)", value=float(st.session_state.defaults["p2_sipp"]))
        p2_sp_amt_in = st.number_input("P2 State Pension", value=float(st.session_state.defaults["p2_sp_amt"]))
        p2_db_in = st.text_input("P2 DB (Age:Amt)", value=st.session_state.defaults["p2_db"])

    with tabs[2]:
        isa_bal_in = st.number_input("Joint ISA (£)", value=float(st.session_state.defaults["isa_bal"]))
        growth_rate = st.slider("Growth (%)", 0.0, 10.0, float(st.session_state.defaults["growth"])) / 100
        infl_rate = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults["inflation"])) / 100
        spend_target = st.number_input("Target Spend (£)", value=float(st.session_state.defaults["spend"]))

# --- 3. CALCULATION ENGINE ---
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
    # Calculate Personal Allowance considering the taper above £100k
    current_pa = max(0, PA - (max(0, income - TAPER) / 2))
    if income <= current_pa:
        return 0.0
    elif income <= BR_LIMIT:
        return (income - current_pa) * 0.20
    else:
        # Basic rate tax on band between PA and BR, 40% on remainder
        basic_tax = (BR_LIMIT - current_pa) * 0.20
        higher_tax = (income - BR_LIMIT) * 0.40
        return basic_tax + higher_tax

p1_db_map, p2_db_map = parse_kv(p1_db_in), parse_kv(p2_db_in)
data_log = []
p1_s, p2_s, joint_i = p1_sipp_in, p2_sipp_in, isa_bal_in
p1_lsa, p2_lsa = 0, 0
sp_growth = infl_rate + 0.005 if t_lock else infl_rate

for year in range(41):
    p1_a, p2_a = p1_age_in + year, p2_age_in + year
    p1_s *= (1 + growth_rate); p2_s *= (1 + growth_rate); joint_i *= (1 + growth_rate)
    
    # 1. 25% Lump Sum Logic (Standard Crystallization)
    if not ufpls:
        if p1_a == st.session_state.defaults["p1_lump_age"]:
            amt = min(p1_s * 0.25, LSA - p1_lsa)
            p1_s -= amt; joint_i += amt; p1_lsa += amt
        if p2_a == st.session_state.defaults["p2_lump_age"]:
            amt = min(p2_s * 0.25, LSA - p2_lsa)
            p2_s -= amt; joint_i += amt; p2_lsa += amt

    # 2. Income Goal (Inflation Adjusted)
    goal = spend_target * ((1 + infl_rate) ** year)
    if p1_a >= st.session_state.defaults["p1_age_drop"]: 
        goal *= (1 - st.session_state.defaults["p1_reduction"] / 100)

    # 3. Guaranteed Income (State + DB)
    p1_guar = (p1_sp_amt_in * ((1 + sp_growth) ** year)) if p1_a >= 67 else 0
    p1_guar += sum(v * ((1 + infl_rate) ** year) for k, v in p1_db_map.items() if p1_a >= k)
    
    p2_guar = (p2_sp_amt_in * ((1 + sp_growth) ** year)) if p2_a >= 67 else 0
    p2_guar += sum(v * ((1 + infl_rate) ** year) for k, v in p2_db_map.items() if p2_a >= k)

    p1_draw, p2_draw, isa_draw = 0, 0, 0
    
    # 4. Fill Personal Allowance (Tax-Free portion)
    p1_pa_req = max(0, PA - p1_guar) / (0.75 if ufpls else 1.0)
    p1_pa_draw = min(p1_s, p1_pa_req) if p1_a >= MIN_AGE else 0
    p1_s -= p1_pa_draw
    
    p2_pa_req = max(0, PA - p2_guar) / (0.75 if ufpls else 1.0)
    p2_pa_draw = min(p2_s, p2_pa_req) if p2_a >= MIN_AGE else 0
    p2_s -= p2_pa_draw

    net_fixed = p1_guar + p2_guar + p1_pa_draw + p2_pa_draw
    gap = max(0, goal - net_fixed)

    if strat == "SIPP to Threshold":
        # Strategy: Take SIPP up to Higher Rate Threshold, save surplus to ISA
        for p_idx in [1, 2]:
            age, s_bal, fixed = (p1_a, p1_s, p1_guar + (p1_pa_draw * 0.75 if ufpls else p1_pa_draw)) if p_idx == 1 else (p2_a, p2_s, p2_guar + (p2_pa_draw * 0.75 if ufpls else p2_pa_draw))
            if age < MIN_AGE: continue
            
            room = max(0, BR_LIMIT - fixed)
            gross = min(s_bal, room / (0.75 if ufpls else 1.0))
            tax_on_draw = calc_tax(fixed + gross * (0.75 if ufpls else 1.0)) - calc_tax(fixed)
            
            if p_idx == 1: p1_draw = gross; p1_s -= gross
            else: p2_draw = gross; p2_s -= gross
            net_fixed += (gross - tax_on_draw)
        
        isa_flow = goal - net_fixed 
        joint_i -= isa_flow # positive = withdraw from ISA, negative = save to ISA
    else:
        # Strategy: ISA First
        isa_draw = min(joint_i, gap)
        joint_i -= isa_draw
        gap = max(0, gap - isa_draw)
        if gap > 0:
            for p_idx in [1, 2]:
                age, s_bal, fixed = (p1_a, p1_s, p1_guar) if p_idx == 1 else (p2_a, p2_s, p2_guar)
                if age < MIN_AGE: continue
                draw_needed = min(s_bal, (gap / 2 if p_idx == 1 else gap) / 0.8)
                if p_idx == 1: p1_draw = draw_needed; p1_s -= draw_needed; gap -= (draw_needed * 0.8)
                else: p2_draw = draw_needed; p2_s -= draw_needed

    p1_tax_final = calc_tax(p1_guar + (p1_pa_draw + p1_draw) * (0.75 if ufpls else 1.0))
    p2_tax_final = calc_tax(p2_guar + (p2_pa_draw + p2_draw) * (0.75 if ufpls else 1.0))

    data_log.append({
        "Age": p1_a, 
        "P1 Pension": round(p1_guar), 
        "P2 Pension": round(p2_guar),
        "SIPP Draw": round(p1_pa_draw + p1_draw + p2_pa_draw + p2_draw),
        "ISA Flow": round(goal - net_fixed + p1_draw + p2_draw),
        "Tax": round(p1_tax_final + p2_tax_final), 
        "Total Wealth": round(p1_s + p2_s + joint_i)
    })

df = pd.DataFrame(data_log)

# --- 4. DISPLAY ---
st.title(f"Retirement Projection: {strat}")
c1, c2, c3 = st.columns(3)
c1.metric("Final Position", f"£{df['Total Wealth'].iloc[-1]:,}")
c2.metric("Total Tax Bill", f"£{df['Tax'].sum():,}")
c3.metric("State Pension (Age 67)", f"£{df.loc[df['Age']==67, 'P1 Pension'].iloc[0]:,}" if not df.loc[df['Age']==67].empty else "N/A")

fig = go.Figure()
for col, color in [("P1 Pension", "#2ca02c"), ("P2 Pension", "#b2df8a"), ("SIPP Draw", "#9467bd"), ("ISA Flow", "#1f77b4")]:
    fig.add_trace(go.Bar(x=df['Age'], y=df[col], name=col, marker_color=color))
fig.add_trace(go.Scatter(x=df['Age'], y=df['Tax'], name="Tax", line=dict(color='red')))
fig.update_layout(barmode='relative', hovermode="x unified", xaxis_title="Age (P1)")
st.plotly_chart(fig, use_container_width=True)

st.line_chart(df.set_index("Age")["Total Wealth"])
