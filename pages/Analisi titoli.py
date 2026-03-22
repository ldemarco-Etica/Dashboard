#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 30 14:49:20 2025

@author: lucademarco
"""

# applicazione/pages/analisi_titoli.py

import streamlit as st
import pandas as pd
import plotly.express as px
#from utils import check_page_access_auth0

# ============================================
# 🔐 CONTROLLO ACCESSO
# ============================================
#check_page_access_auth0("Analisi titoli")

st.set_page_config(layout="wide")
st.markdown("<h2 style='margin-bottom:0.2em;'>🔍 Analisi Titoli nel Portafoglio</h2>", unsafe_allow_html=True)

# --- Caricamento Dati ---
df = st.session_state.get("portfolio_data", pd.DataFrame())

if df.empty:
    st.error("Caricamento dati fallito. Controlla i file nella cartella 'data/portfolios/.")
    st.stop()

# --- Controlli e filtri ---
st.sidebar.header("🔧 Filtri Titolo")
available_funds = sorted(df['Descrizione'].unique())
selected_fund = st.sidebar.selectbox("1. Seleziona un Fondo:", available_funds)

fund_subset = df[df['Descrizione'] == selected_fund].copy()

if fund_subset.empty:
    st.warning("Nessun dato per il fondo selezionato.")
else:
    # Trova l'ultima data disponibile per il fondo
    ultima_data_fondo = fund_subset['DataRiferimento'].max()
    
    # Filtra i titoli presenti all'ultima data con peso > 0
    titoli_ultima_data = fund_subset[
        (fund_subset['DataRiferimento'] == ultima_data_fondo) & 
        (fund_subset['PesoPort'].notna()) & 
        (fund_subset['PesoPort'] > 0)
    ].copy()
    
    # Ordina per peso decrescente e prendi i titoli
    titoli_ordinati = titoli_ultima_data.sort_values('PesoPort', ascending=False)['DesTitolo'].unique().tolist()
    
    # Aggiungi eventuali titoli che non sono presenti all'ultima data ma lo erano in passato
    tutti_titoli_storici = sorted(fund_subset['DesTitolo'].dropna().unique())
    titoli_non_attuali = [t for t in tutti_titoli_storici if t not in titoli_ordinati]
    available_titles = titoli_ordinati + sorted(titoli_non_attuali)
    
    # --- NUOVO: Selettore per settore ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏢 Filtro per Settore")
    
    # Estrai i settori disponibili per i titoli all'ultima data
    settori_disponibili = sorted(titoli_ultima_data['DescrizioneSector'].dropna().unique())
    
    if settori_disponibili:
        selected_sectors = st.sidebar.multiselect(
            "Seleziona settori (opzionale):",
            settori_disponibili,
            help="Seleziona uno o più settori per filtrare i titoli disponibili"
        )
        
        # Se sono selezionati dei settori, filtra i titoli disponibili
        if selected_sectors:
            titoli_nei_settori = fund_subset[
                (fund_subset['DataRiferimento'] == ultima_data_fondo) & 
                (fund_subset['DescrizioneSector'].isin(selected_sectors)) &
                (fund_subset['PesoPort'].notna()) & 
                (fund_subset['PesoPort'] > 0)
            ]['DesTitolo'].unique().tolist()
            
            # Mantieni solo i titoli dei settori selezionati, ordinati per peso
            available_titles = [t for t in titoli_ordinati if t in titoli_nei_settori]
            
            # Aggiungi titoli storici del settore non presenti all'ultima data
            titoli_storici_settori = fund_subset[
                fund_subset['DescrizioneSector'].isin(selected_sectors)
            ]['DesTitolo'].dropna().unique().tolist()
            titoli_storici_non_attuali = [t for t in sorted(titoli_storici_settori) if t not in available_titles]
            available_titles = available_titles + titoli_storici_non_attuali
            
            default_selection = available_titles[:1] if available_titles else []
        else:
            default_selection = [available_titles[0]] if available_titles else []
    else:
        selected_sectors = []
        default_selection = [available_titles[0]] if available_titles else []
    
    st.sidebar.markdown("---")
    
    # --- Selettore titoli (ora ordinato per peso) ---
    selected_titles = st.sidebar.multiselect(
        "2. Seleziona uno o più Titoli:", 
        available_titles, 
        default=default_selection,
        help="Titoli ordinati per peso attuale in portafoglio (decrescente)"
    )

    st.markdown(
        f"<h3 style='margin-top:0.001em;'>Analisi dei titoli selezionati nel fondo <i>{selected_fund}</i></h3>",
        unsafe_allow_html=True
    )

    if not selected_titles:
        st.info("Seleziona almeno un titolo per visualizzare i dati.")
    else:
        # --- Preparazione dati per il grafico ---
        plot_dfs = []
        threshold_days = 5

        for title in selected_titles:
            title_rows = fund_subset[fund_subset['DesTitolo'] == title].copy()
            if title_rows.empty:
                st.warning(f"Nessun dato per il titolo {title} in questo fondo.")
                continue

            # Prendi righe uniche per data
            title_rows = title_rows.sort_values('DataRiferimento').drop_duplicates(subset='DataRiferimento', keep='last')
            present_rows = title_rows[title_rows['PesoPort'].notna() & (title_rows['PesoPort'] != 0)].copy()

            if present_rows.empty:
                st.warning(f"Il titolo {title} non risulta mai stato presente in portafoglio.")
                continue

            # Logica per discontinuità
            present_rows_sorted = present_rows.sort_values('DataRiferimento').reset_index(drop=True)
            plot_records = []
            for i, row in present_rows_sorted.iterrows():
                if i > 0:
                    prev_date = present_rows_sorted.loc[i - 1, 'DataRiferimento']
                    current_date = row['DataRiferimento']
                    gap = (current_date - prev_date).days
                    if gap > threshold_days:
                        plot_records.append({
                            'DataRiferimento': prev_date + pd.Timedelta(days=1),
                            'PesoPort': None,
                            'DesTitolo': title
                        })
                plot_records.append({
                    'DataRiferimento': row['DataRiferimento'],
                    'PesoPort': row['PesoPort'],
                    'DesTitolo': title
                })
            plot_dfs.append(pd.DataFrame(plot_records))

        if plot_dfs:
            # Unisci tutti i DataFrame
            plot_df = pd.concat(plot_dfs, ignore_index=True)

            # --- Grafico ---
            st.markdown("<h4>📈 Evoluzione del Peso nel Tempo</h4>", unsafe_allow_html=True)
            fig = px.line(
                plot_df,
                x='DataRiferimento',
                y='PesoPort',
                color='DesTitolo',
                markers=False,
                labels={'PesoPort': 'Peso (%)', 'DataRiferimento': 'Data', 'DesTitolo': 'Titolo'}
            )
            fig.update_traces(connectgaps=False)
            fig.update_layout(hovermode='x unified', legend_title_text='Titolo')
            st.plotly_chart(fig, use_container_width=True)

            # --- Statistiche ---
            st.markdown("<h4>📊 Metriche Chiave</h4>", unsafe_allow_html=True)
            stats_data = []
            for title in selected_titles:
                title_rows = fund_subset[fund_subset['DesTitolo'] == title].copy()
                present_rows = title_rows[title_rows['PesoPort'].notna() & (title_rows['PesoPort'] != 0)].copy()
                if not present_rows.empty:
                    peso_medio = present_rows['PesoPort'].mean()
                    peso_max = present_rows['PesoPort'].max()
                    peso_min = present_rows['PesoPort'].min()
                    peso_attuale = present_rows.sort_values('DataRiferimento').iloc[-1]['PesoPort']
                    primo_ingresso = present_rows['DataRiferimento'].min().strftime('%d/%m/%Y')
                    ultima_presenza = present_rows['DataRiferimento'].max().strftime('%d/%m/%Y')
                    ultima_data_fondo = fund_subset['DataRiferimento'].max()
                    ultima_data_titolo = present_rows['DataRiferimento'].max()
                    presenza_attuale = "✅ Sì" if ultima_data_fondo == ultima_data_titolo else "❌ No"
                    stats_data.append({
                        'Titolo': title,
                        'Peso Medio (%)': f"{peso_medio:.2f}",
                        'Peso Max (%)': f"{peso_max:.2f}",
                        'Peso Min (%)': f"{peso_min:.2f}",
                        'Peso Attuale (%)': f"{peso_attuale:.2f}",
                        'Primo Ingresso': primo_ingresso,
                        'Ultima Presenza': ultima_presenza,
                        'In Portafoglio Oggi': presenza_attuale
                    })

            if stats_data:
                st.dataframe(pd.DataFrame(stats_data), use_container_width=True)
            else:
                st.warning("Nessun dato disponibile per i titoli selezionati.")

            # --- Dati Dettagliati ---
            if st.checkbox("📋 Mostra storico dettagliato dei titoli"):
                display_dfs = []
                for title in selected_titles:
                    title_rows = fund_subset[fund_subset['DesTitolo'] == title].copy()
                    present_rows = title_rows[title_rows['PesoPort'].notna() & (title_rows['PesoPort'] != 0)].copy()
                    if not present_rows.empty:
                        present_rows['Titolo'] = title
                        display_dfs.append(present_rows[['Titolo', 'DataRiferimento', 'PesoPort', 'DescrizioneSector', 'Rating', 'CodicePaeseEsposizione']])
                if display_dfs:
                    display_df = pd.concat(display_dfs, ignore_index=True)
                    st.dataframe(
                        display_df.sort_values(['Titolo', 'DataRiferimento'], ascending=[True, False]),
                        use_container_width=True
                    )
                else:
                    st.info("Nessun dato storico disponibile per i titoli selezionati.")
