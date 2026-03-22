#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 30 12:37:04 2025

@author: lucademarco
"""

# applicazione/pages/Limiti.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
#from utils import check_page_access_auth0

# ============================================
# 🔐 CONTROLLO ACCESSO
# ============================================
#check_page_access_auth0("Limiti da CDA")

st.set_page_config(layout="wide")
st.title("⚖️ Analisi Limiti CDA")

# --- Funzioni di calcolo dei limiti ---

def calculate_azioni(df):
    """Calcola il peso delle azioni (AZ + SE)"""
    return df[df['CodiceTipo'].isin(['AZ ', 'SE '])]['PesoPort'].sum()

def calculate_obbligazioni(df):
    """Calcola il peso delle obbligazioni (OB)"""
    return df[df['CodiceTipo'] == 'OB ']['PesoPort'].sum()

def calculate_oicr(df):
    """Calcola il peso degli OICR (FO)"""
    return df[df['CodiceTipo'] == 'FO ']['PesoPort'].sum()

def calculate_mercati_emergenti(df):
    """Calcola l'esposizione a mercati emergenti tra le azioni"""
    emerging_countries = ['BR ', 'CN ', 'PL ', 'KR ', 'GR ', 'TW ', 'TR ', 'IN ', 'ZA ', 'ID ', 'MX ', 'PE ', 'PH ', 'CL ', 'CO ']
    azioni_df = df[df['CodiceTipo'].isin(['AZ ', 'SE '])]
    return azioni_df[azioni_df['CodicePaeseEsposizione'].isin(emerging_countries)]['PesoPort'].sum()

def calculate_esposizione_eur(df):
    """Calcola l'esposizione valutaria alla divisa Euro"""
    df_copy = df.copy()
    mask_688 = df_copy['CodiceBloomberg'].str.contains('688 HK Equity', na=False)
    mask_992 = df_copy['CodiceBloomberg'].str.contains('992 HK Equity', na=False)
    df_copy.loc[mask_688 | mask_992, 'CodiceDivisaEsposizione'] = 'HKD'
    
    return df_copy[df_copy['CodiceDivisaEsposizione'].isin(['EUR', 'MUL'])]['PesoPort'].sum()

def calculate_rating_inferiore(df):
    """Calcola il peso dei titoli con rating inferiore ad adeguato (C, D, NR)"""
    obbligazioni_df = df[df['CodiceTipo'] == 'OB ']
    return obbligazioni_df[obbligazioni_df['Rating'].isin(['C', 'D', 'NR'])]['PesoPort'].sum()

def calculate_rating_d(df):
    """Calcola il peso dei titoli con rating D"""
    obbligazioni_df = df[df['CodiceTipo'] == 'OB ']
    return obbligazioni_df[obbligazioni_df['Rating'] == 'D']['PesoPort'].sum()

def calculate_rating_nr(df):
    """Calcola il peso dei titoli con rating NR"""
    obbligazioni_df = df[df['CodiceTipo'] == 'OB ']
    return obbligazioni_df[obbligazioni_df['Rating'] == 'NR']['PesoPort'].sum()

def get_duration_value(fondo, data_riferimento, duration_data):
    """Recupera il valore di duration più vicino alla data di riferimento"""
    fondo_duration = duration_data[duration_data['Fondo'] == fondo].copy()
    fondo_duration = fondo_duration[fondo_duration['Data'] <= data_riferimento]
    
    if fondo_duration.empty:
        return None
    
    closest_date = fondo_duration['Data'].max()
    return fondo_duration[fondo_duration['Data'] == closest_date]['Duration Fondo'].iloc[0]

def calculate_limit_value(limite_row, portfolio_data, duration_data, data_riferimento):
    """Calcola il valore attuale per un limite specifico"""
    fondo = limite_row['Fondo']
    limite_tipo = limite_row['che limite è?']
    
    fund_data = portfolio_data[
        (portfolio_data['Descrizione'] == fondo) & 
        (portfolio_data['DataRiferimento'] == data_riferimento)
    ]
    
    if fund_data.empty:
        return None
    
    if limite_tipo == "Azioni":
        return calculate_azioni(fund_data)
    elif limite_tipo == "Obbligazioni":
        return calculate_obbligazioni(fund_data)
    elif limite_tipo == "OICR":
        return calculate_oicr(fund_data)
    elif limite_tipo == "Esposizione a mercati emergenti":
        return calculate_mercati_emergenti(fund_data)
    elif limite_tipo == "Esposizione Valutaria alla divisa Euro":
        return calculate_esposizione_eur(fund_data)
    elif limite_tipo == "Rating inferiore ad adeguato":
        return calculate_rating_inferiore(fund_data)
    elif limite_tipo == "Rating D":
        return calculate_rating_d(fund_data)
    elif limite_tipo == "Rating NR":
        return calculate_rating_nr(fund_data)
    elif limite_tipo == "Duration":
        return get_duration_value(fondo, data_riferimento, duration_data)
    elif limite_tipo == "Convertibili":
        return None
    else:
        return None

