

# applicazione/pages/Compliance.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
from utils import check_page_access_auth0
check_page_access_auth0("Limiti Regolamentari")



st.set_page_config(layout="wide")
st.title("⚖️ Monitoraggio Compliance Normativa")

# --- Caricamento Dati ---
df = st.session_state.get("portfolio_data", pd.DataFrame())
duration_data = st.session_state.get("duration_data", pd.DataFrame())

if df.empty:
    st.error("Caricamento dati fallito. Controlla i file nella cartella 'data/portfolios/'.")
    st.stop()

# --- Definizione Requirements e Logiche di Calcolo ---

def get_compliance_rules():
    """Definisce tutte le regole di compliance per ogni fondo"""
    
    # Liste paesi
    paesi_ume = ["AT ", "BE ", "CY ", "HR ", "EE ", "FI ", "FR ", "DE ", "GR ", "IE ", "IT ", "LV ", "LT ", "LU ", "MT ", "NL ", "PT ", "SK ", "SI ", "ES ", "SNA"]
    paesi_ocse = ["AU ", "AT ", "BE ", "CA ", "CL ", "CO ", "KR ", "CR ", "DK ", "EE ", "FI ", "FR ", "DE ", "JP ", "GR ", "IE ", "IS ", "IL ", "IT ",
                  "LV ", "LT ", "LU ", "MX ", "NO ", "NZ ", "NL ", "PL ", "PT ", "GB ", "CZ ", "SK ", "SI ", "ES ", "US ", "SE ", "CH ", "TR ", "HU ", "SNA"]
    
    paesi_sviluppati = [
    "AT ", "BE ", "BG ", "HR ", "CY ", "CZ ", "DK ", "EE ", "FI ", "FR ", "DE ", "GR ", "HU ", "IE ", "IT ",
    "LV ", "LT ", "LU ", "MT ", "NL ", "PL ", "PT ", "RO ", "SK ", "SI ", "ES ", "SE ", "US ", "CA ", "MX ", "JP "]
 

    
    rules = {
        "Etica Obbligazionario Breve Termine": [
            {"name": "Ammissibilità derivati", "type": "qualitative", "calc_func": lambda d: check_derivatives_admissibility(d)},
            {"name": "Concentrazione corporate", "type": "max", "limit": 10, "calc_func": lambda d: calc_corporate_concentration(d)},
            {"name": "Duration", "type": "range", "min_limit": 0, "max_limit": 2.5, "calc_func": lambda d, date: get_duration_value(d, date, "Etica Obbligazionario Breve Termine")},
            {"name": "Geografia obbligazioni", "type": "min", "limit": 70, "calc_func": lambda d: calc_bonds_geography_ume(d, paesi_ume)},
            {"name": "Esposizione Valutaria Lorda", "type": "max", "limit": 30, "calc_func": lambda d: calc_gross_currency_exposure(d)},
            {"name": "Esposizione Valutaria Netta", "type": "max", "limit": 10, "calc_func": lambda d: calc_net_currency_exposure(d)},
            {"name": "Quota OICR", "type": "max", "limit": 10, "calc_func": lambda d: calc_oicr_quota(d)},
            {"name": "Concentrazione emittente", "type": "special", "limit": 35, "calc_func": lambda d: check_issuer_concentration_ume(d, paesi_ume)}
        ],
        "Etica Obiettivo Sociale": [
            {"name": "Ammissibilità derivati", "type": "qualitative", "calc_func": lambda d: check_derivatives_admissibility(d)},
            {"name": "Limite depositi", "type": "max", "limit": 25, "calc_func": lambda d: calc_deposits_limit(d)},
            {"name": "Duration", "type": "range", "min_limit": 2, "max_limit": 9, "calc_func": lambda d, date: get_duration_value(d, date, "Etica Obiettivo Sociale")},
            {"name": "Quota azionaria", "type": "range", "min_limit": 10, "max_limit": 45, "calc_func": lambda d: calc_equity_quota(d)},
            {"name": "Geografia azioni", "type": "min", "limit": 70, "calc_func": lambda d: calc_equity_geography_developed(d, paesi_sviluppati)},
            {"name": "Geografia obbligazioni", "type": "min", "limit": 70, "calc_func": lambda d: calc_bonds_geography_ume(d, paesi_ume)},
            {"name": "Esposizione Valutaria Lorda", "type": "max", "limit": 100, "calc_func": lambda d: calc_gross_currency_exposure(d)},
            {"name": "Esposizione Valutaria Netta", "type": "max", "limit": 50, "calc_func": lambda d: calc_net_currency_exposure(d)},
            {"name": "Quota OICR", "type": "max", "limit": 10, "calc_func": lambda d: calc_oicr_quota(d)},
            {"name": "Concentrazione emittente", "type": "special", "limit": 35, "calc_func": lambda d: check_issuer_concentration_ocse(d, paesi_ocse)}
        ],
        "Etica Transizione Climatica": [
            {"name": "Ammissibilità derivati", "type": "qualitative", "calc_func": lambda d: check_derivatives_admissibility(d)},
            {"name": "Limite depositi", "type": "max", "limit": 40, "calc_func": lambda d: calc_deposits_limit(d)},
            {"name": "Duration", "type": "range", "min_limit": 2, "max_limit": 9, "calc_func": lambda d, date: get_duration_value(d, date, "Etica Transizione Climatica")},
            {"name": "Quota azionaria", "type": "max", "limit": 60, "calc_func": lambda d: calc_equity_quota(d)},
            {"name": "Esposizione Valutaria Lorda", "type": "max", "limit": 100, "calc_func": lambda d: calc_gross_currency_exposure(d)},
            {"name": "Esposizione Valutaria Netta", "type": "max", "limit": 50, "calc_func": lambda d: calc_net_currency_exposure(d)},
            {"name": "Quota OICR", "type": "max", "limit": 10, "calc_func": lambda d: calc_oicr_quota(d)},
            {"name": "Concentrazione emittente", "type": "special", "limit": 35, "calc_func": lambda d: check_issuer_concentration_ocse(d, paesi_ocse)}
        ],
        "Etica Azionario": [
            {"name": "Quota azionaria", "type": "min", "limit": 70, "calc_func": lambda d: calc_equity_quota(d)},
            {"name": "Geografia azioni", "type": "min", "limit": 70, "calc_func": lambda d: calc_equity_geography_developed(d, paesi_sviluppati)},
            {"name": "Limite depositi", "type": "max", "limit": 20, "calc_func": lambda d: calc_deposits_limit(d)},
            {"name": "Esposizione Valutaria Lorda", "type": "max", "limit": 100, "calc_func": lambda d: calc_gross_currency_exposure(d)},
            {"name": "Esposizione Valutaria Netta", "type": "max", "limit": 100, "calc_func": lambda d: calc_net_currency_exposure(d)},
            {"name": "Quota OICR", "type": "max", "limit": 10, "calc_func": lambda d: calc_oicr_quota(d)},
            {"name": "Concentrazione emittente", "type": "special", "limit": 35, "calc_func": lambda d: check_issuer_concentration_ocse(d, paesi_ocse)}
        ],
        "Etica Bilanciato": [
            {"name": "Ammissibilità derivati", "type": "qualitative", "calc_func": lambda d: check_derivatives_admissibility(d)},
            {"name": "Concentrazione corporate", "type": "max", "limit": 10, "calc_func": lambda d: calc_corporate_concentration(d)},
            {"name": "Limite depositi", "type": "max", "limit": 40, "calc_func": lambda d: calc_deposits_limit(d)},
            {"name": "Duration", "type": "range", "min_limit": 3, "max_limit": 9, "calc_func": lambda d, date: get_duration_value(d, date, "Etica Bilanciato")},
            {"name": "Geografia azioni", "type": "min", "limit": 50, "calc_func": lambda d: calc_equity_geography_developed(d, paesi_sviluppati)},
            {"name": "Geografia obbligazioni", "type": "min", "limit": 50, "calc_func": lambda d: calc_bonds_geography_ume(d, paesi_ume)},
            {"name": "Quota azionaria", "type": "max", "limit": 70, "calc_func": lambda d: calc_equity_quota(d)},
            {"name": "Esposizione Valutaria Lorda", "type": "max", "limit": 100, "calc_func": lambda d: calc_gross_currency_exposure(d)},
            {"name": "Esposizione Valutaria Netta", "type": "max", "limit": 100, "calc_func": lambda d: calc_net_currency_exposure(d)},
            {"name": "Quota OICR", "type": "max", "limit": 10, "calc_func": lambda d: calc_oicr_quota(d)},
            {"name": "Concentrazione emittente", "type": "special", "limit": 35, "calc_func": lambda d: check_issuer_concentration_ocse(d, paesi_ocse)}
        ],
        "Etica Rendita Bilanciata": [
            {"name": "Ammissibilità derivati", "type": "qualitative", "calc_func": lambda d: check_derivatives_admissibility(d)},
            {"name": "Geografia azioni", "type": "min", "limit": 50, "calc_func": lambda d: calc_equity_geography_developed(d, paesi_sviluppati)},
            {"name": "Geografia obbligazioni", "type": "range", "min_limit": 50, "max_limit": 70, "calc_func": lambda d: calc_bonds_geography_ume(d, paesi_ume)},
            {"name": "Concentrazione corporate", "type": "max", "limit": 10, "calc_func": lambda d: calc_corporate_concentration(d)},
            {"name": "Limite depositi", "type": "max", "limit": 40, "calc_func": lambda d: calc_deposits_limit(d)},
            {"name": "Duration", "type": "range", "min_limit": 2, "max_limit": 9, "calc_func": lambda d, date: get_duration_value(d, date, "Etica Rendita Bilanciata")},
            {"name": "Quota azionaria", "type": "max", "limit": 40, "calc_func": lambda d: calc_equity_quota(d)},
            {"name": "Esposizione Valutaria Lorda", "type": "max", "limit": 70, "calc_func": lambda d: calc_gross_currency_exposure(d)},
            {"name": "Esposizione Valutaria Netta", "type": "max", "limit": 40, "calc_func": lambda d: calc_net_currency_exposure(d)},
            {"name": "Quota OICR", "type": "max", "limit": 10, "calc_func": lambda d: calc_oicr_quota(d)},
            {"name": "Concentrazione emittente", "type": "special", "limit": 35, "calc_func": lambda d: check_issuer_concentration_ocse(d, paesi_ocse)}
        ],
        "Etica Obbligazionario Misto": [
            {"name": "Ammissibilità derivati", "type": "qualitative", "calc_func": lambda d: check_derivatives_admissibility(d)},
            {"name": "Quota monetaria+obbligazionaria (min)", "type": "min", "limit": 70, "calc_func": lambda d: calc_monetary_bond_quota(d)},
            {"name": "Concentrazione corporate", "type": "max", "limit": 10, "calc_func": lambda d: calc_corporate_concentration(d)},
            {"name": "Duration", "type": "range", "min_limit": 2, "max_limit": 8, "calc_func": lambda d, date: get_duration_value(d, date, "Etica Obbligazionario Misto")},
            {"name": "Quota azionaria", "type": "max", "limit": 20, "calc_func": lambda d: calc_equity_quota(d)},
            {"name": "Geografia azioni", "type": "min", "limit": 50, "calc_func": lambda d: calc_equity_geography_developed(d, paesi_sviluppati)},
            {"name": "Geografia obbligazioni", "type": "range", "min_limit": 50, "max_limit": 70, "calc_func": lambda d: calc_bonds_geography_ume(d, paesi_ume)},
            {"name": "Esposizione Valutaria Lorda", "type": "max", "limit": 50, "calc_func": lambda d: calc_gross_currency_exposure(d)},
            {"name": "Esposizione Valutaria Netta", "type": "max", "limit": 25, "calc_func": lambda d: calc_net_currency_exposure(d)},
            {"name": "Quota OICR", "type": "max", "limit": 10, "calc_func": lambda d: calc_oicr_quota(d)},
            {"name": "Concentrazione emittente", "type": "special", "limit": 35, "calc_func": lambda d: check_issuer_concentration_ume(d, paesi_ume)}
        ]
    }
    
    return rules

