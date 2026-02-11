# applicazione/pages/Allocazioni_improved.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import logging

# Import improved modules
from config import APP_CONFIG, UI_CONFIG
from data_repository import data_repository
from models.portfolio import PortfolioAnalyzer, PerformanceAnalyzer
from utils import (
    ui_components, chart_factory, data_exporter, 
    format_date, format_number, create_info_box, check_page_access_auth0
)
from validators import ErrorHandler, safe_percentage

# ============================================
# CONTROLLO ACCESSO RUOLI
# ============================================
check_page_access_auth0("Allocazioni")

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(layout=APP_CONFIG.layout)
st.title("📊 Allocazioni di Portafoglio")

def validate_data_availability():
    """Validate that required data is available"""
    if 'portfolio_data' not in st.session_state or st.session_state['portfolio_data'].empty:
        st.error("❌ Portfolio data not loaded. Please return to Home page to initialize data.")
        st.stop()
    
    return st.session_state['portfolio_data']

def create_allocation_charts(analyzer: PortfolioAnalyzer, fund_name: str, date: datetime):
    """Create all allocation charts for a specific date"""
    try:
        charts = {}

        with st.spinner("Creating allocation charts..."):
            # Sector allocation
            sector_data = analyzer.calculate_sector_allocation(fund_name, date)
            if not sector_data.empty:

                # ==================== INIZIO NUOVA LOGICA CONDIZIONALE ====================
                # Controlla la presenza di valori negativi, che non sono compatibili con i grafici a torta
                has_negative_values = (sector_data['PesoPort'] < 0).any()

                if has_negative_values:
                    # CASO 1: CI SONO VALORI NEGATIVI -> Usa un grafico a barre
                    st.warning(
                        f"⚠️ **Attenzione:** L'allocazione settoriale per il fondo **{fund_name}** contiene valori negativi. "
                        "Un grafico a torta non può rappresentare questi dati, perciò viene mostrato un grafico a barre per una visualizzazione corretta."
                    )
                    charts['sector'] = chart_factory.create_bar_chart(
                        sector_data.sort_values('PesoPort', ascending=False),
                        x_col='DescrizioneSector',
                        y_col='PesoPort',
                        title="Allocazione Settoriale"
                    )
                else:
                    # CASO 2: NON CI SONO VALORI NEGATIVI -> Procedi con il grafico a torta
                    total_weight = sector_data['PesoPort'].sum()
                    values_col = 'PesoPort'
                    custom_hover_col = None

                    if total_weight > 100.1:
                        st.info(
                            f"ℹ️ Il fondo **{fund_name}** ha un'esposizione settoriale totale del **{total_weight:.1f}%**. "
                            "Il grafico a torta è stato normalizzato al 100% per la visualizzazione."
                        )
                        sector_data['PesoPort_Normalized'] = (sector_data['PesoPort'] / total_weight) * 100
                        values_col = 'PesoPort_Normalized'
                        custom_hover_col = 'PesoPort'

                    charts['sector'] = chart_factory.create_pie_chart(
                        sector_data,
                        values_col=values_col,
                        names_col='DescrizioneSector',
                        title="Allocazione Settoriale",
                        color_sequence=px.colors.qualitative.Set3,
                        custom_hover_col=custom_hover_col
                    )
                    
                    # ✨ MODIFICA: Nascondi la legenda per evitare sovrapposizioni
                    charts['sector'].update_layout(showlegend=False)
                # ===================== FINE NUOVA LOGICA =====================
            
            # Geographic allocation
            geo_data = analyzer.calculate_geographic_allocation(fund_name, date)
            if not geo_data.empty:
                # Limit to top 10 countries for readability
                geo_data_top = geo_data.head(10)
                charts['geography'] = chart_factory.create_bar_chart(
                    geo_data_top, 'CodicePaeseEsposizione', 'PesoPort',
                    title="Allocazione Geografica (Top 10)",
                    orientation='h'
                )
            
            # Asset class allocation
            asset_data = analyzer.calculate_asset_class_allocation(fund_name, date)
            if not asset_data.empty:
                charts['asset_class'] = chart_factory.create_bar_chart(
                    asset_data, 'Description', 'PesoPort',
                    title="Allocazione per Asset Class"
                )
            
            # Currency exposure
            currency_data = analyzer.calculate_currency_exposure(fund_name, date)
            if not currency_data.empty:
                charts['currency'] = chart_factory.create_pie_chart(
                    currency_data, 'PesoPort', 'CodiceDivisaEsposizione',
                    title="Esposizione Valutaria",
                    color_sequence=px.colors.qualitative.Pastel
                )
                
                # ✨ MODIFICA: Nascondi la legenda per evitare sovrapposizioni
                charts['currency'].update_layout(showlegend=False)
        
        return charts
        
    except Exception as e:
        logger.error(f"Error creating allocation charts: {e}")
        ErrorHandler.handle_calculation_error(e, "allocation charts")
        return {}

