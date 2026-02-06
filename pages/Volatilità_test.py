# pages/Volatilità.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from pathlib import Path
from utils import check_page_access_auth0, format_date

# ============================================
# 🔐 CONTROLLO ACCESSO
# ============================================
# check_page_access_auth0("Volatilità")

# ============================================
# CONFIGURAZIONE
# ============================================
st.set_page_config(layout="wide")
st.title("📊 Analisi Volatilità")

# Parametri di calcolo
ROLLING_WINDOW = 260  # giorni lavorativi in un anno
ANNUALIZATION_FACTOR = np.sqrt(260)

# Percorso file
QUOTE_FILE = Path("data") / "quote lorde.xlsx"

# ============================================
# CARICAMENTO DATI
# ============================================

@st.cache_data(ttl=3600)
def load_quote_data():
    """Carica dati quote dal file Excel"""
    try:
        if not QUOTE_FILE.exists():
            st.error(f"❌ File non trovato: {QUOTE_FILE}")
            st.info("💡 Assicurati che il file 'quote lorde.xlsx' sia nella cartella 'data/'")
            return pd.DataFrame()
        
        df = pd.read_excel(
            QUOTE_FILE,
            sheet_name="Quote Lorde",
            skiprows=1  # salta riga 1
        )
        
        # Rinomina prima colonna come "Date"
        df = df.rename(columns={df.columns[0]: "Date"})
        
        # Converti data
        df["Date"] = pd.to_datetime(df["Date"])
        
        # Rimuovi colonne completamente vuote
        df = df.dropna(axis=1, how='all')
        
        # Ordina per data
        df = df.sort_values("Date")
        
        st.success(f"✅ Caricati dati quote: {len(df)} righe, {len(df.columns)-1} fondi")
        
        return df
        
    except Exception as e:
        st.error(f"❌ Errore caricamento dati quote: {e}")
        return pd.DataFrame()


# Carica dati
df_quote = load_quote_data()

if df_quote.empty:
    st.error("❌ Impossibile procedere senza dati quote.")
    st.stop()

# Lista fondi (tutte le colonne eccetto Date)
available_funds = [col for col in df_quote.columns if col != "Date"]

if not available_funds:
    st.error("❌ Nessun fondo trovato nel file")
    st.stop()

# ============================================
# FUNZIONI DI CALCOLO
# ============================================

def calculate_volatility_metrics(df: pd.DataFrame, fund_name: str) -> pd.DataFrame:
    """
    Calcola metriche di volatilità per un fondo
    
    Returns:
        DataFrame con Date, Quota, Volatilità 1Y, Drawdown
    """
    try:
        if fund_name not in df.columns:
            return pd.DataFrame()
        
        # Prepara dati
        df_fund = df[['Date', fund_name]].copy()
        df_fund = df_fund.rename(columns={fund_name: 'Quota'})
        df_fund = df_fund.dropna(subset=['Quota'])
        df_fund = df_fund.sort_values('Date')
        
        if len(df_fund) < 2:
            return pd.DataFrame()
        
        # Calcola rendimenti giornalieri
        df_fund['Returns'] = df_fund['Quota'].pct_change()
        
        # Volatilità rolling 1Y annualizzata
        df_fund['Volatilità_1Y'] = (
            df_fund['Returns']
            .rolling(window=ROLLING_WINDOW, min_periods=ROLLING_WINDOW)
            .std() * ANNUALIZATION_FACTOR * 100  # in percentuale
        )
        
        # Drawdown
        cum_max = df_fund['Quota'].cummax()
        df_fund['Drawdown'] = ((df_fund['Quota'] / cum_max) - 1) * 100  # in percentuale
        
        return df_fund[['Date', 'Quota', 'Volatilità_1Y', 'Drawdown', 'Returns']]
        
    except Exception as e:
        st.error(f"Errore nel calcolo volatilità per {fund_name}: {e}")
        return pd.DataFrame()


