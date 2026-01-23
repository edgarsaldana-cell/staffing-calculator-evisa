import streamlit as st
import math
import pandas as pd
from io import StringIO
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="WFM: Strategy & Operations", layout="wide")

# --- HELPER FUNCTIONS ---
def get_working_days(year, month):
    start = pd.Timestamp(year, month, 1)
    end = start + pd.offsets.MonthEnd(0)
    return len(pd.bdate_range(start, end))

# --- MAIN APP ---
st.title("📊 Workforce Management: Macro to Micro")

tab_calc, tab_bulk, tab_micro = st.tabs([
    "📍 Macro: Monthly Calculator", 
    "🗂️ Bulk: Multi-Month Input", 
    "🔬 Micro: Schedule Optimizer"
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
shrinkage = shrinkage_input / 100
growth_input = st.sidebar.number_input("Growth Factor (%)", min_value=0.0, max_value=100.0, value=0.0)
growth = growth_input / 100
hrs_shift = st.sidebar.number_input("Hours per Shift (Working)", value=8.0)

st.sidebar.divider()
st.sidebar.subheader("🎯 Target Concurrency")
f_c = st.sidebar.number_input("FLS Concurrency", value=2.0)
s_c = st.sidebar.number_input("SLS Concurrency", value=1.5)

# (Lógica de Tab 1 y Tab 2 se mantiene igual para preservar los datos)
with tab_calc:
    work_days = get_working_days(selected_year, month_map[selected_month_name])
    hrs_eff = (work_days * hrs_shift) * (1 - shrinkage)
    col1, col2 = st.columns(2)
    with col1:
        st.header("FLS (Level 1)")
        v_c_f = st.number_input("Chat Vol FLS", value=11691) * (1 + growth)
        a_c_f = st.number_input("Chat AHT FLS (sec)", value=3731)
        v_e_f = st.number_input("Email Vol FLS", value=4595) * (1 + growth)
        a_e_f = st.number_input("Email AHT FLS (sec)", value=3215)
        wl_fls = ((v_c_f * a_c_f) / 3600 / f_c) + ((v_e_f * a_e_f) / 3600 / f_c)
        hc_fls = math.ceil(wl_fls / hrs_eff) if hrs_eff > 0 else 0
        st.metric("FLS Headcount", hc_fls)
    with col2:
        st.header("SLS (Level 2)")
        v_c_s = st.number_input("Chat Vol SLS", value=1085) * (1 + growth)
        a_c_s = st.number_input("Chat AHT SLS (sec)", value=7324)
        v_e_s = st.number_input("Email Vol SLS", value=361) * (1 + growth)
        a_e_s = st.number_input("Email AHT SLS (sec)", value=9927)
        wl_sls = ((v_c_s * a_c_s) / 3600 / s_c) + ((v_e_s * a_e_s) / 3600 / s_c)
        hc_sls = math.ceil(wl_sls / hrs_eff) if hrs_eff > 0 else 0
        st.metric("SLS Headcount", hc_sls)

with tab_bulk:
    st.header("Bulk Multi-Month Analysis")
    col_v, col_a = st.columns(2)
    with col_v: vol_bulk = st.text_area("Paste Volume here", height=150)
    with col_a: aht_bulk = st.text_area("Paste AHT here", height=150)
    if st.button("Calculate Bulk"):
        if vol_bulk and aht_bulk:
            df_v = pd.read_csv(StringIO(vol_bulk), header=None, names=['Date','v_em','v_ch','v_sch','v_sem'])
            df_a = pd.read_csv(StringIO(aht_bulk), header=None, names=['Date','a_sem','a_sch','a_ch','a_em'])
            df_m = pd.merge(df_v, df_a, on='Date')
            bulk_res = []
            for _, r in df_m.iterrows():
                dt = pd.to_datetime(r['Date'])
                d_l = get_working_days(dt.year, dt.month)
                cp = (d_l * hrs_shift) * (1 - shrinkage)
                v_em_g, v_ch_g = r['v_em']*(1+growth), r['v_ch']*(1+growth)
                v_sem_g, v_sch_g = r['v_sem']*(1+growth), r['v_sch']*(1+growth)
                wl_f = ((v_em_g*r['a_em'])/3600/f_c) + ((v_ch_g*r['a_ch'])/3600/f_c)
                wl_s = ((v_sem_g*r['a_sem'])/3600/s_c) + ((v_sch_g*r['a_sch'])/3600/s_c)
                hc_f, hc_s = math.ceil(wl_f/cp), math.ceil(wl_s/cp)
                bulk_res.append({
                    "Month": dt.strftime('%B %Y'), "Vol Email FLS": int(v_em_g), "AHT Email FLS": int(r['a_em']),
                    "Vol Chat FLS": int(v_ch_g), "AHT Chat FLS": int(r['a_ch']),
                    "Vol Email SLS": int(v_sem_g), "AHT Email SLS": int(r['a_sem']),
                    "Vol Chat SLS": int(v_sch_g), "AHT Chat SLS": int(r['a_sch']),
                    "TOTAL VOL": int(v_em_g+v_ch_g+v_sem_g+v_sch_g), "FLS HC": hc_f, "SLS HC": hc_s, "Total HC": hc_f + hc_s
                })
            st.session_state['bulk_data'] = bulk_res
            st.table(bulk_res)

# --- TAB 3: MICRO SCHEDULE OPTIMIZER ---
with tab_micro:
    st.header("🔬 Schedule Optimizer & Roster")
    if 'bulk_data' not in st.session_state:
        st.warning("⚠️ Please run 'Calculate Bulk' in the Multi-Month tab first.")
    
    with st.expander("🚀 Target Simulation (Target Minutes)"):
        c1, c2, c3 = st.columns(3)
        with c1: dt_weekly = st.number_input("Weekly Downtime (Min)", value=120)
        with c2: aht_f_target = st.number_input("Target AHT FLS (Min)", value=55.0)
        with c3: aht_s_target = st.number_input("Target AHT SLS (Min)", value=110.0)

    uploaded_file = st.file_uploader("Upload Raw CSV (Columns: Conversation started at (America/Lima) & Team currently assigned)", type="csv")
    
    if uploaded_file and 'bulk_data' in st.session_state:
        df_raw = pd.read_csv(uploaded_file)
        time_col = 'Conversation started at (America/Lima)'
        team_col = 'Team currently assigned'
        df_raw[time_col] = pd.to_datetime(df_raw[time_col])
        current_month = df_raw[time_col].dt.strftime('%B %Y').iloc[0]
        num_days = df_raw[time_col].dt.date.nunique()
        
        month_info = next((item for item in st.session_state['bulk_data'] if item["Month"] == current_month), None)
        
        if month_info:
            df_raw['Hour'] = df_raw[time_col].dt.hour
            df_raw['Day'] = df_raw[time_col].dt.day_name()
            
            # Separación FLS / SLS (Modificación 3)
            fls_raw = df_raw[~df_raw[team_col].str.contains('SLS', na=False)]
            sls_raw = df_raw[df_raw[team_col].str.contains('SLS', na=False)]
            
            mesh = []
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            # Análisis Horario Separado
            for h in range(24):
                vol_f = len(fls_raw[fls_raw['Hour'] == h]) / num_days
                vol_s = len(sls_raw[sls_raw['Hour'] == h]) / num_days
                
                # Actual vs Target FLS
                aht_f_act = (month_info['AHT Email FLS'] + month_info['AHT Chat FLS']) / 2
                hc_f_act = math.ceil(((vol_f * aht_f_act)/3600/f_c)/(1-(shrinkage_input/100)))
                hc_f_tar = math.ceil(((vol_f * aht_f_target * 60)/3600/f_c)/(1-(shrinkage_input/100)))
                
                # Actual vs Target SLS
                aht_s_act = (month_info['AHT Email SLS'] + month_info['AHT Chat SLS']) / 2
                hc_s_act = math.ceil(((vol_s * aht_s_act)/3600/s_c)/(1-(shrinkage_input/100)))
                hc_s_tar = math.ceil(((vol_s * aht_s_target * 60)/3600/s_c)/(1-(shrinkage_input/100)))

                mesh.append({
                    "Hour": f"{h:02d}:00", "Vol FLS": round(vol_f,1), "HC FLS (Act)": hc_f_act, "HC FLS (Tar)": hc_f_tar,
                    "Vol SLS": round(vol_s,1), "HC SLS (Act)": hc_s_act, "HC SLS (Tar)": hc_s_tar, "Total HC": hc_f_act + hc_s_act
                })
            
            st.subheader("1. Hourly Distribution (FLS vs SLS)")
            st.table(mesh)

            # --- ROSTER & SHIFT GROUPING ---
            st.divider()
            st.subheader("2. Suggested Monthly Roster & Shift Groups")
            
            # Identificar los dos días de menor volumen para OFF DAYS (Modificación 2)
            vol_per_day = df_raw.groupby('Day').size().reindex(days_order).fillna(0)
            off_days = vol_per_day.nsmallest(2).index.tolist()
            st.info(f"Optimized Off-Days based on lowest volume: **{off_days[0]} and {off_days[1]}**")

            roster = []
            shift_counts = {}
            total_hc = month_info['Total HC']
            
            for i in range(1, total_hc + 1):
                # Distribuir inicios de turno según volumen
                start_h = (7 + (i % 5) * 2) % 24 
                end_h = (start_h + 9) % 24
                shift_label = f"{start_h:02d}:00 - {end_h:02d}:00"
                shift_counts[shift_label] = shift_counts.get(shift_label, 0) + 1
                
                # Downtime: Asegurar que sea dentro del turno (Modificación 1)
                dt_hour = (start_h + 2) % 24 
                lunch_hour = (start_h + 4) % 24
                
                agent_row = {"Agent": f"Agent {i:02d}", "Shift": shift_label}
                dt_day = [d for d in days_order if d not in off_days][i % 5]
                
                for d in days_order:
                    if d in off_days:
                        agent_row[d] = "OFF"
                    elif d == dt_day:
                        agent_row[d] = f"Work (DT @ {dt_hour:02d}:00)"
                    else:
                        agent_row[d] = f"Work (Lunch @ {lunch_hour:02d}:00)"
                roster.append(agent_row)
            
            # Modificación 4: Agrupación de Horarios
            st.write("### Shift Grouping Summary")
            group_data = [{"Shift": k, "Count": v} for k, v in shift_counts.items()]
            st.table(group_data)
            
            st.write("### Individual Agent Roster")
            st.table(roster)
