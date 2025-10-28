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

def main():
    """
    Funzione principale per la pagina di Lookthrough del Portafoglio.
    """
    # --- 1. Configurazione Iniziale e Validazione Dati ---
    st.set_page_config(layout=APP_CONFIG.layout)
    st.title("🔬 Lookthrough di Portafoglio")

    # Controlla che i dati siano stati caricati in sessione
    if 'portfolio_data' not in st.session_state or st.session_state['portfolio_data'].empty:
        st.error("❌ Dati di portafoglio non trovati. Torna alla Home per caricarli.")
        st.stop()
    
    portfolio_data = st.session_state['portfolio_data']

    # --- 2. Controlli nella Sidebar ---
    st.sidebar.header("🔧 Filtri di Analisi")

    # Selettore del fondo
    selected_fund = ui_components.create_fund_selector(
        portfolio_data, 
        label="1. Seleziona un Fondo:", 
        key="lookthrough_fund_selector"
    )

    if not selected_fund:
        st.info("Seleziona un fondo dalla barra laterale per iniziare.")
        st.stop()

    # Ottieni il range di date disponibile per il fondo selezionato
    try:
        min_date, max_date = data_repository.get_date_range(portfolio_data, selected_fund)
    except Exception as e:
        st.error(f"Impossibile determinare il range di date per il fondo {selected_fund}.")
        ErrorHandler.handle_calculation_error(e, "date range retrieval")
        st.stop()

    # Selettore della data
    selected_date = st.sidebar.date_input(
        "2. Seleziona una data:",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        key="lookthrough_date_selector",
        help="Scegli la data per cui visualizzare la composizione del portafoglio."
    )

    # --- 3. Logica di Filtro e Visualizzazione Dati ---
    st.header(f"Composizione di {selected_fund} al {format_date(selected_date)}")

    # Converti la data selezionata in datetime per il filtraggio
    selected_datetime = datetime.combine(selected_date, datetime.min.time())

    # Recupera i dati per il fondo e la data specifici
    composition_df = data_repository.get_fund_data_for_date(
        portfolio_data, selected_fund, selected_datetime
    )

    if composition_df.empty:
        st.warning(f"Nessun dato di portafoglio trovato per la data selezionata o per date precedenti.")
        st.stop()
        
    actual_date = composition_df['DataRiferimento'].iloc[0]
    if actual_date.date() != selected_date:
        create_info_box(
            "Nota sulla Data",
            f"Nessun dato per il {format_date(selected_date)}. Vengono mostrati i dati del giorno precedente più vicino: **{format_date(actual_date)}**.",
            "info"
        )

    # --- Preparazione colonne ---
    display_cols = [
        'DesTitolo', 
        'PesoPort', 
        'DescrizioneSector', 
        'CodiceTipo',
        'Rating', 
        'CodicePaeseEsposizione', 
        'CodiceDivisaEsposizione', 
        'ISIN', 
        'CodiceBloomberg'
    ]
    
    available_cols = [col for col in display_cols if col in composition_df.columns]
    display_df = composition_df[available_cols].copy()
    display_df = display_df.sort_values('PesoPort', ascending=False).reset_index(drop=True)

    # --- 🎛️ FILTRO CodiceTipo (stile Excel) ---
    if 'CodiceTipo' in display_df.columns:
        unique_types = sorted(display_df['CodiceTipo'].dropna().unique())
        selected_types = st.multiselect(
            "Filtra per tipo di strumento (CodiceTipo):",
            options=unique_types,
            default=unique_types,
            help="Deseleziona o seleziona i tipi di strumento che vuoi visualizzare."
        )

        display_df = display_df[display_df['CodiceTipo'].isin(selected_types)].reset_index(drop=True)

    # --- 🔍 FILTRO SETTORI (stile Excel) ---
    if 'DescrizioneSector' in display_df.columns:
        unique_sectors = sorted(display_df['DescrizioneSector'].dropna().unique())
        selected_sectors = st.multiselect(
            "Filtra per settore (DescrizioneSector):",
            options=unique_sectors,
            default=unique_sectors,
            help="Deseleziona o seleziona i settori che vuoi visualizzare."
        )

        display_df = display_df[display_df['DescrizioneSector'].isin(selected_sectors)].reset_index(drop=True)

    # --- 💄 Formattazione ---
    formatted_df = display_df.copy()
    if 'PesoPort' in formatted_df.columns:
        formatted_df['PesoPort'] = formatted_df['PesoPort'].map('{:.2f}%'.format)

    # --- 📊 Info + Pulsante Esporta in una riga ---
    col_info, col_export = st.columns([0.8, 0.2])
    with col_info:
        st.info("Puoi ordinare la tabella cliccando sulle intestazioni delle colonne o usare l'icona 🔍 per filtrare.")
    with col_export:
        st.download_button(
            label="📅 Esporta Dati in Excel",
            data=data_exporter.to_excel_download(display_df),
            file_name=f"lookthrough_{selected_fund}_{selected_date.strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Scarica la composizione del portafoglio visualizzata in un file Excel."
        )

    # --- Mostra la tabella ---
    st.dataframe(formatted_df, use_container_width=True, height=500)
    
    # --- 4. Visualizzazione Metriche ---
    total_weight = display_df['PesoPort'].sum()
    num_holdings = len(display_df)
    top_holding_row = display_df.loc[display_df['PesoPort'].idxmax()]

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Numero Titoli in Portafoglio", f"{num_holdings}")
    col2.metric("Peso Totale Calcolato", f"{total_weight:.2f}%")
    col3.metric("Titolo con Peso Maggiore", top_holding_row['DesTitolo'], f"{top_holding_row['PesoPort']:.2f}%")
    st.markdown("---")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("Si è verificato un errore inaspettato durante l'esecuzione della pagina.")
        ErrorHandler.handle_calculation_error(e, "Pagina Lookthrough")
