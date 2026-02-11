# applicazione/config.py
"""
Configurazione applicazione - ADATTATA PER PARQUET
"""

import os
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class DataPaths:
    """Data file paths configuration - MODIFICATO"""
    base_dir: Path = Path(os.getenv('DATA_DIRECTORY', 'data'))
    
    # ✅ NUOVO: Path file Parquet consolidati
    portfolio_parquet: Path = base_dir / 'consolidated' / 'portfolio_data.parquet'
    depositaria_parquet: Path = base_dir / 'consolidated' / 'depositaria_data.parquet'
    
    # ⚠️ DEPRECATI: Manteniamo per backward compatibility ma non usati
    portfolios: Path = base_dir / 'portfolios'  # Non più usato
    portfolios_depositaria: Path = base_dir / 'portfolios_depositaria'  # Non più usato
    
    # ✅ INVARIATI: File Excel rimangono come sono
    aum: Path = base_dir / 'AUM' / 'storico_aum.xlsm'
    tev: Path = base_dir / 'TEV' / 'Grafici TEV.xlsm'
    duration: Path = base_dir / 'duration' / 'storico_duration_fondi.xlsx'
    limiti_cda: Path = base_dir / 'limiti' / 'Limiti_CDA.xlsx'

@dataclass
class AppConfig:
    """Application configuration - INVARIATO"""
    page_title: str = "Dashboard di Analisi Portafoglio"
    page_icon: str = "📊"
    layout: str = "wide"
    cache_ttl: int = 3600  # 1 hour in seconds
    max_file_size_mb: int = 100

class PortfolioColumns:
    """Portfolio data column definitions - INVARIATO"""
    COLUMNS = [
        'DataRiferimento', 'CodicePortafoglio', 'Descrizione', 'CodiceTitolo',
        'DesTitolo', 'PesoPort', 'PesoBmk', 'CodiceTipo', 'DescrizioneSector',
        'ISIN', 'Sedol', 'CodiceBloomberg', 'CodicePaeseEsposizione',
        'CodiceDivisaEsposizione', 'TE', 'Rating', 'DataFormattata'
    ]
    
    REQUIRED_COLUMNS = [
        'DataRiferimento', 'Descrizione', 'PesoPort', 'CodiceTipo'
    ]

class DataMappings:
    """Data standardization mappings - INVARIATO"""
    
    FUND_MAPPINGS = {
        "Etica Impatto Clima": "Etica Transizione Climatica",
        "Etica ESG Conservative Allocation": "Etica Conservative Allocation",
        "Etica  Conservative Allocation": "Etica Conservative Allocation",
        "Etica ESG Dynamic Allocation": "Etica Dynamic Allocation",
        "Etica  Dynamic Allocation": "Etica Dynamic Allocation",
        "Etica ESG Global Equity": "Etica Global Equity",
        "Etica  Global Equity": "Etica Global Equity",
    }
    
    ASSET_CLASS_MAPPINGS = {
        "SE ": "AZ "
    }
    
    TEV_FUND_MAPPINGS = {
        "Etica Rendita Bilanciata": "RB", 
        "Etica Obbligazionario Breve Termine": "BT",
        "Etica Obbligazionario Misto": "OM", 
        "Etica Bilanciato": "Bil",
        "Etica Azionario": "AZ", 
        "Etica Transizione Climatica": "IC",
        "Etica Obiettivo Sociale": "OS", 
        "Etica Conservative Allocation": "Cons",
        "Etica Dynamic Allocation": "Dyn", 
        "Etica Global Equity": "Glob"
    }

