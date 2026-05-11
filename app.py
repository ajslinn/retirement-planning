import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Retirement Planner Pro", layout="wide")

# Default settings with safety keys for older profile compatibility
if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "mode": "Joint", "p1_age": 55, "p2_age": 55, "retire_year": 1,
        "isa_bal": 43000, "p1_sipp": 1750000, "p2_sipp": 18415,
        "growth": 5.0, "inflation": 2.5,
        "p1_sp_amt": 12548, "p2_sp_amt": 12548,
        "p1_db": "", "p2_db": "60:2336, 65:5633, 67:6292", 
        "p1_lump_age": 57, "p2_lump_age": 57,
        "p1_access_age": 57, "p2_access_age": 57, 
        "spend": 80000, "p1_age_drop": 75, "p1_reduction": 20, 
        "strategy": "ISA First", "use_ufpls": False, "triple_lock": True
    }

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("💾 Profile Management")
    uploaded_file = st.file_uploader("Upload '.json' profile", type="json")
    if uploaded_file is not None:
        try:
            loaded_data = json.load(uploaded_file)
            # Safe update to prevent infinite loops on mismatching keys
            for key, value in loaded_data.items():
                st.session_state.defaults[key] = value
            st.rerun()
        except Exception as e: 
            st.error(f"Error loading profile: {e}")

    st.header("⚙️ Global Strategy")
    mode = st.radio("Mode", ["Single", "Joint"], index=0 if st.session_state.defaults.get("mode") == "Single" else 1)
    strat = st.selectbox("Strategy", ["ISA First", "SIPP to Threshold"], 
                         index=0 if st.session_state.defaults.get("strategy") == "ISA First" else 1)
    ufpls = st.toggle("Use UFPLS (25% Tax-Free Trickle)", value=st.session_state.defaults.get("use_ufpls", False))
    t_lock = st.toggle("Triple Lock (+0.5% vs Infl)", value=st.session_state.defaults.get("triple_lock", True))

    tabs = st.tabs(["Partner 1", "Partner 2", "Household"]) if mode == "Joint" else st.tabs(["User", "Household"])
    
    with tabs[0]:
        p1_age_start = st.number_input("P1 Current Age", value=int(st.session_state.defaults.get("p1_age", 55)))
        p1_acc_age = st.number_input("P1 SIPP Access Age (NMPA)", 50, 75, int(st.session_state.defaults.get("p1_access_age", 57)))
        p1_l_age = st.number_input("P1 Lump Sum Age", 50, 75, int(st.session_state.defaults.get("p1_lump_age", 57)))
        st.divider()
        p1_sipp_init = st.number_input("P1 SIPP Balance (£)", value=float(st.session_state.defaults.get("p1_sipp", 0)))
        p1_sp_amt = st.number_input("P1 State Pension (£)", value=float(st.session_state.defaults.get("p1_sp_amt", 12548)))
        p1_db_in = st.text_input("P1 DB (Age:Amt)", value=st.session_state.defaults.get("p1_db", ""))

    if mode == "Joint":
        with tabs[1]:
            p2_age_start = st.number_input("P2 Current Age", value=int(st.session_state.defaults.get("p2_age", 55)))
            p2_acc_age = st.number_input("P2 SIPP Access Age (NMPA)", 50, 75, int(st.session_state.defaults.get("p2_access_age", 57)))
            p2_l_age = st.number_input("P2 Lump Sum Age", 50, 75, int(st.session_state.defaults.get("p2_lump_age", 57)))
            st.divider()
            p2_sipp_init = st.number_input("P2 SIPP Balance (£)", value=float(st.session_state.defaults.get("p2_sipp", 0)))
            p2_sp_amt = st.number_input("P2 State Pension (£)", value=float(st.session_state.defaults.get("p2_sp_amt", 12548)))
            p2_db_in = st.text_input("P2 DB (Age:Amt)", value=st.session_state.defaults.get("p2_db", ""))
    else: p2_age_start, p2_sipp_init, p2_sp_amt, p2_db_in, p2_acc_age, p2_l_age = 0, 0, 0, "", 57, 57

    with tabs[-1]:
        isa_joint_init = st.number_input("Joint ISA/Savings (£)", value=float(st.session_state.defaults.get("isa_bal", 0)))
        growth = st.slider("Growth (%)", 0.0, 10.0, float(st.session_state.defaults.get("growth", 5.0))) / 100
        infl = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults.get("inflation", 2.5))) / 100
        target_spend = st.number_input("Target Annual Spend (£)", value=float(st.session_state.defaults.get("spend", 80000)))
        p1_drop_age = st.slider("Step-Down Age", 60, 95, int(st.session_state.defaults.get("p1_age_drop", 75)))
        p1_red = st.slider("Reduction %", 0, 50, int(st.session_state.defaults.get("p1_reduction", 20))) / 100

    # Save logic for exporting
    current_params = {
        "mode": mode, "p1_age": p1_age_start, "p2_age": p2_age_start,
        "isa_bal": isa_joint_init, "p1_sipp": p1_sipp_init, "p2_sipp": p2_sipp_init,
        "growth": growth*100, "inflation": infl*100, "p1_sp_amt": p1_sp_amt, "p2_sp_amt": p2_sp_amt,
        "p1_db": p1_db_in, "p2_db": p2_db_in, "p1_lump_age": p1_l_age, "p2_lump_age": p2_l_age,
        "p1_access_age": p1_acc_age, "p2_access_age": p2_acc_age,
        "spend": target_spend, "p1_age_drop": p1_drop_age, "p1_reduction": p1_red*100,
        "strategy": strat, "use_ufpls": ufpls, "triple_lock": t_lock
    }
    st.download_button("💾 Save Profile (JSON)", data=json.dumps(current_params, indent=4), file_name="retirement_profile.json", mime="application/json")

