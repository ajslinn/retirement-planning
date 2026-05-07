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

# Safety Check: Reset if structure changed
if 'defaults' in st.session_state:
    if "p1_age" not in st.session_state.defaults:
        del st.session_state['defaults']

if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "mode": "Joint", "p1_age": 55, "p2_age": 53, "retire_year": 5,
        "isa_bal": 100000, "p1_sipp": 400000, "p2_sipp": 300000,
        "growth": 5.0, "inflation": 2.5,
        "p1_sp_age": 67, "p1_sp_amt": 12548, "p2_sp_age": 67, "p2_sp_amt": 12548,
        "p1_db": "", "p2_db": "", "p1_lump_age": 60, "p2_lump_age": 60,
        "spend": 45000, "p1_age_drop": 75, "p1_reduction": 10, "p2_age_drop": 85, "p2_reduction": 10,
        "splurge": ""
    }

# --- 2. USER GUIDE ---
st.title("Retirement Planner Pro (2026/27)")

with st.expander("📖 USER GUIDE & SYSTEM LOGIC", expanded=False):
    st.write("Toggle between **Single** and **Joint** modes in the sidebar. The engine dynamically adjusts tax allowances.")
    st.markdown("---")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Tax Optimization")
        st.write("The model automatically utilizes the £12,570 Personal Allowance per person. In Joint mode, it splits withdrawals to keep both partners in the lowest tax bracket.")
    with col_g2:
        st.subheader("Waterfall Methodology")
        st.write("1. Guaranteed Income (DB/State Pension) -> 2. SIPP 'Allowance Fill' (0% Tax) -> 3. ISA/Tax-Free Cash -> 4. Taxable SIPP (Grossed up).")

# --- 3. SIDEBAR: MODE TOGGLE & INPUTS ---
with st.sidebar:
    st.header("⚙️ Configuration")
    mode = st.radio("Planning Mode", ["Single", "Joint"], index=1 if st.session_state.defaults["mode"] == "Joint" else 0)
    
    st.header("💾 Profile Management")
    uploaded_file = st.file_uploader("Upload '.json' profile", type="json")
    if uploaded_file is not None:
        try:
            st.session_state.defaults.update(json.load(uploaded_file))
            st.success("Profile Loaded!")
        except: st.error("Invalid Format")

    # CONDITIONAL TABS
    if mode == "Joint":
        tab_p1, tab_p2, tab_joint = st.tabs(["Partner 1", "Partner 2", "Household"])
    else:
        tab_p1, tab_joint = st.tabs(["User Details", "Household"])
        tab_p2 = None # Ghost Partner 2

    with tab_p1:
        p1_age_start = st.number_input("P1 Age", value=int(st.session_state.defaults["p1_age"]))
        p1_sipp = st.number_input("P1 SIPP (£)", value=float(st.session_state.defaults["p1_sipp"]))
        p1_sp_age = st.slider("P1 State Pension Age", 66, 68, int(st.session_state.defaults["p1_sp_age"]))
        p1_sp_amt = st.number_input("P1 State Pension (£)", value=float(st.session_state.defaults["p1_sp_amt"]))
        p1_db_in = st.text_input("P1 DB (Age:Amt)", value=st.session_state.defaults["p1_db"])
        p1_lump_age = st.slider("P1 Tax-Free Age", 55, 75, int(st.session_state.defaults["p1_lump_age"]))

    if mode == "Joint":
        with tab_p2:
            p2_age_start = st.number_input("P2 Age", value=int(st.session_state.defaults["p2_age"]))
            p2_sipp = st.number_input("P2 SIPP (£)", value=float(st.session_state.defaults["p2_sipp"]))
            p2_sp_age = st.slider("P2 State Pension Age", 66, 68, int(st.session_state.defaults["p2_sp_age"]))
            p2_sp_amt = st.number_input("P2 State Pension (£)", value=float(st.session_state.defaults["p2_sp_amt"]))
            p2_db_in = st.text_input("P2 DB (Age:Amt)", value=st.session_state.defaults["p2_db"])
            p2_lump_age = st.slider("P2 Tax-Free Age", 55, 75, int(st.session_state.defaults["p2_lump_age"]))
    else:
        # Defaults for Single Mode to keep engine running
        p2_age_start, p2_sipp, p2_sp_age, p2_sp_amt, p2_db_in, p2_lump_age = 0, 0, 99, 0, "", 99

    with tab_joint:
        retire_in_yrs = st.number_input("Years to Retirement", value=int(st.session_state.defaults["retire_year"]))
        isa_joint = st.number_input("Joint ISA/Savings (£)", value=float(st.session_state.defaults["isa_bal"]))
        growth = st.slider("Growth (%)", 0.0, 10.0, float(st.session_state.defaults["growth"])) / 100
        infl = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults["inflation"])) / 100
        target_spend = st.number_input("Target Spend (£)", value=float(st.session_state.defaults["spend"]))
        p1_drop_age = st.slider("Phase 1 Age", 60, 95, int(st.session_state.defaults["p1_age_drop"]))
        p1_red = st.slider("Reduction (%)", 0, 50, int(st.session_state.defaults["p1_reduction"])) / 100
        p2_drop_age = st.slider("Phase 2 Age", 70, 100, int(st.session_state.defaults["p2_age_drop"]))
        p2_red = st.slider("Addl Reduction (%)", 0, 50, int(st.session_state.defaults["p2_reduction"])) / 100
        splurge_in = st.text_input("Splurges (P1_Age:Amt)", value=st.session_state.defaults["splurge"])

    # Save
    exp = {**st.session_state.defaults, "mode": mode}
    st.download_button("📥 Save Profile", json.dumps(exp, indent=4), "retirement_profile.json")

