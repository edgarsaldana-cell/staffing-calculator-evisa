import streamlit as st
import math
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG & CUSTOM STYLES ---
st.set_page_config(page_title="Staffing Tool", layout="wide")

# Custom CSS for Company Colors
st.markdown(f"""
    <style>
    .stApp {{
        background-color: #ecfbff;
        color: #0b3947;
    }}
    h1, h2, h3, p, span, label, .stMetric {{
        color: #0b3947 !important;
    }}
    .stNumberInput input, .stSelectbox div {{
        background-color: #ffffff;
        color: #0b3947;
    }}
    </style>
    """, unsafe_content_label=True)

# --- HELPER FUNCTIONS ---
def get_working_days(year, month):
    start = pd.Timestamp(year, month, 1)
    end = start + pd.offsets.MonthEnd(0)
    return len(pd.bdate_range(start, end))

# --- MAIN APP ---
st.title("📊 Workforce Management Calculator")

# --- TAB SELECTION ---
tab_calc, tab_bulk = st.tabs(["Monthly Calculator", "Bulk Input (Multiple Months)"])

with tab_calc:
    # --- SIDEBAR: PARAMETERS ---
    st.sidebar.header("⚙️ Month Parameters")
    
    selected_year = st.sidebar.number_input("Year", min_value=2024, max_value=2030, value=2025)
    selected_month_name = st.sidebar.selectbox("Month", 
        ["January", "February", "March", "April", "May", "June", 
         "July", "August", "September", "October", "November", "December"], index=11)
    
    month_map = {"January":1, "February":2, "March":3, "April":4, "May":5, "June":6, 
                 "July":7, "August":8, "September":9, "October":10, "November":11, "December":12}
    
    work_days = get_working_days(selected_year, month_map[selected_month_name])
    st.sidebar.write(f"Net Working Days: **{work_days}**")

    shrinkage = st.sidebar.slider("Shrinkage (%)", 0, 50, 10) / 100
    growth = st.sidebar.slider("Growth Factor (%)", 0, 100, 0) / 100
    hrs_shift = st.sidebar.number_input("Hours per Shift", value=8)

    # Agent Capacity
    hrs_eff = (work_days * hrs_shift) * (1 - shrinkage)
    
    # Calculation Logic for Inputs
    st.sidebar.divider()
    st.sidebar.subheader("📈 Monthly Summary")
    
    # Initial placeholders for summary
    summary_placeholder = st.sidebar.empty()

    # --- INPUTS ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("FLS (Level 1)")
        f_c = st.number_input("FLS Concurrency", value=2.0)
        v_c_f = st.number_input("Chat Vol FLS", value=11691) * (1 + growth)
        a_c_f = st.number_input("Chat AHT FLS (sec)", value=3731)
        v_e_f = st.number_input("Email Vol FLS", value=4595) * (1 + growth)
        a_e_f = st.number_input("Email AHT FLS (sec)", value=3215)
        
        wl_fls = ((v_c_f * a_c_f) / 3600 / f_c) + ((v_e_f * a_e_f) / 3600 / f_c)
        hc_fls = math.ceil(wl_fls / hrs_eff) if hrs_eff > 0 else 0
        st.metric("FLS Headcount", hc_fls)

    with col2:
        st.header("SLS (Level 2)")
        s_c = st.number_input("SLS Concurrency", value=1.5)
        v_c_s = st.number_input("Chat Vol SLS", value=1085) * (1 + growth)
        a_c_s = st.number_input("Chat AHT SLS (sec)", value=7324)
        v_e_s = st.number_input("Email Vol SLS", value=361) * (1 + growth)
        a_e_s = st.number_input("Email AHT SLS (sec)", value=9927)
        
        wl_sls = ((v_c_s * a_c_s) / 3600 / s_c) + ((v_e_s * a_e_s) / 3600 / s_c)
        hc_sls = math.ceil(wl_sls / hrs_eff) if hrs_eff > 0 else 0
        st.metric("SLS Headcount", hc_sls)

    # --- UPDATE SIDEBAR SUMMARY ---
    total_vol = (v_c_f + v_e_f + v_c_s + v_e_s)
    avg_aht = (a_c_f + a_e_f + a_c_s + a_e_s) / 4
    total_hc = hc_fls + hc_sls
    
    summary_placeholder.markdown(f"""
    - **Total Vol:** {total_vol:,.0f}
    - **Avg AHT:** {avg_aht:.0f} sec
    - **Total HC:** {total_hc} Agents
    """)

with tab_bulk:
    st.header("Bulk Input Mode")
    st.write("Paste your data below. Format: Month, Year, Vol, AHT")
    
    bulk_data = st.text_area("Paste CSV/Excel data here (Month, Year, Vol, AHT)", 
                             "December, 2025, 17732, 4500\nJanuary, 2026, 15000, 4200")
    
    if st.button("Calculate Bulk"):
        # Simple parser for the text area
        lines = [line.split(",") for line in bulk_data.split("\n") if line]
        results = []
        for l in lines:
            m_idx = month_map[l[0].strip()]
            y_val = int(l[1].strip())
            v_val = float(l[2].strip()) * (1 + growth)
            a_val = float(l[3].strip())
            
            d_lab = get_working_days(y_val, m_idx)
            cap = (d_lab * hrs_shift) * (1 - shrinkage)
            # Using 1.75 as an average concurrency for the bulk preview
            staff = math.ceil(((v_val * a_val) / 3600 / 1.75) / cap)
            results.append({"Month": l[0], "Year": y_val, "Volume": v_val, "Req. HC": staff})
        
        st.table(pd.DataFrame(results))
