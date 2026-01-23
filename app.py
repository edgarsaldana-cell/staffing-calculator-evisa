import streamlit as st
import math
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Workforce Management Tool", layout="wide")

# --- HELPER FUNCTIONS ---
def get_working_days(year, month):
    # Calculate business days (Mon-Fri) using pandas
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
    
    shrinkage = st.sidebar.slider("Shrinkage (%)", 0, 50, 10) / 100
    growth = st.sidebar.slider("Growth Factor (%)", 0, 100, 0) / 100
    hrs_shift = st.sidebar.number_input("Hours per Shift", value=8)

    # Agent Capacity Calculation
    hrs_eff = (work_days * hrs_shift) * (1 - shrinkage)
    
    st.sidebar.divider()
    st.sidebar.subheader("📈 Monthly Summary")
    
    # Placeholders for dynamic summary
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
    total_hc = hc_fls + hc_sls
    
    summary_placeholder.markdown(f"""
    - **Working Days:** {work_days}
    - **Capacity/Agent:** {hrs_eff:.1f} hrs
    - **Total Volume:** {total_vol:,.0f}
    - **Total Headcount:** {total_hc} Agents
    """)

with tab_bulk:
    st.header("Bulk Input Mode")
    st.write("Enter monthly data below to calculate multiple periods at once.")
    
    # Sample data format for the user
    example_csv = "Month, Year, Chat Vol, Chat AHT, Email Vol, Email AHT\nDecember, 2025, 11691, 3731, 4595, 3215"
    bulk_input = st.text_area("Paste your data (CSV format)", example_csv, height=200)
    
    if st.button("Calculate Bulk Staffing"):
        try:
            from io import StringIO
            df_bulk = pd.read_csv(StringIO(bulk_input))
            
            # Clean column names
            df_bulk.columns = df_bulk.columns.str.strip()
            
            results = []
            for _, row in df_bulk.iterrows():
                m_name = row['Month'].strip()
                y_val = int(row['Year'])
                m_num = month_map[m_name]
                
                # Apply growth
                v_c = row['Chat Vol'] * (1 + growth)
                v_e = row['Email Vol'] * (1 + growth)
                
                d_lab = get_working_days(y_val, m_num)
                cap = (d_lab * hrs_shift) * (1 - shrinkage)
                
                # Using a generic average concurrency of 1.75 for bulk preview
                wl = ((v_c * row['Chat AHT']) / 3600 / 1.75) + ((v_e * row['Email AHT']) / 3600 / 1.75)
                hc = math.ceil(wl / cap) if cap > 0 else 0
                
                results.append({
                    "Month": m_name,
                    "Year": y_val,
                    "Total Vol (with Growth)": round(v_c + v_e),
                    "Work Days": d_lab,
                    "Required Headcount": hc
                })
            
            st.table(pd.DataFrame(results))
        except Exception as e:
            st.error(f"Error processing data: {e}. Please ensure the format matches the example.")