class GeographicRegions:
    """Geographic region definitions for compliance - INVARIATO"""
    
    PAESI_UME = [
        "AT ", "BE ", "CY ", "HR ", "EE ", "FI ", "FR ", "DE ", "GR ", "IE ", "IT ",
        "LV ", "LT ", "LU ", "MT ", "NL ", "PT ", "SK ", "SI ", "ES ", "SNA"
    ]
    
    PAESI_OCSE = [
        "AU ", "AT ", "BE ", "CA ", "CL ", "CO ", "KR ", "CR ", "DK ", "EE ", "FI ",
        "FR ", "DE ", "JP ", "GR ", "IE ", "IS ", "IL ", "IT ", "LV ", "LT ", "LU ",
        "MX ", "NO ", "NZ ", "NL ", "PL ", "PT ", "GB ", "CZ ", "SK ", "SI ", "ES ",
        "US ", "SE ", "CH ", "TR ", "HU ", "SNA"
    ]
    
    PAESI_SVILUPPATI = [
        "AT ", "BE ", "BG ", "HR ", "CY ", "CZ ", "DK ", "EE ", "FI ", "FR ", "DE ",
        "GR ", "HU ", "IE ", "IT ", "LV ", "LT ", "LU ", "MT ", "NL ", "PL ", "PT ",
        "RO ", "SK ", "SI ", "ES ", "SE ", "US ", "CA ", "MX ", "JP "
    ]
    
    MERCATI_EMERGENTI = [
        'BR ', 'CN ', 'PL ', 'KR ', 'GR ', 'TW ', 'TR ', 'IN ', 'ZA ', 'ID ',
        'MX ', 'PE ', 'PH ', 'CL ', 'CO '
    ]

class CurrencyConfig:
    """Currency configuration - INVARIATO"""
    
    EUR_CURRENCIES = ['EUR', 'MUL']
    
    MAJOR_CURRENCIES = [
        'JPY', 'USD', 'GBP', 'SEK', 'CAD', 'CHF', 'DKK', 'NOK', 'AUD', 'SGD', 'KRW', 'HKD'
    ]
    
    CURRENCY_EXCEPTIONS = {
        '688 HK Equity': 'HKD',
        '992 HK Equity': 'HKD'
    }

class ComplianceConfig:
    """Compliance rules configuration - INVARIATO"""
    
    DERIVATI_AMMESSI = [
        "Short Euro-BTP", "Euro-BTP", "EURO-SCHATZ", "EURO-BOBL", "EURO-BUND",
        "EURO-BUXL 30Y", "Euro-OAT Future", "Euro-BONO Future", "MidTerm Euro-OAT Future"
    ]
    
    SETTORI_GOVERNATIVI = [
        'SOVEREIGN', 'Quasi & Foreign Government', 'Covered'
    ]
    
    RATING_INFERIORE_ADEGUATO = ['C', 'D', 'NR']

class LimitsConfig:
    """CDA Limits configuration - INVARIATO"""
    
    ASSET_CLASSES = {
        'EQUITY': ['AZ ', 'SE '],
        'BONDS': ['OB '],
        'OICR': ['FO '],
        'LIQUIDITY': ['LQ '],
        'FUTURES': ['FU '],
        'FORWARDS': ['FW ']
    }

class UIConfig:
    """UI configuration - INVARIATO"""
    
    COLORS = {
        'success': '#d4edda',
        'warning': '#fff3cd',
        'error': '#f8d7da',
        'info': '#d1ecf1'
    }
    
    CHART_COLORS = {
        'viridis': 'viridis',
        'plasma': 'plasma',
        'pastel': 'Pastel'
    }
    
    DATE_FORMAT = '%d/%m/%Y'
    FLOAT_FORMAT = '{:.2f}'

# Global configuration instances
DATA_PATHS = DataPaths()
APP_CONFIG = AppConfig()
PORTFOLIO_COLUMNS = PortfolioColumns()
DATA_MAPPINGS = DataMappings()
GEOGRAPHIC_REGIONS = GeographicRegions()
CURRENCY_CONFIG = CurrencyConfig()
COMPLIANCE_CONFIG = ComplianceConfig()
LIMITS_CONFIG = LimitsConfig()
UI_CONFIG = UIConfig()

def get_config() -> Dict[str, Any]:
    """Get all configuration as a dictionary"""
    return {
        'data_paths': DATA_PATHS,
        'app_config': APP_CONFIG,
        'portfolio_columns': PORTFOLIO_COLUMNS,
        'data_mappings': DATA_MAPPINGS,
        'geographic_regions': GEOGRAPHIC_REGIONS,
        'currency_config': CURRENCY_CONFIG,
        'compliance_config': COMPLIANCE_CONFIG,
        'limits_config': LIMITS_CONFIG,
        'ui_config': UI_CONFIG
    }
