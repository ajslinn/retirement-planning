import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Retirement Planner Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "mode": "Joint", "p1_age": 55, "p2_age": 53, "retire_year": 5,
        "isa_bal": 100000, "p1_sipp": 400000, "p2_sipp": 300000,
        "growth": 5.0, "inflation": 2.5,
        "p1_sp_age": 67, "p1_sp_amt": 12548, "p2_sp_age": 67, "p2_sp_amt": 12548,
        "p1_db": "", "p2_db": "", "p1_lump_age": 60, "p2_lump_age": 60,
        "spend": 45000, "p1_age_drop": 75, "p1_reduction": 10, "p2_age_drop": 85, "p2_reduction": 10,
        "splurge": "", "strategy": "ISA First", "use_ufpls": False
    }

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    mode = st.radio("Planning Mode", ["Single", "Joint"], index=0 if st.session_state.defaults.get("mode") == "Single" else 1)
    
    st.header("💾 Profile Management")
    uploaded_file = st.file_uploader("Upload '.json' profile", type="json")
    if uploaded_file is not None:
        try:
            file_contents = uploaded_file.read()
            loaded_data = json.loads(file_contents)
            st.session_state.defaults.update(loaded_data)
            st.rerun()
        except Exception: pass

    st.header("📈 Drawdown Strategy")
    strat = st.selectbox("Sequencing Logic", ["ISA First", "SIPP to Threshold"], 
                         index=0 if st.session_state.defaults.get("strategy") == "ISA First" else 1)
    ufpls = st.toggle("Use UFPLS (Trickle Tax-Free Cash)", value=st.session_state.defaults.get("use_ufpls", False))

    tabs = st.tabs(["Partner 1", "Partner 2", "Household"]) if mode == "Joint" else st.tabs(["User", "Household"])
    
    with tabs[0]:
        p1_age_start = st.number_input("P1 Age", value=int(st.session_state.defaults["p1_age"]))
        p1_sipp = st.number_input("P1 SIPP (£)", value=float(st.session_state.defaults["p1_sipp"]))
        p1_sp_age = st.slider("P1 State Pension Age", 66, 68, int(st.session_state.defaults["p1_sp_age"]))
        p1_sp_amt = st.number_input("P1 State Pension (£)", value=float(st.session_state.defaults["p1_sp_amt"]))
        p1_db_in = st.text_input("P1 DB (Age:Amt)", value=st.session_state.defaults["p1_db"])
        p1_lump_age = st.slider("P1 Lump Sum Age", 55, 75, int(st.session_state.defaults["p1_lump_age"]))

    if mode == "Joint":
        with tabs[1]:
            p2_age_start = st.number_input("P2 Age", value=int(st.session_state.defaults["p2_age"]))
            p2_sipp = st.number_input("P2 SIPP (£)", value=float(st.session_state.defaults["p2_sipp"]))
            p2_sp_age = st.slider("P2 State Pension Age", 66, 68, int(st.session_state.defaults["p2_sp_age"]))
            p2_sp_amt = st.number_input("P2 State Pension (£)", value=float(st.session_state.defaults["p2_sp_amt"]))
            p2_db_in = st.text_input("P2 DB (Age:Amt)", value=st.session_state.defaults["p2_db"])
            p2_lump_age = st.slider("P2 Lump Sum Age", 55, 75, int(st.session_state.defaults["p2_lump_age"]))
    else:
        p2_age_start, p2_sipp, p2_sp_age, p2_sp_amt, p2_db_in, p2_lump_age = 0, 0, 99, 0, "", 99

    with tabs[-1]:
        retire_in_yrs = st.number_input("Years to Retirement", value=int(st.session_state.defaults["retire_year"]))
        isa_joint = st.number_input("Joint ISA (£)", value=float(st.session_state.defaults["isa_bal"]))
        growth = st.slider("Growth (%)", 0.0, 10.0, float(st.session_state.defaults["growth"])) / 100
        infl = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults["inflation"])) / 100
        target_spend = st.number_input("Target Spend (£)", value=float(st.session_state.defaults["spend"]))
        p1_drop_age = st.slider("Phase 1 Reduc. Age", 60, 95, int(st.session_state.defaults["p1_age_drop"]))
        p1_red = st.slider("Reduction %", 0, 50, int(st.session_state.defaults["p1_reduction"])) / 100
        splurge_in = st.text_input("Splurges (P1_Age:Amt)", value=st.session_state.defaults["splurge"])

    export_data = {**st.session_state.defaults, "strategy": strat, "use_ufpls": ufpls}
    st.download_button("📥 Save Profile", json.dumps(export_data, indent=4), "retirement_profile.json")

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

