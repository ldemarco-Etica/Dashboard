import streamlit as st
import pandas as pd
from datetime import datetime

# Import moduli applicazione
from config import APP_CONFIG
from data_repository import data_repository
from utils import data_exporter, check_page_access_auth0

# 🔐 Accesso
check_page_access_auth0("Lookthrough")

def main():
    st.set_page_config(layout=APP_CONFIG.layout)
    st.title("🔬 Lookthrough Multi-Fondo")

    if 'portfolio_data' not in st.session_state or st.session_state['portfolio_data'].empty:
        st.error("❌ Dati non trovati.")
        st.stop()
    
    portfolio_data = st.session_state['portfolio_data']
    fund_col = 'Descrizione' 

    # --- 1. Sidebar: Selezione Fondo (Torna il "Tutti i fondi" immediato) ---
    st.sidebar.header("🔧 Filtri Generali")
    
    available_funds = data_repository.get_available_funds(portfolio_data)
    fund_options = ["Tutti i Fondi"] + available_funds
    
    selected_option = st.sidebar.selectbox("1. Seleziona Fondi:", fund_options, index=0)

    if selected_option == "Tutti i Fondi":
        selected_funds = available_funds
    else:
        selected_funds = [selected_option]

    # Filtro data
    df_temp = portfolio_data[portfolio_data[fund_col].isin(selected_funds)]
    min_date, max_date = df_temp['DataRiferimento'].min(), df_temp['DataRiferimento'].max()
    selected_date = st.sidebar.date_input("2. Seleziona data:", value=max_date, min_value=min_date, max_value=max_date)
    
    # --- 2. Preparazione Dati ---
    target_dt = datetime.combine(selected_date, datetime.min.time())
    base_df = df_temp[df_temp['DataRiferimento'] == target_dt].copy()

    if base_df.empty:
        st.warning("Nessun dato per la data selezionata.")
        st.stop()

    # --- 3. FIX COLONNE (Ricerca dei nomi corretti nel tuo DataFrame) ---
    # Cerchiamo i nomi delle colonne che hanno dati
    def get_valid_col(possible_names, df):
        for name in possible_names:
            if name in df.columns and df[name].notna().any():
                return name
        return None

    # Mappatura intelligente
    col_paese = get_valid_col(['CodicePaese', 'DescrizionePaese', 'Paese', 'CodicePaeseEsposizione'], base_df)
    col_tipo = get_valid_col(['AssetClass', 'TipoStrumento', 'DescrizioneSottoclasse', 'CodiceTipo'], base_df)
    col_divisa = get_valid_col(['CodiceDivisaEsposizione', 'Divisa', 'Valuta'], base_df)

    # --- 4. Ricerca con Suggerimenti (Autocomplete) ---
    st.markdown("### 🔍 Ricerca Titolo")
    all_titles = sorted(base_df['DesTitolo'].unique())
    selected_titles = st.multiselect(
        "Inizia a scrivere il nome di un titolo o ISIN:",
        options=all_titles,
        help="Suggerimenti automatici basati sui titoli in portafoglio."
    )

    # --- 5. Filtri Excel Style ---
    st.write("### 📊 Filtri Rapidi")
    f1, f2 = st.columns(2)
    
    filtered_df = base_df.copy()

    if selected_titles:
        filtered_df = filtered_df[filtered_df['DesTitolo'].isin(selected_titles)]

    with f1:
        if 'DescrizioneSector' in filtered_df.columns:
            u_sectors = sorted(filtered_df['DescrizioneSector'].dropna().unique())
            sel_sectors = st.multiselect("Settore:", u_sectors, default=u_sectors)
            filtered_df = filtered_df[filtered_df['DescrizioneSector'].isin(sel_sectors)]

    with f2:
        if col_tipo:
            u_types = sorted(filtered_df[col_tipo].dropna().unique())
            sel_types = st.multiselect(f"Tipo ({col_tipo}):", u_types, default=u_types)
            filtered_df = filtered_df[filtered_df[col_tipo].isin(sel_types)]

    # --- 6. Tabella Risultati ---
    cols_to_show = [fund_col, 'DesTitolo', 'ISIN', 'PesoPort']
    if col_tipo: cols_to_show.append(col_tipo)
    if col_divisa: cols_to_show.append(col_divisa)
    if col_paese: cols_to_show.append(col_paese)
    if 'DescrizioneSector' in filtered_df.columns: cols_to_show.append('DescrizioneSector')

    final_df = filtered_df[cols_to_show].sort_values(by=[fund_col, 'PesoPort'], ascending=[True, False])

    # Vista formattata
    view_df = final_df.copy()
    if 'PesoPort' in view_df.columns:
        view_df['PesoPort'] = view_df['PesoPort'].map('{:.2f}%'.format)

    st.dataframe(view_df, use_container_width=True, height=550, hide_index=True)

    # --- 7. Export e Metriche ---
    st.download_button(
        label="📥 Scarica Report Excel",
        data=data_exporter.to_excel_download(final_df),
        file_name=f"lookthrough_{selected_date.strftime('%Y%m%d')}.xlsx"
    )

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Titoli", len(final_df))
    m2.metric("Fondi", final_df[fund_col].nunique())
    m3.metric("Peso Totale", f"{final_df['PesoPort'].sum():.2f}%")

if __name__ == "__main__":
    main()
