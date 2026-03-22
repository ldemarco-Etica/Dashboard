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

# ============================================
# 🔐 CONTROLLO ACCESSO
# ============================================
#check_page_access_auth0("Analisi titoli")

st.set_page_config(layout="wide")
st.markdown("<h2 style='margin-bottom:0.2em;'>🔍 Analisi Titoli nel Portafoglio</h2>", unsafe_allow_html=True)

# --- Caricamento Dati ---
df = st.session_state.get("portfolio_data", pd.DataFrame())

if df.empty:
    st.error("Caricamento dati fallito. Controlla i file nella cartella 'data/portfolios/'.")
    st.stop()

# --- Inizializzazione Memoria Sessione ---
if "titoli_memorizzati" not in st.session_state:
    st.session_state.titoli_memorizzati = []
if "settori_memorizzati" not in st.session_state:
    st.session_state.settori_memorizzati = []

# Variabili per tracciare i cambiamenti di contesto (Fondo o Settore)
if "last_selected_fund" not in st.session_state:
    st.session_state.last_selected_fund = None
if "last_selected_sectors" not in st.session_state:
    st.session_state.last_selected_sectors = []

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
    
    # --- Selettore per settore (con memoria e FIX menu) ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏢 Filtro per Settore")
    
    # Estrai i settori disponibili per i titoli all'ultima data
    settori_disponibili = sorted(titoli_ultima_data['DescrizioneSector'].dropna().unique())
    selected_sectors = []

    if settori_disponibili:
        # Callback per salvare i settori
        def update_settori_memory():
            st.session_state.settori_memorizzati = st.session_state.widget_settori

        # Verifica se il fondo è cambiato per resettare/aggiornare i settori
        fund_changed = (st.session_state.last_selected_fund != selected_fund)
        
        # Se il fondo è cambiato o il widget non è inizializzato, calcoliamo i valori da mostrare
        if fund_changed or "widget_settori" not in st.session_state:
             settori_validi = [s for s in st.session_state.settori_memorizzati if s in settori_disponibili]
             st.session_state.widget_settori = settori_validi

        selected_sectors = st.sidebar.multiselect(
            "Seleziona settori (opzionale):",
            settori_disponibili,
            key="widget_settori",     # KEY fondamentale per evitare chiusura menu
            on_change=update_settori_memory, # Callback per salvare
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
    else:
        st.session_state.settori_memorizzati = []
    
    st.sidebar.markdown("---")
    
    # --- Selettore titoli (con memoria e FIX menu) ---
    
    # 1. Callback per salvare i titoli in memoria globale quando l'utente li cambia
    def update_titoli_memory():
        st.session_state.titoli_memorizzati = st.session_state.widget_titoli

    # 2. Logica per capire se dobbiamo forzare l'aggiornamento del widget (es. cambio fondo o cambio settore)
    #    Se cambiamo fondo O se cambiamo settore, i titoli disponibili cambiano, quindi ricalcoliamo la selezione.
    #    Nota: confrontiamo i settori attuali con quelli dell'ultimo run per capire se il filtro è cambiato.
    sectors_changed = (st.session_state.last_selected_sectors != selected_sectors)
    fund_changed = (st.session_state.last_selected_fund != selected_fund)
    
    # 3. Se il contesto è cambiato, ricalcoliamo cosa deve essere selezionato nel widget basandoci sulla memoria
    if fund_changed or sectors_changed or "widget_titoli" not in st.session_state:
        
        # Recupera titoli validi dalla memoria globale intersecati con quelli disponibili ora
        titoli_da_selezionare = [t for t in st.session_state.titoli_memorizzati if t in available_titles]
        
        # Avviso titoli persi (solo se non è il primo caricamento assoluto e abbiamo cambiato fondo)
        if fund_changed and st.session_state.titoli_memorizzati:
            titoli_persi = set(st.session_state.titoli_memorizzati) - set(available_titles)
            # (Opzionale: scommenta se vuoi l'avviso, ma a volte è fastidioso nel loop)
            # if titoli_persi:
            #     st.sidebar.info(f"⚠️ Titoli non presenti: {', '.join(titoli_persi)}")

        # Default fallback se vuoto
        if not titoli_da_selezionare and available_titles:
            # Seleziona il primo solo se non c'è nulla in memoria
            # O se vogliamo forzare sempre un default:
             titoli_da_selezionare = available_titles[:1]
        
        # Scriviamo direttamente nello stato del widget
        st.session_state.widget_titoli = titoli_da_selezionare

    # 4. Aggiorniamo le variabili di tracciamento per il prossimo run
    st.session_state.last_selected_fund = selected_fund
    st.session_state.last_selected_sectors = selected_sectors

    # 5. Il Widget Multiselect con KEY
    selected_titles = st.sidebar.multiselect(
        "2. Seleziona uno o più Titoli:", 
        available_titles, 
        key="widget_titoli",              # <--- Questo impedisce la chiusura del menu!
        on_change=update_titoli_memory,   # <--- Questo salva la scelta
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
                    
                    # Usiamo solo un'icona o un testo breve per risparmiare spazio
                    presenza_attuale = "✅" if ultima_data_fondo == ultima_data_titolo else "❌"
                    
                    stats_data.append({
                        'Titolo': title,
                        'Medio %': f"{peso_medio:.2f}",   # Nome accorciato
                        'Max %': f"{peso_max:.2f}",       # Nome accorciato
                        'Min %': f"{peso_min:.2f}",       # Nome accorciato
                        'Oggi %': f"{peso_attuale:.2f}",  # Nome accorciato
                        'Inizio': primo_ingresso,         # Nome accorciato
                        'Fine': ultima_presenza,          # Nome accorciato
                        'Attivo': presenza_attuale        # Nome molto più corto
                    })

            if stats_data:
                # hide_index=True nasconde la colonna dei numeri di riga (0,1,2) guadagnando spazio
                st.dataframe(
                    pd.DataFrame(stats_data), 
                    use_container_width=True, 
                    hide_index=True 
                )
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