# --- Funzioni di Calcolo ---

def check_derivatives_admissibility(fund_data):
    """Verifica ammissibilità derivati"""
    futures = fund_data[fund_data['CodiceTipo'] == 'FU ']
    if futures.empty:
        return {"value": "N/A", "compliant": True, "details": "Nessun future in portafoglio"}
    
    allowed_keywords = ["Short Euro-BTP", "Euro-BTP", "EURO-SCHATZ", "EURO-BOBL", "EURO-BUND", "EURO-BUXL 30Y", "Euro-OAT Future", "Euro-BONO Future", "MidTerm Euro-OAT Future"]
    
    non_compliant = []
    for _, future in futures.iterrows():
        title = str(future['DesTitolo'])
        if not any(keyword in title for keyword in allowed_keywords):
            non_compliant.append(title)
    
    if non_compliant:
        return {"value": f"{len(non_compliant)} future non ammissibili", "compliant": False, "details": f"Future non ammissibili: {', '.join(non_compliant[:3])}{'...' if len(non_compliant) > 3 else ''}"}
    else:
        return {"value": f"{len(futures)} future ammissibili", "compliant": True, "details": "Tutti i future sono ammissibili"}

def calc_corporate_concentration(fund_data):
    """Calcola concentrazione corporate"""
    corporate_bonds = fund_data[
        (fund_data['CodiceTipo'] == 'OB ') & 
        (~fund_data['DescrizioneSector'].isin(['SOVEREIGN', 'Quasi & Foreign Government', 'Covered']))
    ]
    return corporate_bonds['PesoPort'].sum()

