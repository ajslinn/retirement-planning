import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Retirement Planner Pro", layout="wide")

# Correct 2026/27 Defaults
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

# --- 2. SIDEBAR & PROFILE MANAGEMENT ---
with st.sidebar:
    st.header("💾 Profile Management")
    uploaded_file = st.file_uploader("Upload '.json' profile", type="json")
    if uploaded_file is not None:
        try:
            loaded_data = json.load(uploaded_file)
            # CRITICAL: Only rerun if the data is different to stop the 'spinning' loop
            if any(st.session_state.defaults.get(k) != v for k, v in loaded_data.items()):
                st.session_state.defaults.update(loaded_data)
                st.rerun()
        except Exception: 
            st.error("Invalid JSON file.")

    st.header("⚙️ Strategy & Global")
    mode = st.radio("Mode", ["Single", "Joint"], index=0 if st.session_state.defaults["mode"] == "Single" else 1)
    strat = st.selectbox("Sequencing Strategy", ["ISA First", "SIPP to Threshold"], 
                         index=0 if st.session_state.defaults.get("strategy") == "ISA First" else 1)
    ufpls = st.toggle("Use UFPLS (25% Tax-Free Trickle)", value=st.session_state.defaults.get("use_ufpls", False))
    t_lock = st.toggle("Triple Lock (+0.5% vs Infl)", value=st.session_state.defaults.get("triple_lock", True))

    tabs = st.tabs(["Partner 1", "Partner 2", "Household"]) if mode == "Joint" else st.tabs(["User", "Household"])
    
    with tabs[0]:
        p1_age_start = st.number_input("P1 Age", value=int(st.session_state.defaults["p1_age"]))
        p1_sipp = st.number_input("P1 SIPP (£)", value=float(st.session_state.defaults["p1_sipp"]))
        p1_sp_amt = st.number_input("P1 State Pension (£)", value=float(st.session_state.defaults["p1_sp_amt"]))
        p1_db_in = st.text_input("P1 DB (Age:Amt)", value=st.session_state.defaults["p1_db"])

    if mode == "Joint":
        with tabs[1]:
            p2_age_start = st.number_input("P2 Age", value=int(st.session_state.defaults["p2_age"]))
            p2_sipp = st.number_input("P2 SIPP (£)", value=float(st.session_state.defaults["p2_sipp"]))
            p2_sp_amt = st.number_input("P2 State Pension (£)", value=float(st.session_state.defaults["p2_sp_amt"]))
            p2_db_in = st.text_input("P2 DB (Age:Amt)", value=st.session_state.defaults["p2_db"])
    else:
        p2_age_start, p2_sipp, p2_sp_amt, p2_db_in = 0, 0, 0, ""

    with tabs[-1]:
        isa_joint = st.number_input("Joint ISA (£)", value=float(st.session_state.defaults["isa_bal"]))
        growth = st.slider("Growth (%)", 0.0, 10.0, float(st.session_state.defaults["growth"])) / 100
        infl = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults["inflation"])) / 100
        target_spend = st.number_input("Target Spend (£)", value=float(st.session_state.defaults["spend"]))
        p1_drop_age = st.slider("Step-Down Age", 60, 95, int(st.session_state.defaults["p1_age_drop"]))
        p1_red = st.slider("Reduction %", 0, 50, int(st.session_state.defaults["p1_reduction"])) / 100

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
    eff_pa = max(0, PA - (max(0, income - TAPER) / 2))
    if income <= eff_pa: return 0.0
    if income <= BR_LIMIT: return (income - eff_pa) * 0.2
    return ((BR_LIMIT - eff_pa) * 0.2) + ((income - BR_LIMIT) * 0.4)

p1_db_map, p2_db_map = parse_kv(p1_db_in), parse_kv(p2_db_in)
data_log = []
p1_s, p2_s, joint_i = p1_sipp, p2_sipp, isa_joint
p1_lsa, p2_lsa = 0, 0
sp_growth = infl + 0.005 if t_lock else infl

