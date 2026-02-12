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

                    fig = chart_factory.create_pie_chart(
                        sector_data.sort_values('PesoPort', ascending=False),
                        x_col='DescrizioneSector',
                        y_col='PesoPort',
                        title="Allocazione Settoriale"
                    )
                    fig.update_layout(showlegend=False)
                    charts['sector'] = fig
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
                evolution_charts['asset_class'] = px.area(
                    asset_evolution, x='DataRiferimento', y='PesoPort', 
                    color='CodiceTipo', title='Evoluzione Asset Class nel Tempo',
                    labels={'PesoPort': 'Peso (%)', 'DataRiferimento': 'Data'}
                )
                evolution_charts['asset_class'].update_layout(hovermode='x unified')
        
        return evolution_charts
        
    except Exception as e:
        logger.error(f"Error creating evolution charts: {e}")
        ErrorHandler.handle_calculation_error(e, "evolution charts")
        return {}

def get_available_sectors(fund_name: str) -> list:
    """Get available sectors for the fund"""
    try:
        portfolio_data = st.session_state['portfolio_data']
        fund_data = portfolio_data[portfolio_data['Descrizione'] == fund_name]
        
        if fund_data.empty:
            return []
        
        sectors = fund_data['DescrizioneSector'].dropna().unique()
        return sorted(sectors)
        
    except Exception as e:
        logger.error(f"Error getting available sectors: {e}")
        return []

def get_top_sectors(fund_name: str, n: int = 5) -> list:
    """Get top N sectors by weight"""
    try:
        portfolio_data = st.session_state['portfolio_data']
        fund_data = portfolio_data[portfolio_data['Descrizione'] == fund_name]
        
        if fund_data.empty:
            return []
        
        # Get latest data
        latest_date = fund_data['DataRiferimento'].max()
        latest_data = fund_data[fund_data['DataRiferimento'] == latest_date]
        
        sector_weights = latest_data.groupby('DescrizioneSector', observed=True)['PesoPort'].sum()
        top_sectors = sector_weights.nlargest(n).index.tolist()
        
        return top_sectors
        
    except Exception as e:
        logger.error(f"Error getting top sectors: {e}")
        return []

def display_allocation_metrics(analyzer: PortfolioAnalyzer, fund_name: str, date: datetime):
    """Display key allocation metrics"""
    try:
        with st.container():
            st.subheader("📊 Metriche di Allocazione")
            
            # Calculate key metrics
            equity_weight = analyzer.calculator.calculate_equity_weight(
                analyzer._get_fund_data_for_date(fund_name, date)
            )
            bond_weight = analyzer.calculator.calculate_bond_weight(
                analyzer._get_fund_data_for_date(fund_name, date)
            )
            oicr_weight = analyzer.calculator.calculate_oicr_weight(
                analyzer._get_fund_data_for_date(fund_name, date)
            )
            liquidity_weight = analyzer.calculator.calculate_liquidity_weight(
                analyzer._get_fund_data_for_date(fund_name, date)
            )
            
            # Display metrics
            metrics = {
                "Quota Azionaria": equity_weight,
                "Quota Obbligazionaria": bond_weight,
                "Quota OICR": oicr_weight,
                "Liquidità": liquidity_weight
            }
            
            ui_components.display_metrics_grid(
                {k: f"{v:.2f}%" for k, v in metrics.items()}
            )
            
            # Calculate and display concentration metrics
            performance_analyzer = PerformanceAnalyzer(st.session_state['portfolio_data'])
            concentration_metrics = performance_analyzer.calculate_concentration_metrics(fund_name, date)
            
            if concentration_metrics:
                st.subheader("📈 Metriche di Concentrazione")
                
                conc_metrics = {
                    "Posizioni Effettive": concentration_metrics.get('effective_positions', 0),
                    "Posizioni Totali": concentration_metrics.get('total_positions', 0),
                    "Top 5 Concentrazione": f"{concentration_metrics.get('top_5_concentration', 0):.1f}%",
                    "Posizione Maggiore": f"{concentration_metrics.get('largest_position', 0):.2f}%"
                }
                
                ui_components.display_metrics_grid(conc_metrics)
        
    except Exception as e:
        logger.error(f"Error displaying allocation metrics: {e}")
        ErrorHandler.handle_calculation_error(e, "allocation metrics")

def main():
    """Main function for the allocations page"""
    try:
        # Validate data availability
        portfolio_data = validate_data_availability()
        
        # Initialize analyzers
        analyzer = PortfolioAnalyzer(portfolio_data)
        performance_analyzer = PerformanceAnalyzer(portfolio_data)
        
        # Sidebar controls
        st.sidebar.header("🔧 Filtri Allocazioni")
        
        # Fund selection
        selected_fund = ui_components.create_fund_selector(
            portfolio_data, key="allocations_fund_selector"
        )
        
        if not selected_fund:
            st.warning("⚠️ Please select a fund to continue")
            return
        
        # Get fund data for date range
        fund_data = data_repository.get_fund_data(portfolio_data, selected_fund)
        
        if fund_data.empty:
            st.error(f"❌ No data found for fund: {selected_fund}")
            return
        
        min_date_fund = fund_data['DataRiferimento'].min()
        max_date_fund = fund_data['DataRiferimento'].max()
        
        # Display fund info
        st.header(f"📈 Analisi Allocazioni: {selected_fund}")
        
        create_info_box(
            "📅 Periodo Dati Disponibili",
            f"Dal **{format_date(min_date_fund)}** al **{format_date(max_date_fund)}**",
            "info"
        )
        
        # Date filters for evolution analysis
        start_date, end_date = ui_components.create_date_filter_sidebar(
            portfolio_data, selected_fund, key_prefix="allocations"
        )
        
        # Snapshot section
        st.subheader("📸 Snapshot Allocazioni")
        
        # Date selection for snapshot
        snapshot_date = st.date_input(
            "Seleziona data per lo snapshot:",
            value=max_date_fund.date(),
            min_value=min_date_fund.date(),
            max_value=max_date_fund.date(),
            help="Scegli una data specifica per vedere la composizione del portafoglio"
        )
        
        snapshot_datetime = datetime.combine(snapshot_date, datetime.min.time())
        
        # Get snapshot data
        snapshot_data = data_repository.get_fund_data_for_date(
            portfolio_data, selected_fund, snapshot_datetime
        )
        
        if snapshot_data.empty:
            st.warning(f"⚠️ Nessun dato disponibile per il {format_date(snapshot_datetime)}. "
                      "Prova con un'altra data.")
        else:
            # Create and display allocation charts
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
