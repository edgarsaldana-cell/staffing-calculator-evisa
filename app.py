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
st.title("📊 Workforce Management: Strategy & Operations")

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

work_days = get_working_days(selected_year, month_map[selected_month_name])
shrinkage_input = st.sidebar.number_input("Shrinkage (%)", min_value=0.0, max_value=100.0, value=10.0)
shrinkage = shrinkage_input / 100
growth_input = st.sidebar.number_input("Growth Factor (%)", min_value=0.0, max_value=100.0, value=0.0)
growth = growth_input / 100
hrs_shift = st.sidebar.number_input("Hours per Shift (Working)", value=8.0)

st.sidebar.divider()
st.sidebar.subheader("🎯 Target Concurrency")
f_c = st.sidebar.number_input("FLS Concurrency", value=2.0)
s_c = st.sidebar.number_input("SLS Concurrency", value=1.5)

hrs_eff = (work_days * hrs_shift) * (1 - shrinkage)

# --- TAB 1 & 2 (Se mantienen igual) ---
with tab_calc:
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
    with col_v: vol_bulk = st.text_area("Paste Volume here", height=150, key="v_b")
    with col_a: aht_bulk = st.text_area("Paste AHT here", height=150, key="a_b")
    if st.button("Calculate Bulk"):
        if vol_bulk and aht_bulk:
            df_v = pd.read_csv(StringIO(vol_bulk), header=None, names=['Date','v_em','v_ch','v_sch','v_sem'])
            df_a = pd.read_csv(StringIO(aht_bulk), header=None, names=['Date','a_sem','a_sch','a_ch','a_em'])
            df_m = pd.merge(df_v, df_a, on='Date')
            res = []
            for _, r in df_m.iterrows():
                dt = pd.to_datetime(r['Date'])
                d_l = get_working_days(dt.year, dt.month)
                cp = (d_l * hrs_shift) * (1 - shrinkage)
                v_em_g = r['v_em']*(1+growth); v_ch_g = r['v_ch']*(1+growth)
                v_sem_g = r['v_sem']*(1+growth); v_sch_g = r['v_sch']*(1+growth)
                wl_f = ((v_em_g*r['a_em'])/3600/f_c) + ((v_ch_g*r['a_ch'])/3600/f_c)
                wl_s = ((v_sem_g*r['a_sem'])/3600/s_c) + ((v_sch_g*r['a_sch'])/3600/s_c)
                hc_f = math.ceil(wl_f/cp); hc_s = math.ceil(wl_s/cp)
                res.append({"Month": dt.strftime('%B %Y'), "TOTAL VOL": f"{int(v_em_g+v_ch_g+v_sem_g+v_sch_g):,}", "FLS HC": hc_f, "SLS HC": hc_s, "Total HC": hc_f + hc_s})
            st.table(res)

# --- TAB 3: MICRO SCHEDULE OPTIMIZER & ROSTER ---
with tab_micro:
    st.header("🔬 Schedule Optimizer & Roster Generator")
    
    with st.expander("🚀 Target Parameters"):
        c1, c2, c3 = st.columns(3)
        with c1:
            dt_weekly = st.number_input("Weekly Downtime (Min)", value=120)
            dt_impact = (dt_weekly / 2400) * 100
        with c2: aht_f_m = st.number_input("Target AHT FLS (Min)", value=60.0)
        with c3: aht_s_m = st.number_input("Target AHT SLS (Min)", value=120.0)
    
    uploaded_file = st.file_uploader("Upload Raw CSV", type="csv")
    
    if uploaded_file:
        df_raw = pd.read_csv(uploaded_file)
        time_col = 'Conversation started at (America/Lima)'
        team_col = 'Team currently assigned'
        
        if time_col in df_raw.columns:
            df_raw[time_col] = pd.to_datetime(df_raw[time_col])
            df_raw['Hour'] = df_raw[time_col].dt.hour
            num_days = df_raw[time_col].dt.date.nunique()
            
            df_fls = df_raw[~df_raw[team_col].str.contains('SLS', na=False)]
            df_sls = df_raw[df_raw[team_col].str.contains('SLS', na=False)]

            h_data = pd.DataFrame({'Hour': range(24)})
            h_data = h_data.merge(df_fls.groupby('Hour').size().reset_index(name='V_F'), on='Hour', how='left').fillna(0)
            h_data = h_data.merge(df_sls.groupby('Hour').size().reset_index(name='V_S'), on='Hour', how='left').fillna(0)

            total_shrink = (shrinkage_input + dt_impact) / 100
            
            mesh = []
            for _, r in h_data.iterrows():
                # FLS logic
                vf = (r['V_F'] / num_days) * (1 + growth)
                hcf = math.ceil(((vf * aht_f_m * 60) / 3600 / f_c) / (1 - total_shrink)) if total_shrink < 1 else 0
                # SLS logic
                vs = (r['V_S'] / num_days) * (1 + growth)
                hcs = math.ceil(((vs * aht_s_m * 60) / 3600 / s_c) / (1 - total_shrink)) if total_shrink < 1 else 0
                
                mesh.append({"Hour": f"{int(r['Hour'])}:00", "Vol FLS": int(vf), "HC FLS": hcf, "Vol SLS": int(vs), "HC SLS": hcs, "Total HC": hcf + hcs})
            
            st.subheader("1. Hourly Requirement (Integers)")
            st.table(mesh)

            # --- ROSTER GENERATION LOGIC ---
            st.divider()
            st.subheader("2. Suggested Monthly Roster (9h Shift: 8h Work + 1h Lunch)")
            
            peak_hc = max([m['Total HC'] for m in mesh])
            
            # Simple heuristic for shift start times based on peak
            # To simplify, we distribute agents across the most needed hours
            roster = []
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            
            # Calculate shift starts based on demand (simplified distribution)
            for i in range(1, peak_hc + 1):
                # Start times vary to cover the day (e.g., 06:00, 08:00, 10:00, 14:00)
                # This is a basic rotation to ensure coverage
                start_h = (6 + (i % 3) * 4) % 24 
                end_h = (start_h + 9) % 24
                lunch_h = (start_h + 4) % 24
                
                agent_row = {"Agent": f"Agent {i:02d}", "Shift": f"{start_h:02d}:00 - {end_h:02d}:00"}
                
                for day in days:
                    # Downtime: Assign to a specific day (e.g., Wednesday)
                    if day == "Wed":
                        agent_row[day] = f"Work (DT @ {start_h+1}:00)"
                    else:
                        agent_row[day] = f"Work (Lunch @ {lunch_h:02d}:00)"
                
                roster.append(agent_row)
            
            st.table(roster)
            
            st.info("💡 **Nota:** El Downtime se programó los miércoles para todos los agentes como sesión semanal. Los almuerzos están fijados a la 4ta hora de cada turno.")
