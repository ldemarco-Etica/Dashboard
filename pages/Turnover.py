#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALISI TURNOVER - VERSIONE MIGLIORATA CON TRACKING MOVIMENTI DETTAGLIATO
==========================================================================
Modifiche principali:
1. Nuovo metodo get_detailed_movements() che traccia TUTTI i movimenti nel periodo
2. Data movimento invece di Contrib %
3. Cattura operazioni intra-periodo (compra-vendi nello stesso periodo)
4. Delta con segno reale (positivo/negativo)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging

# Import utils per autenticazione


# Configurazione pagina
st.set_page_config(
    page_title="Analisi Turnover",
    page_icon="🔀",
    layout="wide"
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# VERIFICA AUTENTICAZIONE
# ============================================================================

#check_page_access_auth0("Turnover")

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

class TurnoverConfig:
    """Configurazione per il calcolo del turnover"""
    
    # Periodi predefiniti
    PERIODS = {
        'Ultimo Mese': 30,
        'Ultimi 3 Mesi': 90,
        'Ultimi 6 Mesi': 180,
        'Ultimo Anno': 365,
        'YTD': 'ytd'
    }
    
    # Soglie
    MIN_VALUE_THRESHOLD = 10000  # Euro minimi per considerare un movimento


# ============================================================================
# CALCOLO TURNOVER
# ============================================================================

class TurnoverCalculator:
    """Calcola metriche di turnover basate su quantità"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
    
    def calculate(self,
                  fund_name: str,
                  start_date: datetime,
                  end_date: datetime) -> Dict[str, Any]:
        """
        Calcola turnover per periodo specificato (basato su quantità)
        """
        try:
            # Filtra dati
            fund_data = self.data[
                (self.data['NomeFondo'] == fund_name) &
                (self.data['DataRiferimento'] >= start_date) &
                (self.data['DataRiferimento'] <= end_date)
            ].copy()
            
            if fund_data.empty:
                return {'error': 'Nessun dato disponibile per il periodo', 'is_valid': False}
            
            # Date effettive
            actual_start = fund_data['DataRiferimento'].min()
            actual_end = fund_data['DataRiferimento'].max()
            
            if actual_start == actual_end:
                return {'error': 'Necessarie almeno 2 date diverse', 'is_valid': False}
            
            # Snapshot inizio e fine
            df_start = fund_data[fund_data['DataRiferimento'] == actual_start]
            df_end = fund_data[fund_data['DataRiferimento'] == actual_end]
            
            # Merge per calcolare variazioni
            merged = pd.merge(
                df_start[['ISIN', 'Descrizione', 'QtaPortafoglio', 'Controvalore_EUR', 'TipoStrumento']],
                df_end[['ISIN', 'Descrizione', 'QtaPortafoglio', 'Controvalore_EUR', 'TipoStrumento']],
                on='ISIN',
                how='outer',
                suffixes=('_start', '_end')
            )
            
            # FIX: Forza unicità su ISIN
            merged = merged.drop_duplicates(subset=['ISIN'])
            
            # Unifica descrizioni e tipo strumento
            merged['Descrizione'] = merged['Descrizione_start'].combine_first(merged['Descrizione_end'])
            merged['TipoStrumento'] = merged['TipoStrumento_start'].combine_first(merged['TipoStrumento_end'])
            
            # Riempi NaN con 0
            for col in ['QtaPortafoglio_start', 'QtaPortafoglio_end', 'Controvalore_EUR_start', 'Controvalore_EUR_end']:
                merged[col] = merged[col].fillna(0)
            
            # Rimuovi colonne temporanee
            merged = merged.drop(columns=['Descrizione_start', 'Descrizione_end', 'TipoStrumento_start', 'TipoStrumento_end'])
            
            # Calcola prezzo medio
            merged['Prezzo_Medio'] = np.where(
                (merged['QtaPortafoglio_start'] + merged['QtaPortafoglio_end']) > 0,
                (merged['Controvalore_EUR_start'] + merged['Controvalore_EUR_end']) /
                (merged['QtaPortafoglio_start'] + merged['QtaPortafoglio_end']),
                0
            )
            
            # Variazioni
            merged['Delta_Qta'] = abs(merged['QtaPortafoglio_end'] - merged['QtaPortafoglio_start'])
            merged['Delta_Valore'] = merged['Delta_Qta'] * merged['Prezzo_Medio']
            
            # Totali
            total_variation = merged['Delta_Valore'].sum()
            
            # AUM
            aum_start = df_start['Controvalore_EUR'].sum()
            aum_end = df_end['Controvalore_EUR'].sum()
            
            # AUM medio mensile
            daily_aum = fund_data.groupby('DataRiferimento')['Controvalore_EUR'].sum().reset_index(name='AUM')
            daily_aum['Mese'] = daily_aum['DataRiferimento'].dt.to_period('M')
            monthly_avg_aum = daily_aum.groupby('Mese')['AUM'].mean()
            avg_aum = monthly_avg_aum.mean() if not monthly_avg_aum.empty else (aum_start + aum_end) / 2
            
            # Acquisti e vendite
            purchases = merged[merged['QtaPortafoglio_end'] > merged['QtaPortafoglio_start']]
            sales = merged[merged['QtaPortafoglio_end'] < merged['QtaPortafoglio_start']]
            
            purchases_value = purchases['Delta_Valore'].sum()
            sales_value = sales['Delta_Valore'].sum()
            
            # Trading volume
            trading_volume = min(purchases_value, sales_value)
            turnover_rate = (trading_volume / avg_aum * 100) if avg_aum > 0 else 0
            
            # Annualizzato
            days = (actual_end - actual_start).days
            annualized = turnover_rate * (365 / days) if days > 0 else 0
            
            return {
                'is_valid': True,
                'turnover_rate': turnover_rate,
                'annualized_turnover': annualized,
                'total_variation': total_variation,
                'purchases_value': purchases_value,
                'sales_value': sales_value,
                'trading_volume': trading_volume,
                'avg_aum': avg_aum,
                'aum_start': aum_start,
                'aum_end': aum_end,
                'num_securities_start': len(df_start),
                'num_securities_end': len(df_end),
                'period_days': days,
                'actual_start_date': actual_start,
                'actual_end_date': actual_end,
                'breakdown': merged
            }
            
        except Exception as e:
            logger.error(f"Turnover calculation error: {e}")
            return {'error': str(e), 'is_valid': False}
    
    def calculate_sequential(self,
                             fund_name: str,
                             start_date: datetime,
                             end_date: datetime) -> Dict[str, Any]:
        """
        Calcola turnover sequenziale per catturare movimenti intermedi
        """
        try:
            fund_data = self.data[
                (self.data['NomeFondo'] == fund_name) &
                (self.data['DataRiferimento'] >= start_date) &
                (self.data['DataRiferimento'] <= end_date)
            ].copy()
            
            if fund_data.empty:
                return {'error': 'Nessun dato disponibile per il periodo', 'is_valid': False}
            
            fund_data = fund_data.sort_values('DataRiferimento')
            dates = sorted(fund_data['DataRiferimento'].unique())
            
            if len(dates) < 2:
                return {'error': 'Necessarie almeno 2 date diverse', 'is_valid': False}
            
            total_variation_seq = 0
            aums = []
            purchases_seq = 0
            sales_seq = 0
            
            for i in range(len(dates) - 1):
                df_curr = fund_data[fund_data['DataRiferimento'] == dates[i]]
                df_next = fund_data[fund_data['DataRiferimento'] == dates[i+1]]
                
                merged_seq = pd.merge(
                    df_curr[['ISIN', 'QtaPortafoglio', 'Controvalore_EUR']],
                    df_next[['ISIN', 'QtaPortafoglio', 'Controvalore_EUR']],
                    on='ISIN',
                    how='outer',
                    suffixes=('_curr', '_next')
                )
                
                for col in ['QtaPortafoglio_curr', 'QtaPortafoglio_next', 'Controvalore_EUR_curr', 'Controvalore_EUR_next']:
                    merged_seq[col] = merged_seq[col].fillna(0)
                
                merged_seq['Prezzo_Medio'] = np.where(
                    (merged_seq['QtaPortafoglio_curr'] + merged_seq['QtaPortafoglio_next']) > 0,
                    (merged_seq['Controvalore_EUR_curr'] + merged_seq['Controvalore_EUR_next']) /
                    (merged_seq['QtaPortafoglio_curr'] + merged_seq['QtaPortafoglio_next']),
                    0
                )
                
                merged_seq['Delta_Qta'] = abs(merged_seq['QtaPortafoglio_next'] - merged_seq['QtaPortafoglio_curr'])
                merged_seq['Delta_Valore'] = merged_seq['Delta_Qta'] * merged_seq['Prezzo_Medio']
                
                delta_seq = merged_seq['Delta_Valore'].sum()
                total_variation_seq += delta_seq
                
                purchases_delta = merged_seq[merged_seq['QtaPortafoglio_next'] > merged_seq['QtaPortafoglio_curr']]['Delta_Valore'].sum()
                sales_delta = merged_seq[merged_seq['QtaPortafoglio_next'] < merged_seq['QtaPortafoglio_curr']]['Delta_Valore'].sum()
                purchases_seq += purchases_delta
                sales_seq += sales_delta
                
                aums.append(df_curr['Controvalore_EUR'].sum())
            
            aums.append(df_next['Controvalore_EUR'].sum())
            
            # AUM medio mensile
            daily_aum = fund_data.groupby('DataRiferimento')['Controvalore_EUR'].sum().reset_index(name='AUM')
            daily_aum['Mese'] = daily_aum['DataRiferimento'].dt.to_period('M')
            monthly_avg_aum = daily_aum.groupby('Mese')['AUM'].mean()
            avg_aum_seq = monthly_avg_aum.mean() if not monthly_avg_aum.empty else np.mean(aums)
            
            trading_volume_seq = min(purchases_seq, sales_seq)
            turnover_rate_seq = (trading_volume_seq / avg_aum_seq * 100) if avg_aum_seq > 0 else 0
            
            days = (dates[-1] - dates[0]).days
            annualized_seq = turnover_rate_seq * (365 / days) if days > 0 else 0
            
            return {
                'is_valid': True,
                'turnover_rate': turnover_rate_seq,
                'annualized_turnover': annualized_seq,
                'total_variation': total_variation_seq,
                'purchases_value': purchases_seq,
                'sales_value': sales_seq,
                'trading_volume': trading_volume_seq,
                'avg_aum': avg_aum_seq,
                'aum_start': aums[0],
                'aum_end': aums[-1],
                'num_securities_start': len(fund_data[fund_data['DataRiferimento'] == dates[0]]),
                'num_securities_end': len(fund_data[fund_data['DataRiferimento'] == dates[-1]]),
                'period_days': days,
                'actual_start_date': dates[0],
                'actual_end_date': dates[-1],
                'breakdown': pd.DataFrame()
            }
            
        except Exception as e:
            logger.error(f"Sequential turnover calculation error: {e}")
            return {'error': str(e), 'is_valid': False}
    
    def get_detailed_movements(self,
                              fund_name: str,
                              start_date: datetime,
                              end_date: datetime) -> pd.DataFrame:
        """
        Genera tabella dettagliata di TUTTI i movimenti nel periodo
        """
        try:
            fund_data = self.data[
                (self.data['NomeFondo'] == fund_name) &
                (self.data['DataRiferimento'] >= start_date) &
                (self.data['DataRiferimento'] <= end_date)
            ].copy()
            
            if fund_data.empty:
                return pd.DataFrame()
            
            fund_data = fund_data.sort_values('DataRiferimento')
            dates = sorted(fund_data['DataRiferimento'].unique())
            
            if len(dates) < 2:
                return pd.DataFrame()
            
            all_movements = []
            
            for i in range(len(dates) - 1):
                date_from = dates[i]
                date_to = dates[i + 1]
                
                df_from = fund_data[fund_data['DataRiferimento'] == date_from]
                df_to = fund_data[fund_data['DataRiferimento'] == date_to]
                
                merged = pd.merge(
                    df_from[['ISIN', 'Descrizione', 'QtaPortafoglio', 'Controvalore_EUR', 'TipoStrumento']],
                    df_to[['ISIN', 'Descrizione', 'QtaPortafoglio', 'Controvalore_EUR', 'TipoStrumento']],
                    on='ISIN',
                    how='outer',
                    suffixes=('_from', '_to')
                )
                
                merged['Descrizione'] = merged['Descrizione_from'].combine_first(merged['Descrizione_to'])
                merged['TipoStrumento'] = merged['TipoStrumento_from'].combine_first(merged['TipoStrumento_to'])
                
                for col in ['QtaPortafoglio_from', 'QtaPortafoglio_to', 'Controvalore_EUR_from', 'Controvalore_EUR_to']:
                    merged[col] = merged[col].fillna(0)
                
                merged['Prezzo_Medio'] = np.where(
                    (merged['QtaPortafoglio_from'] + merged['QtaPortafoglio_to']) > 0,
                    (merged['Controvalore_EUR_from'] + merged['Controvalore_EUR_to']) /
                    (merged['QtaPortafoglio_from'] + merged['QtaPortafoglio_to']),
                    0
                )
                
                merged['Delta_Qta_Signed'] = merged['QtaPortafoglio_to'] - merged['QtaPortafoglio_from']
                merged['Delta_Qta'] = abs(merged['Delta_Qta_Signed'])
                merged['Delta_Valore'] = merged['Delta_Qta'] * merged['Prezzo_Medio']
                
                def classify_movement(row):
                    if row['QtaPortafoglio_from'] == 0 and row['QtaPortafoglio_to'] > 0:
                        return 'Nuova Posizione'
                    elif row['QtaPortafoglio_from'] > 0 and row['QtaPortafoglio_to'] == 0:
                        return 'Chiusura Posizione'
                    elif row['Delta_Qta_Signed'] > 0:
                        return 'Incremento'
                    elif row['Delta_Qta_Signed'] < 0:
                        return 'Riduzione'
                    else:
                        return 'Invariato'
                
                merged['Tipo_Movimento'] = merged.apply(classify_movement, axis=1)
                merged['Data_Movimento'] = date_to
                
                movements = merged[merged['Delta_Qta'] > 0].copy()
                
                movements = movements[[
                    'Data_Movimento',
                    'Descrizione', 
                    'Tipo_Movimento',
                    'QtaPortafoglio_from',
                    'QtaPortafoglio_to',
                    'Controvalore_EUR_from',
                    'Controvalore_EUR_to',
                    'Delta_Qta',
                    'Delta_Valore',
                    'Delta_Qta_Signed',
                    'Prezzo_Medio',
                    'ISIN'
                ]]
                
                all_movements.append(movements)
            
            if not all_movements:
                return pd.DataFrame()
            
            result_df = pd.concat(all_movements, ignore_index=True)
            result_df = result_df.sort_values('Delta_Valore', ascending=False)
            
            return result_df
            
        except Exception as e:
            logger.error(f"Detailed movements error: {e}")
            return pd.DataFrame()


# ============================================================================
# STREAMLIT UI
# ============================================================================

st.title("🔀 Analisi Turnover di Portafoglio")
st.markdown("**Analisi movimentazione titoli basata su dati depositaria**")
st.markdown("---")

# ============================================================================
# VERIFICA DATI
# ============================================================================

if 'depositaria_data' not in st.session_state or st.session_state['depositaria_data'].empty:
    st.error("❌ **Dati depositaria non disponibili**")
    st.info("""
    **Per utilizzare l'analisi Turnover:**
    
    1. Assicurati che il file Parquet sia stato creato
    2. Torna alla **Home** e clicca su **"Load/Reload All Data"**
    3. I dati depositaria verranno caricati automaticamente
    """)
    st.stop()

data = st.session_state['depositaria_data']

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    
    st.divider()
    st.header("⚙️ Configurazione Analisi")
    
    st.subheader("Modalità Calcolo")
    sequential_mode = st.checkbox(
        "Modalità Sequenziale",
        value=True,
        help="✅ Raccomandato: cattura TUTTI i movimenti nel periodo"
    )
    
    st.markdown("---")
    st.subheader("📊 Dati Caricati")
    st.metric("Record Totali", f"{len(data):,}")
    st.metric("Fondi", data['NomeFondo'].nunique())
    date_range = f"{data['DataRiferimento'].min():%d/%m/%Y} - {data['DataRiferimento'].max():%d/%m/%Y}"
    st.caption(f"📅 Range: {date_range}")

# ============================================================================
# FILTRI
# ============================================================================

st.subheader("🎯 Parametri Analisi")

col1, col2 = st.columns([1, 2])

with col1:
    available_funds = sorted(data['NomeFondo'].dropna().unique())
    if not available_funds:
        st.error("❌ Nessun fondo disponibile")
        st.stop()
    selected_fund = st.selectbox("Fondo", available_funds, key='fund_select')

with col2:
    period_options = list(TurnoverConfig.PERIODS.keys()) + ['Personalizzato']
    selected_period = st.selectbox("Periodo Analisi", period_options, key='period_select')

fund_data = data[data['NomeFondo'] == selected_fund]
max_date = fund_data['DataRiferimento'].max()
min_date = fund_data['DataRiferimento'].min()

if selected_period == 'Personalizzato':
    col_a, col_b = st.columns(2)
    with col_a:
        start_date = st.date_input("Data Inizio", value=max_date - timedelta(days=30),
                                   min_value=min_date.date(), max_value=max_date.date())
    with col_b:
        end_date = st.date_input("Data Fine", value=max_date.date(),
                                min_value=min_date.date(), max_value=max_date.date())
    start_date = datetime.combine(start_date, datetime.min.time())
    end_date = datetime.combine(end_date, datetime.min.time())
elif selected_period == 'YTD':
    start_date = datetime(max_date.year, 1, 1)
    end_date = max_date
else:
    days = TurnoverConfig.PERIODS[selected_period]
    start_date = max_date - timedelta(days=days)
    end_date = max_date

st.markdown("---")

# ============================================================================
# CALCOLO
# ============================================================================

st.subheader("📊 Risultati Turnover")

with st.spinner("Calcolo turnover..."):
    calc = TurnoverCalculator(data)
    if sequential_mode:
        result = calc.calculate_sequential(selected_fund, start_date, end_date)
    else:
        result = calc.calculate(selected_fund, start_date, end_date)

if not result.get('is_valid'):
    st.error(f"❌ Errore: {result.get('error')}")
    st.stop()

# ============================================================================
# METRICHE
# ============================================================================

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Turnover Periodo", f"{result['turnover_rate']:.2f}%",
             help=f"{result['period_days']} giorni")
with col2:
    st.metric("Turnover Annualizzato", f"{result['annualized_turnover']:.2f}%",
             help="Proiezione annuale")
with col3:
    st.metric("Acquisti", f"€{result['purchases_value']/1_000_000:.1f}M")
with col4:
    st.metric("Vendite", f"€{result['sales_value']/1_000_000:.1f}M")
with col5:
    st.metric("Trading Volume", f"€{result['trading_volume']/1_000_000:.1f}M",
             help="Minimo tra acquisti e vendite")

with st.expander("ℹ️ Dettagli Calcolo"):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("AUM Inizio", f"€{result['aum_start']/1_000_000:.1f}M")
        st.metric("Titoli Inizio", result['num_securities_start'])
    with col_b:
        st.metric("AUM Fine", f"€{result['aum_end']/1_000_000:.1f}M")
        st.metric("Titoli Fine", result['num_securities_end'])
    with col_c:
        st.metric("AUM Medio", f"€{result['avg_aum']/1_000_000:.1f}M")
        st.metric("Periodo", f"{result['period_days']} giorni")
    st.caption(f"📅 Date effettive: {result['actual_start_date']:%d/%m/%Y} - {result['actual_end_date']:%d/%m/%Y}")

st.markdown("---")

# ============================================================================
# DETTAGLIO MOVIMENTI
# ============================================================================

st.subheader("📋 Dettaglio Movimenti")

with st.spinner("Caricamento dettaglio movimenti..."):
    breakdown = calc.get_detailed_movements(selected_fund, start_date, end_date)

if breakdown.empty:
    st.info("ℹ️ Nessun movimento significativo nel periodo")
else:
    total_movements = len(breakdown)
    unique_securities = breakdown['ISIN'].nunique()
    
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Movimenti Totali", f"{total_movements:,}")
    with col_info2:
        st.metric("Titoli Movimentati", unique_securities)
    with col_info3:
        avg_value = breakdown['Delta_Valore'].mean()
        st.metric("Valore Medio Movimento", f"€{avg_value:,.0f}")
    
    st.markdown("---")
    
    # Prepara display con segno
    display_df = breakdown.copy()
    display_df['Delta_Valore_Signed'] = display_df['Delta_Qta_Signed'] * display_df['Prezzo_Medio']
    
    display_df = display_df[[
        'Data_Movimento',
        'Descrizione',
        'Tipo_Movimento',
        'QtaPortafoglio_from',
        'QtaPortafoglio_to',
        'Controvalore_EUR_from',
        'Controvalore_EUR_to',
        'Delta_Qta_Signed',
        'Delta_Valore_Signed',
        'ISIN'
    ]]
    
    display_df.columns = [
        'Data Movimento',
        'Titolo',
        'Tipo Movimento',
        'Qta Inizio',
        'Qta Fine',
        'Valore Inizio',
        'Valore Fine',
        'Delta Qta',
        'Delta Valore',
        'ISIN'
    ]
    
    formatter = {
        'Data Movimento': lambda x: x.strftime('%d/%m/%Y'),
        'Qta Inizio': '{:,.2f}',
        'Qta Fine': '{:,.2f}',
        'Delta Qta': '{:+,.2f}',
        'Valore Inizio': '€{:,.0f}',
        'Valore Fine': '€{:,.0f}',
        'Delta Valore': '€{:+,.0f}'
    }
    
    st.dataframe(
        display_df.style.format(formatter),
        use_container_width=True,
        height=400
    )
    
    st.download_button(
        "📥 Esporta CSV Completo",
        data=breakdown.to_csv(index=False).encode('utf-8'),
        file_name=f"turnover_dettaglio_{selected_fund}_{start_date:%Y%m%d}_{end_date:%Y%m%d}.csv",
        mime="text/csv"
    )

st.markdown("---")

# ============================================================================
# GRAFICI
# ============================================================================

st.subheader("📈 Visualizzazioni")

tab1, tab2, tab3 = st.tabs(["Top Movimenti", "Distribuzione per Tipo", "Timeline Movimenti"])

with tab1:
    if not breakdown.empty:
        top_20 = breakdown.nlargest(20, 'Delta_Valore')
        fig1 = px.bar(
            top_20,
            y='Descrizione',
            x='Delta_Valore',
            color='Tipo_Movimento',
            orientation='h',
            title="Top 20 Titoli per Valore Movimento",
            labels={'Delta_Valore': 'Variazione Assoluta (€)', 'Descrizione': 'Titolo'},
            color_discrete_map={
                'Nuova Posizione': '#28a745',
                'Chiusura Posizione': '#dc3545',
                'Incremento': '#007bff',
                'Riduzione': '#ffc107'
            }
        )
        fig1.update_layout(height=600)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("ℹ️ Nessun dato per grafico")

with tab2:
    if not breakdown.empty:
        movement_summary = breakdown.groupby('Tipo_Movimento').agg({
            'Delta_Valore': 'sum',
            'ISIN': 'count'
        }).reset_index()
        
        movement_summary.columns = ['Tipo', 'Controvalore', 'Numero Movimenti']
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            fig2 = px.pie(
                movement_summary,
                names='Tipo',
                values='Controvalore',
                title="Distribuzione Turnover per Tipo",
                hole=0.4
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        with col_chart2:
            fig3 = px.pie(
                movement_summary,
                names='Tipo',
                values='Numero Movimenti',
                title="Numero Movimenti per Tipo",
                hole=0.4
            )
            st.plotly_chart(fig3, use_container_width=True)
        
        st.dataframe(movement_summary, use_container_width=True)
    else:
        st.info("ℹ️ Nessun dato per grafico")

with tab3:
    if not breakdown.empty:
        # Raggruppa per data
        daily_movements = breakdown.groupby('Data_Movimento').agg({
            'Delta_Valore': 'sum',
            'ISIN': 'count'
        }).reset_index()
        
        daily_movements.columns = ['Data', 'Valore Totale', 'Numero Movimenti']
        
        fig4 = go.Figure()
        
        fig4.add_trace(go.Scatter(
            x=daily_movements['Data'],
            y=daily_movements['Valore Totale'],
            mode='lines+markers',
            name='Valore Movimenti',
            line=dict(color='#007bff', width=2),
            marker=dict(size=8)
        ))
        
        fig4.update_layout(
            title="Timeline Movimenti - Valore Giornaliero",
            xaxis_title="Data",
            yaxis_title="Valore Movimenti (€)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig4, use_container_width=True)
        
        # Tabella riassuntiva
        st.dataframe(
            daily_movements.style.format({
                'Data': lambda x: x.strftime('%d/%m/%Y'),
                'Valore Totale': '€{:,.0f}',
                'Numero Movimenti': '{:,.0f}'
            }),
            use_container_width=True
        )
    else:
        st.info("ℹ️ Nessun dato per grafico")

# ============================================================================
# ANALISI AVANZATA
# ============================================================================

if not breakdown.empty:
    st.markdown("---")
    st.subheader("🔬 Analisi Avanzata")
    
    with st.expander("📊 Statistiche per Tipo Strumento"):
        # Recupera TipoStrumento dal breakdown originale prima della riorganizzazione
        breakdown_with_type = calc.get_detailed_movements(selected_fund, start_date, end_date)
        
        if not breakdown_with_type.empty and 'TipoStrumento' in breakdown_with_type.columns:
            instrument_analysis = breakdown_with_type.groupby('TipoStrumento').agg({
                'Delta_Valore': ['sum', 'mean', 'count'],
                'ISIN': 'nunique'
            }).round(2)
            
            instrument_analysis.columns = ['Valore Totale', 'Valore Medio', 'N° Movimenti', 'Titoli Unici']
            instrument_analysis = instrument_analysis.sort_values('Valore Totale', ascending=False)
            
            st.dataframe(
                instrument_analysis.style.format({
                    'Valore Totale': '€{:,.0f}',
                    'Valore Medio': '€{:,.0f}',
                    'N° Movimenti': '{:,.0f}',
                    'Titoli Unici': '{:,.0f}'
                }),
                use_container_width=True
            )
        else:
            st.info("ℹ️ Informazioni sul tipo strumento non disponibili")
    
    with st.expander("🔝 Titoli con Più Movimenti"):
        # Titoli che hanno avuto più movimenti nel periodo
        multi_movements = breakdown.groupby(['ISIN', 'Descrizione']).agg({
            'Data_Movimento': 'count',
            'Delta_Valore': 'sum'
        }).reset_index()
        
        multi_movements.columns = ['ISIN', 'Titolo', 'N° Movimenti', 'Valore Totale']
        multi_movements = multi_movements[multi_movements['N° Movimenti'] > 1]
        multi_movements = multi_movements.sort_values('N° Movimenti', ascending=False)
        
        if not multi_movements.empty:
            st.dataframe(
                multi_movements.style.format({
                    'N° Movimenti': '{:,.0f}',
                    'Valore Totale': '€{:,.0f}'
                }),
                use_container_width=True
            )
            
            st.info(f"ℹ️ {len(multi_movements)} titoli hanno avuto movimenti multipli nel periodo")
        else:
            st.info("ℹ️ Nessun titolo con movimenti multipli nel periodo")

# ============================================================================
# CONFRONTO MODALITÀ
# ============================================================================

st.markdown("---")

with st.expander("⚖️ Confronto Modalità Standard vs Sequenziale"):
    st.markdown("""
    ### Differenze Chiave
    
    **Modalità Standard** (Snapshot Inizio-Fine):
    - ✅ Più veloce
    - ✅ Semplice da interpretare
    - ❌ **Perde movimenti intra-periodo**
    - ❌ Mostra solo delta netto per titolo
    
    **Esempio**: Se un titolo viene comprato a inizio periodo e rivenduto a metà periodo,
    la modalità standard **NON lo rileva**.
    
    ---
    
    **Modalità Sequenziale** ✅ *Raccomandata*:
    - ✅ **Cattura TUTTI i movimenti**
    - ✅ Include operazioni intra-periodo
    - ✅ Più accurata per analisi dettagliate
    - ⚠️ Leggermente più lenta su dataset molto grandi
    
    **Esempio**: Stesso caso sopra, la modalità sequenziale rileva **entrambe** le operazioni
    (acquisto + vendita) con le rispettive date.
    
    ---
    
    ### 💡 Raccomandazione
    Usa **sempre la modalità sequenziale** per analisi complete, specialmente per:
    - Periodi lunghi (3+ mesi)
    - Portafogli con alta rotazione
    - Analisi di compliance/reporting
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
<div style="text-align: center; color: gray; font-size: 0.8em;">
    Analisi Turnover Enhanced - Dashboard Portfolio Etica SGR<br>
    🆕 Versione 2.0 - Tracking Movimenti Dettagliato
</div>
""", unsafe_allow_html=True)
