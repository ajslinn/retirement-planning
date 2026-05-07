import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Joint Retirement Planner", layout="wide")

# Custom CSS for a professional "FinTech" look
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

# Safety Check: Reset session state if it contains old "single-user" keys
if 'defaults' in st.session_state:
    if "sipp_bal" in st.session_state.defaults:
        del st.session_state['defaults']

# Initialize NEW Joint Defaults
if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "p1_age": 55, "p2_age": 53, "retire_year": 5,
        "isa_bal": 100000, "p1_sipp": 400000, "p2_sipp": 300000,
        "growth": 5.0, "inflation": 2.5,
        "p1_sp_age": 67, "p1_sp_amt": 12548, "p2_sp_age": 67, "p2_sp_amt": 12548,
        "p1_db": "", "p2_db": "",
        "p1_lump_age": 60, "p2_lump_age": 60,
        "spend": 55000, "p1_age_drop": 75, "p1_reduction": 10, "p2_age_drop": 85, "p2_reduction": 10,
        "splurge": ""
    }

# --- 2. USER GUIDE ---
st.title("Joint Retirement Planner Prototype (2026/27)")

with st.expander("📖 JOINT USER GUIDE: Strategic Household Planning", expanded=False):
    st.write("This tool models a couple's retirement. It syncs your ages and optimizes **two** sets of UK tax allowances.")
    st.markdown("---")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Step 1: Household Ages")
        st.write("Enter ages for both partners. The model runs for 45 years from today. Define when the household stops working.")
        st.subheader("Step 2: Asset Management")
        st.write("SIPPs are tracked individually for tax purposes. Use the **Joint ISA** for shared liquid savings.")
    with col_g2:
        st.subheader("Step 3: Spending & Phasing")
        st.write("Enter a combined 'Target Spend'. Use the Phasing sliders to model reduced activity in later life.")
        st.subheader("Step 4: The Joint Waterfall")
        st.info("💡 **Smart Household Bedding:** The engine 'fills' **both** Personal Allowances (£12,570 each) from SIPPs at 0% tax before touching ISAs. This effectively secures £25,140/year tax-free for the household.")
    st.write("**Privacy Note:** Your data never leaves your device. Download your profile in the sidebar to save progress.")

