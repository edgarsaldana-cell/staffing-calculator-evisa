{\rtf1\ansi\ansicpg1252\cocoartf2867
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import pandas as pd\
import math\
\
# Configuraci\'f3n de la p\'e1gina\
st.set_page_config(page_title="Calculadora de Staffing eVisa", layout="wide")\
\
st.title("\uc0\u55357 \u56522  Calculadora de Staffing Din\'e1mica")\
\
# --- PANEL LATERAL (INPUTS) ---\
st.sidebar.header("Configuraci\'f3n de Variables")\
hours_shift = st.sidebar.number_input("Horas por Turno", value=8)\
shrinkage = st.sidebar.slider("Shrinkage (%)", 0, 100, 10) / 100\
concurrency_fls = st.sidebar.number_input("Concurrencia FLS", value=2.0)\
concurrency_sls = st.sidebar.number_input("Concurrencia SLS", value=1.5)\
\
# --- ENTRADA DE DATOS ---\
st.header("Entrada de Datos Mensuales")\
col1, col2, col3 = st.columns(3)\
\
with col1:\
    month_name = st.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])\
    work_days = st.number_input("D\'edas Laborales del Mes", value=21)\
\
with col2:\
    vol_fls = st.number_input("Volumen FLS (Total)", value=1000)\
    aht_fls = st.number_input("AHT FLS (Segundos)", value=400)\
\
with col3:\
    vol_sls = st.number_input("Volumen SLS (Total)", value=200)\
    aht_sls = st.number_input("AHT SLS (Segundos)", value=1500)\
\
# --- C\'c1LCULOS LOGICOS ---\
# 1. Capacidad individual\
hrs_eff = work_days * hours_shift * (1 - shrinkage)\
\
# 2. Carga de trabajo (Workload)\
workload_fls = (vol_fls * aht_fls) / 3600 / concurrency_fls\
workload_sls = (vol_sls * aht_sls) / 3600 / concurrency_sls\
\
# 3. FTEs\
fte_fls = math.ceil(workload_fls / hrs_eff) if hrs_eff > 0 else 0\
fte_sls = math.ceil(workload_sls / hrs_eff) if hrs_eff > 0 else 0\
\
# --- RESULTADOS ---\
st.divider()\
st.subheader(f"Resultados para \{month_name\}")\
\
res_col1, res_col2, res_col3 = st.columns(3)\
res_col1.metric("Agentes FLS", f"\{fte_fls\}")\
res_col2.metric("Agentes SLS", f"\{fte_sls\}")\
res_col3.metric("Total Headcount", f"\{fte_fls + fte_sls\}")\
\
st.info(f"Cada agente trabajar\'e1 \{hrs_eff:.1f\} horas efectivas en el mes.")}
