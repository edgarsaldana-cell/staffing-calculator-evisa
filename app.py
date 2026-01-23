import streamlit as st
import math
import pandas as pd
from io import StringIO, BytesIO
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Workforce Management Tool", layout="wide")

# --- FUNCIONES AUXILIARES ---
def get_working_days(year, month):
    start = pd.Timestamp(year, month, 1)
    end = start + pd.offsets.MonthEnd(0)
    return len(pd.bdate_range(start, end))

def to_excel(df_list, sheet_names):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for df, name in zip(df_list, sheet_names):
            df.to_excel(writer, index=False, sheet_name=name)
    return output.getvalue()

# --- ESTILOS DE TEXTO POR COLOR (Modificación solicitada) ---
def style_levels(styler):
    # FLS: Texto Azul, SLS: Texto Verde
    styler.set_properties(subset=[col for col in styler.columns if 'FLS' in col], 
                         **{'color': '#0056b3', 'font-weight': 'bold'})
    styler.set_properties(subset=[col for col in styler.columns if 'SLS' in col], 
                         **{'color': '#1a8754', 'font-weight': 'bold'})
    return styler

# --- TÍTULO Y TABS ---
st.title("Workforce Management: Strategy & Operations")

tab_calc, tab_bulk, tab_micro = st.tabs([
    "Macro: Monthly Calculator", 
    "Bulk: Multi-Month Input", 
    "Micro: Schedule Optimizer"
])

# --- SIDEBAR: GLOBAL PARAMETERS ---
st.sidebar.header("⚙️ Global Parameters")
selected_year = st.sidebar.number_input("Year", min_value=2024, max_value=2030, value=2025)
selected_month_name = st.sidebar.selectbox("Month", 
    ["January", "February", "March", "April", "May", "June", 
     "July", "August", "September", "October", "November", "December"], index=11)

month_map = {"January":1, "February":2, "March":3, "April":4, "May":5, "June":6, 
             "July":7, "August":8, "September":9, "October":10, "November":11, "December":12}

shrinkage_input = st.sidebar.number_input("Shrinkage (%)", min_value=0.0, max_value=100.0, value=10.0)
growth_input = st.sidebar.number_input("Growth Factor (%)", min_value=0.0, max_value=100.0, value=0.0)
hrs_shift = st.sidebar.number_input("Hours per Shift (Working)", value=8.0)

st.sidebar.divider()
st.sidebar.subheader("Target Concurrency")
f_c = st.sidebar.number_input("FLS Concurrency", value=2.0)
s_c = st.sidebar.number_input("SLS Concurrency", value=1.5)

# --- TAB 1: MACRO ---
with tab_calc:
    work_days = get_working_days(selected_year, month_map[selected_month_name])
    hrs_eff = (work_days * hrs_shift) * (1 - (shrinkage_input/100))
    col1, col2 = st.columns(2)
    with col1:
        st.header("FLS (Level 1)")
        v_c_f = st.number_input("Chat Vol FLS", value=11691) * (1 + (growth_input/100))
        a_c_f = st.number_input("Chat AHT FLS (sec)", value=3731)
        v_e_f = st.number_input("Email Vol FLS", value=4595) * (1 + (growth_input/100))
        a_e_f = st.number_input("Email AHT FLS (sec)", value=3215)
        wl_fls = ((v_c_f * a_c_f) / 3600 / f_c) + ((v_e_f * a_e_f) / 3600 / f_c)
        hc_fls = math.ceil(wl_fls / hrs_eff) if hrs_eff > 0 else 0
        st.metric("FLS Headcount", hc_fls)
    with col2:
        st.header("SLS (Level 2)")
        v_c_s = st.number_input("Chat Vol SLS", value=1085) * (1 + (growth_input/100))
        a_c_s = st.number_input("Chat AHT SLS (sec)", value=7324)
        v_e_s = st.number_input("Email Vol SLS", value=361) * (1 + (growth_input/100))
        a_e_s = st.number_input("Email AHT SLS (sec)", value=9927)
        wl_sls = ((v_c_s * a_c_s) / 3600 / s_c) + ((v_e_s * a_e_s) / 3600 / s_c)
        hc_sls = math.ceil(wl_sls / hrs_eff) if hrs_eff > 0 else 0
        st.metric("SLS Headcount", hc_sls)

# --- TAB 2: BULK ---
with tab_bulk:
    st.header("Bulk Multi-Month Analysis")
    cv, ca = st.columns(2)
    vol_b = cv.text_area("Paste Volume here (Date, Email FLS, Chat FLS, Chat SLS, Email SLS)", height=150)
    aht_b = ca.text_area("Paste AHT here (Date, SLS Email, SLS Chat, Chat FLS, Email FLS)", height=150)
    if st.button("Calculate Bulk"):
        if vol_b and aht_b:
            df_v = pd.read_csv(StringIO(vol_b), header=None, names=['Date','v_em_f','v_ch_f','v_ch_s','v_em_s'])
            df_a = pd.read_csv(StringIO(aht_b), header=None, names=['Date','a_em_s','a_ch_s','a_ch_f','a_em_f'])
            df_m = pd.merge(df_v, df_a, on='Date')
            bulk_res = []
            for _, r in df_m.iterrows():
                dt = pd.to_datetime(r['Date'])
                d_l = get_working_days(dt.year, dt.month)
                cp = (d_l * hrs_shift) * (1 - (shrinkage_input/100))
                wl_f = ((r['v_em_f']*(1+(growth_input/100))*r['a_em_f'])/3600/f_c) + ((r['v_ch_f']*(1+(growth_input/100))*r['a_ch_f'])/3600/f_c)
                # Lógica de tope de HC por volumen para FLS
                v_f_total = (r['v_em_f'] + r['v_ch_f']) * (1+(growth_input/100))
                hc_f = min(math.ceil(v_f_total), math.ceil(wl_f/cp)) if v_f_total > 0 else 0
                
                wl_s = ((r['v_em_s']*(1+(growth_input/100))*r['a_em_s'])/3600/s_c) + ((r['v_ch_s']*(1+(growth_input/100))*r['a_ch_s'])/3600/s_c)
                v_s_total = (r['v_ch_s'] + r['v_em_s']) * (1+(growth_input/100))
                hc_s = min(math.ceil(v_s_total), math.ceil(wl_s/cp)) if v_s_total > 0 else 0
                
                bulk_res.append({
                    "Month": dt.strftime('%B %Y'), 
                    "Vol Email FLS": int(r['v_em_f']), "AHT Email FLS": int(r['a_em_f']),
                    "Vol Chat FLS": int(r['v_ch_f']), "AHT Chat FLS": int(r['a_ch_f']),
                    "Vol Email SLS": int(r['v_em_s']), "AHT Email SLS": int(r['a_em_s']),
                    "Vol Chat SLS": int(r['v_ch_s']), "AHT Chat SLS": int(r['a_ch_s']),
                    "TOTAL VOL": int(v_f_total + v_s_total),
                    "FLS HC": hc_f, "SLS HC": hc_s, "Total HC": hc_f + hc_s
                })
            st.session_state['bulk_data'] = bulk_res
            st.table(pd.DataFrame(bulk_res).style.pipe(style_levels))

# --- TAB 3: MICRO ---
with tab_micro:
    st.header("Schedule Optimizer & Roster")
    if 'bulk_data' not in st.session_state: st.error("Run Bulk
