import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Retirement Planner Pro 2026", layout="wide")

# Persistent defaults reflecting 2026/27 UK Tax Year
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
    
    # Improved Uploader: Prevents infinite spinning
    uploaded_file = st.file_uploader("Upload Profile (.json)", type="json")
    if uploaded_file is not None:
        try:
            loaded_data = json.load(uploaded_file)
            # Only update if the data is different from current state
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
        p1_age = st.number_input("P1 Age", value=int(st.session_state.defaults["p1_age"]))
        p1_sipp = st.number_input("P1 SIPP (£)", value=float(st.session_state.defaults["p1_sipp"]))
        p1_sp_amt = st.number_input("P1 State Pension", value=float(st.session_state.defaults["p1_sp_amt"]))
        p1_db_in = st.text_input("P1 DB (Age:Amt)", value=st.session_state.defaults["p1_db"])

    with tabs[1]:
        p2_age = st.number_input("P2 Age", value=int(st.session_state.defaults["p2_age"]))
        p2_sipp = st.number_input("P2 SIPP (£)", value=float(st.session_state.defaults["p2_sipp"]))
        p2_sp_amt = st.number_input("P2 State Pension", value=float(st.session_state.defaults["p2_sp_amt"]))
        p2_db_in = st.text_input("P2 DB (Age:Amt)", value=st.session_state.defaults["p2_db"])

    with tabs[2]:
        isa_bal = st.number_input("Joint ISA (£)", value=float(st.session_state.defaults["isa_bal"]))
        growth = st.slider("Growth (%)", 0.0, 10.0, float(st.session_state.defaults["growth"])) / 100
        infl = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults["inflation"])) / 100
        target = st.number_input("Target Spend (£)", value=float(st.session_state.defaults["spend"]))

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
    pa = max(0, PA - (max(0, income - TAPER)/2))
    if income > BR_LIMIT: return (BR_
