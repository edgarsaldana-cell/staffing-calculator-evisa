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

# --- ESTILOS DE TABLA (COLORES) ---
def style_levels(styler):
    # FLS: Azul claro, SLS: Verde/Cian claro
    styler.set_properties(subset=[col for col in styler.columns if 'FLS' in col], **{'background-color': '#e1f5fe'})
    styler.set_properties(subset=[col for col in styler.columns if 'SLS' in col], **{'background-color': '#e0f2f1'})
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

# --- TAB 2: BULK (DETALLE SEPARADO) ---
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
                # Cálculos FLS
                wl_f = ((r['v_em_f']*(1+(growth_input/100))*r['a_em_f'])/3600/f_c) + ((r['v_ch_f']*(1+(growth_input/100))*r['a_ch_f'])/3600/f_c)
                hc_f = math.ceil(wl_f/cp)
                # Cálculos SLS (Lógica: si vol <= 1, hc = 1)
                v_total_s = (r['v_ch_s'] + r['v_em_s']) * (1+(growth_input/100))
                wl_s = ((r['v_em_s']*(1+(growth_input/100))*r['a_em_s'])/3600/s_c) + ((r['v_ch_s']*(1+(growth_input/100))*r['a_ch_s'])/3600/s_c)
                hc_s = 1 if (v_total_s > 0 and v_total_s <= 1) else math.ceil(wl_s/cp)
                
                bulk_res.append({
                    "Month": dt.strftime('%B %Y'), 
                    "Vol Email FLS": int(r['v_em_f']), "AHT Email FLS": int(r['a_em_f']),
                    "Vol Chat FLS": int(r['v_ch_f']), "AHT Chat FLS": int(r['a_ch_f']),
                    "Vol Email SLS": int(r['v_em_s']), "AHT Email SLS": int(r['a_em_s']),
                    "Vol Chat SLS": int(r['v_ch_s']), "AHT Chat SLS": int(r['a_ch_s']),
                    "TOTAL VOL": int(r['v_em_f'] + r['v_ch_f'] + r['v_ch_s'] + r['v_em_s']),
                    "FLS HC": hc_f, "SLS HC": hc_s, "Total HC": hc_f + hc_s
                })
            st.session_state['bulk_data'] = bulk_res
            st.table(pd.DataFrame(bulk_res).style.pipe(style_levels))
            df_br = pd.DataFrame(bulk_res)
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Cumulative Vol", f"{df_br['TOTAL VOL'].sum():,}")
            c2.metric("Peak FLS Headcount", df_br['FLS HC'].max())
            c3.metric("Peak SLS Headcount", df_br['SLS HC'].max())

