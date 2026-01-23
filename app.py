import streamlit as st
import math
import pandas as pd
from io import StringIO, BytesIO
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Workforce Management Tool", layout="wide")

# --- HELPER FUNCTIONS ---
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

# --- MAIN APP ---
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
    vol_b = cv.text_area("Paste Volume here", height=150)
    aht_b = ca.text_area("Paste AHT here", height=150)
    if st.button("Calculate Bulk"):
        if vol_b and aht_b:
            df_v = pd.read_csv(StringIO(vol_b), header=None, names=['Date','v_em','v_ch','v_sch','v_sem'])
            df_a = pd.read_csv(StringIO(aht_b), header=None, names=['Date','a_sem','a_sch','a_ch','a_em'])
            df_m = pd.merge(df_v, df_a, on='Date')
            bulk_res = []
            for _, r in df_m.iterrows():
                dt = pd.to_datetime(r['Date'])
                d_l = get_working_days(dt.year, dt.month)
                cp = (d_l * hrs_shift) * (1 - (shrinkage_input/100))
                v_f = (r['v_em']+r['v_ch'])*(1+(growth_input/100))
                v_s = (r['v_sch']+r['v_sem'])*(1+(growth_input/100))
                wl_f = ((r['v_em']*(1+(growth_input/100))*r['a_em'])/3600/f_c) + ((r['v_ch']*(1+(growth_input/100))*r['a_ch'])/3600/f_c)
                wl_s = ((r['v_sem']*(1+(growth_input/100))*r['a_sem'])/3600/s_c) + ((r['v_sch']*(1+(growth_input/100))*r['a_sch'])/3600/s_c)
                hc_f, hc_s = math.ceil(wl_f/cp), math.ceil(wl_s/cp)
                bulk_res.append({"Month": dt.strftime('%B %Y'), "Vol FLS": int(v_f), "AHT FLS (Avg)": int((r['a_em']+r['a_ch'])/2), "Vol SLS": int(v_s), "AHT SLS (Avg)": int((r['a_sem']+r['a_sch'])/2), "TOTAL VOL": int(v_f+v_s), "FLS HC": hc_f, "SLS HC": hc_s, "Total HC": hc_f + hc_s})
            st.session_state['bulk_data'] = bulk_res
            st.table(bulk_res)
            st.divider()
            c1, c2, c3 = st.columns(3)
            df_br = pd.DataFrame(bulk_res)
            c1.metric("Total Cumulative Vol", f"{df_br['TOTAL VOL'].sum():,}")
            c2.metric("Peak FLS Headcount", df_br['FLS HC'].max())
            c3.metric("Peak SLS Headcount", df_br['SLS HC'].max())

# --- TAB 3: MICRO ---
with tab_micro:
    st.header("Schedule Optimizer & 24/7 Roster")
    if 'bulk_data' not in st.session_state: st.warning("Run Bulk tab first."); st.stop()
    
    with st.expander("Target Simulation"):
        c1, c2, c3 = st.columns(3)
        dt_weekly = c1.number_input("Weekly Downtime (Min)", value=120)
        aht_f_target = c2.number_input("Target AHT FLS (Min)", value=55.0)
        aht_s_target = c3.number_input("Target AHT SLS (Min)", value=110.0)

    uploaded_file = st.file_uploader("Upload Raw CSV", type="csv")
    if uploaded_file:
        df_raw = pd.read_csv(uploaded_file)
        time_col = 'Conversation started at (America/Lima)'
        team_col = 'Team currently assigned'
        df_raw[time_col] = pd.to_datetime(df_raw[time_col])
        current_month = df_raw[time_col].dt.strftime('%B %Y').iloc[0]
        num_days = df_raw[time_col].dt.date.nunique()
        month_info = next((i for i in st.session_state['bulk_data'] if i["Month"] == current_month), None)
        
        if month_info:
            df_raw['Hour'] = df_raw[time_col].dt.hour
            df_raw['Day'] = df_raw[time_col].dt.day_name()
            fls_raw = df_raw[~df_raw[team_col].str.contains('SLS', na=False)]
            sls_raw = df_raw[df_raw[team_col].str.contains('SLS', na=False)]
            
            mesh = []
            aht_f_act_m = month_info['AHT FLS (Avg)'] / 60
            aht_s_act_m = month_info['AHT SLS (Avg)'] / 60
            
            for h in range(24):
                vf = len(fls_raw[fls_raw['Hour'] == h]) / num_days
                vs = len(sls_raw[sls_raw['Hour'] == h]) / num_days
                hc_f_act = math.ceil(((vf * aht_f_act_m * 60)/3600/f_c)/(1-(shrinkage_input/100)))
                hc_f_tar = math.ceil(((vf * aht_f_target * 60)/3600/f_c)/(1-(shrinkage_input/100)))
                hc_s_act = math.ceil(((vs * aht_s_act_m * 60)/3600/s_c)/(1-(shrinkage_input/100)))
                hc_s_tar = math.ceil(((vs * aht_s_target * 60)/3600/s_c)/(1-(shrinkage_input/100)))
                
                mesh.append({
                    "Hour": f"{h:02d}:00", "Vol FLS": int(vf), "AHT FLS Act (min)": round(aht_f_act_m,1), "HC FLS (Act)": hc_f_act, "AHT FLS Tar (min)": aht_f_target, "HC FLS (Tar)": hc_f_tar,
                    "Vol SLS": int(vs), "AHT SLS Act (min)": round(aht_s_act_m,1), "HC SLS (Act)": hc_s_act, "AHT SLS Tar (min)": aht_s_target, "HC SLS (Tar)": hc_s_tar, "Total HC Interval": hc_f_act + hc_s_act
                })
            st.table(mesh)

            st.divider()
            total_hc = month_info['Total HC']
            st.subheader(f"Suggested Monthly Roster (Total Headcount: {total_hc})")
            
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            roster = []
            shift_groups = {}
            
            for i in range(1, total_hc + 1):
                start_h = (i % 24) 
                end_h = (start_h + 9) % 24
                shift_label = f"{start_h:02d}:00 - {end_h:02d}:00"
                shift_groups[shift_label] = shift_groups.get(shift_label, 0) + 1
                
                off1 = days_order[(i % 7)]
                off2 = days_order[((i + 1) % 7)]
                
                agent_row = {"Agent": f"Agent {i:02d}", "Shift": shift_label}
                dt_day = [d for d in days_order if d not in [off1, off2]][i % 5]
                
                for d in days_order:
                    if d in [off1, off2]: agent_row[d] = "OFF"
                    else:
                        lunch_h = (start_h + (3 if i%2==0 else 5)) % 24
                        if d == dt_day: agent_row[d] = f"Work (DT @ {(start_h+2)%24:02d}:00)"
                        else: agent_row[d] = f"Work (Lunch @ {lunch_h:02d}:00)"
                roster.append(agent_row)
            
            st.write("Shift Grouping Summary")
            df_groups = pd.DataFrame([{"Shift": k, "Agents": v} for k, v in shift_groups.items()])
            st.table(df_groups)
            
            st.write("Individual Roster")
            df_roster = pd.DataFrame(roster)
            st.table(df_roster)

            # Botón de Descarga
            df_mesh = pd.DataFrame(mesh)
            excel_data = to_excel([df_mesh, df_groups, df_roster], ["Hourly Analysis", "Shift Groups", "Roster"])
            st.download_button(label="Download Roster to Excel", data=excel_data, file_name=f"Roster_{current_month}.xlsx", mime="application/vnd.ms-excel")