def calc_tax(total_taxable):
    pa = max(0, PA - (max(0, total_taxable - TAPER)/2))
    if total_taxable > BR_LIMIT: return (BR_LIMIT - pa) * 0.2 + (total_taxable - BR_LIMIT) * 0.4
    return max(0, (total_taxable - pa) * 0.2)

p1_db_map, p2_db_map, splurges = parse_kv(p1_db_in), parse_kv(p2_db_in), parse_kv(splurge_in)
data_log = []
p1_s, p2_s, joint_i = p1_sipp, p2_sipp, isa_joint
p1_lsa, p2_lsa = 0, 0
curr_spend, p1_curr_sp, p2_curr_sp = target_spend, p1_sp_amt, p2_sp_amt

for year in range(46):
    p1_a, p2_a = p1_age_start + year, p2_age_start + year
    p1_s *= (1+growth); p2_s *= (1+growth); joint_i *= (1+growth)
    
    # 1. Lump Sum Strategy (Only if NOT using UFPLS)
    if not ufpls:
        if p1_a == p1_lump_age and p1_a >= MIN_AGE:
            amt = min(p1_s*0.25, LSA-p1_lsa); p1_s -= amt; joint_i += amt; p1_lsa += amt
        if mode == "Joint" and p2_a == p2_lump_age and p2_a >= MIN_AGE:
            amt = min(p2_s*0.25, LSA-p2_lsa); p2_s -= amt; joint_i += amt; p2_lsa += amt

    # 2. Income Goal
    goal = curr_spend if year >= retire_in_yrs else 0
    if p1_a >= p1_drop_age: goal *= (1-p1_red)
    goal += splurges.get(p1_a, 0)

    # 3. Guaranteed Income
    p1_sp = p1_curr_sp if p1_a >= p1_sp_age else 0
    p2_sp = p2_curr_sp if (mode=="Joint" and p2_a >= p2_sp_age) else 0
    p1_db = sum(v*((1+infl)**year) for k,v in p1_db_map.items() if p1_a >= k)
    p2_db = sum(v*((1+infl)**year) for k,v in p2_db_map.items() if p2_a >= k) if mode=="Joint" else 0
    
    # 4. Drawdown Strategy Selection
    p1_draw, p2_draw, isa_draw = 0, 0, 0
    
    # Fill Personal Allowance first (Standard for all strategies)
    p1_pa_bed = min(p1_s, max(0, PA - (p1_sp + p1_db))) if p1_a >= MIN_AGE else 0
    p2_pa_bed = min(p2_s, max(0, PA - (p2_sp + p2_db))) if (mode=="Joint" and p2_a >= MIN_AGE) else 0
    p1_s -= p1_pa_bed; p2_s -= p2_pa_bed
    
    current_income = (p1_sp + p1_db + p1_pa_bed) + (p2_sp + p2_db + p2_pa_bed)
    gap = max(0, goal - current_income)

    if strat == "SIPP to Threshold" and p1_a >= MIN_AGE:
        # Strategy: Withdraw up to Higher Rate Threshold regardless of need
        target_taxable = BR_LIMIT
        for p_idx in ([1, 2] if mode=="Joint" else [1]):
            age, s_bal, fixed = (p1_a, p1_s, p1_sp+p1_db+p1_pa_bed) if p_idx==1 else (p2_a, p2_s, p2_sp+p2_db+p2_pa_bed)
            if age < MIN_AGE: continue
            available_room = max(0, target_taxable - fixed)
            draw = min(s_bal, available_room)
            net_draw = draw - (calc_tax(fixed + draw) - calc_tax(fixed))
            if p_idx == 1: p1_draw = draw; p1_s -= draw
            else: p2_draw = draw; p2_s -= draw
            current_income += net_draw
        
        # If we have excess income, put it in ISA. If we still have a gap, take from ISA.
        if current_income > goal: joint_i += (current_income - goal)
        else:
            isa_draw = min(joint_i, goal - current_income)
            joint_i -= isa_draw
    else:
        # Strategy: ISA First (Bridge gap with ISA before taking taxable SIPP)
        isa_draw = min(joint_i, gap)
        joint_i -= isa_draw
        gap = max(0, gap - isa_draw)
        
        if gap > 0:
            for p_idx in ([1, 2] if mode=="Joint" else [1]):
                target = gap * (0.5 if mode=="Joint" else 1.0)
                age, s_bal, fixed = (p1_a, p1_s, p1_sp+p1_db+p1_pa_bed) if p_idx==1 else (p2_a, p2_s, p2_sp+p2_db+p2_pa_bed)
                if age < MIN_AGE: continue
                # Solve for gross needed to get net target
                low, high = target, target * 2
                for _ in range(15):
                    mid = (low + high) / 2
                    if (mid - (calc_tax(fixed + mid) - calc_tax(fixed))) < target: low = mid
                    else: high = mid
                draw = min(s_bal, high)
                if p_idx == 1: p1_draw = draw; p1_s -= draw
                else: p2_draw = draw; p2_s -= draw

    # 5. Final Tax Calculation
    p1_total_taxable = p1_sp + p1_db + p1_pa_bed + p1_draw
    p2_total_taxable = p2_sp + p2_db + p2_pa_bed + p2_draw
    
    # UFPLS Adjustment: If using UFPLS, 25% of the draw is tax-free
    p1_tax = calc_tax(p1_total_taxable - (p1_draw * 0.25 if ufpls else 0))
    p2_tax = calc_tax(p2_total_taxable - (p2_draw * 0.25 if ufpls else 0)) if mode=="Joint" else 0

    data_log.append({
        "Age": p1_a, "P1 State Pension": round(p1_sp), "P2 State Pension": round(p2_sp),
        "P1 DB Pension": round(p1_db), "P2 DB Pension": round(p2_db),
        "P1 SIPP Draw": round(p1_pa_bed + p1_draw), "P2 SIPP Draw": round(p2_pa_bed + p2_draw),
        "ISA Draw/Save": round(isa_draw if current_income <= goal else (goal - current_income)),
        "Tax": round(p1_tax + p2_tax), "Total Wealth": round(p1_s + p2_s + joint_i),
        "P1_SIPP": round(p1_s), "P2_SIPP": round(p2_s), "Joint_ISA": round(joint_i)
    })
    curr_spend *= (1+infl); p1_curr_sp *= (1+infl); p2_curr_sp *= (1+infl)

