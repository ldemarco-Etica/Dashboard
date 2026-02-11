#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  6 11:30:42 2025

@author: lucademarco
"""

import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import timedelta, datetime
from utils import format_date, check_page_access_auth0

# ============================================
# CONTROLLO ACCESSO RUOLI
# ============================================
check_page_access_auth0("AUM")

# === Logica della pagina AUM ===
st.set_page_config(layout="wide")
st.title("💰 Analisi AUM ")

df_tot_original = st.session_state.get("aum_data", pd.DataFrame())
dfs_fondi_original = st.session_state.get("aum_fondi", {})

if df_tot_original.empty and not dfs_fondi_original:
    st.warning("Dati AUM non caricati. Impossibile visualizzare la pagina.")
    st.stop()

vista = st.sidebar.radio(
    "Seleziona la vista",
    ["Confronto fondi", "Serie storica AUM", "Decomposizione variazione", "Contributi cumulati"]
)

# Filtro data unificato per le viste AUM (escluso 'Confronto fondi')
if vista != "Confronto fondi" and not df_tot_original.empty:
    min_date_aum = df_tot_original["Data"].min().to_pydatetime()
    max_date_aum = df_tot_original["Data"].max().to_pydatetime()

    preset_aum = st.sidebar.selectbox(
        "Periodo predefinito",
        ["Tutto", "Ultimi 3 mesi", "Ultimi 6 mesi", "Ultimo anno", "YTD", "Personalizzato"],
        key="aum_period"
    )
    
    today_aum = max_date_aum
    if preset_aum == "Ultimi 3 mesi":
        start_date_aum, end_date_aum = today_aum - timedelta(days=90), today_aum
    elif preset_aum == "Ultimi 6 mesi":
        start_date_aum, end_date_aum = today_aum - timedelta(days=180), today_aum
    elif preset_aum == "Ultimo anno":
        start_date_aum, end_date_aum = today_aum - timedelta(days=365), today_aum
    elif preset_aum == "YTD":
        start_date_aum, end_date_aum = datetime(year=today_aum.year, month=1, day=1), today_aum
    elif preset_aum == "Tutto":
        start_date_aum, end_date_aum = min_date_aum, max_date_aum
    else: # Personalizzato
        start_date_aum, end_date_aum = st.sidebar.slider(
            "Seleziona l'intervallo temporale",
            min_value=min_date_aum,
            max_value=max_date_aum,
            value=(min_date_aum, max_date_aum),
            format="DD/MM/YYYY",
            key="aum_slider"
        )
    
    # Crea copie filtrate locali senza modificare gli originali
    df_tot = df_tot_original[(df_tot_original["Data"] >= start_date_aum) & (df_tot_original["Data"] <= end_date_aum)].copy()
    dfs_fondi = {}
    for fondo_key in dfs_fondi_original:
        dfs_fondi[fondo_key] = dfs_fondi_original[fondo_key][(dfs_fondi_original[fondo_key]["Data"] >= start_date_aum) & (dfs_fondi_original[fondo_key]["Data"] <= end_date_aum)].copy()

# --- Viste ---
if vista == "Confronto fondi":
    if df_tot_original.empty:
        st.error("Foglio totale AUM non disponibile.")
    else:
        # Preparazione dati generali
        df_melted = df_tot_original.melt(id_vars='Data', var_name='Fondo', value_name='AUM').dropna(subset=['AUM'])
        
        # --- CALCOLO KPI ATTUALE ---
        # Troviamo l'ultima data valida per ogni fondo
        df_last_valid = df_melted.loc[df_melted.groupby('Fondo')['Data'].idxmax()].copy()
        
        # Calcolo Totale sanitizzato (valori negativi considerati come 0)
        aum_totale = df_last_valid["AUM"].clip(lower=0).sum()
        ultima_data_generale = df_tot_original["Data"].max()
        
        # Visualizzazione KPI in alto
       
        st.metric(
            label=f"AUM Totale (al {format_date(ultima_data_generale.date())})",
            value=f"€ {aum_totale:,.2f}"
        )
        st.markdown("---")

        # --- GRAFICO 1: ANDAMENTO STORICO AGGREGATO (NO NEGATIVI) ---
        # Creiamo una copia per il calcolo storico
        df_history = df_melted.copy()
        # Sostituiamo i valori negativi con 0 prima di sommare
        df_history['AUM_Clean'] = df_history['AUM'].clip(lower=0)
        
        # Raggruppiamo per data sommando i valori puliti
        df_agg_history = df_history.groupby("Data")["AUM_Clean"].sum().reset_index()
        
        st.subheader("Andamento AUM Complessivo")
   
        
        fig_trend = px.area(
            df_agg_history,
            x="Data",
            y="AUM_Clean",
            title="Evoluzione AUM Totale (Esclusi fondi negativi)",
            labels={"AUM_Clean": "AUM Totale (€)", "Data": "Data"}
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("---")

        # --- GRAFICO 2: DETTAGLIO BAR CHART (ULTIMA DATA) ---
        st.subheader("Dettaglio per Fondo")
        
        fig_bar = px.bar(
            df_last_valid.sort_values("AUM", ascending=False),
            x="Fondo",
            y="AUM",
            title="AUM attuale per ciascun fondo",
            labels={"AUM": "AUM", "Fondo": "Fondo"},
            hover_data=['Data']
        )
        fig_bar.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Tabella dati
        st.dataframe(df_last_valid.sort_values("AUM", ascending=False))

elif vista == "Serie storica AUM":
    mode = st.sidebar.radio("Tipo di confronto", ["Singolo fondo", "Tutti i fondi"])
    if mode == "Singolo fondo":
        fondi = list(dfs_fondi.keys())
        if not fondi:
            st.error("Nessun foglio fondo trovato nel file AUM.")
        else:
            fondo_sel = st.sidebar.selectbox("Seleziona il fondo", fondi)
            df_fondo = dfs_fondi[fondo_sel].sort_values("Data")
            
            # Calcola AUM all'ultima data disponibile
            aum_ultima_data = df_fondo.iloc[-1]["AUM"] if not df_fondo.empty else 0
            ultima_data_fondo = df_fondo.iloc[-1]["Data"] if not df_fondo.empty else None
            
            st.subheader(f"Andamento AUM — {fondo_sel} (AUM al {format_date(ultima_data_fondo.date()) if ultima_data_fondo else 'N/A'}: €{aum_ultima_data:,.2f})")
            
            fig = px.line(df_fondo, x="Data", y="AUM", title=f"Andamento AUM - {fondo_sel}", labels={"AUM": "AUM", "Data": "Data"}, markers=True)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_fondo)
    else:
        if df_tot.empty:
            st.error("Foglio totale AUM non disponibile.")
        else:
            st.subheader("Andamento AUM — Tutti i fondi (foglio totale)")
            df_melt = df_tot.melt(id_vars="Data", var_name="Fondo", value_name="AUM").dropna(subset=['AUM'])
            df_melt = df_melt.sort_values(["Fondo", "Data"])
            fig = px.line(df_melt, x="Data", y="AUM", color="Fondo", title="Andamento AUM - Tutti i fondi", labels={"AUM": "AUM", "Data": "Data"})
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_melt)

elif vista == "Decomposizione variazione":
    fondi = list(dfs_fondi.keys())
    if not fondi:
        st.error("Nessun foglio fondo trovato nel file AUM.")
    else:
        fondo_sel = st.sidebar.selectbox("Seleziona il fondo", fondi)
        grouping = st.sidebar.radio("Raggruppamento", ["Mensile", "Annuale"])
        
        df_fondo = dfs_fondi[fondo_sel].sort_values("Data")
        st.subheader(f"Decomposizione variazione AUM — {fondo_sel}")

        df_grouped = df_fondo.copy()
        df_grouped = df_grouped.dropna(subset=["Data", "Effetto mercato", "Flussi netti"])

        if grouping == "Mensile":
            df_grouped["Periodo"] = df_grouped["Data"].dt.to_period("M").dt.to_timestamp()
            title_suffix = "mensile"
        else: # Annuale
            df_grouped["Periodo"] = df_grouped["Data"].dt.to_period("Y").dt.to_timestamp()
            title_suffix = "annuale"
        
        df_agg = df_grouped.groupby("Periodo")[["Effetto mercato", "Flussi netti"]].sum().reset_index()

        fig = px.bar(
            df_agg,
            x="Periodo",
            y=["Effetto mercato", "Flussi netti"],
            title=f"Decomposizione variazione AUM - {fondo_sel} ({title_suffix})",
            labels={"value": "Variazione AUM", "Periodo": "Periodo"},
            barmode="relative"
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_agg)

elif vista == "Contributi cumulati":
    fondi = list(dfs_fondi.keys())
    if not fondi:
        st.error("Nessun foglio fondo trovato nel file AUM.")
    else:
        fondo_sel = st.sidebar.selectbox("Seleziona il fondo", fondi)
        df_fondo = dfs_fondi[fondo_sel].sort_values("Data")
        st.subheader(f"Contributi cumulati all'AUM — {fondo_sel}")
        df_cum = df_fondo.copy()
        df_cum["Effetto mercato cumulato"] = df_cum["Effetto mercato"].fillna(0).cumsum()
        df_cum["Flussi netti cumulati"] = df_cum["Flussi netti"].fillna(0).cumsum()
        fig = px.area(df_cum, x="Data", y=["Effetto mercato cumulato", "Flussi netti cumulati"], title=f"Contributi cumulati all'AUM - {fondo_sel}", labels={"value": "Contributo cumulato", "Data": "Data"})
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_cum)