def check_limit_compliance(current_value, min_limit, max_limit):
    """Verifica se un limite è rispettato"""
    if current_value is None:
        return None
    
    if min_limit is not None and current_value < min_limit:
        return False
    if max_limit is not None and current_value > max_limit:
        return False
    return True

def create_gauge_chart(current_value, min_limit, max_limit, title, is_duration=False):
    """Crea un grafico a gauge per visualizzare il limite"""
    if current_value is None:
        fig = go.Figure()
        fig.add_annotation(
            text="Dato non disponibile",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title=title,
            height=300,
            showlegend=False
        )
        return fig
    
    if min_limit is not None and max_limit is not None:
        gauge_min = max(0, min_limit - 10)
        gauge_max = max_limit + 10
    elif max_limit is not None:
        gauge_min = 0
        gauge_max = max_limit + 10
    elif min_limit is not None:
        gauge_min = max(0, min_limit - 10)
        gauge_max = min_limit + 20
    else:
        gauge_min = 0
        gauge_max = 100
    
    color = "green"
    if min_limit is not None and current_value < min_limit:
        color = "red"
    elif max_limit is not None and current_value > max_limit:
        color = "red"
    
    steps = []
    if min_limit is not None:
        steps.append(dict(range=[gauge_min, min_limit], color="lightgray"))
        if max_limit is not None:
            steps.append(dict(range=[min_limit, max_limit], color="lightgreen"))
            steps.append(dict(range=[max_limit, gauge_max], color="lightcoral"))
        else:
            steps.append(dict(range=[min_limit, gauge_max], color="lightgreen"))
    elif max_limit is not None:
        steps.append(dict(range=[gauge_min, max_limit], color="lightgreen"))
        steps.append(dict(range=[max_limit, gauge_max], color="lightcoral"))
    else:
        steps.append(dict(range=[gauge_min, gauge_max], color="lightgreen"))
    
    unit = "" if is_duration else "%"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=current_value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        number={'suffix': unit},
        gauge={
            'axis': {'range': [gauge_min, gauge_max]},
            'bar': {'color': color},
            'steps': steps,
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_limit if max_limit else min_limit
            }
        }
    ))
    
    fig.update_layout(height=300)
    return fig

# --- Caricamento dati ---
portfolio_data = st.session_state.get("portfolio_data", pd.DataFrame())
duration_data = st.session_state.get("duration_data", pd.DataFrame())
limiti_data = st.session_state.get("limiti_data", pd.DataFrame())

if portfolio_data.empty:
    st.error("Dati portafoglio non caricati. Vai alla Home per caricarli.")
    st.stop()

if limiti_data.empty:
    st.error("Dati limiti CDA non caricati. Controlla il file 'data/limiti/Limiti CDA.xlsx' e ricarica i dati dalla Home.")
    st.stop()

# --- Selezione data globale ---
min_date_global = portfolio_data['DataRiferimento'].min()
max_date_global = portfolio_data['DataRiferimento'].max()

selected_date = st.sidebar.date_input(
    "📅 Data di riferimento globale:",
    value=max_date_global,
    min_value=min_date_global,
    max_value=max_date_global,
    help="Questa data verrà utilizzata per tutti i fondi nell'analisi"
)

# --- TAB SYSTEM ---
tab1, tab2 = st.tabs(["📊 Dashboard Generale", "🔍 Analisi Dettagliata Fondo"])

