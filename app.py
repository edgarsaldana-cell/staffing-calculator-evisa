import streamlit as st
import math
import pandas as pd
from io import StringIO
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="WFM: Macro & Micro Support", layout="wide")

# --- HELPER FUNCTIONS ---
def get_working_days(year, month):
    start = pd.Timestamp(year, month, 1)
    end = start + pd.offsets.MonthEnd(0)
    return len(pd.bdate_range(start, end))

# --- MAIN APP ---
st.title("📊 Workforce Management: Strategy & Operations")

# TABS DEFINITION
tab_calc, tab_bulk, tab_micro = st.tabs([
    "📍 Macro: Monthly Calculator", 
    "🗂️ Bulk: Multi-Month Input", 
    "🔬 Micro: Schedule Optimizer"
])

# --- TAB 1: MACRO CALCULATOR (CONSERVADO) ---
with tab_calc:
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

# --- TAB 2: BULK INPUT (CONSERVADO) ---
with tab_bulk:
    st.header("Bulk Multi-Month Analysis")
    st.warning("Paste data WITHOUT headers.")
    col_v, col_a = st.columns(2)
    with col_v:
        st.subheader("1. Volume Data")
        st.caption("Order: Date, Email, Chat, SLS Chat, SLS Email")
        vol_bulk = st.text_area("Paste Volume here", height=200, key="vol_bulk")
    with col_a:
        st.subheader("2. AHT Data (sec)")
        st.caption("Order: Date, SLS Email, SLS Chat, Chat, Email")
        aht_bulk = st.text_area("Paste AHT here", height=200, key="aht_bulk")

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
                res.append({"Month": dt.strftime('%B %Y'), "Vol Email FLS": f"{int(v_em_g):,}", "AHT Email FLS": f"{int(r['a_em'])}s", "Vol Chat FLS": f"{int(v_ch_g):,}", "AHT Chat FLS": f"{int(r['a_ch'])}s", "Vol Email SLS": f"{int(v_sem_g):,}", "AHT Email SLS": f"{int(r['a_sem'])}s", "Vol Chat SLS": f"{int(v_sch_g):,}", "AHT Chat SLS": f"{int(r['a_sch'])}s", "TOTAL VOL": f"{int(v_em_g+v_ch_g+v_sem_g+v_sch_g):,}", "Work Days": d_l, "FLS HC": hc_f, "SLS HC": hc_s, "Total HC": hc_f + hc_s})
            st.table(res)

# --- TAB 3: MICRO SCHEDULE OPTIMIZER (NUEVO) ---
with tab_micro:
    st.header("🔬 Raw Data to Hourly Schedule")
    
    with st.expander("Step 1: Set Downtime & Micro Parameters"):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            dt_weekly = st.number_input("Weekly Downtime per Agent (Minutes)", value=120, help="Coaching, Meetings, 1:1s")
            # 40 hrs base (2400 min). Calculate how this impacts shrinkage.
            dt_impact = (dt_weekly / 2400) * 100
            st.info(f"Downtime adds **{dt_impact:.2f}%** to your base shrinkage.")
        with col_m2:
            micro_aht = st.number_input("Average AHT for this Dataset (sec)", value=4000)
            micro_concur = st.number_input("Target Concurrency for Schedule", value=1.75)
    
    uploaded_file = st.file_uploader("Upload Raw CSV (Must have: 'Conversation started at (America/Lima)')", type="csv")
    
    if uploaded_file:
        df_raw = pd.read_csv(uploaded_file)
        time_col = 'Conversation started at (America/Lima)'
        
        if time_col in df_raw.columns:
            df_raw[time_col] = pd.to_datetime(df_raw[time_col])
            df_raw['Hour'] = df_raw[time_col].dt.hour
            df_raw['DayName'] = df_raw[time_col].dt.day_name()
            
            # Average Volume per Hour
            hourly_data = df_raw.groupby(['Hour']).size().reset_index(name='Total_Vol')
            # Normalize by days in dataset to get 'Average Hour Arrival'
            num_days = df_raw[time_col].dt.date.nunique()
            hourly_data['Avg_Arrival'] = hourly_data['Total_Vol'] / num_days
            
            # WORKLOAD CALCULATION per Hour
            # (Avg_Arrival * AHT) / 3600 / Concurrency
            hourly_data['Logged_In_Needed'] = (hourly_data['Avg_Arrival'] * micro_aht) / 3600 / micro_concur
            
            # Applying Micro-Shrinkage (Downtime + Base Shrinkage)
            total_micro_shrink = (shrinkage_input + dt_impact) / 100
            hourly_data['HC_Required'] = hourly_data['Logged_In_Needed'].apply(lambda x: math.ceil(x / (1 - total_micro_shrink)))

            st.subheader("Hourly Demand vs Coverage Required")
            st.bar_chart(data=hourly_data, x='Hour', y='HC_Required')
            
            # Final Mesh Table
            mesh_display = []
            for _, row in hourly_data.iterrows():
                mesh_display.append({
                    "Hour Interval": f"{int(row['Hour'])}:00 - {int(row['Hour'])+1}:00",
                    "Avg Arrival (Chats)": round(row['Avg_Arrival'], 2),
                    "Staff Logged-in (Net)": round(row['Logged_In_Needed'], 2),
                    "Total Headcount (Gross)": row['HC_Required']
                })
            st.table(mesh_display)
        else:
            st.error(f"Column '{time_col}' not found in CSV.")