def get_duration_value(fund_data, selected_date, fund_name):
    """Ottiene valore duration dalla data più vicina"""
    if duration_data.empty:
        return {"value": "N/A", "compliant": None, "details": "Dati duration non disponibili"}
    
    fund_duration = duration_data[duration_data['Fondo'] == fund_name]
    if fund_duration.empty:
        return {"value": "N/A", "compliant": None, "details": f"Duration non disponibile per {fund_name}"}
    
    # Trova la data più vicina antecedente o uguale
    valid_dates = fund_duration[fund_duration['Data'] <= selected_date]
    if valid_dates.empty:
        return {"value": "N/A", "compliant": None, "details": "Nessun dato duration per la data selezionata"}
    
    closest_date = valid_dates['Data'].max()
    duration_value = valid_dates[valid_dates['Data'] == closest_date]['Duration Fondo'].iloc[0]
    
    return duration_value

def calc_equity_quota(fund_data):
    """Calcola quota azionaria"""
    equity_instruments = fund_data[fund_data['CodiceTipo'].isin(['AZ ', 'SE '])]
    return equity_instruments['PesoPort'].sum()

def calc_deposits_limit(fund_data):
    """Calcola limite depositi"""
    deposits = fund_data[fund_data['CodiceTipo'] == 'LQ ']
    return deposits['PesoPort'].sum()

