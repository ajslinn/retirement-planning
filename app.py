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
        growth = st.slider("Growth (%)", 0.0, 15.0, float(st.session_state.defaults["growth"])) / 100
        infl = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults["inflation"])) / 100
        target_spend = st.number_input("Target Spend", value=float(st.session_state.defaults["spend"]))
        st.divider()
        s1_age = st.slider("Step 1 Age", 60, 95, int(st.session_state.defaults["step1_age"]))
        s1_red = st.slider("Step 1 Red %", 0, 50, int(st.session_state.defaults["step1_red"])) / 100
        s2_age = st.slider("Step 2 Age", 60, 95, int(st.session_state.defaults["step2_age"]))
        s2_red = st.slider("Step 2 Red %", 0, 50, int(st.session_state.defaults["step2_red"])) / 100

    st.divider()
    profile_to_save = {
        "mode": mode, "p1_age": p1_age_start, "p2_age": p2_age_start, "p1_isa_bal": p1_isa_init, "p2_isa_bal": p2_isa_init,
        "p1_sipp": p1_sipp_init, "p2_sipp": p2_sipp_init, "growth": growth*100, "inflation": infl*100,
        "p1_sp_amt": p1_sp_amt, "p2_sp_amt": p2_sp_amt, "p1_db": p1_db_in, "p2_db": p2_db_in,
        "p1_lump_age": p1_l_age, "p2_lump_age": p2_l_age, "p1_access_age": p1_acc_age, "p2_access_age": p2_acc_age,
        "spend": target_spend, "step1_age": s1_age, "step1_red": s1_red*100, "step2_age": s2_age, "step2_red": s2_red*100,
        "strategy": strat, "use_ufpls": ufpls, "triple_lock": t_lock
    }
    st.download_button(label="💾 Save Profile", data=json.dumps(profile_to_save, indent=4), file_name="retirement_profile.json", mime="application/json")

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
    if net_needed <= 0 or available_pot <= 0: return 0.0
    tax_factor = 0.75 if use_ufpls else 1.0
    low, high = 0.0, float(available_pot)
    
    # Binary search for exact gross
    for _ in range(30):
        mid = (low + high) / 2
        tax_at_mid = calc_tax(existing_taxable + (mid * tax_factor))
        net_at_mid = mid - (tax_at_mid - calc_tax(existing_taxable))
        if net_at_mid < net_needed: low = mid
        else: high = mid
    return high

p1_db_map, p2_db_map = parse_kv(p1_db_in), parse_kv(p2_db_in)
data_log = []
p1_s, p2_s, p1_i, p2_i = p1_sipp_init, p2_sipp_init, p1_isa_init, p2_isa_init
p1_tfls_pot, p2_tfls_pot = 0.0, 0.0
p1_lsa_taken, p2_lsa_taken = 0.0, 0.0
sp_growth = infl + 0.005 if t_lock else infl