def create_evolution_charts(performance_analyzer: PerformanceAnalyzer, 
                          fund_name: str, start_date: datetime, end_date: datetime):
    """Create evolution charts over time"""
    try:
        evolution_charts = {}
        
        with st.spinner("Creating evolution analysis..."):
            # Sector evolution
            selected_sectors = st.multiselect(
                "Seleziona settori per l'analisi evolutiva:",
                options=get_available_sectors(fund_name),
                default=get_top_sectors(fund_name, 5),
                help="Massimo 8 settori per leggibilità del grafico"
            )
            
            if selected_sectors:
                sector_evolution = performance_analyzer.calculate_allocation_evolution(
                    fund_name, 'sector', start_date, end_date
                )
                
                if not sector_evolution.empty:
                    # Filter by selected sectors
                    sector_filtered = sector_evolution[
                        sector_evolution['DescrizioneSector'].isin(selected_sectors)
                    ]
                    
                    if not sector_filtered.empty:
                        evolution_charts['sector'] = chart_factory.create_line_chart(
                            sector_filtered, 'DataRiferimento', 'PesoPort',
                            color='DescrizioneSector',
                            title="Evoluzione Settoriale nel Tempo",
                        )
                        
                        # Color by sector
                        evolution_charts['sector'].update_traces(
                            mode='lines',
                            hovertemplate='<b>%{customdata[0]}</b><br>Date: %{x}<br>Weight: %{y:.2f}%<extra></extra>'
                        )
            
            # Asset class evolution
            asset_evolution = performance_analyzer.calculate_allocation_evolution(
                fund_name, 'asset_class', start_date, end_date
            )
            
            if not asset_evolution.empty:
                evolution_charts['asset_class'] = chart_factory.create_line_chart(
                    asset_evolution, 'DataRiferimento', 'PesoPort',
                    color='Description',
                    title="Evoluzione Asset Class nel Tempo"
                )
        
        return evolution_charts
        
    except Exception as e:
        logger.error(f"Error creating evolution charts: {e}")
        ErrorHandler.handle_calculation_error(e, "evolution charts")
        return {}

def get_available_sectors(fund_name: str) -> List[str]:
    """Get list of available sectors for a fund"""
    try:
        portfolio_data = st.session_state['portfolio_data']
        fund_data = portfolio_data[portfolio_data['DesFondo'] == fund_name]
        
        if fund_data.empty:
            return []
        
        sectors = fund_data['DescrizioneSector'].dropna().unique().tolist()
        return sorted(sectors)
        
    except Exception as e:
        logger.error(f"Error getting available sectors: {e}")
        return []

def get_top_sectors(fund_name: str, n: int = 5) -> List[str]:
    """Get top N sectors by weight for a fund"""
    try:
        portfolio_data = st.session_state['portfolio_data']
        
        # Get most recent date
        latest_date = portfolio_data['DataRiferimento'].max()
        
        fund_data = portfolio_data[
            (portfolio_data['DesFondo'] == fund_name) & 
            (portfolio_data['DataRiferimento'] == latest_date)
        ]
        
        if fund_data.empty:
            return []
        
        # Aggregate by sector
        sector_weights = fund_data.groupby('DescrizioneSector')['PesoPort'].sum()
        top_sectors = sector_weights.nlargest(n).index.tolist()
        
        return top_sectors
        
    except Exception as e:
        logger.error(f"Error getting top sectors: {e}")
        return []

