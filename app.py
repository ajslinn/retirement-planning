import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Retirement Planner Pro", layout="wide")

if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "mode": "Joint", "p1_age": 55, "p2_age": 55, 
        "p1_isa_bal": 290000.0, "p2_isa_bal": 290000.0,
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
        try:
            loaded_data = json.load(uploaded_file)
            if "isa_bal" in loaded_data and "p1_isa_bal" not in loaded_data:
                loaded_data["p1_isa_bal"] = loaded_data["isa_bal"] / 2
                loaded_data["p2_isa_bal"] = loaded_data["isa_bal"] / 2
            st.session_state.defaults.update(loaded_data)
        except Exception as e:
            st.error(f"Error loading file: {e}")

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
        p1_isa_init = st.number_input("P1 ISA Balance", value=float(st.session_state.defaults.get("p1_isa_bal", 0)))
        p1_sp_amt = st.number_input("P1 State Pension", value=float(st.session_state.defaults["p1_sp_amt"]))
        p1_db_in = st.text_input("P1 DB (Age:Amt)", value=st.session_state.defaults["p1_db"])

    if mode == "Joint":
        with tabs[1]:
            p2_age_start = st.number_input("P2 Age", value=int(st.session_state.defaults["p2_age"]))
            p2_acc_age = st.number_input("P2 SIPP Access Age", value=int(st.session_state.defaults["p2_access_age"]))
            p2_l_age = st.number_input("P2 Lump Sum Age", value=int(st.session_state.defaults["p2_lump_age"]))
            p2_sipp_init = st.number_input("P2 SIPP Balance", value=float(st.session_state.defaults["p2_sipp"]))
            p2_isa_init = st.number_input("P2 ISA Balance", value=float(st.session_state.defaults.get("p2_isa_bal", 0)))
            p2_sp_amt = st.number_input("P2 State Pension", value=float(st.session_state.defaults["p2_sp_amt"]))
            p2_db_in = st.text_input("P2 DB (Age:Amt)", value=st.session_state.defaults["p2_db"])
    else:
        p2_age_start, p2_acc_age, p2_l_age, p2_sipp_init, p2_isa_init, p2_sp_amt, p2_db_in = 0, 0, 0, 0, 0, 0, ""

    with tabs[-1]:
        growth = st.slider("Growth (%)", 0.0, 10.0, float(st.session_state.defaults["growth"])) / 100
        infl = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults["inflation"])) / 100
        target_spend = st.number_input("Target Spend", value=float(st.session_state.defaults["spend"]))
        st.divider()
        s1_age = st.slider("Step 1 Age", 60, 95, int(st.session_state.defaults["step1_age"]))
        s1_red = st.slider("Step 1 Red %", 0, 50, int(st.session_state.defaults["step1_red"])) / 100
        s2_age = st.slider("Step 2 Age", 60, 95, int(st.session_state.defaults["step2_age"]))
        s2_red = st.slider("Step 2 Red %", 0, 50, int(st.session_state.defaults["step2_red"])) / 100

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

def solve_gross_for_net(net_needed, existing_taxable, available_pot, use_ufpls):
    """Calculates the gross SIPP withdrawal needed to reach a net cash target."""
    if net_needed <= 0 or available_pot <= 0: return 0
    
    tax_multiplier = 0.75 if use_ufpls else 1.0
    low, high = 0.0, float(available_pot)
    
    # Quick check: if emptying the pot doesn't meet the need
    total_tax_at_max = calc_tax(existing_taxable + available_pot * tax_multiplier)
    base_tax = calc_tax(existing_taxable)
    if (available_pot - (total_tax_at_max - base_tax)) <= net_needed:
        return available_pot

    for _ in range(25): # Binary search for precision
        mid = (low + high) / 2
        tax_at_mid = calc_tax(existing_taxable + mid * tax_multiplier)
        net_yield = mid - (tax_at_mid - base_tax)
        if net_yield < net_needed: low = mid
        else: high = mid
    return high

p1_db_map, p2_db_map = parse_kv(p1_db_in), parse_kv(p2_db_in)
data_log = []
p1_s, p2_s, p1_i, p2_i = p1_sipp_init, p2_sipp_init, p1_isa_init, p2_isa_init
p1_tfls_pot, p2_tfls_pot = 0, 0
p1_lsa_taken, p2_lsa_taken = 0, 0
sp_growth = infl + 0.005 if t_lock else infl

