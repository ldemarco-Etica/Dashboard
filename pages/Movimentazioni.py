# applicazione/pages/Monitoraggio_Movimenti.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta

# Importa i moduli della tua applicazione
from config import APP_CONFIG
from data_repository import data_repository
from utils import ui_components, format_date, create_info_box, check_page_access_auth0
from validators import ErrorHandler

# ============================================
# 🔐 CONTROLLO ACCESSO
# ============================================
check_page_access_auth0("Movimentazioni")

def analyze_full_period_movements(
    portfolio_data: pd.DataFrame,
    fund_name: str,
    start_date: datetime,
    end_date: datetime,
    threshold: float,
    exclude_cash: bool = True,   # ✅ nuovo parametro
):
    """
    Analizza l'intero periodo per identificare tutte le movimentazioni, incluse quelle infra-periodo.
    L'opzione `exclude_cash` consente di includere o escludere i titoli con DescrizioneSector = 'CASH'.
    """
    # 1. Filtra i dati per il fondo e il periodo di interesse
    fund_period_data = portfolio_data[
        (portfolio_data['Descrizione'] == fund_name)
        & (portfolio_data['DataRiferimento'] >= start_date)
        & (portfolio_data['DataRiferimento'] <= end_date)
    ].copy()

    if fund_period_data.empty:
        return None

    detail_cols = ['CodiceTipo', 'DescrizioneSector', 'CodiceBloomberg']

    actual_start_date = fund_period_data['DataRiferimento'].min()
    actual_end_date = fund_period_data['DataRiferimento'].max()

    df_start = fund_period_data[fund_period_data['DataRiferimento'] == actual_start_date]
    df_end = fund_period_data[fund_period_data['DataRiferimento'] == actual_end_date]

    all_titles_in_period = fund_period_data['DesTitolo'].unique()
    titles_at_start = df_start['DesTitolo'].unique()
    titles_at_end = df_end['DesTitolo'].unique()

    entries, exits, round_trips = [], [], []

    for title in all_titles_in_period:
        title_history = fund_period_data[fund_period_data['DesTitolo'] == title].sort_values('DataRiferimento')

        is_at_start = title in titles_at_start
        is_at_end = title in titles_at_end

        first_date = title_history['DataRiferimento'].min()
        last_date = title_history['DataRiferimento'].max()

        last_record_details = title_history.iloc[-1][detail_cols].to_dict()
        first_record_details = title_history.iloc[0][detail_cols].to_dict()

        sector_first = first_record_details.get('DescrizioneSector', '')
        sector_last = last_record_details.get('DescrizioneSector', '')

        # ✅ Usa il flag exclude_cash per decidere se filtrare CASH
        if not is_at_start and is_at_end:
            if not (exclude_cash and sector_last == "CASH"):
                final_weight = title_history.iloc[-1]['PesoPort']
                entry_data = {"DesTitolo": title, "Data Entrata": first_date, "Peso Finale": final_weight}
                entry_data.update(last_record_details)
                entries.append(entry_data)

        elif is_at_start and not is_at_end:
            if not (exclude_cash and sector_first == "CASH"):
                initial_weight = title_history.iloc[0]['PesoPort']
                exit_data = {"DesTitolo": title, "Data Uscita": last_date, "Peso Iniziale": initial_weight}
                exit_data.update(first_record_details)
                exits.append(exit_data)

        elif not is_at_start and not is_at_end:
            if not (exclude_cash and sector_last == "CASH"):
                peak_weight = title_history['PesoPort'].max()
                round_trip_data = {
                    "DesTitolo": title,
                    "Data Entrata": first_date,
                    "Data Uscita": last_date,
                    "Peso Massimo Raggiunto": peak_weight,
                }
                round_trip_data.update(last_record_details)
                round_trips.append(round_trip_data)

    stayed_titles = [t for t in all_titles_in_period if t in titles_at_start and t in titles_at_end]

    cols_to_merge = ['DesTitolo', 'PesoPort'] + detail_cols

    merged_df = pd.merge(
        df_start[df_start['DesTitolo'].isin(stayed_titles)][cols_to_merge],
        df_end[df_end['DesTitolo'].isin(stayed_titles)][cols_to_merge],
        on='DesTitolo',
        suffixes=('_start', '_end'),
    )

    merged_df['Variazione'] = merged_df['PesoPort_end'] - merged_df['PesoPort_start']

    # ✅ Escludi CASH solo se richiesto
    significant_movements = merged_df[
        (abs(merged_df['Variazione']) >= threshold)
        & ((merged_df['DescrizioneSector_end'] != "CASH") if exclude_cash else True)
    ].copy()

    for col in detail_cols:
        significant_movements[col] = significant_movements[f"{col}_end"]
        significant_movements = significant_movements.drop(columns=[f"{col}_start", f"{col}_end"])

    # Analisi intra-periodo
    intra_period = []
    intra_history = {}

    for title in stayed_titles:
        title_history = fund_period_data[fund_period_data['DesTitolo'] == title].sort_values('DataRiferimento')
        last_record_details = title_history.iloc[-1][detail_cols].to_dict()

        if not (exclude_cash and last_record_details.get('DescrizioneSector', '') == "CASH"):
            initial_weight = title_history.iloc[0]['PesoPort']
            final_weight = title_history.iloc[-1]['PesoPort']
            net_variation = final_weight - initial_weight
            min_weight = title_history['PesoPort'].min()
            max_weight = title_history['PesoPort'].max()
            max_intra_variation = max_weight - min_weight
            avg_weight = title_history['PesoPort'].mean()

            daily_changes = title_history['PesoPort'].diff().dropna()
            sign_changes = (daily_changes * daily_changes.shift(1) < 0).sum()
            num_oscillations = sign_changes + 1 if len(daily_changes) > 0 else 0

            intra_data = {
                "DesTitolo": title,
                "Peso Iniziale": initial_weight,
                "Peso Finale": final_weight,
                "Variazione Netta (%)": net_variation,
                "Peso Minimo": min_weight,
                "Peso Massimo": max_weight,
                "Variazione Max Intra (%)": max_intra_variation,
                "Peso Medio": avg_weight,
                "Num. Oscillazioni": num_oscillations,
            }
            intra_data.update(last_record_details)
            intra_period.append(intra_data)
            intra_history[title] = title_history[['DataRiferimento', 'PesoPort']].copy()

    intra_period_df = pd.DataFrame(intra_period)
    significant_intra = intra_period_df[intra_period_df['Variazione Max Intra (%)'] >= threshold].copy()

    return {
        "entries": pd.DataFrame(entries),
        "exits": pd.DataFrame(exits),
        "round_trips": pd.DataFrame(round_trips),
        "significant": significant_movements,
        "significant_intra": significant_intra,
        "intra_history": intra_history,
        "actual_start_date": actual_start_date,
        "actual_end_date": actual_end_date,
    }