df = pd.DataFrame(data_log)

# --- 4. VISUALS ---
st.title(f"Retirement Projection ({strat})")
m1, m2, m3 = st.columns(3)
m1.metric("Final Wealth", f"£{df['Total Wealth'].iloc[-1]:,}")
m2.metric("Total Tax Paid", f"£{df['Tax'].sum():,}")
m3.metric("Plan Status", "SECURE" if df['Total Wealth'].iloc[-1] > 0 else "EXHAUSTED")

fig = go.Figure()
cols = [("P1 State Pension", "#2ca02c"), ("P2 State Pension", "#b2df8a"), ("P1 DB Pension", "#ff7f0e"), 
        ("P2 DB Pension", "#ffbb78"), ("P1 SIPP Draw", "#9467bd"), ("P2 SIPP Draw", "#cab2d6"), ("ISA Draw/Save", "#1f77b4")]
for col, color in cols:
    if df[col].sum() != 0: fig.add_trace(go.Bar(x=df['Age'], y=df[col], name=col, marker_color=color))
fig.add_trace(go.Scatter(x=df['Age'], y=df['Tax'], name='Tax', line=dict(color='red', width=2)))
fig.update_layout(barmode='relative', hovermode="x unified", xaxis_title="Age (P1)")
st.plotly_chart(fig, use_container_width=True)

st.line_chart(df.set_index("Age")[["Total Wealth", "P1_SIPP", "Joint_ISA"] + (["P2_SIPP"] if mode=="Joint" else [])])
with st.expander("📊 View Raw Data"): st.dataframe(df)