def calc_bonds_geography_ume(fund_data, paesi_ume):
    """Calcola geografia obbligazioni UME"""
    bonds = fund_data[fund_data['CodiceTipo'] == 'OB ']
    if bonds.empty:
        return 0
    
    ume_bonds = bonds[bonds['CodicePaeseEsposizione'].isin(paesi_ume)]
    total_bonds_weight = bonds['PesoPort'].sum()
    
    if total_bonds_weight == 0:
        return 0
    
    return (ume_bonds['PesoPort'].sum() / total_bonds_weight) * 100

def calc_equity_geography_developed(fund_data, paesi_sviluppati):
    """Calcola geografia azioni paesi sviluppati """
    equity = fund_data[fund_data['CodiceTipo'].isin(['AZ ', 'SE '])]
    if equity.empty:
        return 0
    
    developed_equity = equity[equity['CodicePaeseEsposizione'].isin(paesi_sviluppati)]
    total_equity_weight = equity['PesoPort'].sum()
    
    if total_equity_weight == 0:
        return 0
    
    return (developed_equity['PesoPort'].sum() / total_equity_weight) * 100

def calc_gross_currency_exposure(fund_data):
    """Calcola esposizione valutaria lorda"""
    foreign_currency = fund_data[
        (fund_data['CodiceDivisaEsposizione'] != 'EUR') & 
        (fund_data['CodiceDivisaEsposizione'] != 'MUL') &
        (fund_data['CodiceTipo'] != 'FW ')
    ]
    return foreign_currency['PesoPort'].sum()

def calc_net_currency_exposure(fund_data):
    """Calcola esposizione valutaria netta"""
    # Identifica le valute estere (non EUR o MUL)
    all_currencies = fund_data['CodiceDivisaEsposizione'].unique()
    foreign_currencies = [c for c in all_currencies if c not in ['EUR', 'MUL']]
    
    net_exposure_total = 0
    
    for currency in foreign_currencies:
        # Calcola il peso della valuta estera (escludendo i forward)
        gross_mask = (
            (fund_data['CodiceDivisaEsposizione'] == currency) &
            (fund_data['CodiceTipo'] != 'FW ')
        )
        peso_valuta = fund_data[gross_mask]['PesoPort'].sum()
        
        # Se il peso è zero o negativo, salta (assumendo esposizioni positive)
        if peso_valuta < 0:
            continue
        
        # Calcola la somma dei pesi dei forward per questa valuta 
        fw_mask = (
            (fund_data['CodiceDivisaEsposizione'] == currency) &
            (fund_data['CodiceTipo'] == 'FW ')
        )
        sum_forwards = fund_data[fw_mask]['PesoPort'].sum()
        
        # Valori di copertura valutaria: moltiplica per -1
        valori_copertura = -sum_forwards
        
        # Percentuale di valuta coperta
        if peso_valuta != 0:
            percentuale_coperta = valori_copertura / peso_valuta
        else:
            percentuale_coperta = 0
        
        # Esposizione netta per questa valuta
        net_currency = (1 - percentuale_coperta) * peso_valuta
        
        # Aggiungi alla totale 
        net_exposure_total += net_currency
    
    return net_exposure_total