def display_allocation_metrics(analyzer: PortfolioAnalyzer, fund_name: str, date: datetime):
    """Display key allocation metrics"""
    try:
        st.subheader("📊 Metriche di Allocazione")
        
        # Get allocation data
        sector_data = analyzer.calculate_sector_allocation(fund_name, date)
        geo_data = analyzer.calculate_geographic_allocation(fund_name, date)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            num_sectors = len(sector_data) if not sector_data.empty else 0
            st.metric("Settori", num_sectors)
        
        with col2:
            num_countries = len(geo_data) if not geo_data.empty else 0
            st.metric("Paesi", num_countries)
        
        with col3:
            if not sector_data.empty:
                top_sector_weight = sector_data['PesoPort'].max()
                st.metric("Top Settore", f"{top_sector_weight:.1f}%")
            else:
                st.metric("Top Settore", "N/A")
        
        with col4:
            if not geo_data.empty:
                top_country_weight = geo_data['PesoPort'].max()
                st.metric("Top Paese", f"{top_country_weight:.1f}%")
            else:
                st.metric("Top Paese", "N/A")
        
    except Exception as e:
        logger.error(f"Error displaying allocation metrics: {e}")
        st.warning("⚠️ Could not display allocation metrics")

def main():
    """Main function for Allocazioni page"""
    try:
        # Validate data availability
        portfolio_data = validate_data_availability()
        
        # Initialize analyzers
        analyzer = PortfolioAnalyzer(portfolio_data)
        performance_analyzer = PerformanceAnalyzer(portfolio_data)
        
        # Sidebar filters
        st.sidebar.header("🎛️ Filtri")
        
        # Fund selection
        selected_fund = ui_components.create_fund_selector(
            portfolio_data, 
            label="📈 Seleziona Fondo:",
            key="allocations_fund"
        )
        
        if not selected_fund:
            st.warning("⚠️ Please select a fund to continue")
            return
        
        # Date range selection
        start_date, end_date = ui_components.create_date_filter_sidebar(
            portfolio_data,
            fund_name=selected_fund,
            key_prefix="allocations"
        )
        
        # Snapshot date selection
        st.sidebar.subheader("📸 Snapshot Date")
        
        available_dates = data_repository.get_available_dates(portfolio_data, selected_fund)
        
        if not available_dates:
            st.error("❌ No data available for the selected fund")
            return
        
        snapshot_date = st.sidebar.selectbox(
            "Seleziona data per lo snapshot:",
            options=available_dates,
            index=len(available_dates) - 1,  # Default to most recent
            format_func=lambda x: format_date(x),
            key="snapshot_date"
        )
        
        snapshot_datetime = datetime.combine(snapshot_date, datetime.min.time())
        
        # Main content
        st.subheader(f"📸 Snapshot Allocazioni - {format_date(snapshot_datetime)}")
        
        # Get snapshot data
        snapshot_data = data_repository.get_fund_data(
            portfolio_data, selected_fund, snapshot_datetime, snapshot_datetime
        )
        
        if snapshot_data.empty:
            st.warning(f"⚠️ No data available for {selected_fund} on {format_date(snapshot_datetime)}")
        else:
            # Create allocation charts
            charts = create_allocation_charts(analyzer, selected_fund, snapshot_datetime)
            
            if charts:
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'sector' in charts:
                        st.plotly_chart(charts['sector'], use_container_width=True)
                    if 'asset_class' in charts:
                        st.plotly_chart(charts['asset_class'], use_container_width=True)
                
                with col2:
                    if 'geography' in charts:
                        st.plotly_chart(charts['geography'], use_container_width=True)
                    if 'currency' in charts:
                        st.plotly_chart(charts['currency'], use_container_width=True)
            
            # Display allocation metrics
            display_allocation_metrics(analyzer, selected_fund, snapshot_datetime)
        
        # Evolution analysis section
        st.subheader("📈 Analisi dell'Evoluzione Temporale")
        
        if st.checkbox("Mostra analisi evolutiva", value=True):
            evolution_charts = create_evolution_charts(
                performance_analyzer, selected_fund, start_date, end_date
            )
            
            if evolution_charts:
                if 'sector' in evolution_charts:
                    st.plotly_chart(evolution_charts['sector'], use_container_width=True)
                
                if 'asset_class' in evolution_charts:
                    st.plotly_chart(evolution_charts['asset_class'], use_container_width=True)
        
        # Detailed data section
        if st.checkbox("📋 Mostra dati dettagliati dello snapshot"):
            if not snapshot_data.empty:
                st.subheader("📊 Dati Dettagliati")
                
                # Select columns to display
                display_columns = [
                    'DesTitolo', 'DescrizioneSector', 'CodiceTipo', 'PesoPort', 
                    'Rating', 'CodicePaeseEsposizione', 'CodiceDivisaEsposizione'
                ]
                
                available_columns = [col for col in display_columns if col in snapshot_data.columns]
                
                # Format the data for display
                display_data = snapshot_data[available_columns].copy()
                display_data = display_data.sort_values('PesoPort', ascending=False)
                
                # Format percentage columns
                if 'PesoPort' in display_data.columns:
                    display_data['PesoPort'] = display_data['PesoPort'].apply(
                        lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A"
                    )
                
                st.dataframe(display_data, use_container_width=True)
                
                # Export functionality
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    if st.button("📥 Export Snapshot"):
                        filename = f"allocations_snapshot_{selected_fund}_{format_date(snapshot_datetime, '%Y%m%d')}.xlsx"
                        data_exporter.create_download_button(
                            snapshot_data[available_columns],
                            filename,
                            "📥 Download Excel"
                        )
                
                with col2:
                    if st.button("📊 Export Charts Data"):
                        # Prepare charts data for export
                        charts_data = {}
                        
                        if not snapshot_data.empty:
                            sector_data = analyzer.calculate_sector_allocation(selected_fund, snapshot_datetime)
                            if not sector_data.empty:
                                charts_data['Sector_Allocation'] = sector_data
                            
                            geo_data = analyzer.calculate_geographic_allocation(selected_fund, snapshot_datetime)
                            if not geo_data.empty:
                                charts_data['Geographic_Allocation'] = geo_data
                            
                            asset_data = analyzer.calculate_asset_class_allocation(selected_fund, snapshot_datetime)
                            if not asset_data.empty:
                                charts_data['Asset_Class_Allocation'] = asset_data
                        
                        if charts_data:
                            filename = f"allocation_charts_{selected_fund}_{format_date(snapshot_datetime, '%Y%m%d')}.xlsx"
                            data_exporter.create_download_button(
                                charts_data,
                                filename,
                                "📊 Download Charts Data"
                            )
        
        # Performance summary
        if st.checkbox("📈 Mostra riepilogo performance allocazioni"):
            st.subheader("🎯 Riepilogo Performance")
            
            try:
                # Calculate allocation stability metrics over the selected period
                fund_period_data = data_repository.get_fund_data(
                    portfolio_data, selected_fund, start_date, end_date
                )
                
                if not fund_period_data.empty:
                    # Calculate allocation consistency metrics
                    dates = sorted(fund_period_data['DataRiferimento'].unique())
                    
                    if len(dates) >= 2:
                        first_date = dates[0]
                        last_date = dates[-1]
                        
                        first_allocation = analyzer.calculate_sector_allocation(selected_fund, first_date)
                        last_allocation = analyzer.calculate_sector_allocation(selected_fund, last_date)
                        
                        if not first_allocation.empty and not last_allocation.empty:
                            # Show allocation changes
                            allocation_changes = pd.merge(
                                first_allocation[['DescrizioneSector', 'PesoPort']],
                                last_allocation[['DescrizioneSector', 'PesoPort']],
                                on='DescrizioneSector',
                                suffixes=('_Start', '_End'),
                                how='outer'
                            ).fillna(0)
                            
                            allocation_changes['Change'] = (
                                allocation_changes['PesoPort_End'] - allocation_changes['PesoPort_Start']
                            )
                            
                            allocation_changes = allocation_changes.sort_values('Change', key=abs, ascending=False)
                            
                            st.write(f"**Principali cambiamenti allocazione** ({format_date(first_date)} → {format_date(last_date)}):")
                            
                            # Show top 5 changes
                            top_changes = allocation_changes.head(5)
                            
                            for _, row in top_changes.iterrows():
                                sector = row['DescrizioneSector']
                                change = row['Change']
                                start_weight = row['PesoPort_Start']
                                end_weight = row['PesoPort_End']
                                
                                change_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                                
                                st.write(f"{change_emoji} **{sector}**: {start_weight:.1f}% → {end_weight:.1f}% "
                                        f"({change:+.1f} pp)")
            
            except Exception as e:
                logger.error(f"Error calculating performance summary: {e}")
                st.warning("⚠️ Could not calculate performance summary")
        
    except Exception as e:
        logger.error(f"Error in main allocations function: {e}")
        ErrorHandler.handle_calculation_error(e, "allocations analysis")
        
        st.error("❌ An error occurred in the allocations analysis")
        
        with st.expander("🔍 Error Details"):
            st.error(f"Error details: {e}")

if __name__ == "__main__":
    main()