# --- TAB 3: MICRO ---
with tab_micro:
    st.header("Schedule Optimizer & Roster")
    if 'bulk_data' not in st.session_state: st.error("Run Bulk tab first."); st.stop()
    
    with st.expander("Target Simulation"):
        c1, c2, c3, c4, c5 = st.columns(5)
        dt_weekly = c1.number_input("Weekly Downtime (Min)", value=120)
        a_f_e_tar = c2.number_input("Target FLS Email AHT (m)", value=50.0)
        a_f_c_tar = c3.number_input("Target FLS Chat AHT (m)", value=60.0)
        a_s_e_tar = c4.number_input("Target SLS Email AHT (m)", value=100.0)
        a_s_c_tar = c5.number_input("Target SLS Chat AHT (m)", value=120.0)

    uploaded_file = st.file_uploader("Upload Raw CSV", type="csv")
    if uploaded_file:
        df_raw = pd.read_csv(uploaded_file)
        time_col = 'Conversation started at (America/Lima)'
        team_col = 'Team currently assigned'
        df_raw[time_col] = pd.to_datetime(df_raw[time_col])
        current_month = df_raw[time_col].dt.strftime('%B %Y').iloc[0]
        num_days = df_raw[time_col].dt.date.nunique()
        m_info = next((i for i in st.session_state['bulk_data'] if i["Month"] == current_month), None)
        
        if m_info:
            df_raw['Hour'] = df_raw[time_col].dt.hour
            # Simulación: asumiendo distribución 50/50 email/chat si el raw no lo dice
            fls_raw = df_raw[~df_raw[team_col].str.contains('SLS', na=False)]
            sls_raw = df_raw[df_raw[team_col].str.contains('SLS', na=False)]
            
            mesh = []
            for h in range(24):
                v_f = len(fls_raw[fls_raw['Hour'] == h]) / num_days
                v_s = len(sls_raw[sls_raw['Hour'] == h]) / num_days
                
                # FLS (Asumiendo proporción del bulk para email/chat)
                p_e_f = m_info['Vol Email FLS'] / (m_info['Vol Email FLS'] + m_info['Vol Chat FLS'])
                v_f_e, v_f_c = v_f * p_e_f, v_f * (1-p_e_f)
                hc_f_act = math.ceil(((v_f_e * m_info['AHT Email FLS'] + v_f_c * m_info['AHT Chat FLS'])/3600/f_c)/(1-(shrinkage_input/100)))
                hc_f_tar = math.ceil(((v_f_e * a_f_e_tar*60 + v_f_c * a_f_c_tar*60)/3600/f_c)/(1-(shrinkage_input/100)))
                
                # SLS (Lógica Vol <= 1)
                p_e_s = m_info['Vol Email SLS'] / (m_info['Vol Email SLS'] + m_info['Vol Chat SLS'])
                v_s_e, v_s_c = v_s * p_e_s, v_s * (1-p_e_s)
                hc_s_act = 1 if (v_s > 0 and v_s <= 1) else math.ceil(((v_s_e * m_info['AHT Email SLS'] + v_s_c * m_info['AHT Chat SLS'])/3600/s_c)/(1-(shrinkage_input/100)))
                hc_s_tar = 1 if (v_s > 0 and v_s <= 1) else math.ceil(((v_s_e * a_s_e_tar*60 + v_s_c * a_s_c_tar*60)/3600/s_c)/(1-(shrinkage_input/100)))

                mesh.append({
                    "Hour": f"{h:02d}:00", "Vol FLS": int(v_f), "HC FLS (Act)": hc_f_act, "HC FLS (Tar)": hc_f_tar,
                    "Vol SLS": int(v_s), "HC SLS (Act)": hc_s_act, "HC SLS (Tar)": hc_s_tar, "Total HC": hc_f_act + hc_s_act
                })
            
            st.subheader("Hourly Distribution (FLS and SLS)")
            df_mesh = pd.DataFrame(mesh)
            st.table(df_mesh.style.pipe(style_levels))
            
            # Gráfico de Volumen, AHT y Agentes
            st.subheader("Interval Performance: Volume and Staffing")
            st.line_chart(df_mesh.set_index('Hour')[['Vol FLS', 'Vol SLS', 'HC FLS (Act)', 'HC SLS (Act)']])

            st.divider()
            # ROSTER DISCRIMINADO
            st.subheader(f"Suggested Monthly Roster (Headcount: {m_info['Total HC']})")
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            roster = []
            
            # Crear Roster para FLS
            for i in range(1, m_info['FLS HC'] + 1):
                start_h = (i % 24); end_h = (start_h + 9) % 24
                off1 = days_order[(i % 7)]; off2 = days_order[((i + 1) % 7)]
                row = {"Agent": f"Agent FLS {i:02d}", "Level": "FLS", "Shift": f"{start_h:02d}:00-{end_h:02d}:00"}
                for d in days_order:
                    if d in [off1, off2]: row[d] = "OFF"
                    else: row[d] = f"Work (Lunch @ {(start_h+4)%24:02d}:00)"
                roster.append(row)
                
            # Crear Roster para SLS
            for i in range(1, m_info['SLS HC'] + 1):
                start_h = (i % 24); end_h = (start_h + 9) % 24
                off1 = days_order[(i % 7)]; off2 = days_order[((i + 1) % 7)]
                row = {"Agent": f"Agent SLS {i:02d}", "Level": "SLS", "Shift": f"{start_h:02d}:00-{end_h:02d}:00"}
                for d in days_order:
                    if d in [off1, off2]: row[d] = "OFF"
                    else: row[d] = f"Work (Lunch @ {(start_h+4)%24:02d}:00)"
                roster.append(row)
            
            df_roster = pd.DataFrame(roster)
            st.table(df_roster.style.pipe(style_levels))
            st.write(f"**Total Assigned Headcount:** {len(df_roster)}")
            
            # Botón de Descarga
            excel_data = to_excel([df_mesh, df_roster], ["Analysis", "Roster"])
            st.download_button(label="Download Excel Report", data=excel_data, file_name=f"WFM_Report_{current_month}.xlsx")