for year in range(41):
    p1_a, p2_a = p1_age_start + year, p2_age_start + year
    goal = target_spend * ((1+infl)**year)
    if p1_a >= s1_age: goal *= (1 - s1_red)
    if p1_a >= s2_age: goal *= (1 - s2_red)
    
    # Trigger TFLS
    if not ufpls:
        if p1_a == p1_l_age and p1_a >= 55:
            ent = min(p1_s * 0.25, LSA_MAX - p1_lsa_taken)
            p1_s -= ent; p1_tfls_pot += ent; p1_lsa_taken += ent
        if mode == "Joint" and p2_a == p2_l_age and p2_a >= 55:
            ent = min(p2_s * 0.25, LSA_MAX - p2_lsa_taken)
            p2_s -= ent; p2_tfls_pot += ent; p2_lsa_taken += ent

    # Base Incomes
    p1_sp = (p1_sp_amt * ((1+sp_growth)**year)) if p1_a >= 67 else 0
    p1_db = sum(v*((1+infl)**year) for k,v in p1_db_map.items() if p1_a >= k)
    p2_sp = (p2_sp_amt * ((1+sp_growth)**year)) if (mode=="Joint" and p2_a >= 67) else 0
    p2_db = sum(v*((1+infl)**year) for k,v in p2_db_map.items() if (mode=="Joint" and p2_a >= k))
    
    p1_base_net = (p1_sp + p1_db) - calc_tax(p1_sp + p1_db)
    p2_base_net = (p2_sp + p2_db) - calc_tax(p2_sp + p2_db)
    
    shortfall = max(0.0, goal - (p1_base_net + p2_base_net))
    p1_sipp_draw, p2_sipp_draw, p1_tfls_draw, p2_tfls_draw, p1_isa_draw, p2_isa_draw = 0,0,0,0,0,0

    # PHASE 1: Efficient SIPP Draws
    if shortfall > 0:
        threshold = BR if strat == "SIPP to Threshold" else PA
        # P1 Efficient
        if p1_a >= p1_acc_age and p1_s > 0:
            max_eff_net = max(0.0, threshold - (p1_sp + p1_db))
            target_net = shortfall if strat == "ISA First" else max_eff_net
            draw = solve_gross_for_net(min(target_net, max_eff_net), p1_sp + p1_db, p1_s, ufpls)
            p1_sipp_draw += draw; p1_s -= draw
        
        # P2 Efficient
        p1_net = (p1_sp + p1_db + p1_sipp_draw) - calc_tax(p1_sp + p1_db + (p1_sipp_draw * (0.75 if ufpls else 1.0)))
        shortfall = max(0.0, goal - (p1_net + p2_base_net))
        if mode == "Joint" and p2_a >= p2_acc_age and p2_s > 0 and shortfall > 0:
            max_eff_net = max(0.0, threshold - (p2_sp + p2_db))
            target_net = shortfall if strat == "ISA First" else max_eff_net
            draw = solve_gross_for_net(min(target_net, max_eff_net), p2_sp + p2_db, p2_s, ufpls)
            p2_sipp_draw += draw; p2_s -= draw

    # PHASE 2: Tax-Free Pots (TFLS & ISA)
    p1_net = (p1_sp + p1_db + p1_sipp_draw) - calc_tax(p1_sp + p1_db + (p1_sipp_draw * (0.75 if ufpls else 1.0)))
    p2_net = (p2_sp + p2_db + p2_sipp_draw) - calc_tax(p2_sp + p2_db + (p2_sipp_draw * (0.75 if ufpls else 1.0)))
    shortfall = max(0.0, goal - (p1_net + p2_net))
    
    for pot in ['tfls', 'isa']:
        if shortfall <= 0: break
        # Partner 1
        rem = p1_tfls_pot if pot == 'tfls' else p1_i
        draw = min(rem, shortfall / 2 if mode == "Joint" else shortfall)
        if pot == 'tfls': p1_tfls_draw += draw; p1_tfls_pot -= draw
        else: p1_isa_draw += draw; p1_i -= draw
        shortfall -= draw
        # Partner 2
        if mode == "Joint" and shortfall > 0:
            rem2 = p2_tfls_pot if pot == 'tfls' else p2_i
            draw2 = min(rem2, shortfall)
            if pot == 'tfls': p2_tfls_draw += draw2; p2_tfls_pot -= draw2
            else: p2_isa_draw += draw2; p2_i -= draw2
            shortfall -= draw2
        # Spillback to P1 if needed
        if shortfall > 0:
            rem = p1_tfls_pot if pot == 'tfls' else p1_i
            draw = min(rem, shortfall)
            if pot == 'tfls': p1_tfls_draw += draw; p1_tfls_pot -= draw
            else: p1_isa_draw += draw; p1_i -= draw
            shortfall -= draw

    # PHASE 3: Emergency SIPP (The "Closer")
    if shortfall > 0:
        if p1_a >= p1_acc_age and p1_s > 0:
            existing = p1_sp + p1_db + (p1_sipp_draw * (0.75 if ufpls else 1.0))
            draw = solve_gross_for_net(shortfall / 2 if mode == "Joint" else shortfall, existing, p1_s, ufpls)
            p1_sipp_draw += draw; p1_s -= draw
        
        # Re-calc shortfall after P1 emergency draw
        p1_net = (p1_sp + p1_db + p1_sipp_draw) - calc_tax(