def main():
    st.set_page_config(layout=APP_CONFIG.layout)
    st.title("📊 Monitoraggio Movimenti di Portafoglio")
    st.markdown("Analizza le variazioni nella composizione dei fondi per identificare entrate, uscite, movimenti infra-periodo e variazioni rilevanti.")

    if 'portfolio_data' not in st.session_state or st.session_state['portfolio_data'].empty:
        st.error("❌ Dati di portafoglio non trovati. Torna alla Home per caricarli.")
        st.stop()

    portfolio_data = st.session_state['portfolio_data']

    st.sidebar.header("🔧 Filtri di Analisi")

    selected_fund = ui_components.create_fund_selector(
        portfolio_data, label="1. Seleziona un Fondo:", key="movements_fund_selector"
    )

    if not selected_fund:
        st.info("Seleziona un fondo per iniziare.")
        st.stop()

    min_date, max_date = data_repository.get_date_range(portfolio_data, selected_fund)

    st.sidebar.markdown("### 2. Seleziona il Periodo di Confronto")
    date_start = st.sidebar.date_input(
        "Data Iniziale",
        value=max_date - timedelta(days=30),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY",
    )
    date_end = st.sidebar.date_input(
        "Data Finale",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY",
    )

    if date_start >= date_end:
        st.sidebar.error("La data iniziale deve essere precedente a quella finale.")
        st.stop()

    st.sidebar.markdown("### 3. Imposta la Soglia di Rilevanza")
    threshold = st.sidebar.slider(
        "Variazione minima del peso (%)",
        min_value=0.05,
        max_value=3.0,
        value=0.2,
        step=0.05,
        help="Imposta la variazione minima per considerare una movimentazione 'significativa'.",
    )

    # ✅ Nuova opzione: escludi CASH
    st.sidebar.markdown("### 4. Opzioni di Visualizzazione")
    exclude_cash = st.sidebar.checkbox(
        "Escludi titoli con settore 'CASH'",
        value=True,
        help="Deseleziona per includere anche i titoli classificati come 'CASH'.",
    )

    dt_start = datetime.combine(date_start, datetime.min.time())
    dt_end = datetime.combine(date_end, datetime.min.time())

    analysis_results = analyze_full_period_movements(
        portfolio_data, selected_fund, dt_start, dt_end, threshold, exclude_cash
    )

    if not analysis_results:
        st.warning("Non sono disponibili dati sufficienti per il periodo selezionato.")
        st.stop()

    st.header(f"Analisi per il fondo: {selected_fund} - {date_end.strftime('%d/%m/%Y')}")

    entries = analysis_results["entries"]
    exits = analysis_results["exits"]
    round_trips = analysis_results["round_trips"]
    significant_intra = analysis_results.get("significant_intra", pd.DataFrame())
    intra_history = analysis_results.get("intra_history", {})
    
    
    #mostriamo i titoli entrati, usciti e le altre variazioni del periodo
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Titoli Entrati", len(entries))
    col2.metric("Titoli Usciti", len(exits))
    col3.metric("Movimenti Infra-Periodo", len(round_trips))
    col4.metric("Variazioni Intra Significative", len(significant_intra))
  

    display_cols_base = ['DesTitolo', 'CodiceTipo', 'DescrizioneSector', 'CodiceBloomberg']

    tab1, tab2, tab3, tab4 = st.tabs(
        ["➕ Entrate", "➖ Uscite", "🔄 Infra-Periodo", "📈 Variazioni Intra-Periodo"]
    )

    with tab1:
        st.subheader("Titoli Entrati nel Portafoglio")
        if entries.empty:
            st.success("Nessun nuovo titolo nel periodo.")
        else:
            display_cols = ['Data Entrata', 'Peso Finale'] + display_cols_base
            entries_display = entries.copy()
            
            # Ordina SENZA convertire in stringa
            entries_display = entries_display.sort_values('Data Entrata', ascending=False)
            entries_display = entries_display.reset_index(drop=True)
            
            # Formatta solo il peso, LASCIA la data come datetime
            entries_display['Peso Finale'] = entries_display['Peso Finale'].map('{:.2f}%'.format)
            
            # Configura la colonna data per la visualizzazione italiana
            st.dataframe(
                entries_display[display_cols], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Data Entrata": st.column_config.DateColumn(
                        "Data Entrata",
                        format="DD/MM/YYYY",
                    )
                }
            )
    
    with tab2:
        st.subheader("Titoli Usciti dal Portafoglio")
        if exits.empty:
            st.success("Nessun titolo è uscito dal portafoglio.")
        else:
            display_cols = ['Data Uscita', 'Peso Iniziale'] + display_cols_base
            exits_display = exits.copy()
            # Ordina PRIMA della conversione in stringa
            exits_display = exits_display.sort_values('Data Uscita', ascending=False)
            # Reset dell'indice per evitare riordinamenti
            exits_display = exits_display.reset_index(drop=True)
            exits_display['Data Uscita'] = exits_display['Data Uscita'].dt.strftime('%d/%m/%Y')
            exits_display['Peso Iniziale'] = exits_display['Peso Iniziale'].map('{:.2f}%'.format)
            st.dataframe(exits_display[display_cols], use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("Movimenti Infra-Periodo (Entrati e Usciti)")
        st.markdown("_Titoli acquistati e venduti completamente all'interno del periodo selezionato._")
        if round_trips.empty:
            st.success("Nessun movimento infra-periodo rilevato.")
        else:
            display_cols = ['Data Entrata', 'Data Uscita', 'Peso Massimo Raggiunto'] + display_cols_base
            round_trips_display = round_trips.copy()
            # Reset dell'indice per evitare riordinamenti
            round_trips_display = round_trips_display.reset_index(drop=True)
            round_trips_display['Data Entrata'] = round_trips_display['Data Entrata'].dt.strftime('%d/%m/%Y')
            round_trips_display['Data Uscita'] = round_trips_display['Data Uscita'].dt.strftime('%d/%m/%Y')
            round_trips_display['Peso Massimo Raggiunto'] = round_trips_display['Peso Massimo Raggiunto'].map('{:.2f}%'.format)
            st.dataframe(round_trips_display[display_cols], use_container_width=True, hide_index=True)
            
    with tab4:
        st.subheader("Variazioni Intra-Periodo per Titoli Stabili")
        st.caption(f"(Variazione massima intra-periodo >= {threshold:.1f} %, escludendo CASH)")
        st.markdown("_Analisi dettagliata delle fluttuazioni all'interno del periodo per titoli rimasti stabili._")
        if significant_intra.empty:
            st.success("Nessuna variazione intra-periodo significativa.")
        else:
            # Ordina per Variazione Max Intra discendente
            significant_intra_sorted = significant_intra.sort_values('Variazione Max Intra (%)', ascending=False)
            significant_intra_sorted = significant_intra_sorted.reset_index(drop=True)
            
            # Rinomina colonne
            intra_display = significant_intra_sorted.rename(columns={
                'Peso Iniziale': 'Peso Iniz.',
                'Peso Finale': 'Peso Fin.',
                'Variazione Netta (%)': 'Var. Netta (%)',
                'Peso Minimo': 'Peso Min.',
                'Peso Massimo': 'Peso Max.',
                'Variazione Max Intra (%)': 'Var. Max Intra (%)',
                'Peso Medio': 'Peso Medio',
                'Num. Oscillazioni': 'Oscillazioni'
            })
            
            # Formatta colonne numeriche
            numeric_cols = ['Peso Iniz.', 'Peso Fin.', 'Var. Netta (%)', 'Peso Min.', 'Peso Max.', 'Var. Max Intra (%)', 'Peso Medio']
            for col in numeric_cols:
                if 'Peso' in col:
                    intra_display[col] = intra_display[col].map(lambda x: '{:.2f}%'.format(x))
                elif 'Var.' in col:
                    intra_display[col] = intra_display[col].map(lambda x: '{:.2f} %'.format(x))
            
            # Colonna formattata per Var. Netta con emoji colore
            def format_net_var(val):
                num_val = float(val.replace(' %', ''))
                if num_val > 0:
                    return f"🟢 +{val}"
                elif num_val < 0:
                    return f"🔴 {val}"
                else:
                    return f"⚪ {val}"
            
            intra_display['Var. Netta Formattata'] = intra_display['Var. Netta (%)'].map(format_net_var)
            
            # Colonne display prioritarie (senza Peso Medio Bar e Oscillazioni, con Var. Max Intra)
            display_cols = ['Var. Netta Formattata', 'Peso Iniz.', 'Peso Fin.', 'Peso Min.', 'Peso Max.', 'Var. Max Intra (%)'] + display_cols_base
            
            # Dataframe semplificato
            st.dataframe(
                intra_display[display_cols], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Var. Netta Formattata": st.column_config.TextColumn(
                        "Var. Netta",
                        help="Variazione netta inizio-fine (con colore per direzione)"
                    )
                }
            )
            
            # Espander per Grafici Sparkline (top 6 per performance, senza marker)
            with st.expander("📊 Grafici Trend Intra-Periodo (Top 6 Titoli)", expanded=False):
                top_6_titles = significant_intra_sorted.head(6)['DesTitolo'].tolist()
                num_cols = min(3, len(top_6_titles))  # Max 3 colonne per leggibilità
                for i in range(0, len(top_6_titles), num_cols):
                    cols = st.columns(num_cols)
                    for j, title in enumerate(top_6_titles[i:i+num_cols]):
                        with cols[j]:
                            if title in intra_history:
                                history = intra_history[title]
                                fig, ax = plt.subplots(figsize=(5, 3))
                                ax.plot(history['DataRiferimento'], history['PesoPort'] , linewidth=1.5, color='blue')
                                ax.set_title(title[:30], fontsize=10)
                                ax.set_ylabel('Peso (%)')
                                ax.tick_params(axis='x', rotation=45, labelsize=8)
                                ax.grid(True, alpha=0.3)
                                plt.tight_layout()
                                st.pyplot(fig)
                                plt.close(fig)
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("Si è verificato un errore inaspettato durante l'analisi.")
        ErrorHandler.handle_calculation_error(e, "Pagina Monitoraggio Movimenti")
        
        # ✅ Aggiungi qui il CSS per tab più grandi
    st.markdown("""
    <style>
    /* Targetta il paragrafo dentro il contenitore Markdown delle tab */
    div[data-testid="stMarkdownContainer"] p {
        font-size: 18px !important;  /* Aumenta la dimensione del font come desiderato */
        margin-bottom: 0px;  /* Mantiene il margin basso se necessario */
        word-break: break-word;  /* Opzionale: gestisce il wrap del testo lungo */
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <style>
        /* Espandi le tab per riempire la larghezza orizzontale */
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.5rem;  /* Spazio tra le tab, regola se vuoi più/meno distanza */
        }
        div[data-testid="stTabs"] [data-baseweb="tab"] {
            flex: 1;  /* Ogni tab cresce uniformemente per riempire lo spazio */
            min-width: 0;  /* Permette il wrap se il testo è troppo lungo */
        }
        /* Opzionale: stile per i pulsanti attivi/selezionati */
        div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
            background-color: #f0f2f6;  /* Colore di sfondo per la tab attiva, adatta al tuo tema */
        }
    </style>
    """, unsafe_allow_html=True)
