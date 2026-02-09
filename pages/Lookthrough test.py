import streamlit as st
import pandas as pd
from datetime import datetime

# Importa i moduli della tua applicazione
from config import APP_CONFIG
from data_repository import data_repository
from utils import format_date, data_exporter, check_page_access_auth0
from validators import ErrorHandler

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

    # --- 2. Sidebar: Selezione Fondo e Data ---
    st.sidebar.header("🔧 Filtri Generali")
    
    available_funds = data_repository.get_available_funds(portfolio_data)
    fund_options = ["Tutti i Fondi"] + available_funds
    selected_fund = st.sidebar.selectbox("1. Seleziona Fondo:", options=fund_options, index=0)

    # Range date
    if selected_fund == "Tutti i Fondi":
        min_date, max_date = portfolio_data['DataRiferimento'].min(), portfolio_data['DataRiferimento'].max()
    else:
        min_date, max_date = data_repository.get_date_range(portfolio_data, selected_fund)

    selected_date = st.sidebar.date_input("2. Seleziona data:", value=max_date, min_value=min_date, max_value=max_date)
    target_datetime = datetime.combine(selected_date, datetime.min.time())

    # --- 3. Dati Base (Filtrati per Data e Fondo) ---
    if selected_fund == "Tutti i Fondi":
        base_df = portfolio_data[portfolio_data['DataRiferimento'] == target_datetime].copy()
    else:
        base_df = data_repository.get_fund_data_for_date(portfolio_data, selected_fund, target_datetime)

    if base_df.empty:
        st.warning("Nessun dato trovato per questa data.")
        st.stop()

    # --- 4. Ricerca con Suggerimenti (Autocomplete) ---
    st.markdown("### 🔍 Ricerca Strumento")
    
    # Creiamo una lista unica di titoli per i suggerimenti
    # Ordiniamo alfabeticamente per facilitare la ricerca
    all_titles = sorted(base_df['DesTitolo'].unique())
    
    selected_titles = st.multiselect(
        "Digita il nome di un titolo (es. 'NV' per NVIDIA):",
        options=all_titles,
        help="Inizia a scrivere per vedere i suggerimenti. Puoi selezionare più titoli contemporaneamente."
    )

    # --- 5. Filtri "Stile Excel" ---
    st.write("### 📊 Altri Filtri")
    f1, f2 = st.columns(2)
    
    filtered_df = base_df.copy()

    # Applichiamo il filtro titoli se l'utente ha selezionato qualcosa
    if selected_titles:
        filtered_df = filtered_df[filtered_df['DesTitolo'].isin(selected_titles)]

    with f1:
        if 'DescrizioneSector' in filtered_df.columns:
            u_sectors = sorted(filtered_df['DescrizioneSector'].dropna().unique())
            sel_sectors = st.multiselect("Settore:", u_sectors, default=u_sectors)
            filtered_df = filtered_df[filtered_df['DescrizioneSector'].isin(sel_sectors)]

    with f2:
        # Usiamo TipoStrumento invece di CodiceTipo perché è popolata da data_repository
        col_tipo = 'TipoStrumento' if 'TipoStrumento' in filtered_df.columns else 'CodiceTipo'
        u_types = sorted(filtered_df[col_tipo].dropna().unique())
        sel_types = st.multiselect("Tipo Strumento:", u_types, default=u_types)
        filtered_df = filtered_df[filtered_df[col_tipo].isin(sel_types)]

    # --- 6. Tabella Risultati ---
    # Inseriamo TipoStrumento nella visualizzazione
    display_cols = [fund_col, 'DesTitolo', 'PesoPort', 'DescrizioneSector', 'TipoStrumento', 'ISIN']
    available_cols = [c for c in display_cols if c in filtered_df.columns]
    
    final_df = filtered_df[available_cols].sort_values(by=[fund_col, 'PesoPort'], ascending=[True, False])

    # Formattazione per la vista
    view_df = final_df.copy()
    if 'PesoPort' in view_df.columns:
        view_df['PesoPort'] = view_df['PesoPort'].map('{:.2f}%'.format)

    st.dataframe(view_df, use_container_width=True, height=500, hide_index=True)

    # Esportazione e Metriche
    st.download_button(
        label="📥 Esporta questa vista in Excel",
        data=data_exporter.to_excel_download(final_df),
        file_name=f"lookthrough_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Titoli in vista", len(final_df))
    m2.metric("Fondi coinvolti", final_df[fund_col].nunique())
    m3.metric("Peso Totale", f"{final_df['PesoPort'].sum():.2f}%")

if __name__ == "__main__":
    main()