# --- 4. CALCULATION ENGINE ---
PA, BR_LIMIT, TAPER, LSA = 12570, 50270, 100000, 268275

def parse_kv(text):
    d = {}
    if text:
        try:
            for item in text.split(","):
                k, v = item.split(":")
                d[int(k.strip())] = float(v.strip())
        except: pass
    return d

p1_db, p2_db, splurges = parse_kv(p1_db_in), parse_kv(p2_db_in if mode=="Joint" else ""), parse_kv(splurge_in)
data = []
p1_s, p2_s, joint_i = p1_sipp, p2_sipp, isa_joint
p1_lsa, p2_lsa = 0, 0
curr_spend, p1_curr_sp, p2_curr_sp = target_spend, p1_sp_amt, p2_sp_amt

for year in range(46):
    p1_a, p2_a = p1_age_start + year, p2_age_start + year
    p1_s *= (1+growth); p2_s *= (1+growth); joint_i *= (1+growth)

    if p1_a == p1_lump_age:
        amt = min(p1_s*0.25, LSA-p1_lsa); p1_s -= amt; joint_i += amt; p1_lsa += amt
    if mode == "Joint" and p2_a == p2_lump_age:
        amt = min(p2_s*0.25, LSA-p2_lsa); p2_s -= amt; joint_i += amt; p2_lsa += amt

    goal = curr_spend if year >= retire_in_yrs else 0
    if p1_a >= p2_drop_age: goal *= (1-p1_red)*(1-p2_red)
    elif p1_a >= p1_drop_age: goal *= (1-p1_red)
    goal += splurges.get(p1_a, 0)

    p1_f = (p1_curr_sp if p1_a >= p1_sp_age else 0) + sum(v*((1+infl)**year) for k,v in p1_db.items() if p1_a >= k)
    p2_f = (p2_curr_sp if p2_a >= p2_sp_age else 0) + sum(v*((1+infl)**year) for k,v in p2_db.items() if p2_a >= k)
    
    # PA BEDDING
    p1_pa_d = min(p1_s, max(0, PA-p1_f), (goal/2 if mode=="Joint" else goal))
    p2_pa_d = min(p2_s, max(0, PA-p2_f), (goal - p1_pa_d)) if mode=="Joint" else 0
    p1_s -= p1_pa_d; p2_s -= p2_pa_d
    
    net_needed = max(0, goal - (p1_f + p2_f + p1_pa_d + p2_pa_d))
    draw_isa = min(joint_i, net_needed)
    joint_i -= draw_isa
    final_gap = max(0, net_needed - draw_isa)

    p1_tax, p2_tax, p1_sn, p2_sn = 0, 0, 0, 0
    if final_gap > 0:
        def calc_tax(gross, fixed, pa_draw):
            tot = gross + fixed + pa_draw
            pa = max(0, PA - (max(0, tot - TAPER)/2))
            if tot > BR_LIMIT: return (BR_LIMIT-pa)*0.2 + (tot-BR_LIMIT)*0.4
            return max(0, (tot-pa)*0.2)

        # In Single mode, P1 takes 100%. In Joint, split 50/50.
        share = 0.5 if mode == "Joint" else 1.0
        for p_idx in ([1, 2] if mode == "Joint" else [1]):
            target = final_gap * share
            low, high = target, target * 3
            f, pad, s = (p1_f, p1_pa_d, p1_s) if p_idx == 1 else (p2_f, p2_pa_d, p2_s)
            for _ in range(15):
                mid = (low + high) / 2
                if (mid - calc_tax(mid, f, pad)) < target: low = mid
                else: high = mid
            
            ad = min(s, high); tx = calc_tax(ad, f, pad)
            if p_idx == 1: p1_tax = tx; p1_sn = ad - tx; p1_s -= ad
            else: p2_tax = tx; p2_sn = ad - tx; p2_s -= ad

    data.append({
        "Age": p1_a, "Total Wealth": round(p1_s + p2_s + joint_i),
        "P1_SIPP": round(p1_s), "P2_SIPP": round(p2_s), "Joint_ISA": round(joint_i),
        "Tax": round(p1_tax + p2_tax), "Target": round(goal),
        "Income_P1": round(p1_f + p1_pa_d + p1_sn),
        "Income_P2": round(p2_f + p2_pa_d + p2_sn) if mode=="Joint" else 0,
        "ISA_Draw": round(draw_isa)
    })
    curr_spend *= (1+infl); p1_curr_sp *= (1+infl); p2_curr_sp *= (1+infl)