# --- 3. SIDEBAR: TABS FOR INPUTS ---
with st.sidebar:
    st.header("💾 Profile Management")
    uploaded_file = st.file_uploader("Upload '.json' profile", type="json")
    if uploaded_file is not None:
        try:
            st.session_state.defaults.update(json.load(uploaded_file))
            st.success("Household Profile Loaded!")
        except: st.error("Invalid Format")

    tab_p1, tab_p2, tab_joint = st.tabs(["Partner 1", "Partner 2", "Household"])
    
    with tab_p1:
        p1_age_start = st.number_input("P1 Current Age", value=int(st.session_state.defaults["p1_age"]))
        p1_sipp = st.number_input("P1 SIPP Balance (£)", value=float(st.session_state.defaults["p1_sipp"]))
        p1_sp_age = st.slider("P1 State Pension Age", 66, 68, int(st.session_state.defaults["p1_sp_age"]))
        p1_sp_amt = st.number_input("P1 State Pension (£)", value=float(st.session_state.defaults["p1_sp_amt"]))
        p1_db_in = st.text_input("P1 DB Pensions (Age:Amt)", value=st.session_state.defaults["p1_db"])
        p1_lump_age = st.slider("P1 Tax-Free Cash Age", 55, 75, int(st.session_state.defaults["p1_lump_age"]))

    with tab_p2:
        p2_age_start = st.number_input("P2 Current Age", value=int(st.session_state.defaults["p2_age"]))
        p2_sipp = st.number_input("P2 SIPP Balance (£)", value=float(st.session_state.defaults["p2_sipp"]))
        p2_sp_age = st.slider("P2 State Pension Age", 66, 68, int(st.session_state.defaults["p2_sp_age"]))
        p2_sp_amt = st.number_input("P2 State Pension (£)", value=float(st.session_state.defaults["p2_sp_amt"]))
        p2_db_in = st.text_input("P2 DB Pensions (Age:Amt)", value=st.session_state.defaults["p2_db"])
        p2_lump_age = st.slider("P2 Tax-Free Cash Age", 55, 75, int(st.session_state.defaults["p2_lump_age"]))

    with tab_joint:
        retire_in_yrs = st.number_input("Years until Retirement", value=int(st.session_state.defaults["retire_year"]))
        isa_joint = st.number_input("Joint ISA/Cash (£)", value=float(st.session_state.defaults["isa_bal"]))
        growth = st.slider("Growth (%)", 0.0, 10.0, float(st.session_state.defaults["growth"])) / 100
        infl = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults["inflation"])) / 100
        target_spend = st.number_input("Target Household Spend (£)", value=float(st.session_state.defaults["spend"]))
        p1_drop_age = st.slider("Phase 1 Age (P1)", 60, 95, int(st.session_state.defaults["p1_age_drop"]))
        p1_red = st.slider("P1 Reduction (%)", 0, 50, int(st.session_state.defaults["p1_reduction"])) / 100
        p2_drop_age = st.slider("Phase 2 Age (P1)", 70, 100, int(st.session_state.defaults["p2_age_drop"]))
        p2_red = st.slider("P2 Additional Reduction (%)", 0, 50, int(st.session_state.defaults["p2_reduction"])) / 100
        splurge_in = st.text_input("Splurges (P1_Age:Amt)", value=st.session_state.defaults["splurge"])

    # Export Logic
    exp_data = {
        "p1_age": p1_age_start, "p2_age": p2_age_start, "retire_year": retire_in_yrs,
        "isa_bal": isa_joint, "p1_sipp": p1_sipp, "p2_sipp": p2_sipp, "growth": growth*100, "inflation": infl*100,
        "p1_sp_age": p1_sp_age, "p1_sp_amt": p1_sp_amt, "p2_sp_age": p2_sp_age, "p2_sp_amt": p2_sp_amt,
        "p1_db": p1_db_in, "p2_db": p2_db_in, "p1_lump_age": p1_lump_age, "p2_lump_age": p2_lump_age,
        "spend": target_spend, "p1_age_drop": p1_drop_age, "p1_reduction": p1_red*100,
        "p2_age_drop": p2_drop_age, "p2_reduction": p2_red*100, "splurge": splurge_in
    }
    st.download_button("📥 Download Joint Profile", json.dumps(exp_data, indent=4), "household_plan.json")

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

p1_db, p2_db, splurges = parse_kv(p1_db_in), parse_kv(p2_db_in), parse_kv(splurge_in)
data = []
p1_s, p2_s, joint_i = p1_sipp, p2_sipp, isa_joint
p1_lsa, p2_lsa = 0, 0
curr_spend, p1_curr_sp, p2_curr_sp = target_spend, p1_sp_amt, p2_sp_amt

