import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="AJS Retirement Ultimate", layout="wide")

if 'defaults' not in st.session_state:
    st.session_state.defaults = {
        "current_age": 55, "retirement_age": 60, "isa_bal": 100000, "sipp_bal": 400000,
        "growth": 5.0, "inflation": 2.5, "sp_age": 67, "sp_amt": 12548,
        "db": "", "lump_sum": True, "lump_age": 60, "splurge": "",
        "spend": 35000, "p1_age": 75, "p1_drop": 10, "p2_age": 85, "p2_drop": 10
    }

# --- 2. USER GUIDE ---
st.title("🚀 AJS Ultimate Retirement Prototype (2026/27)")

with st.expander("📖 USER GUIDE: How to Stress-Test Your Retirement", expanded=False):
    st.write("This tool models the 'Decumulation' phase—turning assets into sustainable income while navigating UK tax laws.")
    st.markdown("---")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Step 1: Assets & Growth")
        st.write("Enter your **current age** and desired **retirement age**. Add the value of your current **ISA**, **cash savings** and total **SIPPs**. The model adjusts these for your selected growth and inflation % automatically.")
        st.subheader("Step 2: Guaranteed Income")
        st.write("Enter your **State Pension Age** and your projected Annual State Pension in todays money. The tool inflation adjusts this automatically. If you will receive any final salary (DB) pensions add these using the format Age:Amount (e.g. 60:10000). You can add multiple values by comma separting the input ")
    with col_g2:
        st.subheader("Step 3: Lifestyle Phases")
        st.write("Model your 'Go-Go' vs 'No-Go' years. Spending drops are compounded to reflect natural lifestyle changes.")
        st.subheader("Step 4: The Red Line")
        st.write("The **Red Tax Line** tracks HMRC's take. If it spikes, you've hit the 40% or 60% tax traps (where Personal Allowance is lost).")
    st.markdown("---")
    st.info("💡 **Smart Allowance Bedding:** Before your State Pension starts, the model 'fills' your Personal Allowance using SIPP funds at 0% tax *before* touching your Tax-Free Pot. This saves your tax-free cash for later.")
    st.write("**Privacy Note:** Use the sidebar to download your profile. Your data never leaves your device.")

# --- 3. SIDEBAR: PROFILE MANAGEMENT ---
with st.sidebar:
    st.header("💾 Profile Management")
    uploaded_file = st.file_uploader("Upload '.json' profile", type="json")
    if uploaded_file is not None:
        try:
            loaded_data = json.load(uploaded_file)
            st.session_state.defaults.update(loaded_data)
            st.success("Profile Data Loaded!")
        except:
            st.error("Invalid File Format")

    st.header("1. Assets & Growth")
    curr_age = st.number_input("Current Age", value=st.session_state.defaults["current_age"])
    ret_age = st.number_input("Retirement Age", value=st.session_state.defaults["retirement_age"])
    isa_bal = st.number_input("Existing ISA/Cash Balance (£)", value=st.session_state.defaults["isa_bal"])
    sipp_bal = st.number_input("SIPP Balance (£)", value=st.session_state.defaults["sipp_bal"])
    growth_rate = st.slider("Investment Growth (%)", 0.0, 10.0, float(st.session_state.defaults["growth"])) / 100
    inflation_rate = st.slider("Inflation (%)", 0.0, 5.0, float(st.session_state.defaults["inflation"])) / 100

    st.header("2. Guaranteed Income")
    sp_age = st.slider("State Pension Age", 66, 68, int(st.session_state.defaults["sp_age"]))
    sp_amt = st.number_input("Annual State Pension (£)", value=st.session_state.defaults["sp_amt"])
    db_input = st.text_input("DB Pensions (Age:Amount)", value=st.session_state.defaults["db"])

    st.header("3. Strategy & Splurges")
    take_lump_sum = st.checkbox("Take 25% Tax-Free Cash?", value=st.session_state.defaults["lump_sum"])
    lump_sum_age = st.slider("Age to take Tax-Free Cash", 55, 75, int(st.session_state.defaults["lump_age"]))
    splurge_input = st.text_input("Splurges (Age:Amount)", value=st.session_state.defaults["splurge"])

    st.header("4. Spending Phases")
    annual_spend = st.number_input("Initial Target Net Spend (£)", value=st.session_state.defaults["spend"])
    p1_age = st.slider("Phase 1 Drop Age", 60, 95, int(st.session_state.defaults["p1_age"]))
    p1_drop = st.slider("Phase 1 Drop (%)", 0, 50, int(st.session_state.defaults["p1_drop"])) / 100
    p2_age = st.slider("Phase 2 Drop Age", 70, 100, int(st.session_state.defaults["p2_age"]))
    p2_drop = st.slider("Phase 2 Drop (%)", 0, 50, int(st.session_state.defaults["p2_drop"])) / 100

    # Save Profile Button
    export_data = {
        "current_age": curr_age, "retirement_age": ret_age, "isa_bal": isa_bal, "sipp_bal": sipp_bal,
        "growth": growth_rate * 100, "inflation": inflation_rate * 100, "sp_age": sp_age, "sp_amt": sp_amt,
        "db": db_input, "lump_sum": take_lump_sum, "lump_age": lump_sum_age, "splurge": splurge_input,
        "spend": annual_spend, "p1_age": p1_age, "p1_drop": p1_drop * 100, "p2_age": p2_age, "p2_drop": p2_drop * 100
    }
    st.download_button(label="📥 Download Current Profile", data=json.dumps(export_data, indent=4), 
                       file_name="my_retirement_plan.json", mime="application/json")

# --- 4. CALCULATION ENGINE ---
PA_BASE, BASIC_LIMIT, TAPER_START, LSA_LIMIT = 12570, 50270, 100000, 268275
BR, HR = 0.20, 0.40

