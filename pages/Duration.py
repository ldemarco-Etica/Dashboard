#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 25 16:28:08 2025

@author: lucademarco
"""

# applicazione/pages/duration.py

import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import timedelta, datetime
from utils import format_date, check_page_access_auth0

# ============================================
# 🔐 CONTROLLO ACCESSO
# ============================================
check_page_access_auth0("Duration")

# === Logica della Pagina Duration ===
st.set_page_config(layout="wide")
st.title("⏳ Analisi Duration")

df = st.session_state.get("duration_data", pd.DataFrame())
if df.empty:
    st.warning("Dati Duration non caricati. Impossibile visualizzare la pagina.")
    st.stop()

# 🔀 Ho rinominato la vista per chiarezza
vista = st.sidebar.radio("Seleziona la vista", ["Serie storica fondo vs benchmark", "Confronto fondi"])

if vista == "Serie storica fondo vs benchmark":
    fondi = sorted(df["Fondo"].unique())
    fondo_sel = st.sidebar.selectbox("Seleziona il fondo", fondi)
    df_fondo = df[df["Fondo"] == fondo_sel].sort_values("Data")

    min_date = df_fondo["Data"].min().to_pydatetime()
    max_date = df_fondo["Data"].max().to_pydatetime()

    preset = st.sidebar.selectbox(
        "Periodo predefinito",
        ["Tutto", "Ultimi 3 mesi", "Ultimi 6 mesi", "Ultimo anno", "YTD", "Personalizzato"]
    )

    today = max_date
    if preset == "Ultimi 3 mesi":
        start_date, end_date = today - timedelta(days=90), today
    elif preset == "Ultimi 6 mesi":
        start_date, end_date = today - timedelta(days=180), today
    elif preset == "Ultimo anno":
        start_date, end_date = today - timedelta(days=365), today
    elif preset == "YTD":
        start_date, end_date = datetime(year=today.year, month=1, day=1), today
    elif preset == "Tutto":
        start_date, end_date = min_date, max_date
    else:
        start_date, end_date = st.sidebar.slider(
            "Seleziona l'intervallo temporale",
            min_value=min_date, max_value=max_date, value=(min_date, max_date),
            format="DD/MM/YYYY"
        )

    # 🛠️ Sistemati gli operatori logici (erano arrivati come HTML entities)
    df_fondo = df_fondo[(df_fondo["Data"] >= start_date) & (df_fondo["Data"] <= end_date)]

    fig = px.line(
        df_fondo,
        x="Data",
        y=["Duration Fondo", "Duration Benchmark"],
        markers=True,
        labels={"value": "Duration", "variable": "Serie"},
        title=f"Duration - {fondo_sel}",
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_fondo, use_container_width=True)

elif vista == "Confronto fondi":
    # 📅 Elenco date disponibili (ordinate dalla più recente)
    available_dates = sorted(df["Data"].unique(), reverse=True)

    # Selezione data (formattata gg/mm/aaaa)
    selected_date = st.sidebar.selectbox(
        "Seleziona la data",
        options=available_dates,
        format_func=lambda d: pd.to_datetime(d).strftime("%d/%m/%Y")
    )

    # Filtro per la data selezionata
    df_sel = df[df["Data"] == pd.to_datetime(selected_date)]

    st.subheader(f"📸 Fotografia per data - Duration al {format_date(pd.to_datetime(selected_date).date())}")

    # Ordinamento decrescente per 'Duration Fondo'
    df_sel_sorted = df_sel.sort_values("Duration Fondo", ascending=False)

    fig_bar = px.bar(
        df_sel_sorted,
        x="Fondo",
        y=["Duration Fondo", "Duration Benchmark"],
        barmode="group",
        title=f"Valori al {pd.to_datetime(selected_date).date()}",
        labels={"value": "Duration", "variable": "Serie"},
        height=600
    )
    fig_bar.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_bar, use_container_width=True)
    st.dataframe(df_sel_sorted, use_container_width=True)
