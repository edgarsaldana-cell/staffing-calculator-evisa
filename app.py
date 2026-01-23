import streamlit as st
import math

st.set_page_config(page_title="Calculadora Staffing eVisa", layout="wide")

st.title("Calculadora de Staffing - iVisa Support")

# --- CONFIGURACIÓN ---
st.sidebar.header("Parámetros Generales")
shrinkage = st.sidebar.slider("Shrinkage Target (%)", 0, 50, 10) / 100
hrs_turno = st.sidebar.number_input("Horas por Turno", value=8)
dias_mes = st.sidebar.number_input("Días Laborales del Mes", value=21)

# Capacidad por agente
hrs_disponibles = (dias_mes * hrs_turno) * (1 - shrinkage)
st.sidebar.info(f"Capacidad real por agente: {hrs_disponibles:.1f} hrs/mes")

# --- ENTRADA DE DATOS ---
col1, col2 = st.columns(2)

with col1:
    st.header("Nivel 1 (FLS)")
    vol_fls = st.number_input("Volumen Total FLS", value=1000)
    aht_fls = st.number_input("AHT FLS (segundos)", value=400)
    concur_fls = st.number_input("Concurrencia FLS", value=2.0)
    
    workload_fls = (vol_fls * aht_fls) / 3600 / concur_fls
    agentes_fls = math.ceil(workload_fls / hrs_disponibles) if hrs_disponibles > 0 else 0
    st.metric("Agentes FLS Necesarios", agentes_fls)

with col2:
    st.header("Nivel 2 (SLS)")
    vol_sls = st.number_input("Volumen Total SLS", value=200)
    aht_sls = st.number_input("AHT SLS (segundos)", value=1500)
    concur_sls = st.number_input("Concurrencia SLS", value=1.5)
    
    workload_sls = (vol_sls * aht_sls) / 3600 / concur_sls
    agentes_sls = math.ceil(workload_sls / hrs_disponibles) if hrs_disponibles > 0 else 0
    st.metric("Agentes SLS Necesarios", agentes_sls)

st.divider()
st.header(f"Total Headcount Requerido: {agentes_fls + agentes_sls} agentes")