for year in range(41):
    p1_a, p2_a = p1_age_start + year, p2_age_start + year
    goal = target_spend * ((1+infl)**year)
    if p1_a >= s1_age: goal *= (1 - s1_red)
    if p1_a >= s2_age: goal *= (1 - s2_red)
    
    # Move SIPP to TFLS Pot on Lump Sum Age
    if not ufpls:
        if p1_a == p1_l_age and p1_a >= 55:
            ent = min(p1_s * 0.25, LSA_MAX - p1_lsa_taken)
            p1_s -= ent; p1_tfls_pot += ent; p1_lsa_taken += ent
        if mode == "Joint" and p2_a == p2_l_age and p2_a >= 55:
            ent = min(p2_s * 0.25, LSA_MAX - p2_lsa_taken)
            p2_s -= ent; p2_tfls_pot += ent; p2_lsa_taken += ent

    # Fixed Incomes
    p1_sp = (p1_sp_amt * ((1+sp_growth)**year)) if p1_a >= 67 else 0
    p1_db = sum(v*((1+infl)**year) for k,v in p1_db_map.items() if p1_a >= k)
    p2_sp = (p2_sp_amt * ((1+sp_growth)**year)) if (mode=="Joint" and p2_a >= 67) else 0
    p2_db = sum(v*((1+infl)**year) for k,v in p2_db_map.items() if p2_a >= k)
    
    p1_tax_fixed = calc_tax(p1_sp + p1_db)
    p2_tax_fixed = calc_tax(p2_sp + p2_db)
    
    current_net = (p1_sp + p1_db - p1_tax_fixed) + (p2_sp + p2_db - p2_tax_fixed)
    shortfall = max(0, goal - current_net)
    
    p1_sipp_draw, p2_sipp_draw, p1_tfls_draw, p2_tfls_draw, p1_isa_draw, p2_isa_draw = 0,0,0,0,0,0

    # WATERFALL START
    # 1. Tax Efficient SIPP (Only if SIPP to Threshold is selected OR if we have shortfall)
    if (p1_a >= p1_acc_age or (mode=="Joint" and p2_a >= p2_acc_age)):
        limit = BR if strat == "SIPP to Threshold" else PA
        
        # P1 efficient draw
        if p1_a >= p1_acc_age and p1_s > 0:
            max_eff = max(0, limit - (p1_sp + p1_db))
            # If "SIPP to Threshold", take the max_eff. If "ISA First", only take what covers shortfall.
            needed = shortfall if strat == "ISA First" else max_eff
            draw = solve_gross_for_net(min(needed, max_eff), p1_sp + p1_db, p1_s, ufpls)
            p1_sipp_draw += draw; p1_s -= draw
            
        # P2 efficient draw
        current_net_calc = (p1_sp+p1_db+p1_sipp_draw-calc_tax(p1_sp+p1_db+p1_sipp_draw*(0.75 if ufpls else 1))) + (p2_sp+p2_db-p2_tax_fixed)
        shortfall = max(0, goal - current_net_calc)
        
        if mode == "Joint" and p2_a >= p2_acc_age and p2_s > 0:
            max_eff = max(0, limit - (p2_sp + p2_db))
            needed = shortfall if strat == "ISA First" else max_eff
            draw = solve_gross_for_net(min(needed, max_eff), p2_sp + p2_db, p2_s, ufpls)
            p2_sipp_draw += draw; p2_s -= draw

    # Recalculate Shortfall
    p1_net = (p1_sp+p1_db+p1_sipp_draw) - calc_tax(p1_sp+p1_db+p1_sipp_draw*(0.75 if ufpls else 1))
    p2_net = (p2_sp+p2_db+p2_sipp_draw) - calc_tax(p2_sp+p2_db+p2_sipp_draw*(0.75 if ufpls else 1))
    shortfall = max(0, goal - (p1_net + p2_net))

    # 2. TFLS Draw
    if shortfall > 0:
        d1 = min(p1_tfls_pot, shortfall / 2 if mode == "Joint" else shortfall)
        p1_tfls_draw += d1; p1_tfls_pot -= d1; shortfall -= d1
        if mode == "Joint":
            d2 = min(p2_tfls_pot, shortfall)
            p2_tfls_draw += d2; p2_tfls_pot -= d2; shortfall -= d2
            # Cleanup if P2 had more but P1 didn't have enough for their half
            d1_extra = min(p1_tfls_pot, shortfall)
            p1_tfls_draw += d1_extra; p1_tfls_pot -= d1_extra; shortfall -= d1_extra

    # 3. ISA Draw
    if shortfall > 0:
        d1 = min(p1_i, shortfall / 2 if mode == "Joint" else shortfall)
        p1_isa_draw += d1; p1_i -= d1; shortfall -= d1
        if mode == "Joint":
            d2 = min(p2_i, shortfall)
            p2_isa_draw += d2; p2_i -= d2; shortfall -= d2
            d1_extra = min(p1_i, shortfall)
            p1_isa_draw += d1_extra; p1_i -= d1_extra; shortfall -= d1_extra

    # 4. Final SIPP Draw (Emergency cover for remaining shortfall, potentially at higher tax)
    if shortfall > 0:
        if p1_a >= p1_acc_age and p1_s > 0:
            existing = p1_sp + p1_db + p1_sipp_draw * (0.75 if ufpls else 1)
            draw = solve_gross_for_net(shortfall / 2 if mode == "Joint" else shortfall, existing, p1_s, ufpls)
            p1_sipp_draw += draw; p1_s -= draw
            # Update shortfall
            p1_net_new = (p1_sp+p1_db+p1_sipp_draw) - calc_tax(p1_sp+p1_db+p1_sipp_draw*(0.75 if ufpls else 1))
            shortfall = max(0, goal - (p1_net_new + p2_net + p1_tfls_draw + p2_tfls_draw + p1_isa_draw + p2_isa_draw))

        if mode == "Joint" and p2_a >= p2_acc_age and p2_s > 0 and shortfall > 0:
            existing = p2_sp + p2_db + p2_sipp_draw * (0.75 if ufpls else 1)
            draw = solve_gross_for_net(shortfall, existing, p2_s, ufpls)
            p2_sipp_draw += draw; p2_s -= draw
            # Final check if P1 needs to cover more
            p2_net_new = (p2_sp+p2_db+p2_sipp_draw) - calc_tax(p2_sp+p2_db+p2_sipp_draw*(0.75 if ufpls else 1))
            shortfall = max(0, goal - (p1_net_new + p2_net_new + p1_tfls_draw + p2_tfls_draw + p1_isa_draw + p2_isa_draw))
            if shortfall > 0 and p1_a >= p1_acc_age and p1_s > 0:
                existing = p1_sp + p1_db + p1_sipp_draw * (0.75 if ufpls else 1)
                draw = solve_gross_for_net(shortfall, existing, p1_s, ufpls)
                p1_sipp_draw += draw; p1_s -= draw

    p1_tax_final = calc_tax(p1_sp + p1_db + p1_sipp_draw * (0.75 if ufpls else 1))
    p2_tax_final = calc_tax(p2_sp + p2_db + p2_sipp_draw * (0.75 if ufpls else 1))

    data_log.append({
        "P1 Age": p1_a, "P1 SP": round(p1_sp), "P1 DB": round(p1_db), "P1 SIPP Draw": round(p1_sipp_draw), "P1 TFLS Draw": round(p1_tfls_draw), "P1 ISA Draw": round(p1_isa_draw), "P1 Tax": round(p1_tax_final), "P1 SIPP Bal": round(p1_s), "P1 TFLS Pot": round(p1_tfls_pot), "P1 ISA Bal": round(p1_i),
        "P2 Age": p2_a, "P2 SP": round(p2_sp), "P2 DB": round(p2_db), "P2 SIPP Draw": round(p2_sipp_draw), "P2 TFLS Draw": round(p2_tfls_draw), "P2 ISA Draw": round(p2_isa_draw), "P2 Tax": round(p2_tax_final), "P2 SIPP Bal": round(p2_s), "P2 TFLS Pot": round(p2_tfls_pot), "P2 ISA Bal": round(p2_i),
        "Total Tax": round(p1_tax_final + p2_tax_final), "Total Wealth": round(p1_s + p2_s + p1_i + p2_i + p1_tfls_pot + p2_tfls_pot), "Spending Goal": round(goal)
    })
    
    # Apply Growth
    p1_s *= (1+growth); p2_s *= (1+growth); p1_i *= (1+growth); p2_i *= (1+growth); p1_tfls_pot *= (1+growth); p2_tfls_pot *= (1+growth)