for year in range(46):
    p1_a, p2_a = p1_age_start + year, p2_age_start + year
    # Growth
    p1_s *= (1+growth); p2_s *= (1+growth); joint_i *= (1+growth)

    # Tax Free Cash Lump Sums
    if p1_a == p1_lump_age:
        amt = min(p1_s*0.25, LSA-p1_lsa); p1_s -= amt; joint_i += amt; p1_lsa += amt
    if p2_a == p2_lump_age:
        amt = min(p2_s*0.25, LSA-p2_lsa); p2_s -= amt; joint_i += amt; p2_lsa += amt

    # Determine Goal
    goal = curr_spend if year >= retire_in_yrs else 0
    if p1_a >= p2_drop_age: goal *= (1-p1_red)*(1-p2_red)
    elif p1_a >= p1_drop_age: goal *= (1-p1_red)
    goal += splurges.get(p1_a, 0)

    # 1. Individual Taxable Bases
    p1_fixed = (p1_curr_sp if p1_a >= p1_sp_age else 0) + sum(v*((1+infl)**year) for k,v in p1_db.items() if p1_a >= k)
    p2_fixed = (p2_curr_sp if p2_a >= p2_sp_age else 0) + sum(v*((1+infl)**year) for k,v in p2_db.items() if p2_a >= k)
    
    # 2. Joint Smart PA Bedding
    p1_pa_draw = min(p1_s, max(0, PA-p1_fixed), goal/2 if goal > 0 else 0)
    p2_pa_draw = min(p2_s, max(0, PA-p2_fixed), (goal-p1_pa_draw) if goal > 0 else 0)
    p1_s -= p1_pa_draw; p2_s -= p2_pa_draw
    
    net_needed = max(0, goal - (p1_fixed + p2_fixed + p1_pa_draw + p2_pa_draw))

    # 3. Joint ISA Draw
    draw_isa = min(joint_i, net_needed)
    joint_i -= draw_isa
    final_gap = max(0, net_needed - draw_isa)

    # 4. Final SIPP Draw (Split 50/50 to optimize tax bands)
    p1_tax, p2_tax, p1_sipp_net, p2_sipp_net = 0, 0, 0, 0
    if final_gap > 0:
        def calc_tax(gross, fixed, pa_draw):
            tot = gross + fixed + pa_draw
            pa = max(0, PA - (max(0, tot - TAPER)/2))
            if tot > BR_LIMIT: return (BR_LIMIT-pa)*0.2 + (tot-BR_LIMIT)*0.4
            return max(0, (tot-pa)*0.2)

        half_gap = final_gap / 2
        for p_idx in [1, 2]:
            low, high = half_gap, half_gap * 3
            fixed = p1_fixed if p_idx == 1 else p2_fixed
            pa_d = p1_pa_draw if p_idx == 1 else p2_pa_draw
            pot = p1_s if p_idx == 1 else p2_s
            for _ in range(15):
                mid = (low + high) / 2
                if (mid - calc_tax(mid, fixed, pa_d)) < half_gap: low = mid
                else: high = mid
            
            actual_draw = min(pot, high)
            tax = calc_tax(actual_draw, fixed, pa_d)
            if p_idx == 1: 
                p1_tax = tax; p1_sipp_net = actual_draw - tax; p1_s -= actual_draw
            else: 
                p2_tax = tax; p2_sipp_net = actual_draw - tax; p2_s -= actual_draw

    data.append({
        "Year": year, "P1_Age": p1_a, "P2_Age": p2_a,
        "Total Wealth": round(p1_s + p2_s + joint_i),
        "P1_SIPP": round(p1_s), "P2_SIPP": round(p2_s), "Joint_ISA": round(joint_i),
        "Tax_Paid": round(p1_tax + p2_tax), "Target_Net": round(goal),
        "Income_P1": round(p1_fixed + p1_pa_draw + p1_sipp_net),
        "Income_P2": round(p2_fixed + p2_pa_draw + p2_sipp_net),
        "ISA_Draw": round(draw_isa)
    })
    curr_spend *= (1+infl); p1_curr_sp *= (1+infl); p2_curr_sp *= (1+infl)

df = pd.DataFrame(data)

# --- 5. VISUALS ---
m1, m2, m3 = st.columns(3)
m1.metric("Final Wealth (Year 45)", f"£{df['Total Wealth'].iloc[-1]:,}")
m2.metric("Total Tax Bill", f"£{df['Tax_Paid'].sum():,}")
m3.metric("Household Status", "SECURE" if df['Total Wealth'].iloc[-1] > 0 else "EXHAUSTED")

st.subheader("Household Income Stack vs Combined Tax")
fig = go.Figure()
fig.add_trace(go.Bar(x=df['P1_Age'], y=df['Income_P1'], name='Partner 1 Income', marker_color='#9467bd'))
fig.add_trace(go.Bar(x=df['P1_Age'], y=df['Income_P2'], name='Partner 2 Income', marker_color='#2ca02c'))
fig.add_trace(go.Bar(x=df['P1_Age'], y=df['ISA_Draw'], name='Joint ISA Draw', marker_color='#1f77b4'))
fig.add_trace(go.Scatter(x=df['P1_Age'], y=df['Tax_Paid'], name='Combined Tax', line=dict(color='red', width=2)))
fig.update_layout(barmode='stack', hovermode="x unified", xaxis_title="P1 Age", yaxis_title="£ Amount")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Wealth Depletion")
st.line_chart(df.set_index("P1_Age")[["P1_SIPP", "P2_SIPP", "Joint_ISA", "Total Wealth"]])

with st.expander("📊 View Detailed Yearly Household Data"):
    st.dataframe(df)