# --- 3. CALCULATION ENGINE ---
PA, BR, TAPER, LSA = 12570, 50270, 100000, 268275

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
p1_lsa, p2_lsa, sp_growth = 0, 0, infl + 0.005 if t_lock else infl

for year in range(41):
    p1_a, p2_a = p1_age_start + year, p2_age_start + year
    p1_s *= (1+growth); p2_s *= (1+growth); joint_i *= (1+growth)
    
    if not ufpls:
        if p1_a == p1_l_age and p1_a >= p1_acc_age:
            amt = min(p1_s*0.25, LSA-p1_lsa); p1_s -= amt; joint_i += amt; p1_lsa += amt
        if mode == "Joint" and p2_a == p2_l_age and p2_a >= p2_acc_age:
            amt = min(p2_s*0.25, LSA-p2_lsa); p2_s -= amt; joint_i += amt; p2_lsa += amt

    goal = target_spend * ((1+infl)**year)
    if p1_a >= p1_drop_age: goal *= (1 - p1_red)

    p1_sp = (p1_sp_amt * ((1+sp_growth)**year)) if p1_a >= 67 else 0
    p1_db = sum(v*((1+infl)**year) for k,v in p1_db_map.items() if p1_a >= k)
    p2_sp = (p2_sp_amt * ((1+sp_growth)**year)) if (mode=="Joint" and p2_a >= 67) else 0
    p2_db = sum(v*((1+infl)**year) for k,v in p2_db_map.items() if p2_a >= k)

    p1_pa_draw = min(p1_s, max(0, PA - (p1_sp + p1_db)) / (0.75 if ufpls else 1.0)) if p1_a >= p1_acc_age else 0
    p1_s -= p1_pa_draw
    p2_pa_draw = min(p2_s, max(0, PA - (p2_sp + p2_db)) / (0.75 if ufpls else 1.0)) if (mode=="Joint" and p2_a >= p2_acc_age) else 0
    p2_s -= p2_pa_draw

    net_fixed = (p1_sp + p1_db + p1_pa_draw) + (p2_sp + p2_db + p2_pa_draw)
    gap, p1_extra, p2_extra = max(0, goal - net_fixed), 0, 0

    if strat == "SIPP to Threshold":
        for p_idx in ([1, 2] if mode=="Joint" else [1]):
            acc, age = (p1_acc_age, p1_a) if p_idx == 1 else (p2_acc_age, p2_a)
            if age >= acc:
                base = (p1_sp + p1_db + p1_pa_draw*0.75 if ufpls else p1_pa_draw) if p_idx==1 else (p2_sp + p2_db + p2_pa_draw*0.75 if ufpls else p2_pa_draw)
                gross = min((p1_s if p_idx==1 else p2_s), (BR - base) / (0.75 if ufpls else 1.0))
                tax = calc_tax(base + (gross*0.75 if ufpls else gross)) - calc_tax(base)
                if p_idx==1: p1_extra = gross; p1_s -= gross
                else: p2_extra = gross; p2_s -= gross
                net_fixed += (gross - tax)
        isa_draw_val = max(0, goal - net_fixed); joint_i -= isa_draw_val
    else:
        isa_draw_val = min(joint_i, gap); joint_i -= isa_draw_val; gap -= isa_draw_val
        if gap > 0 and p1_a >= p1_acc_age:
            p1_extra = min(p1_s, gap / 0.8); p1_s -= p1_extra

    p1_total_inc = p1_sp + p1_db + (p1_pa_draw + p1_extra) * (0.75 if ufpls else 1.0)
    p2_total_inc = p2_sp + p2_db + (p2_pa_draw + p2_extra) * (0.75 if ufpls else 1.0)

    data_log.append({
        "P1 Age": p1_a, "P1 SP": round(p1_sp), "P1 DB": round(p1_db), "P1 SIPP Draw": round(p1_pa_draw + p1_extra), 
        "P1 SIPP Balance": round(p1_s), "P1 Tax": round(calc_tax(p1_total_inc)),
        "P2 Age": p2_a if mode=="Joint" else "-", 
        "P2 SP": round(p2_sp) if mode=="Joint" else 0, 
        "P2 DB": round(p2_db) if mode=="Joint" else 0, 
        "P2 SIPP Draw": round(p2_pa_draw + p2_extra) if mode=="Joint" else 0, 
        "P2 SIPP Balance": round(p2_s) if mode=="Joint" else 0, 
        "P2 Tax": round(calc_tax(p2_total_inc)) if mode=="Joint" else 0,
        "ISA Draw": round(isa_draw_val), "ISA Balance": round(joint_i),
        "Total Wealth": round(p1_s + p2_s + joint_i)
    })

