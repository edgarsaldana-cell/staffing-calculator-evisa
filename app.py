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
    
    shrinkage_input = st.sidebar.number_input("Shrinkage (%)", min_value=0.0, max_value=100.0, value=10.0)
    shrinkage = shrinkage_input / 100
    
    growth_input = st.sidebar.number_input("Growth Factor (%)", min_value=0.0, max_value=100.0, value=0.0)
    growth = growth_input / 100
    
    hrs_shift = st.sidebar.number_input("Hours per Shift", value=8.0)

    hrs_eff = (work_days * hrs_shift) * (1 - shrinkage)
    
    st.sidebar.divider()
    st.sidebar.subheader("📈 Monthly Summary")
    summary_placeholder = st.sidebar.empty()

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
    summary_placeholder.markdown(f"- **Working Days:** {work_days}\n- **Capacity/Agent:** {hrs_eff:.1f} hrs\n- **Total Vol:** {total_vol:,.0f}\n- **Total HC:** {total_hc} Agents")

with tab_bulk:
    st.header("Bulk Input Mode")
    st.warning("Paste data WITHOUT headers. Order: Volume (Date, Email, Chat, SLS Chat, SLS Email) | AHT (Date, SLS Email, SLS Chat, Chat, Email)")
    
    col_v, col_a = st.columns(2)
    with col_v:
        st.subheader("1. Volume Data")
        vol_input = st.text_area("Paste Volume here", height=200)
    with col_a:
        st.subheader("2. AHT Data (sec)")
        a_input = st.text_area("Paste AHT here", height=200)

    if st.button("Calculate Bulk Staffing"):
        if vol_input and a_input:
            try:
                df_vol = pd.read_csv(StringIO(vol_input), header=None, names=['Date', 'v_em', 'v_ch', 'v_sch', 'v_sem'])
                df_aht = pd.read_csv(StringIO(a_input), header=None, names=['Date', 'a_sem', 'a_sch', 'a_ch', 'a_em'])
                df_f = pd.merge(df_vol, df_aht, on='Date')
                
                results = []
                for _, r in df_f.iterrows():
                    dt = pd.to_datetime(r['Date'])
                    month_year = dt.strftime('%B %Y')
                    d_lab = get_working_days(dt.year, dt.month)
                    cap = (d_lab * hrs_shift) * (1 - shrinkage)
                    
                    # Totales con Growth
                    v_fls = (r['v_em'] + r['v_ch']) * (1+growth)
                    v_sls = (r['v_sch'] + r['v_sem']) * (1+growth)
                    a_fls = (r['a_em'] + r['a_ch']) / 2
                    a_sls = (r['a_sem'] + r['a_sch']) / 2
                    
                    wl_f = (((r['v_em']*(1+growth))*r['a_em'])/3600/f_c) + (((r['v_ch']*(1+growth))*r['a_ch'])/3600/f_c)
                    wl_s = (((r['v_sem']*(1+growth))*r['a_sem'])/3600/s_c) + (((r['v_sch']*(1+growth))*r['a_sch'])/3600/s_c)
                    
                    hc_f = math.ceil(wl_f / cap) if cap > 0 else 0
                    hc_s = math.ceil(wl_s / cap) if cap > 0 else 0
                    
                    results.append({
                        "Month": month_year,
                        "Vol FLS": int(v_fls),
                        "Avg AHT FLS": int(a_fls),
                        "Vol SLS": int(v_sls),
                        "Avg AHT SLS": int(a_sls),
                        "Work Days": d_lab,
                        "FLS Agents": hc_f,
                        "SLS Agents": hc_s,
                        "Total Agents": hc_f + hc_s
                    })
                
                df_res = pd.DataFrame(results)
                
                # Crear Fila de Totales
                totals = pd.Series({
                    "Month": "TOTAL",
                    "Vol FLS": df_res["Vol FLS"].sum(),
                    "Vol SLS": df_res["Vol SLS"].sum(),
                    "FLS Agents": df_res["FLS Agents"].max(), # Usamos Max o Avg según prefieras
                    "SLS Agents": df_res["SLS Agents"].max(),
                    "Total Agents": df_res["Total Agents"].max()
                })
                
                st.success("Analysis Complete")
                # Mostrar tabla sin índice
                st.table(df_res.style.format({
                    "Vol FLS": "{:,}", "Vol SLS": "{:,}", 
                    "Avg AHT FLS": "{:}s", "Avg AHT SLS": "{:}s"
                }))
                
                # Resumen destacado de totales
                st.subheader("Summary Totals (Cumulative Volume & Peak Staffing)")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Yearly Volume", f"{df_res['Vol FLS'].sum() + df_res['Vol SLS'].sum():,}")
                c2.metric("Peak FLS Staffing", df_res['FLS Agents'].max())
                c3.metric("Peak SLS Staffing", df_res['SLS Agents'].max())
                
            except Exception as e:
                st.error(f"Error: {e}")