def calc_oicr_quota(fund_data):
    """Calcola quota OICR"""
    oicr = fund_data[fund_data['CodiceTipo'] == 'FO ']
    return oicr['PesoPort'].sum()

def calc_monetary_bond_quota(fund_data):
    """Calcola quota monetaria + obbligazionaria per Obbligazionario Misto"""
    sovereign_bonds = fund_data[
        (fund_data['CodiceTipo'] == 'OB ') & 
        (fund_data['DescrizioneSector'].isin(['SOVEREIGN', 'Quasi & Foreign Government', 'Covered']))
    ]
    deposits = fund_data[fund_data['CodiceTipo'] == 'LQ ']
    
    return sovereign_bonds['PesoPort'].sum() + deposits['PesoPort'].sum()

def check_issuer_concentration_ume(fund_data, paesi_ume):
    """Verifica concentrazione emittente UME secondo il regolamento"""
    # Filtra obbligazioni governative
    relevant_bonds = fund_data[
        (fund_data['CodiceTipo'] == 'OB ') &
        (fund_data['DescrizioneSector'].isin(['SOVEREIGN', 'Quasi & Foreign Government', 'Covered'])) &
        (fund_data['CodicePaeseEsposizione'].isin(paesi_ume))
    ]
    
    if relevant_bonds.empty:
        return {"value": "N/A", "compliant": True, "details": "Nessun titolo governativo rilevante"}
    
    # Raggruppa per paese
    country_exposure = relevant_bonds.groupby('CodicePaeseEsposizione', observed=True)['PesoPort'].sum()
    max_country_exposure = country_exposure.max() if not country_exposure.empty else 0
    max_country = country_exposure.idxmax() if not country_exposure.empty else 'N/A'
    
    # Se l'esposizione massima è <= 35%, compliant
    if max_country_exposure <= 35:
        return {
            "value": f"Max esposizione paese: {max_country_exposure:.1f}%",
            "compliant": True,
            "details": f"Maggiore esposizione: {max_country}"
        }
    
    # Se > 35%, verifica condizioni aggiuntive
    country_bonds = relevant_bonds[relevant_bonds['CodicePaeseEsposizione'] == max_country]
    num_emissions = len(country_bonds['DesTitolo'].unique())  # O usa ISIN se disponibile
    max_emission_weight = country_bonds.groupby('DesTitolo', observed=True)['PesoPort'].sum().max()
    
    compliant = num_emissions >= 6 and max_emission_weight <= 30
    details = (f"Maggiore esposizione: {max_country} ({max_country_exposure:.1f}%), "
               f"Emissioni: {num_emissions}, Max emissione: {max_emission_weight:.1f}%")
    
    return {
        "value": f"Max esposizione paese: {max_country_exposure:.1f}%",
        "compliant": compliant,
        "details": details
    }

def check_issuer_concentration_ocse(fund_data, paesi_ocse):
    """Verifica concentrazione emittente OCSE"""
    return check_issuer_concentration_ume(fund_data, paesi_ocse)  # Stessa logica ma con paesi OCSE

def evaluate_compliance(value, rule):
    """Valuta la compliance in base al tipo di regola"""
    if rule["type"] == "qualitative" or rule["type"] == "special":
        return value  # Già valutato nella funzione specifica
    
    compliant = True
    details = ""
    
    if rule["type"] == "min":
        compliant = value >= rule["limit"]
        details = f"Minimo richiesto: {rule['limit']}%"
    elif rule["type"] == "max":
        compliant = value <= rule["limit"]
        details = f"Massimo consentito: {rule['limit']}%"
    elif rule["type"] == "range":
        compliant = rule["min_limit"] <= value <= rule["max_limit"]
        details = f"Range richiesto: {rule['min_limit']}% - {rule['max_limit']}%"
    
    return {"value": f"{value:.2f}%", "compliant": compliant, "details": details}

def calculate_fund_compliance(fund_name, snapshot_data, selected_date, rules):
    """Calcola la compliance per un singolo fondo"""
    results = []
    
    for rule in rules:
        try:
            if rule["name"] == "Duration":
                calc_result = rule["calc_func"](snapshot_data, pd.to_datetime(selected_date))
            else:
                calc_result = rule["calc_func"](snapshot_data)
            
            if isinstance(calc_result, dict) and "compliant" in calc_result:
                result = calc_result
            else:
                result = evaluate_compliance(calc_result, rule)
            
            results.append({
                "Fondo": fund_name,
                "Requirement": rule["name"],
                "Valore": result["value"],
                "Compliant": result["compliant"],
                "Dettagli": result["details"]
            })
        except Exception as e:
            results.append({
                "Fondo": fund_name,
                "Requirement": rule["name"],
                "Valore": "Errore",
                "Compliant": None,
                "Dettagli": f"Errore nel calcolo: {str(e)}"
            })
    
    return results