df = pd.DataFrame(data_log)

# --- 4. DISPLAY ---
st.title(f"Retirement Forecast: {strat}")

# Income Chart
fig_inc = go.Figure(data=[
    go.Bar(x=df['P1 Age'], y=df['P1 SP'], name="P1 State Pension", marker_color="#4A148C"),
    go.Bar(x=df['P1 Age'], y=df['P1 DB'], name="P1 DB Pension", marker_color="#7B1FA2"),
    go.Bar(x=df['P1 Age'], y=df['P1 SIPP Draw'], name="P1 SIPP Draw", marker_color="#9C27B0"),
    go.Bar(x=df['P1 Age'], y=df['P2 SP'], name="P2 State Pension", marker_color="#1B5E20"),
    go.Bar(x=df['P1 Age'], y=df['P2 DB'], name="P2 DB Pension", marker_color="#388E3C"),
    go.Bar(x=df['P1 Age'], y=df['P2 SIPP Draw'], name="P2 SIPP Draw", marker_color="#4CAF50"),
    go.Bar(x=df['P1 Age'], y=df['ISA Draw'], name="ISA Draw", marker_color="#1F77B4"),
    go.Scatter(x=df['P1 Age'], y=df['P1 Tax'] + df['P2 Tax'], name="Total Tax", line=dict(color='red', width=2))
])
fig_inc.update_layout(barmode='stack', hovermode="x unified", title="Income Sources Over Time")
st.plotly_chart(fig_inc, use_container_width=True)

# Wealth Chart
st.subheader("Asset Depletion (Total Wealth)")
st.line_chart(df.set_index("P1 Age")["Total Wealth"])

# Final Structured Table
st.subheader("Yearly Breakdown")
final_cols = ["P1 Age", "P1 SP", "P1 DB", "P1 SIPP Draw", "P1 SIPP Balance", "P1 Tax", 
              "P2 Age", "P2 SP", "P2 DB", "P2 SIPP Draw", "P2 SIPP Balance", "P2 Tax", 
              "ISA Draw", "ISA Balance", "Total Wealth"]

if mode == "Single":
    final_cols = [c for c in final_cols if "P2" not in c]

st.dataframe(df[final_cols], use_container_width=True)
st.download_button("📥 Export Results (CSV)", df[final_cols].to_csv(index=False), "retirement_plan.csv", "text/csv")
