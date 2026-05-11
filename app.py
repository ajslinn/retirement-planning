import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

# --- 1. CONFIG ---
st.set_page_config(page_title="Retirement Debugger", layout="wide")

if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "mode": "Joint", "p1_age": 55, "p2_age": 55, "isa_bal": 580000.0,
        "p1_sipp": 1200000.0, "p2_sipp": 0.0, "growth": 5.0, "inflation": 2.5,
        "p1_sp_amt": 12548.0, "p2_sp_amt": 12548.0, "p1_db": "", "p2_db": "57:17000",
        "spend": 65000.0, "step1_age": 75, "step1_red": 20.0, "strategy": "ISA First"
    }

# --- 2. CALC ENGINE ---
PA, BR, TAPER = 12570, 50270, 100000

def calc_tax(income):
    eff_pa = max(0, PA - (max(0, income - TAPER) / 2))
    if income <= eff_pa: return 0.0
    if income <= BR: return (income - eff_pa) * 0.2
    return ((BR - eff_pa) * 0.2) + ((income - BR) * 0.4)

# Data generation
data_log = []
p1_s, joint_i = 1200000.0, 580000.0 # From your JSON
growth, infl = 0.05, 0.025

for year in range(41):
    age = 55 + year
    p1_s *= (1 + growth)
    joint_i *= (1 + growth)
    
    # Income logic
    sp = (12548 * ((1.03)**year)) if age >= 67 else 0 # 3% lock approx
    db = (17000 * ((1+infl)**year)) if age >= 57 else 0
    
    # SIPP Draw (ISA First Strategy)
    # Fill Personal Allowance first
    pa_draw = max(0, min(p1_s, PA - (sp + db)))
    p1_s -= pa_draw
    
    # Calculate Tax on everything but ISA
    taxable_inc = sp + db + pa_draw
    tax_bill = calc_tax(taxable_inc)
    
    # Goal coverage from ISA
    goal = 65000 * ((1+infl)**year)
    if age >= 75: goal *= 0.8
    
    net_fixed = taxable_inc - tax_bill
    isa_draw = max(0, goal - net_fixed)
    joint_i -= isa_draw

    data_log.append({
        "Age": age,
        "Fixed Income": round(sp + db),
        "SIPP Draw": round(pa_draw),
        "ISA Draw": round(isa_draw),
        "TAX_DATA": round(tax_bill) # Explicitly named for debugging
    })

df = pd.DataFrame(data_log)

# --- 3. DUAL AXIS CHART ---
st.subheader("Income (Bars) vs Tax (Red Line)")

# Create figure with secondary y-axis
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Add Bars (Primary Y-Axis)
fig.add_trace(go.Bar(x=df['Age'], y=df['Fixed Income'], name="Fixed Pension"), secondary_y=False)
fig.add_trace(go.Bar(x=df['Age'], y=df['SIPP Draw'], name="SIPP Draw"), secondary_y=False)
fig.add_trace(go.Bar(x=df['Age'], y=df['ISA Draw'], name="ISA Draw"), secondary_y=False)

# Add Tax Line (Secondary Y-Axis - makes it much easier to see)
fig.add_trace(
    go.Scatter(
        x=df['Age'], 
        y=df['TAX_DATA'], 
        name="Annual Tax Bill",
        line=dict(color='red', width=4),
        mode='lines+markers'
    ),
    secondary_y=True
)

fig.update_layout(
    barmode='stack',
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

# Set y-axis titles
fig.update_yaxes(title_text="Income / Spend (£)", secondary_y=False)
fig.update_yaxes(title_text="Total Tax (£)", secondary_y=True, color="red")

st.plotly_chart(fig, use_container_width=True)

# --- 4. DEBUG TABLE ---
with st.expander("🐞 Click here to verify the Raw Data"):
    st.write("If 'TAX_DATA' shows numbers here, but not on the chart, Plotly is the issue.")
    st.dataframe(df[["Age", "TAX_DATA"]].T)