for year in range(41):
    p1_a, p2_a = p1_age_start + year, p2_age_start + year
    p1_s *= (1+growth); p2_s *= (1+growth); joint_i *= (1+growth)
    
    # 1. Goal & Guaranteed Income
    goal = target_spend * ((1+infl)**year)
    if p1_a >= p1_drop_age: goal *= (1 - p1_red)

    p1_guar = (p1_sp_amt * ((1+sp_growth)**year)) if p1_a >= 67 else 0
    p1_guar += sum(v*((1+infl)**year) for k,v in p1_db_map.items() if p1_a >= k)
    p2_guar = (p2_sp_amt * ((1+sp_growth)**year)) if (mode == "Joint" and p2_a >= 67) else 0
    p2_guar += sum(v*((1+infl)**year) for k,v in p2_db_map.items() if p2_a >= k)

    # 2. Crystallization (Non-UFPLS)
    if not ufpls:
        if p1_a == st.session_state.defaults["p1_lump_age"]:
            amt = min(p1_s*0.25, LSA-p1_lsa); p1_s -= amt; joint_i += amt; p1_lsa += amt
        if mode == "Joint" and p2_a == st.session_state.defaults["p2_lump_age"]:
            amt = min(p2_s*0.25, LSA-p2_lsa); p2_s -= amt; joint_i += amt; p2_lsa += amt

    # 3. Fill Personal Allowance
    p1_pa_draw = min(p1_s, max(0, PA - p1_guar) / (0.75 if ufpls else 1.0)) if p1_a >= MIN_AGE else 0
    p1_s -= p1_pa_draw
    p2_pa_draw = min(p2_s, max(0, PA - p2_guar) / (0.75 if ufpls else 1.0)) if (mode=="Joint" and p2_a >= MIN_AGE) else 0
    p2_s -= p2_pa_draw

    net_fixed = p1_guar + p2_guar + p1_pa_draw + p2_pa_draw
    gap = max(0, goal - net_fixed)
    p1_extra, p2_extra = 0, 0

    if strat == "SIPP to Threshold":
        for p_idx in ([1, 2] if mode=="Joint" else [1]):
            # Calculate taxable base
            fixed = (p1_guar + p1_pa_draw*0.75 if ufpls else p1_pa_draw) if p_idx==1 else (p2_guar + p2_pa_draw*0.75 if ufpls else p2_pa_draw)
            gross = min((p1_s if p_idx==1 else p2_s), (BR_LIMIT - fixed) / (0.75 if ufpls else 1.0))
            tax = calc_tax(fixed + (gross * 0.75 if ufpls else gross)) - calc_tax(fixed)
            if p_idx == 1: p1_extra = gross; p1_s -= gross
            else: p2_extra = gross; p2_s -= gross
            net_fixed += (gross - tax)
        joint_i -= (goal - net_fixed)
    else:
        # ISA First
        isa_draw = min(joint_i, gap); joint_i -= isa_draw; gap -= isa_draw
        if gap > 0:
            p1_extra = min(p1_s, gap / 0.8) # Approx tax adjustment
            p1_s -= p1_extra

    data_log.append({
        "Age": p1_a, 
        "P1 Pension": round(p1_guar), 
        "P2 Pension": round(p2_guar),
        "SIPP Draw": round(p1_pa_draw + p1_extra + p2_pa_draw + p2_extra),
        "Tax": round(calc_tax(p1_guar + p1_extra) + calc_tax(p2_guar + p2_extra)),
        "Total Wealth": round(p1_s + p2_s + joint_i)
    })

df = pd.DataFrame(data_log)

# --- 4. VISUALS ---
st.title(f"Retirement Forecast: {strat} ({mode})")
c1, c2, c3 = st.columns(3)
c1.metric("Final Position", f"£{df['Total Wealth'].iloc[-1]:,}")
c2.metric("Total Tax Paid", f"£{df['Tax'].sum():,}")
c3.metric("State Pension (67)", f"£{df.loc[df['Age']==67, 'P1 Pension'].iloc[0]:,}" if 67 in df['Age'].values else "N/A")

fig = go.Figure()
for col, color in [("P1 Pension", "#2ca02c"), ("P2 Pension", "#b2df8a"), ("SIPP Draw", "#9467bd")]:
    fig.add_trace(go.Bar(x=df['Age'], y=df[col], name=col, marker_color=color))
fig.add_trace(go.Scatter(x=df['Age'], y=df['Tax'], name="Tax", line=dict(color='red')))
fig.update_layout(barmode='relative', hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.line_chart(df.set_index("Age")["Total Wealth"])