df = pd.DataFrame(data)

# --- 5. VISUALS ---
m1, m2, m3 = st.columns(3)
m1.metric("Final Wealth", f"£{df['Total Wealth'].iloc[-1]:,}")
m2.metric("Total Tax", f"£{df['Tax'].sum():,}")
m3.metric("Status", "SECURE" if df['Total Wealth'].iloc[-1] > 0 else "EXHAUSTED")

fig = go.Figure()
fig.add_trace(go.Bar(x=df['Age'], y=df['Income_P1'], name='P1 Income', marker_color='#9467bd'))
if mode == "Joint":
    fig.add_trace(go.Bar(x=df['Age'], y=df['Income_P2'], name='P2 Income', marker_color='#2ca02c'))
fig.add_trace(go.Bar(x=df['Age'], y=df['ISA_Draw'], name='ISA Draw', marker_color='#1f77b4'))
fig.add_trace(go.Scatter(x=df['Age'], y=df['Tax'], name='Tax (HMRC)', line=dict(color='red')))
fig.update_layout(barmode='stack', title="Annual Income Breakdown", xaxis_title="Age (P1)")
st.plotly_chart(fig, use_container_width=True)

st.line_chart(df.set_index("Age")[["Total Wealth"] + (["P1_SIPP", "P2_SIPP", "Joint_ISA"] if mode=="Joint" else ["P1_SIPP", "Joint_ISA"])])