# TAB 1: Dashboard Generale
with tab1:
    st.header("📊 Dashboard Limiti CDA - Tutti i Fondi")
    st.info(f"Data di riferimento: **{selected_date.strftime('%d/%m/%Y')}**")
    
    available_funds = sorted(limiti_data['Fondo'].unique())
    
    all_results = []
    summary_data = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, fund_name in enumerate(available_funds):
        status_text.text(f"Elaborazione {fund_name}...")
        progress_bar.progress((i + 1) / len(available_funds))
        
        fund_limits = limiti_data[limiti_data['Fondo'] == fund_name]
        
        for idx, row in fund_limits.iterrows():
            current_value = calculate_limit_value(row, portfolio_data, duration_data, pd.to_datetime(selected_date))
            
            compliant = check_limit_compliance(current_value, row['Min (%)'], row['Max (%)'])
            
            status = "✅"
            if compliant is False:
                status = "🔴"
            elif compliant is None:
                status = "⚠️"
            
            all_results.append({
                'Fondo': fund_name,
                'Limite': row['che limite è?'],
                'Valore Attuale': current_value,
                'Min (%)': row['Min (%)'],
                'Max (%)': row['Max (%)'],
                'Compliant': compliant,
                'Status': status
            })
        
        # Summary per fondo
        fund_results = [r for r in all_results if r['Fondo'] == fund_name]
        total_limits = len(fund_results)
        compliant_limits = sum(1 for r in fund_results if r['Compliant'] == True)
        non_compliant_limits = sum(1 for r in fund_results if r['Compliant'] == False)
        na_limits = sum(1 for r in fund_results if r['Compliant'] is None)
        
        compliance_rate = (compliant_limits / (total_limits - na_limits) * 100) if (total_limits - na_limits) > 0 else 0
        
        summary_data.append({
            'Fondo': fund_name,
            'Totale Limiti': total_limits,
            'Conformi': compliant_limits,
            'Non Conformi': non_compliant_limits,
            'N/A': na_limits,
            '% Compliance': compliance_rate,
            'Status': "🟢 OK" if non_compliant_limits == 0 else f"🔴 {non_compliant_limits} Violazioni"
        })
    
    progress_bar.empty()
    status_text.empty()
    
    # Summary Dashboard
    if summary_data:
        col1, col2, col3, col4 = st.columns(4)
        
        total_funds = len(summary_data)
        funds_ok = len([s for s in summary_data if s['Non Conformi'] == 0])
        funds_violations = total_funds - funds_ok
        avg_compliance = np.mean([s['% Compliance'] for s in summary_data])
        
        col1.metric("🏦 Totale Fondi", total_funds)
        col2.metric("✅ Fondi Conformi", funds_ok)
        col3.metric("⚠️ Fondi con Violazioni", funds_violations)
        col4.metric("📊 Compliance Media", f"{avg_compliance:.1f}%")
        
        # Tabella riassuntiva
        st.subheader("📋 Riepilogo per Fondo")
        df_summary = pd.DataFrame(summary_data)
        
        def color_summary_row(row):
            if row['Non Conformi'] == 0:
                return ['background-color: #d4edda'] * len(row)
            else:
                return ['background-color: #f8d7da'] * len(row)
        
        styled_summary = df_summary.style.apply(color_summary_row, axis=1)
        st.dataframe(styled_summary, use_container_width=True)
        
        # Grafici
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.bar(
                df_summary,
                x='Fondo',
                y='% Compliance',
                title='Tasso di Compliance per Fondo',
                color='% Compliance',
                color_continuous_scale='RdYlGn',
                range_color=[0, 100]
            )
            fig1.update_xaxes(tickangle=45)
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            violation_counts = df_summary['Non Conformi'].value_counts().sort_index()
            fig2 = px.pie(
                values=violation_counts.values,
                names=[f"{idx} violazioni" for idx in violation_counts.index],
                title='Distribuzione Violazioni per Fondo'
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Dettaglio violazioni
        violations_df = pd.DataFrame([r for r in all_results if r['Compliant'] is False])
        if not violations_df.empty:
            st.subheader("⚠️ Dettaglio Violazioni")
            st.error(f"Trovate {len(violations_df)} violazioni totali")
            
            violation_summary = violations_df.groupby('Limite').agg({
                'Fondo': 'count',
                'Valore Attuale': lambda x: list(x)
            }).reset_index()
            violation_summary.columns = ['Limite Violato', 'N° Fondi', 'Valori']
            violation_summary = violation_summary.sort_values('N° Fondi', ascending=False)
            
            st.dataframe(violation_summary, use_container_width=True)
            
            for _, violation in violations_df.iterrows():
                with st.expander(f"🔴 {violation['Fondo']} - {violation['Limite']}"):
                    st.write(f"**Valore Attuale:** {violation['Valore Attuale']:.2f}%")
                    if pd.notna(violation['Min (%)']):
                        st.write(f"**Minimo Richiesto:** {violation['Min (%)']}%")
                    if pd.notna(violation['Max (%)']):
                        st.write(f"**Massimo Consentito:** {violation['Max (%)']}%")
        else:
            st.success("🎉 Nessuna violazione rilevata! Tutti i fondi sono conformi.")

# TAB 2: Analisi Dettagliata Fondo
with tab2:
    st.header("🔍 Analisi Dettagliata per Fondo")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_fund = st.selectbox("📈 Seleziona Fondo:", available_funds)
    
    with col2:
        use_custom_date = st.checkbox("Usa data personalizzata per questo fondo")
    
    if use_custom_date:
        fund_data_temp = portfolio_data[portfolio_data['Descrizione'] == selected_fund]
        min_date_fund = fund_data_temp['DataRiferimento'].min()
        max_date_fund = fund_data_temp['DataRiferimento'].max()
        
        custom_date = st.date_input(
            "📅 Data personalizzata:",
            value=max_date_fund,
            min_value=min_date_fund,
            max_value=max_date_fund
        )
        analysis_date = custom_date
    else:
        analysis_date = selected_date
    
    fund_portfolio_data = portfolio_data[portfolio_data['Descrizione'] == selected_fund]
    
    if fund_portfolio_data.empty:
        st.error(f"Nessun dato portafoglio trovato per il fondo: {selected_fund}")
        st.stop()
    
    snapshot_data = fund_portfolio_data[fund_portfolio_data['DataRiferimento'] == pd.to_datetime(analysis_date)]
    
    if snapshot_data.empty:
        st.warning(f"Nessun dato disponibile per il {analysis_date.strftime('%d/%m/%Y')}. Prova un'altra data.")
        st.stop()
    
    st.info(f"Analisi per **{selected_fund}** alla data: **{analysis_date.strftime('%d/%m/%Y')}**")
    
    # Calcola limiti
    fund_limits = limiti_data[limiti_data['Fondo'] == selected_fund].copy()
    
    results = []
    for idx, row in fund_limits.iterrows():
        current_value = calculate_limit_value(row, portfolio_data, duration_data, pd.to_datetime(analysis_date))
        
        compliant = check_limit_compliance(current_value, row['Min (%)'], row['Max (%)'])
        
        status = "✅"
        if compliant is False:
            status = "🔴"
        elif compliant is None:
            status = "⚠️"
        
        results.append({
            'Limite': row['che limite è?'],
            'Valore Attuale': current_value,
            'Min (%)': row['Min (%)'],
            'Max (%)': row['Max (%)'],
            'Status': status,
            'Compliant': compliant,
            'Note': row['Come calcolarlo'] if current_value is None else ""
        })
    
    results_df = pd.DataFrame(results)
    
    # Dashboard riassuntiva
    total_limits = len(results)
    compliant_limits = sum(1 for r in results if r['Compliant'] == True)
    non_compliant_limits = sum(1 for r in results if r['Compliant'] == False)
    na_limits = sum(1 for r in results if r['Compliant'] is None)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Totale Limiti", total_limits)
    col2.metric("✅ Conformi", compliant_limits)
    col3.metric("❌ Non Conformi", non_compliant_limits)
    
    # Tabella dettagliata
    st.subheader("📋 Dettaglio Limiti")
    
    display_df = results_df.copy()
    for col in ['Valore Attuale', 'Min (%)', 'Max (%)']:
        display_df[col] = display_df[col].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
        )
    
    def color_compliance(row):
        if row['Compliant'] is True:
            return ['background-color: #d4edda'] * len(row)
        elif row['Compliant'] is False:
            return ['background-color: #f8d7da'] * len(row)
        else:
            return ['background-color: #fff3cd'] * len(row)
    
    styled_df = display_df.style.apply(color_compliance, axis=1)
    st.dataframe(styled_df, use_container_width=True)
    
    # Grafico compliance
    if total_limits > 0:
        fig = go.Figure(data=[
            go.Bar(name='Conforme', x=['Compliance Status'], y=[compliant_limits], marker_color='green'),
            go.Bar(name='Non Conforme', x=['Compliance Status'], y=[non_compliant_limits], marker_color='red'),
            go.Bar(name='N/A', x=['Compliance Status'], y=[na_limits], marker_color='orange')
        ])
        
        fig.update_layout(
            title=f'Stato Compliance - {selected_fund}',
            barmode='stack',
            yaxis_title='Numero di Limiti',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Dettagli violazioni
    non_compliant = [r for r in results if r['Compliant'] is False]
    if non_compliant:
        st.subheader("⚠️ Limiti Non Conformi")
        for rule in non_compliant:
            val_str = f"{rule['Valore Attuale']:.2f}%" if pd.notna(rule['Valore Attuale']) else "N/A"
            st.error(f"**{rule['Limite']}**: {val_str}")
    
    # Grafici Gauge
    st.subheader("📊 Visualizzazione Gauge dei Limiti")
    
    calculable_limits = results_df[results_df['Valore Attuale'].notna()]
    
    if not calculable_limits.empty:
        n_limits = len(calculable_limits)
        n_cols = min(3, n_limits)
        cols = st.columns(n_cols)
        
        for idx, (_, row) in enumerate(calculable_limits.iterrows()):
            col_idx = idx % n_cols
            
            with cols[col_idx]:
                is_duration = row['Limite'] == 'Duration'
                fig = create_gauge_chart(
                    current_value=row['Valore Attuale'],
                    min_limit=row['Min (%)'],
                    max_limit=row['Max (%)'],
                    title=row['Limite'],
                    is_duration=is_duration
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Dettagli non calcolabili
    non_calculable = results_df[results_df['Valore Attuale'].isna()]
    if not non_calculable.empty:
        st.subheader("⚠️ Limiti Non Calcolabili")
        st.warning("I seguenti limiti non possono essere calcolati automaticamente:")
        
        for _, row in non_calculable.iterrows():
            st.write(f"**{row['Limite']}**: {row['Note']}")
    
    # Storico evoluzione
    if st.checkbox("📈 Mostra evoluzione storica dei limiti"):
        st.subheader("Evoluzione Storica dei Limiti")
        
        available_dates = sorted(fund_portfolio_data['DataRiferimento'].unique(), reverse=True)
        
        cache_key = f"historical_limits_{selected_fund}"
        if cache_key not in st.session_state:
            historical_data = []
            for date in available_dates:
                for _, limit_row in fund_limits.iterrows():
                    if limit_row['che limite è?'] != 'Convertibili':
                        value = calculate_limit_value(limit_row, portfolio_data, duration_data, date)
                        if value is not None:
                            historical_data.append({
                                'Data': date,
                                'Limite': limit_row['che limite è?'],
                                'Valore': value,
                                'Min': limit_row['Min (%)'],
                                'Max': limit_row['Max (%)']
                            })
            st.session_state[cache_key] = pd.DataFrame(historical_data)
        
        hist_df = st.session_state[cache_key]
        
        if not hist_df.empty:
            available_hist_limits = sorted(hist_df['Limite'].unique())
            selected_limit = st.selectbox("Seleziona limite da visualizzare:", available_hist_limits)
            
            limit_hist = hist_df[hist_df['Limite'] == selected_limit]
            
            fig = px.line(
                limit_hist,
                x='Data', y='Valore',
                title=f'Evoluzione {selected_limit}',
                markers=True
            )
            
            if limit_hist['Min'].notna().any():
                min_val = limit_hist['Min'].iloc[0]
                fig.add_hline(y=min_val, line_dash="dash", line_color="red", annotation_text=f"Min: {min_val}%")
            if limit_hist['Max'].notna().any():
                max_val = limit_hist['Max'].iloc[0]
                fig.add_hline(y=max_val, line_dash="dash", line_color="red", annotation_text=f"Max: {max_val}%")
            
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato storico disponibile.")

# Footer
st.markdown("---")
st.markdown("### ℹ️ Note Tecniche")
with st.expander("Dettagli implementazione"):
    st.markdown("""
    **Versione**: 2.0 con Dashboard Generale
    
    **Funzionalità principali**:
    - Dashboard generale con vista su tutti i fondi
    - Analisi dettagliata per singolo fondo
    - Calcolo automatico limiti CDA
    - Visualizzazioni gauge e trend storici
    
    **Limiti calcolabili**:
    - Azioni, Obbligazioni, OICR
    - Esposizione mercati emergenti
    - Esposizione valutaria EUR
    - Rating (inferiore ad adeguato, D, NR)
    - Duration
    
    **Limiti non calcolabili**: Convertibili (richiede dati aggiuntivi)
    """)