def calculate_summary_stats(df_metrics: pd.DataFrame) -> dict:
    """Calcola statistiche riassuntive"""
    if df_metrics.empty or df_metrics['Volatilità_1Y'].isna().all():
        return {
            'vol_current': np.nan,
            'vol_3y': np.nan,
            'vol_5y': np.nan,
            'vol_max': np.nan,
            'dd_max': np.nan
        }
    
    vol_data = df_metrics['Volatilità_1Y'].dropna()
    dd_data = df_metrics['Drawdown'].dropna()
    returns_data = df_metrics['Returns'].dropna()
    
    # Volatilità attuale (ultima disponibile)
    vol_current = vol_data.iloc[-1] if len(vol_data) > 0 else np.nan
    
    # Volatilità ultimi 3 anni (circa 780 giorni lavorativi)
    if len(returns_data) >= 780:
        last_3y_returns = returns_data.tail(780)
        vol_3y = last_3y_returns.std() * ANNUALIZATION_FACTOR * 100
    else:
        vol_3y = np.nan
    
    # Volatilità ultimi 5 anni (circa 1300 giorni lavorativi)
    if len(returns_data) >= 1300:
        last_5y_returns = returns_data.tail(1300)
        vol_5y = last_5y_returns.std() * ANNUALIZATION_FACTOR * 100
    else:
        vol_5y = np.nan
    
    return {
        'vol_current': vol_current,
        'vol_3y': vol_3y,
        'vol_5y': vol_5y,
        'vol_max': vol_data.max(),
        'dd_max': dd_data.min()  # min perché drawdown è negativo
    }

# ============================================
# SIDEBAR - FILTRI
# ============================================
st.sidebar.header("🔧 Filtri Analisi")

# ============================================
# TAB SYSTEM
# ============================================
tab1, tab2 = st.tabs(["📊 Confronto Fondi", "📈 Analisi Serie Storica"])

# ============================================
# TAB 1: CONFRONTO FONDI
# ============================================
with tab1:
    st.subheader("📊 Confronto Metriche di Volatilità tra Fondi")
    
    st.info("💡 Snapshot delle metriche di volatilità per tutti i fondi basato sui dati disponibili")
    
    # Calcola metriche per tutti i fondi
    with st.spinner("Calcolo metriche per tutti i fondi..."):
        summary_data = []
        
        progress_bar = st.progress(0)
        
        for i, fund in enumerate(available_funds):
            metrics_df = calculate_volatility_metrics(df_quote, fund)
            
            if not metrics_df.empty:
                stats = calculate_summary_stats(metrics_df)
                
                summary_data.append({
                    'Fondo': fund,
                    'Volatilità 1Y Attuale (%)': stats['vol_current'],
                    'Volatilità 3Y (%)': stats['vol_3y'],
                    'Volatilità 5Y (%)': stats['vol_5y'],
                    'Volatilità Massima Storica (%)': stats['vol_max'],
                    'Max Drawdown Storico (%)': stats['dd_max']
                })
            
            progress_bar.progress((i + 1) / len(available_funds))
        
        progress_bar.empty()
    
    if not summary_data:
        st.warning("⚠️ Nessun dato disponibile per il confronto")
    else:
        df_summary = pd.DataFrame(summary_data)
        
        # Ordina per volatilità attuale decrescente
        df_summary = df_summary.sort_values('Volatilità 1Y Attuale (%)', ascending=False)
        
        # Formatta tabella
        df_display = df_summary.copy()
        
        # Formatta numeri
        numeric_cols = [col for col in df_display.columns if col != 'Fondo']
        for col in numeric_cols:
            df_display[col] = df_display[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        
        # Mostra tabella
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Fondo": st.column_config.TextColumn("Fondo", width="medium"),
                "Volatilità 1Y Attuale (%)": st.column_config.TextColumn("Vol. 1Y Attuale", width="small"),
                "Volatilità 3Y (%)": st.column_config.TextColumn("Vol. 3Y", width="small"),
                "Volatilità 5Y (%)": st.column_config.TextColumn("Vol. 5Y", width="small"),
                "Volatilità Massima Storica (%)": st.column_config.TextColumn("Vol. Max", width="small"),
                "Max Drawdown Storico (%)": st.column_config.TextColumn("Max DD", width="small")
            }
        )
        
        # Grafico comparativo
        st.subheader("📊 Confronto Visivo")
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # Grafico volatilità multipla
            fig_vol = go.Figure()
            
            # Vol 1Y
            fig_vol.add_trace(go.Bar(
                x=df_summary['Fondo'],
                y=df_summary['Volatilità 1Y Attuale (%)'],
                name='Vol. 1Y',
                marker_color='steelblue'
            ))
            
            # Vol 3Y
            fig_vol.add_trace(go.Bar(
                x=df_summary['Fondo'],
                y=df_summary['Volatilità 3Y (%)'],
                name='Vol. 3Y',
                marker_color='lightseagreen'
            ))
            
            # Vol 5Y
            fig_vol.add_trace(go.Bar(
                x=df_summary['Fondo'],
                y=df_summary['Volatilità 5Y (%)'],
                name='Vol. 5Y',
                marker_color='mediumslateblue'
            ))
            
            fig_vol.update_layout(
                title="Confronto Volatilità per Fondo",
                xaxis_title="Fondo",
                yaxis_title="Volatilità (%)",
                xaxis_tickangle=-45,
                height=500,
                barmode='group'
            )
            
            st.plotly_chart(fig_vol, use_container_width=True)
        
        with col_chart2:
            # Grafico max drawdown
            fig_dd = go.Figure()
            
            fig_dd.add_trace(go.Bar(
                x=df_summary['Fondo'],
                y=df_summary['Max Drawdown Storico (%)'],
                name='Max Drawdown',
                marker_color='crimson'
            ))
            
            fig_dd.update_layout(
                title="Max Drawdown Storico per Fondo",
                xaxis_title="Fondo",
                yaxis_title="Drawdown (%)",
                xaxis_tickangle=-45,
                height=500
            )
            
            st.plotly_chart(fig_dd, use_container_width=True)
        
        # Export
        st.divider()
        
        if st.button("📥 Esporta Confronto CSV"):
            csv = df_summary.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"confronto_volatilità_{datetime.now():%Y%m%d}.csv",
                mime="text/csv"
            )

