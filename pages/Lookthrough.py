import streamlit as st
import pandas as pd
from datetime import datetime

# Importa i moduli della tua applicazione
from config import APP_CONFIG
from data_repository import data_repository
from utils import data_exporter#, check_page_access_auth0

# ============================================
# 🔐 CONTROLLO ACCESSO
# ============================================
#check_page_access_auth0("Lookthrough")

def main():
    st.set_page_config(layout=APP_CONFIG.layout)
    st.title("🔬 Lookthrough Multi-Fondo")

    # 1. Caricamento Dati
    if 'portfolio_data' not in st.session_state or st.session_state['portfolio_data'].empty:
        st.error("❌ Dati di portafoglio non trovati.")
        st.stop()
    
    portfolio_data = st.session_state['portfolio_data']
    fund_col = 'Descrizione' 

    # --- 2. Sidebar: Selezione Intelligente dei Fondi ---
    st.sidebar.header("🔧 Filtri Generali")
    
    available_funds = data_repository.get_available_funds(portfolio_data)
    
    # Opzione per selezionare tutto con un click
    selection_mode = st.sidebar.radio(
        "Modalità Selezione Fondi:",
        ["Tutti i Fondi", "Selezione Personalizzata"],
        index=0
    )

    if selection_mode == "Tutti i Fondi":
        selected_funds = available_funds
    else:
        selected_funds = st.sidebar.multiselect(
            "Scegli i fondi da includere:",
            options=available_funds,
            default=available_funds[:1] # Almeno uno selezionato di default
        )

    if not selected_funds:
        st.warning("⚠️ Seleziona almeno un fondo.")
        st.stop()

    # Range date basato sui fondi scelti
    df_funds_filtered = portfolio_data[portfolio_data[fund_col].isin(selected_funds)]
    min_date, max_date = df_funds_filtered['DataRiferimento'].min(), df_funds_filtered['DataRiferimento'].max()

    selected_date = st.sidebar.date_input("Seleziona data:", value=max_date, min_value=min_date, max_value=max_date)
    target_datetime = datetime.combine(selected_date, datetime.min.time())

    # --- 3. Dati Base Filtrati per Data ---
    base_df = df_funds_filtered[df_funds_filtered['DataRiferimento'] == target_datetime].copy()

    # --- 4. FIX COLONNA PAESE ---
    # Cerchiamo la colonna paese con vari nomi possibili
    possibili_nomi_paese = ['CodicePaeseEsposizione', 'CodicePaese', 'Paese', 'CountryCode']
    colonna_paese = next((c for c in possibili_nomi_paese if c in base_df.columns), None)

    if base_df.empty:
        st.warning("Nessun dato trovato per questa data.")
        st.stop()

    # --- 5. Ricerca con Suggerimenti (Autocomplete) ---
    st.markdown("### 🔍 Ricerca Titolo")
    # Suggerimenti basati sui titoli presenti nel set filtrato
    all_titles = sorted(base_df['DesTitolo'].unique())
    selected_titles = st.multiselect(
        "Digita per cercare un titolo o un ISIN:",
        options=all_titles,
        help="L'elenco mostra solo i titoli presenti nei fondi e nella data selezionata."
    )

    # --- 6. Filtri Excel Style (Settore e Tipo) ---
    st.write("### 📊 Filtri Rapidi")
    f1, f2 = st.columns(2)
    
    filtered_df = base_df.copy()

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

    # --- 7. Tabella Risultati ---
    cols_to_show = [fund_col, 'DesTitolo', 'ISIN', 'PesoPort', 'DescrizioneSector']
    
    if col_tipo in filtered_df.columns: cols_to_show.append(col_tipo)
    if 'CodiceDivisaEsposizione' in filtered_df.columns: cols_to_show.append('CodiceDivisaEsposizione')
    if colonna_paese: cols_to_show.append(colonna_paese)

    final_df = filtered_df[cols_to_show].sort_values(by=[fund_col, 'PesoPort'], ascending=[True, False])

    # Formattazione
    view_df = final_df.copy()
    if 'PesoPort' in view_df.columns:
        # Modifica richiesta: se x è 0 mette "-", altrimenti formatta come percentuale
        view_df['PesoPort'] = view_df['PesoPort'].apply(lambda x: "-" if x == 0 else f"{x:.2f}%")

    st.dataframe(view_df, use_container_width=True, height=500, hide_index=True)

    # --- 8. Export e Metriche ---
    st.download_button(
        label="📥 Scarica Report Excel",
        data=data_exporter.to_excel_download(final_df),
        file_name=f"lookthrough_{selected_date.strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Titoli Trovati", len(final_df))
    m2.metric("Fondi Attivi", final_df[fund_col].nunique())
    
    if colonna_paese:
        m3.metric("Paesi Diversi", final_df[colonna_paese].nunique())
    else:
        # Nota: Qui usiamo final_df['PesoPort'] che è numerico, non view_df che ha le stringhe
        m3.metric("Peso Totale", f"{final_df['PesoPort'].sum():.2f}%")

if __name__ == "__main__":
    main()
