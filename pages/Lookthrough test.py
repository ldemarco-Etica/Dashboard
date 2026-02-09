import streamlit as st
import pandas as pd
from datetime import datetime

# Importa i moduli della tua applicazione
from config import APP_CONFIG
from data_repository import data_repository
from utils import format_date, data_exporter, create_info_box, check_page_access_auth0
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
        st.error("❌ Dati di portafoglio non trovati. Torna alla Home per caricarli.")
        st.stop()
    
    portfolio_data = st.session_state['portfolio_data']
    fund_col = 'Descrizione' # Colonna corretta identificata in data_repository.py

    # --- 2. Sidebar: Selettore Fondo con opzione "Tutti" ---
    st.sidebar.header("🔧 Filtri di Analisi")
    
    available_funds = data_repository.get_available_funds(portfolio_data)
    fund_options = ["Tutti i Fondi"] + available_funds
    
    selected_fund = st.sidebar.selectbox(
        "1. Seleziona Fondo:",
        options=fund_options,
        index=0, # Default su "Tutti i Fondi" come richiesto
        key="multi_fund_selector"
    )

    # Determinazione del range di date
    if selected_fund == "Tutti i Fondi":
        min_date = portfolio_data['DataRiferimento'].min()
        max_date = portfolio_data['DataRiferimento'].max()
    else:
        min_date, max_date = data_repository.get_date_range(portfolio_data, selected_fund)

    selected_date = st.sidebar.date_input(
        "2. Seleziona data:",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )

    # --- 3. Ricerca Specifica Titolo (Per trovare un titolo in tutti i fondi) ---
    st.markdown("### 🔍 Ricerca Rapida Strumento")
    search_query = st.text_input(
        "Inserisci ISIN o Nome Titolo:", 
        placeholder="Es: IT000..., ENEL, APPLE...",
        help="Cerca il titolo all'interno di tutti i fondi selezionati"
    )

    # --- 4. Logica di Estrazione Dati ---
    target_datetime = datetime.combine(selected_date, datetime.min.time())
    
    if selected_fund == "Tutti i Fondi":
        # Filtriamo per data su tutto il dataset
        composition_df = portfolio_data[portfolio_data['DataRiferimento'] == target_datetime].copy()
    else:
        composition_df = data_repository.get_fund_data_for_date(
            portfolio_data, selected_fund, target_datetime
        )

    if composition_df.empty:
        st.warning("Nessun dato trovato per i parametri selezionati.")
        st.stop()

    # Filtro di ricerca testuale (ISIN o Titolo)
    if search_query:
        composition_df = composition_df[
            composition_df['DesTitolo'].str.contains(search_query, case=False, na=False) | 
            composition_df['ISIN'].str.contains(search_query, case=False, na=False)
        ]

    # --- 5. Filtri "Stile Excel" (Multiselect sopra la tabella) ---
    st.write("### 📊 Filtri Tabella")
    f1, f2, f3 = st.columns(3)
    
    filtered_df = composition_df.copy()

    with f1:
        if fund_col in filtered_df.columns:
            u_funds = sorted(filtered_df[fund_col].unique())
            sel_funds = st.multiselect("Filtra Fondi:", u_funds, default=u_funds)
            filtered_df = filtered_df[filtered_df[fund_col].isin(sel_funds)]

    with f2:
        if 'DescrizioneSector' in filtered_df.columns:
            u_sectors = sorted(filtered_df['DescrizioneSector'].dropna().unique())
            sel_sectors = st.multiselect("Settore:", u_sectors, default=u_sectors)
            filtered_df = filtered_df[filtered_df['DescrizioneSector'].isin(sel_sectors)]

    with f3:
        if 'Rating' in filtered_df.columns:
            u_rating = sorted(filtered_df['Rating'].dropna().unique())
            sel_rating = st.multiselect("Rating:", u_rating, default=u_rating)
            filtered_df = filtered_df[filtered_df['Rating'].isin(sel_rating)]

    # --- 6. Visualizzazione ---
    display_cols = [fund_col, 'DesTitolo', 'PesoPort', 'DescrizioneSector', 'Rating', 'ISIN', 'CodiceTipo']
    available_cols = [c for c in display_cols if c in filtered_df.columns]
    
    # Ordinamento: Fondo e poi Peso decrescente
    final_df = filtered_df[available_cols].sort_values(by=[fund_col, 'PesoPort'], ascending=[True, False])

    # Formattazione per la visualizzazione
    view_df = final_df.copy()
    if 'PesoPort' in view_df.columns:
        view_df['PesoPort'] = view_df['PesoPort'].map('{:.2f}%'.format)

    st.dataframe(view_df, use_container_width=True, height=600, hide_index=True)

    # Esportazione
    st.download_button(
        label="📥 Esporta Risultati in Excel",
        data=data_exporter.to_excel_download(final_df),
        file_name=f"lookthrough_custom_{selected_date.strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Metriche
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Titoli Trovati", len(final_df))
    m2.metric("Fondi Coinvolti", final_df[fund_col].nunique() if fund_col in final_df.columns else 0)
    if not final_df.empty:
        m3.metric("Peso Totale (Filtro)", f"{final_df['PesoPort'].sum():.2f}%")

if __name__ == "__main__":
    main()