df = pd.DataFrame(data_log)

# --- 4. VISUALS ---
st.subheader("Annual Income Mix & Tax")
fig1 = go.Figure()
stack = [
    ("P1 SP", "#4A148C"), ("P2 SP", "#1B5E20"), ("P1 DB", "#6A1B9A"), ("P2 DB", "#2E7D32"),
    ("P1 SIPP Draw", "#9C27B0"), ("P2 SIPP Draw", "#4CAF50"), 
    ("P1 TFLS Draw", "#E91E63"), ("P2 TFLS Draw", "#F06292"),
    ("P1 ISA Draw", "#1F77B4"), ("P2 ISA Draw", "#64B5F6")
]
for label, color in stack:
    if label in df.columns:
        fig1.add_trace(go.Bar(x=df['P1 Age'], y=df[label], name=label, marker_color=color))

fig1.add_trace(go.Scatter(x=df['P1 Age'], y=df['Spending Goal'], name="Spending Goal", line=dict(color='black', width=2, dash='dash')))
fig1.add_trace(go.Scatter(x=df['P1 Age'], y=df['Total Tax'], name="Tax Paid", line=dict(color='red', width=3)))
fig1.update_layout(barmode='stack', hovermode="x unified", legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig1, use_container_width=True)

st.subheader("Asset Value Over Time")
fig2 = go.Figure()
assets = [
    ("P1 SIPP Bal", "#9C27B0"), ("P2 SIPP Bal", "#4CAF50"), 
    ("P1 TFLS Pot", "#E91E63"), ("P2 TFLS Pot", "#F06292"),
    ("P1 ISA Bal", "#1F77B4"), ("P2 ISA Bal", "#64B5F6")
]
for label, color in assets:
    if label in df.columns:
        fig2.add_trace(go.Bar(x=df['P1 Age'], y=df[label], name=label, marker_color=color))
fig2.update_layout(barmode='stack', hovermode="x unified", legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig2, use_container_width=True)

st.subheader("Yearly Breakdown")
st.dataframe(df, use_container_width=True)
