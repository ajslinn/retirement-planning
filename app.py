import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG ---
st.set_page_config(page_title="Retirement Pro", layout="wide")

if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "p1_age": 55, "p2_age": 55, "isa": 43000, "p1_s": 1750000, "p2_s": 18415,
        "growth": 0.05, "infl": 0.025, "sp": 12548, "spend": 80000, "strat": "ISA First"
    }

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    strat = st.selectbox("Strategy", ["ISA First", "SIPP to Threshold"])
    ufpls = st.toggle("Use UFPLS")
    
    p1_s_val = st.number_input("P1 SIPP", value=float(st.session_state.defaults["p1_s"]))
    p2_s_val = st.number_input("P2 SIPP", value=float(st.session_state.defaults["p2_s"]))
    isa_val = st.number_input("ISA", value=float(st.session_state.defaults["isa"]))
    target = st.number_input("Annual Spend Target", value=float(st.session_state.defaults["spend"]))
    growth = st.slider("Growth %", 0, 10, 5) / 100
    infl = st.slider("Inflation %", 0, 5, 2) / 100

# --- 3. THE ENGINE ---
PA = 12570
BR = 50270

def get_tax(income):
    if income <= PA:
        return 0.0
    if income <= BR:
        return (income - PA) * 0.2
    return ((BR - PA) * 0.2) + ((income - BR) * 0.4)

p1_s, p2_s, joint_i = p1_s_val, p2_s_val, isa_val
history = []

for yr in range(41):
    p1_a = 55 + yr
    p1_s *= (1 + growth)
    p2_s *= (1 + growth)
    joint_i *= (1 + growth)
    
    # Simple Logic: Fill Personal Allowance first
    goal = target * ((1 + infl) ** yr)
    p1_sp = 12548 * ((1 + infl) ** yr) if p1_a >= 67 else 0
    
    # Draw logic
    p1_pa_draw = min(p1_s, max(0, PA - p1_sp))
    p1_s -= p1_pa_draw
    
    current_net = p1_sp + p1_pa_draw
    gap = max(0, goal - current_net)
    
    if strat == "ISA First":
        i_draw = min(joint_i, gap)
        joint_i -= i_draw
        gap -= i_draw
        
        p1_taxable_draw = 0
        if gap > 0:
            p1_taxable_draw = min(p1_s, gap / 0.8)
            p1_s -= p1_taxable_draw
    else:
        # SIPP to Threshold
        room = max(0, BR - p1_sp - p1_pa_draw)
        p1_taxable_draw = min(p1_s, room)
        p1_s -= p1_taxable_draw
        tax = get_tax(p1_sp + p1_pa_draw + p1_taxable_draw)
        net_inc = (p1_sp + p1_pa_draw + p1_taxable_draw) - tax
        if net_inc > goal:
            joint_i += (net_inc - goal)
        else:
            i_draw = min(joint_i, goal - net_inc)
            joint_i -= i_draw

    total_w = p1_s + p2_s + joint_i
    history.append({"Age": p1_a, "Wealth": total_w, "SIPP": p1_s, "ISA": joint_i})

# --- 4. DISPLAY ---
df = pd.DataFrame(history)
st.title("Retirement Forecast")
st.line_chart(df.set_index("Age")[["Wealth", "SIPP", "ISA"]])
st.write(df)