# ============================================
# TAB 2: SERIE STORICA
# ============================================
with tab2:
    st.subheader("📈 Analisi Serie Storica - Quota e Volatilità")
    
    # Selezione fondo
    selected_fund = st.sidebar.selectbox(
        "Seleziona il fondo",
        available_funds,
        key="fund_selector_tab2"
    )
    
    # Calcola metriche per il fondo selezionato
    with st.spinner(f"Calcolo metriche per {selected_fund}..."):
        df_metrics = calculate_volatility_metrics(df_quote, selected_fund)
    
    if df_metrics.empty:
        st.error(f"❌ Nessun dato disponibile per {selected_fund}")
        st.stop()
    
    # Filtro periodo
    min_date = df_metrics['Date'].min().to_pydatetime()
    max_date = df_metrics['Date'].max().to_pydatetime()
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Selezione Periodo")
    
    preset = st.sidebar.selectbox(
        "Periodo predefinito",
        ["Tutto", "Ultimi 3 mesi", "Ultimi 6 mesi", "Ultimo anno", "YTD", "Personalizzato"],
        key="period_selector"
    )
    
    today = max_date
    if preset == "Ultimi 3 mesi":
        start_date, end_date = today - timedelta(days=90), today
    elif preset == "Ultimi 6 mesi":
        start_date, end_date = today - timedelta(days=180), today
    elif preset == "Ultimo anno":
        start_date, end_date = today - timedelta(days=365), today
    elif preset == "YTD":
        start_date, end_date = datetime(year=today.year, month=1, day=1), today
    elif preset == "Tutto":
        start_date, end_date = min_date, max_date
    else:  # Personalizzato
        start_date = st.sidebar.date_input(
            "Data Inizio",
            value=min_date,
            min_value=min_date,
            max_value=max_date
        )
        end_date = st.sidebar.date_input(
            "Data Fine",
            value=max_date,
            min_value=min_date,
            max_value=max_date
        )
        start_date = datetime.combine(start_date, datetime.min.time())
        end_date = datetime.combine(end_date, datetime.min.time())
    
    # Filtra dati per periodo
    df_filtered = df_metrics[
        (df_metrics['Date'] >= start_date) & 
        (df_metrics['Date'] <= end_date)
    ].copy()
    
    if df_filtered.empty:
        st.warning("⚠️ Nessun dato disponibile per il periodo selezionato")
        st.stop()
    
    # Calcola statistiche
    stats = calculate_summary_stats(df_filtered)
    
    # Metriche principali
    st.markdown(f"### Metriche di Rischio — {selected_fund}")
    st.caption(f"Periodo: {format_date(start_date)} - {format_date(end_date)}")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        val = stats['vol_current']
        st.metric(
            "Volatilità 1Y Attuale",
            f"{val:.2f}%" if pd.notna(val) else "N/A"
        )
    
    with col2:
        val = stats['vol_3y']
        st.metric(
            "Volatilità 3Y",
            f"{val:.2f}%" if pd.notna(val) else "N/A"
        )
    
    with col3:
        val = stats['vol_5y']
        st.metric(
            "Volatilità 5Y",
            f"{val:.2f}%" if pd.notna(val) else "N/A"
        )
    
    with col4:
        val = stats['vol_max']
        st.metric(
            "Volatilità Massima Storica",
            f"{val:.2f}%" if pd.notna(val) else "N/A"
        )
    
    with col5:
        val = stats['dd_max']
        st.metric(
            "Max Drawdown Storico",
            f"{val:.2f}%" if pd.notna(val) else "N/A"
        )
    
    st.divider()
    
    # Grafico combinato Quota + Volatilità
    st.subheader("📊 Grafico Combinato: Quota e Volatilità 1Y Rolling")
    
    fig = make_subplots(
        rows=1, cols=1,
        specs=[[{"secondary_y": True}]]
    )
    
    # Quota (asse sinistro)
    fig.add_trace(
        go.Scatter(
            x=df_filtered['Date'],
            y=df_filtered['Quota'],
            name="Quota",
            line=dict(color='steelblue', width=2),
            hovertemplate='<b>Quota</b><br>Data: %{x}<br>Valore: %{y:.2f}<extra></extra>'
        ),
        secondary_y=False
    )
    
    # Volatilità (asse destro)
    fig.add_trace(
        go.Scatter(
            x=df_filtered['Date'],
            y=df_filtered['Volatilità_1Y'],
            name="Volatilità 1Y",
            line=dict(color='orange', width=2, dash='dash'),
            hovertemplate='<b>Volatilità 1Y</b><br>Data: %{x}<br>Valore: %{y:.2f}%<extra></extra>'
        ),
        secondary_y=True
    )
    
    # Layout
    fig.update_layout(
        title=f"{selected_fund} — Quota e Volatilità 1Y Rolling",
        hovermode='x unified',
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(title_text="Data")
    fig.update_yaxes(title_text="Quota", secondary_y=False)
    fig.update_yaxes(title_text="Volatilità Annualizzata (%)", secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Grafico Drawdown separato
    st.subheader("📉 Drawdown nel Tempo")
    
    fig_dd = go.Figure()
    
    fig_dd.add_trace(go.Scatter(
        x=df_filtered['Date'],
        y=df_filtered['Drawdown'],
        fill='tozeroy',
        name='Drawdown',
        line=dict(color='crimson', width=1),
        fillcolor='rgba(220, 53, 69, 0.3)',
        hovertemplate='<b>Drawdown</b><br>Data: %{x}<br>Valore: %{y:.2f}%<extra></extra>'
    ))
    
    fig_dd.update_layout(
        title=f"Drawdown - {selected_fund}",
        xaxis_title="Data",
        yaxis_title="Drawdown (%)",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig_dd, use_container_width=True)
    
    # Tabella dati dettagliati
    if st.checkbox("📋 Mostra dati dettagliati"):
        st.subheader("Dati Dettagliati")
        
        df_display = df_filtered[['Date', 'Quota', 'Volatilità_1Y', 'Drawdown']].copy()
        df_display['Date'] = df_display['Date'].dt.strftime('%d/%m/%Y')
        
        # Formatta numeri
        for col in ['Quota', 'Volatilità_1Y', 'Drawdown']:
            df_display[col] = df_display[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Export
        if st.button("📥 Esporta Serie Storica CSV"):
            csv = df_filtered[['Date', 'Quota', 'Volatilità_1Y', 'Drawdown']].to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"volatilità_{selected_fund}_{start_date:%Y%m%d}_{end_date:%Y%m%d}.csv",
                mime="text/csv"
            )

# ============================================
# FOOTER
# ============================================
st.divider()
st.markdown("""
<div style="text-align: center; color: gray; font-size: 0.8em;">
    Analisi Volatilità - Dashboard Portfolio Etica SGR
</div>
""", unsafe_allow_html=True)