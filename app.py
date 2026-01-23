import streamlit as st
import math
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="WFM Macro to Micro", layout="wide")

# --- HELPER FUNCTIONS ---
def get_working_days(year, month):
    start = pd.Timestamp(year, month, 1)
    end = start + pd.offsets.MonthEnd(0)
    return len(pd.bdate_range(start, end))

# --- MAIN APP ---
st.title("📊 Workforce Management: Macro to Micro Optimizer")

tab_calc, tab_bulk, tab_micro = st.tabs(["Macro: Monthly Calculator", "Bulk: Multi-Month", "Micro: Schedule Optimizer"])

# (Mantenemos la lógica de tab_calc y tab_bulk que ya funcionaba perfectamente)
# ... [Omitido por brevedad en la explicación, pero incluido en el bloque de código final que subirás] ...

with tab_micro:
    st.header("🗂️ Raw Data to Schedule Layout")
    
    col_u, col_p = st.columns([2, 1])
    
    with col_p:
        st.subheader("Optimization Parameters")
        target_aht = st.number_input("Average AHT for this Dataset (sec)", value=4500)
        target_concurrency = st.number_input("Target Concurrency (Micro)", value=1.75)
        downtime_weekly = st.number_input("Downtime minutes per week/agent", value=120, help="Coaching, meetings, etc.")
        
        # Recalculate Shrinkage with Downtime
        # 40 hours per week (2400 mins). 
        extra_shrinkage = (downtime_weekly / 2400) * 100
        st.info(f"Downtime adds **{extra_shrinkage:.2f}%** to your base shrinkage.")

    with col_u:
        st.subheader("1. Upload Raw Conversations")
        uploaded_file = st.file_uploader("Upload CSV (Columns: Conversation ID, Conversation started at (America/Lima))", type="csv")

    if uploaded_file is not None:
        try:
            df_raw = pd.read_csv(uploaded_file)
            # Date Parsing
            date_col = 'Conversation started at (America/Lima)'
            df_raw[date_col] = pd.to_datetime(df_raw[date_col])
            
            # Extract Hour and Day
            df_raw['Hour'] = df_raw[date_col].dt.hour
            df_raw['Date'] = df_raw[date_col].dt.date
            
            # Grouping by Hour (Average per day in the dataset)
            hourly_vol = df_raw.groupby(['Date', 'Hour']).size().reset_index(name='Count')
            avg_hourly_vol = hourly_vol.groupby('Hour')['Count'].mean().reset_index()
            
            st.subheader("2. Hourly Workload Analysis")
            
            # Calculate Staff Needed per Hour
            # Workload = (Vol * AHT) / 3600 / Concurrency
            avg_hourly_vol['Staff_Needed'] = (avg_hourly_vol['Count'] * target_aht) / 3600 / target_concurrency
            
            # Chart
            st.bar_chart(data=avg_hourly_vol, x='Hour', y='Staff_Needed')
            
            st.subheader("3. Suggested Schedule Mesh (9h Shifts)")
            st.write("Based on peak demand, here is the coverage requirement:")
            
            # Final Table
            schedule_mesh = []
            for _, row in avg_hourly_vol.iterrows():
                hour_label = f"{int(row['Hour'])}:00"
                agents_req = math.ceil(row['Staff_Needed'] / (1 - (extra_shrinkage/100)))
                schedule_mesh.append({
                    "Interval (Hour)": hour_label,
                    "Avg Conversations": round(row['Count'], 1),
                    "Net Agents Logged-in": round(row['Staff_Needed'], 1),
                    "Total Agents (inc. Downtime)": agents_req
                })
            
            st.table(schedule_mesh)
            
        except Exception as e:
            st.error(f"Error processing file: {e}. Check if column names match exactly.")
