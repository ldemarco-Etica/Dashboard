import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import logging

from config import APP_CONFIG, UI_CONFIG
from data_repository import data_repository
from models.portfolio import PortfolioAnalyzer, PerformanceAnalyzer
from utils import (
    ui_components, chart_factory, data_exporter, 
    format_date, create_info_box, check_page_access_auth0
)
from validators import ErrorHandler

# ============================================
# CONTROLLO ACCESSO RUOLI
# ============================================
check_page_access_auth0("Allocazioni")

logger = logging.getLogger(__name__)

st.set_page_config(layout=APP_CONFIG.layout)
st.title("📊 Allocazioni di Portafoglio")


def validate_data_availability():
    if 'portfolio_data' not in st.session_state or st.session_state['portfolio_data'].empty:
        st.error("❌ Portfolio data not loaded. Please return to Home page.")
        st.stop()
    
    return st.session_state['portfolio_data']


def create_allocation_charts(analyzer: PortfolioAnalyzer, fund_name: str, date: datetime):
    try:
        charts = {}

        with st.spinner("Creating allocation charts..."):

            # ==================== SETTORI ====================
            sector_data = analyzer.calculate_sector_allocation(fund_name, date)
            if not sector_data.empty:

                has_negative_values = (sector_data['PesoPort'] < 0).any()

                if has_negative_values:
                    st.warning(
                        f"⚠️ Allocazione settoriale con valori negativi per **{fund_name}** → grafico a barre."
                    )
                    fig = chart_factory.create_bar_chart(
                        sector_data.sort_values('PesoPort', ascending=False),
                        x_col='DescrizioneSector',
                        y_col='PesoPort',
                        title="Allocazione Settoriale"
                    )
                    fig.update_layout(showlegend=False)
                    charts['sector'] = fig

                else:
                    total_weight = sector_data['PesoPort'].sum()
                    values_col = 'PesoPort'
                    custom_hover_col = None

                    if total_weight > 100.1:
                        st.info(
                            f"ℹ️ Totale settori = **{total_weight:.1f}%** → normalizzazione."
                        )
                        sector_data['PesoPort_Normalized'] = (
                            sector_data['PesoPort'] / total_weight * 100
                        )
                        values_col = 'PesoPort_Normalized'
                        custom_hover_col = 'PesoPort'

                    fig = chart_factory.create_pie_chart(
                        sector_data,
                        values_col=values_col,
                        names_col='DescrizioneSector',
                        title="Allocazione Settoriale",
                        color_sequence=px.colors.qualitative.Set3,
                        custom_hover_col=custom_hover_col
                    )
                    fig.update_layout(showlegend=False)
                    charts['sector'] = fig

            # ==================== GEOGRAFICA ====================
            geo_data = analyzer.calculate_geographic_allocation(fund_name, date)
            if not geo_data.empty:
                geo_data_top = geo_data.head(10)

                fig = chart_factory.create_bar_chart(
                    geo_data_top,
                    'CodicePaeseEsposizione',
                    'PesoPort',
                    title="Allocazione Geografica (Top 10)",
                    orientation='h'
                )
                fig.update_layout(showlegend=False)
                charts['geography'] = fig

            # ==================== ASSET CLASS ====================
            asset_data = analyzer.calculate_asset_class_allocation(fund_name, date)
            if not asset_data.empty:
                fig = chart_factory.create_bar_chart(
                    asset_data,
                    'Description',
                    'PesoPort',
                    title="Allocazione per Asset Class"
                )
                fig.update_layout(showlegend=False)
                charts['asset_class'] = fig

            # ==================== VALUTE ====================
            currency_data = analyzer.calculate_currency_exposure(fund_name, date)
            if not currency_data.empty:
                fig = chart_factory.create_pie_chart(
                    currency_data,
                    'PesoPort',
                    'CodiceDivisaEsposizione',
                    title="Esposizione Valutaria",
                    color_sequence=px.colors.qualitative.Pastel
                )
                fig.update_layout(showlegend=False)
                charts['currency'] = fig

        return charts

    except Exception as e:
        logger.error(f"Error creating charts: {e}")
        ErrorHandler.handle_calculation_error(e, "allocation charts")
        return {}


def create_evolution_charts(performance_analyzer: PerformanceAnalyzer, fund_name: str, start_date, end_date):
    try:
        evolution_charts = {}

        with st.spinner("Creating evolution charts..."):

            sector_evolution = performance_analyzer.calculate_allocation_evolution(
                fund_name, 'sector', start_date, end_date
            )

            if not sector_evolution.empty:
                fig = chart_factory.create_line_chart(
                    sector_evolution,
                    'DataRiferimento',
                    'PesoPort',
                    color='DescrizioneSector',
                    title="Evoluzione Settoriale nel Tempo"
                )
                fig.update_layout(showlegend=False)
                evolution_charts['sector'] = fig

            asset_evolution = performance_analyzer.calculate_allocation_evolution(
                fund_name, 'asset_class', start_date, end_date
            )

            if not asset_evolution.empty:
                fig = px.area(
                    asset_evolution,
                    x='DataRiferimento',
                    y='PesoPort',
                    color='CodiceTipo',
                    title='Evoluzione Asset Class nel Tempo'
                )
                fig.update_layout(showlegend=False)
                evolution_charts['asset_class'] = fig

        return evolution_charts

    except Exception as e:
        logger.error(f"Error creating evolution charts: {e}")
        return {}


def main():
    try:
        portfolio_data = validate_data_availability()

        analyzer = PortfolioAnalyzer(portfolio_data)
        performance_analyzer = PerformanceAnalyzer(portfolio_data)

        st.sidebar.header("🔧 Filtri")

        selected_fund = ui_components.create_fund_selector(portfolio_data)

        if not selected_fund:
            st.warning("⚠️ Seleziona un fondo")
            return

        fund_data = data_repository.get_fund_data(portfolio_data, selected_fund)

        min_date_fund = fund_data['DataRiferimento'].min()
        max_date_fund = fund_data['DataRiferimento'].max()

        st.header(f"📈 {selected_fund}")

        create_info_box(
            "📅 Periodo Dati",
            f"Dal **{format_date(min_date_fund)}** al **{format_date(max_date_fund)}**",
            "info"
        )

        snapshot_date = st.date_input(
            "Seleziona data snapshot:",
            value=max_date_fund.date(),
            min_value=min_date_fund.date(),
            max_value=max_date_fund.date()
        )

        snapshot_datetime = datetime.combine(snapshot_date, datetime.min.time())

        snapshot_data = data_repository.get_fund_data_for_date(
            portfolio_data, selected_fund, snapshot_datetime
        )

        if snapshot_data.empty:
            st.warning("⚠️ Nessun dato per la data selezionata")
        else:
            charts = create_allocation_charts(analyzer, selected_fund, snapshot_datetime)

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

        if st.checkbox("📈 Mostra Evoluzione"):
            evolution_charts = create_evolution_charts(
                performance_analyzer,
                selected_fund,
                min_date_fund,
                max_date_fund
            )

            if 'sector' in evolution_charts:
                st.plotly_chart(evolution_charts['sector'], use_container_width=True)

            if 'asset_class' in evolution_charts:
                st.plotly_chart(evolution_charts['asset_class'], use_container_width=True)

    except Exception as e:
        logger.error(f"Main error: {e}")
        st.error("❌ Errore nella pagina Allocazioni")


if __name__ == "__main__":
    main()