def parse_kv(text):
    d = {}
    if text:
        try:
            for item in text.split(","):
                k, v = item.split(":")
                d[int(k.strip())] = float(v.strip())
        except: pass
    return d

db_schemes, splurges = parse_kv(db_input), parse_kv(splurge_input)
data = []
temp_tf_pot, temp_sipp = isa_bal, sipp_bal
temp_spend, temp_sp, lsa_used = annual_spend, sp_amt, 0

for age in range(curr_age, 101):
    temp_tf_pot *= (1 + growth_rate)
    temp_sipp *= (1 + growth_rate)
    
    if take_lump_sum and age == lump_sum_age:
        lump_amt = min(temp_sipp * 0.25, LSA_LIMIT - lsa_used)
        temp_sipp -= lump_amt
        temp_tf_pot += lump_amt
        lsa_used += lump_amt

    target_net = temp_spend if age >= ret_age else 0
    if age >= p2_age: target_net *= (1 - p1_drop) * (1 - p2_drop)
    elif age >= p1_age: target_net *= (1 - p1_drop)
    target_net += splurges.get(age, 0)
    
    # 1. Guaranteed Income Base
    db_income = sum(amt * ((1 + inflation_rate)**(age - curr_age)) for s_age, amt in db_schemes.items() if age >= s_age)
    sp_rec = temp_sp if age >= sp_age else 0
    fixed_taxable = db_income + sp_rec
    net_needed = max(0, target_net - fixed_taxable)
    
    # --- SMART PA BEDDING LOGIC ---
    # Draw from SIPP first to fill the Personal Allowance at 0% tax
    remaining_pa = max(0, PA_BASE - fixed_taxable)
    pa_fill_draw = min(temp_sipp, remaining_pa, net_needed)
    temp_sipp -= pa_fill_draw
    
    # Update need after the 'free' SIPP draw
    net_after_pa = max(0, net_needed - pa_fill_draw)
    
    # 2. Tax-Free Pot Draw (Bridging the gap)
    draw_tf = min(temp_tf_pot, net_after_pa)
    temp_tf_pot -= draw_tf
    
    # 3. Final Taxable SIPP Draw (The 'Gross-Up' Pass)
    final_gap = max(0, net_after_pa - draw_tf)
    draw_sipp_taxable_gross, tax_paid = 0, 0
    
    if final_gap > 0:
        low, high = final_gap, final_gap * 4
        for _ in range(20):
            mid = (low + high) / 2
            tot_taxable = mid + fixed_taxable + pa_fill_draw # Total taxable income this year
            pa = max(0, PA_BASE - (max(0, tot_taxable - TAPER_START) / 2))
            tax = 0
            if tot_taxable > BASIC_LIMIT:
                tax += (BASIC_LIMIT - pa) * BR + (tot_taxable - BASIC_LIMIT) * HR
            elif tot_taxable > pa:
                tax += (tot_taxable - pa) * BR
            
            # We already used pa_fill_draw, so we only need to cover the tax increase
            if (mid - tax) < final_gap: low = mid
            else: high = mid
        draw_sipp_taxable_gross = min(temp_sipp, high)
        tax_paid = max(0, draw_sipp_taxable_gross - final_gap)
        temp_sipp -= draw_sipp_taxable_gross

    data.append({
        "Age": age, "Total Wealth": round(temp_tf_pot + temp_sipp),
        "Tax-Free Pot": round(temp_tf_pot), "SIPP": round(temp_sipp),
        "DB Income": round(db_income), "State Pension": round(sp_rec),
        "Tax-Free Draw": round(draw_tf), "SIPP (Net)": round(pa_fill_draw + final_gap),
        "Tax Paid": round(tax_paid), "Target Net": round(target_net)
    })
    temp_spend *= (1 + inflation_rate); temp_sp *= (1 + inflation_rate)

df = pd.DataFrame(data)

# --- 5. VISUALS ---
m1, m2, m3 = st.columns(3)
m1.metric("Final Wealth (Age 100)", f"£{df['Total Wealth'].iloc[-1]:,}")
m2.metric("Total Tax Bill", f"£{df['Tax Paid'].sum():,}")
m3.metric("Plan Status", "SECURE" if df['Total Wealth'].iloc[-1] > 0 else "EXHAUSTED", 
          delta_color="normal" if df['Total Wealth'].iloc[-1] > 0 else "inverse")

st.subheader("Annual Income Stack vs Tax Drag")
fig = go.Figure()
fig.add_trace(go.Bar(x=df['Age'], y=df['DB Income'], name='DB Pension', marker_color='#9467bd'))
fig.add_trace(go.Bar(x=df['Age'], y=df['State Pension'], name='State Pension', marker_color='#2ca02c'))
fig.add_trace(go.Bar(x=df['Age'], y=df['Tax-Free Draw'], name='Tax-Free Cash Draw', marker_color='#1f77b4'))
fig.add_trace(go.Bar(x=df['Age'], y=df['SIPP (Net)'], name='SIPP (Net)', marker_color='#ff7f0e'))
fig.add_trace(go.Scatter(x=df['Age'], y=df['Tax Paid'], name='Tax (HMRC)', line=dict(color='#d62728', width=2)))
fig.update_layout(barmode='stack', hovermode="x unified", xaxis_title="Age", yaxis_title="£ Amount")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Asset Depletion")
st.line_chart(df.set_index("Age")[["Tax-Free Pot", "SIPP", "Total Wealth"]])

with st.expander("📊 View Detailed Yearly Data Table"):
    st.dataframe(df)
    st.download_button(label="📩 Download Table as CSV", data=df.to_csv(index=False).encode('utf-8'), 
                       file_name='retirement_projection.csv', mime='text/csv')
