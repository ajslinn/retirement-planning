class RetirementModel:
    def __init__(self, current_isa, current_sipp, annual_spend, growth_rate, inflation):
        self.isa = current_isa
        self.sipp = current_sipp
        self.annual_spend = annual_spend
        self.growth = growth_rate
        self.inflation = inflation

    def calculate_year(self):
        # Grow assets
        self.isa *= (1 + self.growth)
        self.sipp *= (1 + self.growth)
        
        # Withdraw strategy: ISA first
        if self.isa >= self.annual_spend:
            self.isa -= self.annual_spend
        else:
            remaining = self.annual_spend - self.isa
            self.isa = 0
            self.sipp -= remaining # Tax logic would be applied here
            
        # Adjust spend for next year
        self.annual_spend *= (1 + self.inflation)

import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="AJS Retirement Prototype", layout="wide")
st.title("🚀 AJS 2026 Retirement Calculator")
st.markdown("Automated wealth modeling based on your 2026 spreadsheet logic.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Current Financials")
current_age = st.sidebar.number_input("Current Age", value=55)
retirement_age = st.sidebar.number_input("Retirement Age", value=60)
isa_bal = st.sidebar.number_input("Total ISA Balance (£)", value=100000)
sipp_bal = st.sidebar.number_input("Total SIPP Balance (£)", value=400000)

st.sidebar.header("Assumptions")
annual_spend = st.sidebar.slider("Desired Annual Spend (£)", 20000, 100000, 35000)
growth_rate = st.sidebar.slider("Investment Growth (%)", 0.0, 10.0, 5.0) / 100
inflation_rate = st.sidebar.slider("Inflation (%)", 0.0, 5.0, 2.5) / 100

# --- CALCULATION ENGINE ---
data = []
temp_isa = isa_bal
temp_sipp = sipp_bal
temp_spend = annual_spend

for age in range(current_age, 96):
    # 1. Grow Assets (Vanguard Style Outlook)
    temp_isa *= (1 + growth_rate)
    temp_sipp *= (1 + growth_rate)
    
    # 2. Drawdown Logic (The "Bridge" Strategy)
    # If retired, start spending
    if age >= retirement_age:
        remaining_to_fund = temp_spend
        
        # Spend ISA first (Tax-Free)
        draw_isa = min(temp_isa, remaining_to_fund)
        temp_isa -= draw_isa
        remaining_to_fund -= draw_isa
        
        # Spend SIPP second (Taxable - simplified for prototype)
        if remaining_to_fund > 0:
            draw_sipp = min(temp_sipp, remaining_to_fund)
            temp_sipp -= draw_sipp
            
    # 3. Inflation adjustment for next year
    temp_spend *= (1 + inflation_rate)
    
    data.append({
        "Age": age,
        "ISA": round(temp_isa),
        "SIPP": round(temp_sipp),
        "Total Wealth": round(temp_isa + temp_sipp)
    })

df = pd.DataFrame(data)

# --- VISUALIZATION ---
st.subheader("Wealth Projection Over Time")
st.line_chart(df.set_index("Age")[["ISA", "SIPP", "Total Wealth"]])

st.subheader("Year-by-Year Breakdown")
st.dataframe(df, use_container_width=True)

