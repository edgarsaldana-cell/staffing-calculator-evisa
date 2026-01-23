import streamlit as st
import math
import pandas as pd
from io import StringIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Workforce Management Tool", layout="wide")

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
    
    # Modificación 1: Inputs numéricos para Shrinkage y Growth
    shrinkage_input = st.sidebar.number_input("Shrinkage (%)", min_value=0.0, max_value=100.0, value=10.0)
    shrinkage = shrinkage_input / 100
    
    growth_input = st.sidebar.number_input("Growth Factor (%)", min_value=0.0, max_value=100.0, value=0.0)
    growth = growth_input / 100
    
    hrs_shift = st.sidebar.number_input("Hours per Shift", value=8.0)

    hrs_eff = (work_days * hrs_shift) * (1 - shrinkage)
    
    st.sidebar.divider()
    st.sidebar.subheader("📈 Monthly Summary")
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
    st.info("Paste your data below as tab-separated or comma-separated values from Excel.")
    
    # Modificación 2: Dos inputs separados para Volumen y AHT
    col_v, col_a = st.columns(2)
    
    with col_v:
        st.subheader("1. Volume Data")
        vol_input = st.text_area("Month, eVisa Email, eVisa Chat, eVisa SLS Chat, eVisa SLS Email", height=200, 
                                 help="Format: Month, Email, Chat, SLS_Chat, SLS_Email")
        
    with col_a:
        st.subheader("2. AHT Data (seconds)")
        aht_input = st.text_area("Month, eVisa SLS Email, eVisa SLS Chat, eVisa Chat, eVisa Email", height=200,
                                 help="Note the order: SLS Email, SLS Chat, Chat, Email")

    # Input para el año de referencia del bulk
    bulk_year = st.number_input("Reference Year for Bulk Calculation", value=2025)

    if st.button("Calculate Bulk Staffing"):
        try:
            # Procesar Volumen - Usamos read_csv con delimitador flexible (coma o espacio)
            df_vol = pd.read_csv(StringIO(vol_input), sep=None, engine='python')
            df_vol.columns = ['Month', 'v_email', 'v_chat', 'v_sls_chat', 'v_sls_email']
            
            # Procesar AHT
            df_aht = pd.read_csv(StringIO(aht_input), sep=None, engine='python')
            df_aht.columns = ['Month', 'a_sls_email', 'a_sls_chat', 'a_chat', 'a_email']
            
            # Unir tablas por Mes
            df_final = pd.merge(df_vol, df_aht, on='Month')
            
            results = []
            for _, row in df_final.iterrows():
                m_name = str(row['Month']).strip()
                if m_name not in month_map: continue
                
                m_num = month_map[m_name]
                d_lab = get_working_days(bulk_year, m_num)
                cap = (d_lab * hrs_shift) * (1 - shrinkage)
                
                # Cálculos con Crecimiento aplicado
                # FLS
                wl_fls_b = (((row['v_email'] * (1+growth)) * row['a_email']) / 3600 / f_c) + \
                           (((row['v_chat'] * (1+growth)) * row['a_chat']) / 3600 / f_c)
                # SLS
                wl_sls_b = (((row['v_sls_email'] * (1+growth)) * row['a_sls_email']) / 3600 / s_c) + \
                           (((row['v_sls_chat'] * (1+growth)) * row['a_sls_chat']) / 3600 / s_c)
                
                hc_f = math.ceil(wl_fls_b / cap) if cap > 0 else 0
                hc_s = math.ceil(wl_sls_b / cap) if cap > 0 else 0
                
                results.append({
                    "Month": m_name,
                    "Work Days": d_lab,
                    "FLS Agents": hc_f,
                    "SLS Agents": hc_s,
                    "Total Agents": hc_f + hc_s
                })
            
            st.table(pd.DataFrame(results))
            
        except Exception as e:
            st.error(f"Error: {e}. Please check the format. Ensure headers are NOT included or match exactly.")
