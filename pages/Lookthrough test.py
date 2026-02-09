#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 15 09:03:17 2025

@author: lucademarco
"""

# applicazione/pages/Lookthrough.py

import streamlit as st
import pandas as pd
from datetime import datetime

# Importa i moduli della tua applicazione
from config import APP_CONFIG
from data_repository import data_repository
from utils import ui_components, format_date, data_exporter, create_info_box, check_page_access_auth0
from validators import ErrorHandler

# ============================================
# 🔐 CONTROLLO ACCESSO
# ============================================
check_page_access_auth0("Lookthrough")

# ... (mantenere gli import iniziali)

def main():
    st.set_page_config(layout=APP_CONFIG.layout)
    st.title("🔬 Lookthrough Multi-Fondo")

    if 'portfolio_data' not in st.session_state or st.session_state['portfolio_data'].empty:
        st.error("❌ Dati di portafoglio non trovati.")
        st.stop()
    
    portfolio_data = st.session_state['portfolio_data']

    # --- 1. Sidebar con Opzione "Tutti i Fondi" ---
    st.sidebar.header("🔧 Filtri di Analisi")
    
    lista_fondi = ["Tutti i Fondi"] + list(portfolio_data['DescrizioneFondo'].unique()) # Assumendo che la colonna si chiami così
    selected_fund = st.sidebar.selectbox("1. Seleziona Fondo:", lista_fondi, index=0)

    # Date Range (calcolato sull'intero dataset o sul fondo specifico)
    temp_df = portfolio_data if selected_fund == "Tutti i Fondi" else portfolio_data[portfolio_data['DescrizioneFondo'] == selected_fund]
    min_date, max_date = temp_df['DataRiferimento'].min(), temp_df['DataRiferimento'].max()

    selected_date = st.sidebar.date_input("2. Seleziona data:", value=max_date, min_value=min_date, max_value=max_date)

    # --- 2. Filtro Ricerca Titolo (Il cuore della richiesta) ---
    st.markdown("### 🔍 Ricerca Rapida Strumento")
    search_query = st.text_input("Inserisci ISIN o parte del nome del titolo:", placeholder="Es: IT000...", help="Filtra immediatamente tutti i fondi per questo valore")

    # --- 3. Logica di Estrazione Dati ---
    # Se "Tutti i fondi", prendiamo i dati di tutti per quella data
    if selected_fund == "Tutti i Fondi":
        composition_df = portfolio_data[portfolio_data['DataRiferimento'].dt.date == selected_date].copy()
    else:
        composition_df = data_repository.get_fund_data_for_date(portfolio_data, selected_fund, datetime.combine(selected_date, datetime.min.time()))

    if composition_df.empty:
        st.warning("Nessun dato trovato per i parametri selezionati.")
        st.stop()

    # Applicazione filtro di ricerca testuale
    if search_query:
        composition_df = composition_df[
            composition_df['DesTitolo'].str.contains(search_query, case=False, na=False) | 
            composition_df['ISIN'].str.contains(search_query, case=False, na=False)
        ]

    # --- 4. Filtri a colonna "Stile Excel" ---
    # Creiamo dei multiselect in colonne per non occupare troppo spazio
    st.write("### 📊 Filtri Tabella")
    f1, f2, f3 = st.columns(3)
    
    with f1:
        if 'DescrizioneFondo' in composition_df.columns:
            fondi_disponibili = sorted(composition_df['DescrizioneFondo'].unique())
            sel_fondi = st.multiselect("Filtra Fondi:", fondi_disponibili, default=fondi_disponibili)
            composition_df = composition_df[composition_df['DescrizioneFondo'].isin(sel_fondi)]

    with f2:
        settori = sorted(composition_df['DescrizioneSector'].dropna().unique())
        sel_settori = st.multiselect("Filtra Settori:", settori, default=settori)
        composition_df = composition_df[composition_df['DescrizioneSector'].isin(sel_settori)]

    with f3:
        rating = sorted(composition_df['Rating'].dropna().unique())
        sel_rating = st.multiselect("Filtra Rating:", rating, default=rating)
        composition_df = composition_df[composition_df['Rating'].isin(sel_rating)]

    # --- 5. Visualizzazione ---
    # Aggiungiamo 'DescrizioneFondo' alle colonne da mostrare se siamo in modalità "Tutti"
    display_cols = ['DescrizioneFondo', 'DesTitolo', 'PesoPort', 'DescrizioneSector', 'Rating', 'ISIN']
    available_cols = [c for c in display_cols if c in composition_df.columns]
    
    display_df = composition_df[available_cols].sort_values(by=['DescrizioneFondo', 'PesoPort'], ascending=[True, False])

    st.dataframe(
        display_df.style.format({"PesoPort": "{:.2f}%"}), 
        use_container_width=True, 
        height=600,
        hide_index=True
    )

    # Metriche aggregate
    st.markdown("---")
    c1, c2 = st.columns(2)
    c1.metric("Titoli trovati", len(display_df))
    if not display_df.empty:
        c2.metric("Esposizione Totale (filtro)", f"{composition_df['PesoPort'].sum():.2f}%")

if __name__ == "__main__":
    main()