# --- Setup iniziale ---
available_funds = sorted(df['Descrizione'].unique())
compliance_rules = get_compliance_rules()
compliant_funds = [fund for fund in available_funds if fund in compliance_rules.keys()]

if not compliant_funds:
    st.error("Nessun fondo con regole di compliance disponibili.")
    st.stop()

# Selezione data globale
min_date_global = df['DataRiferimento'].min()
max_date_global = df['DataRiferimento'].max()

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
    st.header("📊 Dashboard Compliance - Tutti i Fondi")
    st.info(f"Data di riferimento: **{selected_date.strftime('%d/%m/%Y')}**")
    
    # Calcola compliance per tutti i fondi
    all_results = []
    summary_data = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, fund_name in enumerate(compliant_funds):
        status_text.text(f"Elaborazione {fund_name}...")
        progress_bar.progress((i + 1) / len(compliant_funds))
        
        fund_data = df[df['Descrizione'] == fund_name]
        snapshot_data = fund_data[fund_data['DataRiferimento'] == pd.to_datetime(selected_date)]
        
        if not snapshot_data.empty:
            rules = compliance_rules[fund_name]
            fund_results = calculate_fund_compliance(fund_name, snapshot_data, selected_date, rules)
            all_results.extend(fund_results)
            
            # Summary per fondo
            total_rules = len(fund_results)
            compliant_rules = sum(1 for r in fund_results if r["Compliant"] == True)
            non_compliant_rules = sum(1 for r in fund_results if r["Compliant"] == False)
            na_rules = sum(1 for r in fund_results if r["Compliant"] == None)
            
            compliance_rate = (compliant_rules / total_rules * 100) if total_rules > 0 else 0
            
            summary_data.append({
                "Fondo": fund_name,
                "Totale Regole": total_rules,
                "Conformi": compliant_rules,
                "Non Conformi": non_compliant_rules,
                "N/A": na_rules,
                "% Compliance": compliance_rate,
                "Status": "🟢 OK" if non_compliant_rules == 0 else f"🔴 {non_compliant_rules} Violazioni"
            })
    
    progress_bar.empty()
    status_text.empty()
    
    # Summary Dashboard
    if summary_data:
        col1, col2, col3, col4 = st.columns(4)
        
        total_funds = len(summary_data)
        funds_ok = len([s for s in summary_data if s["Non Conformi"] == 0])
        funds_violations = total_funds - funds_ok
        avg_compliance = np.mean([s["% Compliance"] for s in summary_data])
        
        col1.metric("🏦 Totale Fondi", total_funds)
        col2.metric("✅ Fondi Conformi", funds_ok)
        col3.metric("⚠️ Fondi con Violazioni", funds_violations)
        col4.metric("📊 Compliance Media", f"{avg_compliance:.1f}%")
        
        # Tabella riassuntiva
        st.subheader("📋 Riepilogo per Fondo")
        df_summary = pd.DataFrame(summary_data)
        
        # Styling della tabella
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
            # Grafico compliance rate
            fig1 = px.bar(
                df_summary, 
                x="Fondo", 
                y="% Compliance",
                title="Tasso di Compliance per Fondo",
                color="% Compliance",
                color_continuous_scale="RdYlGn",
                range_color=[0, 100]
            )
            fig1.update_xaxes(tickangle=45)
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Grafico distribuzione violazioni
            violation_counts = df_summary['Non Conformi'].value_counts().sort_index()
            fig2 = px.pie(
                values=violation_counts.values,
                names=[f"{idx} violazioni" for idx in violation_counts.index],
                title="Distribuzione Violazioni per Fondo"
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Dettaglio violazioni
        violations_df = pd.DataFrame([r for r in all_results if r["Compliant"] is False])
        if not violations_df.empty:
            st.subheader("⚠️ Dettaglio Violazioni")
            st.error(f"Trovate {len(violations_df)} violazioni totali")
            
            # Raggruppa violazioni per tipo
            violation_summary = violations_df.groupby('Requirement').agg({
                'Fondo': 'count',
                'Valore': lambda x: list(x),
                'Dettagli': lambda x: list(x)
            }).reset_index()
            violation_summary.columns = ['Regola Violata', 'N° Fondi', 'Valori', 'Dettagli']
            violation_summary = violation_summary.sort_values('N° Fondi', ascending=False)
            
            st.dataframe(violation_summary, use_container_width=True)
            
            # Mostra dettaglio espandibile per ogni violazione
            for _, violation in violations_df.iterrows():
                with st.expander(f"🔴 {violation['Fondo']} - {violation['Requirement']}"):
                    st.write(f"**Valore:** {violation['Valore']}")
                    st.write(f"**Dettagli:** {violation['Dettagli']}")
        else:
            st.success("🎉 Nessuna violazione rilevata! Tutti i fondi sono conformi.")

# TAB 2: Analisi Dettagliata Fondo
with tab2:
    st.header("🔍 Analisi Dettagliata per Fondo")
    
    # Filtri specifici per la tab dettaglio
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_fund = st.selectbox("📈 Seleziona Fondo:", compliant_funds)
    
    with col2:
        # Opzione per sovrascrivere la data globale
        use_custom_date = st.checkbox("Usa data personalizzata per questo fondo")
    
    if use_custom_date:
        fund_data_temp = df[df['Descrizione'] == selected_fund]
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
    
    # Filtra dati per fondo selezionato
    fund_data = df[df['Descrizione'] == selected_fund].copy()
    
    if fund_data.empty:
        st.error(f"Nessun dato trovato per il fondo: {selected_fund}")
        st.stop()
    
    # Filtra per la data di analisi
    snapshot_data = fund_data[fund_data['DataRiferimento'] == pd.to_datetime(analysis_date)]
    
    if snapshot_data.empty:
        st.warning(f"Nessun dato disponibile per il {analysis_date.strftime('%d/%m/%Y')}. Prova un'altra data.")
        st.stop()
    
    st.info(f"Analisi per **{selected_fund}** alla data: **{analysis_date.strftime('%d/%m/%Y')}**")
    
    # Calcola compliance per il fondo selezionato
    rules = compliance_rules[selected_fund]
    results = calculate_fund_compliance(selected_fund, snapshot_data, analysis_date, rules)
    
# Calcola i contatori (usa == invece di is per gestire numpy.bool_)
    total_rules = len(results)
    compliant_rules = sum(1 for r in results if r["Compliant"] == True)
    non_compliant_rules = sum(1 for r in results if r["Compliant"] == False)
    na_rules = sum(1 for r in results if r["Compliant"] is None)
    
    # Dashboard riassuntiva
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Totale Regole", total_rules)
    col2.metric("✅ Conformi", compliant_rules, delta=None)
    col3.metric("❌ Non Conformi", non_compliant_rules, delta=None)
    
    # Rimuovi la colonna "Fondo" dai risultati per la visualizzazione dettagliata
    results_clean = [{k: v for k, v in r.items() if k != 'Fondo'} for r in results]
    
    # Tabella dettagliata
    st.subheader("📋 Dettaglio Compliance")
    
    df_results = pd.DataFrame(results_clean)
    
    # Colora le righe in base alla compliance
    def color_compliance(row):
        if row['Compliant'] is True:
            return ['background-color: #d4edda'] * len(row)
        elif row['Compliant'] is False:
            return ['background-color: #f8d7da'] * len(row)
        else:
            return ['background-color: #fff3cd'] * len(row)
    
    styled_df = df_results.style.apply(color_compliance, axis=1)
    st.dataframe(styled_df, use_container_width=True)
    
    # Grafico compliance per il fondo specifico
    if total_rules > 0:
        fig = go.Figure(data=[
            go.Bar(name='Conforme', x=['Compliance Status'], y=[compliant_rules], marker_color='green'),
            go.Bar(name='Non Conforme', x=['Compliance Status'], y=[non_compliant_rules], marker_color='red'),
            go.Bar(name='N/A', x=['Compliance Status'], y=[total_rules - compliant_rules - non_compliant_rules], marker_color='orange')
        ])
        
        fig.update_layout(
            title=f'Stato Compliance - {selected_fund}',
            barmode='stack',
            yaxis_title='Numero di Regole',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Dettagli per regole non conformi
    non_compliant = [r for r in results_clean if r["Compliant"] is False]
    if non_compliant:
        st.subheader("⚠️ Regole Non Conformi")
        for rule in non_compliant:
            st.error(f"**{rule['Requirement']}**: {rule['Valore']} - {rule['Dettagli']}")
    
    # Timeline compliance (se ci sono dati storici)
    st.subheader("📈 Storico Compliance")
    
    # Calcola compliance per tutte le date disponibili per questo fondo
    historical_dates = sorted(fund_data['DataRiferimento'].unique(), reverse=True)[:10]  # Ultime 10 date
    
    if len(historical_dates) > 1:
        historical_compliance = []
        
        for hist_date in historical_dates:
            hist_snapshot = fund_data[fund_data['DataRiferimento'] == hist_date]
            if not hist_snapshot.empty:
                hist_results = calculate_fund_compliance(selected_fund, hist_snapshot, hist_date, rules)
                hist_compliant = sum(1 for r in hist_results if r["Compliant"] is True)
                hist_total = len(hist_results)
                hist_rate = (hist_compliant / hist_total * 100) if hist_total > 0 else 0
                
                historical_compliance.append({
                    'Data': hist_date,
                    'Compliance Rate': hist_rate,
                    'Violazioni': sum(1 for r in hist_results if r["Compliant"] is False)
                })
        
        if historical_compliance:
            df_historical = pd.DataFrame(historical_compliance)
            df_historical = df_historical.sort_values('Data')
            
            fig_timeline = go.Figure()
            fig_timeline.add_trace(go.Scatter(
                x=df_historical['Data'],
                y=df_historical['Compliance Rate'],
                mode='lines+markers',
                name='Compliance Rate (%)',
                line=dict(color='green', width=3),
                marker=dict(size=8)
            ))
            
            # Aggiungi una linea di riferimento al 100%
            fig_timeline.add_hline(y=100, line_dash="dash", line_color="gray", 
                                 annotation_text="100% Compliance")
            
            fig_timeline.update_layout(
                title=f'Trend Compliance - {selected_fund}',
                xaxis_title='Data',
                yaxis_title='Compliance Rate (%)',
                height=400,
                yaxis_range=[0, 105]
            )
            
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("Dati storici insufficienti per mostrare il trend.")
    else:
        st.info("Una sola data disponibile - impossibile mostrare trend storico.")
    
    # Mostra i dati raw se richiesto
    if st.checkbox("🔍 Mostra dati portafoglio utilizzati per i calcoli"):
        st.subheader("Dati Portafoglio")
        display_cols = ['DesTitolo', 'CodiceTipo', 'DescrizioneSector', 'PesoPort', 'CodiceDivisaEsposizione', 'CodicePaeseEsposizione']
        available_cols = [col for col in display_cols if col in snapshot_data.columns]
        st.dataframe(snapshot_data[available_cols].sort_values('PesoPort', ascending=False), use_container_width=True)
    
    # Export funzionalità
    st.subheader("💾 Export Dati")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Scarica Report Compliance (CSV)"):
            csv = df_results.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"compliance_report_{selected_fund}_{analysis_date.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        # Prepara un summary report in formato testo
        if st.button("📄 Genera Report Testuale"):
            report = f"""
REPORT COMPLIANCE - {selected_fund}
Data: {analysis_date.strftime('%d/%m/%Y')}
{'='*50}

SUMMARY:
- Totale Regole: {total_rules}
- Regole Conformi: {compliant_rules}
- Regole Non Conformi: {non_compliant_rules}
- Tasso di Compliance: {(compliant_rules/total_rules*100):.1f}%

DETTAGLIO REGOLE:
"""
            for result in results_clean:
                status = "✅ OK" if result["Compliant"] else "❌ VIOLAZIONE" if result["Compliant"] is False else "⚠️ N/A"
                report += f"\n{status} {result['Requirement']}: {result['Valore']} - {result['Dettagli']}"
            
            if non_compliant:
                report += f"\n\nVIOLAZIONI RILEVATE: {len(non_compliant)}"
                for rule in non_compliant:
                    report += f"\n- {rule['Requirement']}: {rule['Valore']}"
            
            st.download_button(
                label="Download Report TXT",
                data=report,
                file_name=f"compliance_report_{selected_fund}_{analysis_date.strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )

# Footer con informazioni aggiuntive
st.markdown("---")
st.markdown("### ℹ️ Note Tecniche")
with st.expander("Dettagli implementazione e limitazioni"):
    st.markdown("""
    **Versione**: 2.0 con Dashboard Generale
    
    **Funzionalità principali**:
    - Dashboard generale con vista su tutti i fondi
    - Analisi dettagliata per singolo fondo  
    - Calcolo automatico compliance su regole normative
    - Visualizzazioni interattive e trend storici
    - Export dati in CSV e report testuali
    
    **Limitazioni**:  
    - Alcune regole qualitative richiedono validazione manuale
    
    **Regole implementate**:
    - Limiti geografici per azioni e obbligazioni
    - Controlli su derivati ammissibili
    - Vincoli di duration e concentrazione settoriale
    - Limiti di esposizione valutaria
    
    Per supporto tecnico o miglioramenti contattare il team di sviluppo.
    """)
