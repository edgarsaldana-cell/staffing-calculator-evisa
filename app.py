import streamlit as st
import math

st.set_page_config(page_title="Calculadora Staffing eVisa", layout="wide")

st.title("Calculadora de Staffing - iVisa Support")

# --- CONFIGURACIÓN GLOBAL (SIDEBAR) ---
st.sidebar.header("⚙️ Parámetros del Mes")
shrinkage = st.sidebar.slider("Shrinkage (%)", 0, 50, 10) / 100
hrs_turno = st.sidebar.number_input("Horas por Turno", value=8)
dias_mes = st.sidebar.number_input("Días Laborales del Mes", value=21)

# Capacidad por agente
hrs_disponibles = (dias_mes * hrs_turno) * (1 - shrinkage)
st.sidebar.divider()
st.sidebar.metric("Capacidad Real / Agente", f"{hrs_disponibles:.1f} hrs")

# --- NIVEL 1 (FLS) ---
st.header("FLS")
col1, col2 = st.columns(2)

with col1:
    st.subheader("💬 Chat FLS")
    vol_chat_fls = st.number_input("Volumen Chat FLS", value=11691)
    aht_chat_fls = st.number_input("AHT Chat FLS (seg)", value=3731)
    concur_fls = st.number_input("Concurrencia FLS", value=2.0, key="c1")
    
    workload_chat_fls = (vol_chat_fls * aht_chat_fls) / 3600 / concur_fls

with col2:
    st.subheader("✉️ Email FLS")
    vol_mail_fls = st.number_input("Volumen Email FLS", value=4595)
    aht_mail_fls = st.number_input("AHT Email FLS (seg)", value=3215)
    # El email suele tener concurrencia diferente o igual, aquí usamos la de FLS
    workload_mail_fls = (vol_mail_fls * aht_mail_fls) / 3600 / concur_fls

agentes_fls = math.ceil((workload_chat_fls + workload_mail_fls) / hrs_disponibles)
st.info(f"💡 Agentes necesarios para FLS: **{agentes_fls}**")

st.divider()

# --- NIVEL 2 (SLS) ---
st.header("SLS")
col3, col4 = st.columns(2)

with col3:
    st.subheader("💬 Chat SLS")
    vol_chat_sls = st.number_input("Volumen Chat SLS", value=1085)
    aht_chat_sls = st.number_input("AHT Chat SLS (seg)", value=7324)
    concur_sls = st.number_input("Concurrencia SLS", value=1.5, key="c2")
    
    workload_chat_sls = (vol_chat_sls * aht_chat_sls) / 3600 / concur_sls

with col4:
    st.subheader("✉️ Email SLS")
    vol_mail_sls = st.number_input("Volumen Email SLS", value=361)
    aht_mail_sls = st.number_input("AHT Email SLS (seg)", value=9927)
    workload_mail_sls = (vol_mail_sls * aht_mail_sls) / 3600 / concur_sls

agentes_sls = math.ceil((workload_chat_sls + workload_mail_sls) / hrs_disponibles)
st.info(f"💡 Agentes necesarios para SLS: **{agentes_sls}**")

st.divider()

# --- RESULTADO FINAL ---
total_hc = agentes_fls + agentes_sls
st.balloons()
st.success(f"### ✅ Headcount TOTAL Requerido: {total_hc} agentes")
