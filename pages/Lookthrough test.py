import streamlit as st
import pandas as pd
from datetime import datetime

# Importa i moduli della tua applicazione
from config import APP_CONFIG
from data_repository import data_repository
from utils import data_exporter, check_page_access_auth0

# ============================================
# 🔐 CONTROLLO ACCESSO
# ============================================
check_page_access_auth0("Lookthrough")

def main():
    st.set_page_config(layout=APP_CONFIG.layout)
    st.title("🔬 Lookthrough Multi-Fondo")

    # 1. Caricamento Dati
    if 'portfolio_data' not in st.session_state or st.session_state['portfolio_data'].empty:
        st.error("❌ Dati di portafoglio non trovati.")
        st.stop()
    
    portfolio_data = st.session_state['portfolio_data']
    fund_col = 'Descrizione' # Colonna identificata in data_repository.py

    # --- 2. Sidebar: Selezione Multipla Fondi ---
    st.sidebar.header("🔧 Filtri Generali")
    
    available_funds = data_repository.get_available_funds(portfolio_data)
    
    # Ora è un multiselect: di default sono selezionati tutti ("Tutti i fondi")
    selected_funds = st.sidebar.multiselect(
        "1. Seleziona Fondi:",
        options=available_funds,
        default=available_funds,
        help="Rimuovi i fondi che non vuoi vedere o selezionali singolarmente."
    )

    if not selected_funds:
        st.warning("⚠️ Seleziona almeno un fondo nella barra laterale per vedere i dati.")
        st.stop()

    # Filtriamo il dataframe per i fondi selezionati per calcolare il range date corretto
    df_funds_filtered = portfolio_data[portfolio_data[fund_col].isin(selected_funds)]
    
    min_date = df_funds_filtered['DataRiferimento'].min()
    max_date = df_funds_filtered['DataRiferimento'].max()

    selected_date = st.sidebar.date_input(
        "2. Seleziona data:", 
        value=max_date, 
        min_value=min_date, 
        max_value=max_date
    )
    target_datetime = datetime.combine(selected_date, datetime.min.time())

    # --- 3. Dati Base Filtrati ---
    base_df = df_funds_filtered[df_funds_filtered['DataRiferimento'] == target_datetime].copy()

    if base_df.empty:
        st.warning(f"Nessun dato trovato per la data {selected_date.strftime('%d/%m/%Y')}.")
        st.stop()

    # --- 4. Ricerca con Suggerimenti (Autocomplete) ---
    st.markdown("### 🔍 Ricerca Strumento")
    all_titles = sorted(base_df['DesTitolo'].unique())
    
    selected_titles = st.multiselect(
        "Cerca titolo nel portafoglio (es. scrivi 'NV' per NVIDIA):",
        options=all_titles,
        help="Inizia a scrivere per filtrare i suggerimenti."
    )

    # --- 5. Filtri "Stile Excel" ---
    st.write("### 📊 Altri Filtri")
    f1, f2 = st.columns(2)
    
    filtered_df = base_df.copy()

    # Filtro Titoli (se l'utente ha usato l'autocomplete)
    if selected_titles:
        filtered_df = filtered_df[filtered_df['DesTitolo'].isin(selected_titles)]

    with f1:
        if 'DescrizioneSector' in filtered_df.columns:
            u_sectors = sorted(filtered_df['DescrizioneSector'].dropna().unique())
            sel_sectors = st.multiselect("Filtra Settore:", u_sectors, default=u_sectors)
            filtered_df = filtered_df[filtered_df['DescrizioneSector'].isin(sel_sectors)]

    with f2:
        col_tipo = 'TipoStrumento' if 'TipoStrumento' in filtered_df.columns else 'CodiceTipo'
        if col_tipo in filtered_df.columns:
            u_types = sorted(filtered_df[col_tipo].dropna().unique())
            sel_types = st.multiselect("Filtra Tipo Strumento:", u_types, default=u_types)
            filtered_df = filtered_df[filtered_df[col_tipo].isin(sel_types)]

    # --- 6. Tabella Risultati con Nuove Colonne ---
    # Aggiunte CodiceDivisaEsposizione e CodicePaeseEsposizione
    display_cols = [
        fund_col, 'DesTitolo', 'ISIN', 'PesoPort', 
        'DescrizioneSector', 'TipoStrumento', 
        'CodiceDivisaEsposizione', 'CodicePaeseEsposizione'
    ]
    
    # Filtriamo solo le colonne effettivamente presenti nel DF per evitare errori
    final_cols = [c for c in display_cols if c in filtered_df.columns]
    
    # Ordinamento per Fondo e Peso decrescente
    final_df = filtered_df[final_cols].sort_values(
        by=[fund_col, 'PesoPort'], 
        ascending=[True, False]
    )

    # Formattazione per la visualizzazione Streamlit
    view_df = final_df.copy()
    if 'PesoPort' in view_df.columns:
        view_df['PesoPort'] = view_df['PesoPort'].map('{:.2f}%'.format)

    st.dataframe(
        view_df, 
        use_container_width=True, 
        height=550, 
        hide_index=True
    )

    # --- 7. Esportazione e Metriche ---
    st.download_button(
        label="📥 Esporta questa vista (Excel)",
        data=data_exporter.to_excel_download(final_df),
        file_name=f"export_lookthrough_{selected_date.strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Titoli Visualizzati", len(final_df))
    m2.metric("Fondi Selezionati", final_df[fund_col].nunique() if fund_col in final_df.columns else 0)
    if not final_df.empty:
        # Calcolo del peso totale basato sulla selezione (attenzione: se sono più fondi, il totale non sarà 100%)
        m3.metric("Peso Sommato", f"{final_df['PesoPort'].sum():.2f}%")

if __name__ == "__main__":
    main()