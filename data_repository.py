# applicazione/data_repository.py
"""
Data Repository con supporto Parquet per Portfolio e Depositaria
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path

from config import (
    DATA_PATHS, PORTFOLIO_COLUMNS, DATA_MAPPINGS, 
    APP_CONFIG, GEOGRAPHIC_REGIONS, LIMITS_CONFIG
)
from validators import (
    DataValidator, ErrorHandler, ValidationError, 
    validate_and_clean_data, safe_divide
)

logger = logging.getLogger(__name__)

# ===== CACHED FUNCTIONS =====

@st.cache_data(ttl=APP_CONFIG.cache_ttl)
def _load_portfolio_data_cached() -> pd.DataFrame:
    """Carica dati portfolio da file Parquet"""
    try:
        parquet_file = DATA_PATHS.portfolio_parquet
        
        if not parquet_file.exists():
            st.error(f"❌ File Parquet portfolio non trovato: {parquet_file}")
            st.info("💡 Esegui prima: python consolidate_csv_to_parquet.py")
            return pd.DataFrame()
        
        with st.spinner('📂 Caricamento dati portfolio da Parquet...'):
            df = pd.read_parquet(parquet_file)
        
        if df.empty:
            st.error("❌ File Parquet portfolio vuoto")
            return pd.DataFrame()
        
        # Standardizzazioni
        df = _standardize_fund_names(df)
        df = _standardize_asset_classes(df)
        
        # Validazione
        validator = DataValidator()
        is_valid, validation_report = validator.validate_portfolio_data(df)
        
        if not is_valid:
            st.error("❌ Validazione dati portfolio fallita:")
            for error in validation_report.get('errors', [])[:3]:
                st.error(f"• {error}")
            st.warning("⚠️ Procedendo con dati disponibili...")
        else:
            st.success(f"✅ Caricati {len(df):,} record portfolio")
            
            if validation_report.get('stats'):
                stats = validation_report['stats']
                st.info(f"📊 {stats.get('unique_funds', 0)} fondi | "
                       f"Range: {stats.get('date_range', ('N/A', 'N/A'))[0].strftime('%d/%m/%Y')} - "
                       f"{stats.get('date_range', ('N/A', 'N/A'))[1].strftime('%d/%m/%Y')}")
        
        return df
        
    except Exception as e:
        logger.error(f"Errore caricamento Parquet portfolio: {e}")
        st.error(f"❌ Errore caricamento portfolio: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=APP_CONFIG.cache_ttl)
def _load_depositaria_data_cached() -> pd.DataFrame:
    """Carica dati depositaria da file Parquet"""
    try:
        parquet_file = DATA_PATHS.depositaria_parquet
        
        if not parquet_file.exists():
            st.warning(f"⚠️ File Parquet depositaria non trovato: {parquet_file}")
            st.info("💡 Per analisi Turnover, esegui: python consolidate_depositaria_to_parquet.py")
            return pd.DataFrame()
        
        with st.spinner('📂 Caricamento dati depositaria da Parquet...'):
            df = pd.read_parquet(parquet_file)
        
        if df.empty:
            st.warning("⚠️ File Parquet depositaria vuoto")
            return pd.DataFrame()
        
        # Validazione base
        required_cols = ['DataRiferimento', 'NomeFondo', 'ISIN']
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            st.error(f"❌ Colonne mancanti nel Parquet depositaria: {missing}")
            return pd.DataFrame()
        
        st.success(f"✅ Caricati {len(df):,} record depositaria")
        
        # Stats
        if 'NomeFondo' in df.columns and 'DataRiferimento' in df.columns:
            n_fondi = df['NomeFondo'].nunique()
            date_min = df['DataRiferimento'].min()
            date_max = df['DataRiferimento'].max()
            st.info(f"📊 {n_fondi} fondi | Range: {date_min:%d/%m/%Y} - {date_max:%d/%m/%Y}")
        
        return df
        
    except Exception as e:
        logger.error(f"Errore caricamento Parquet depositaria: {e}")
        st.warning(f"⚠️ Dati depositaria non disponibili: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=APP_CONFIG.cache_ttl)
def _load_aum_data_cached() -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """Cached function to load AUM data"""
    try:
        if not DATA_PATHS.aum.exists():
            st.error(f"❌ AUM file non trovato: {DATA_PATHS.aum}")
            return pd.DataFrame(), {}
        
        xls = pd.ExcelFile(DATA_PATHS.aum)
        
        if not xls.sheet_names:
            st.error("❌ File AUM senza sheet leggibili")
            return pd.DataFrame(), {}
        
        # Carica foglio principale
        df_tot = pd.DataFrame()
        try:
            df_tot = pd.read_excel(DATA_PATHS.aum, sheet_name=0, skiprows=1)
            df_tot = df_tot.rename(columns={df_tot.columns[0]: "Data"})
            df_tot["Data"] = pd.to_datetime(df_tot["Data"])
            
            for col in df_tot.columns[1:]:
                df_tot[col] = pd.to_numeric(
                    df_tot[col].astype(str).str.replace(",", "").str.replace(" ", ""),
                    errors="coerce"
                )
            
            logger.info(f"Caricato foglio AUM principale: {len(df_tot)} record")
            
        except Exception as e:
            logger.error(f"Errore caricamento foglio AUM principale: {e}")
            st.warning(f"⚠️ Impossibile caricare foglio AUM principale: {e}")
        
        # Carica fogli fondi
        fund_sheets = xls.sheet_names[1:] if len(xls.sheet_names) > 1 else []
        dfs_fondi = {}
        failed_sheets = []
        
        for sheet in fund_sheets:
            try:
                df = pd.read_excel(DATA_PATHS.aum, sheet_name=sheet, skiprows=1)
                
                rename_map = {
                    df.columns[0]: "Data",
                    df.columns[2]: "Performance",
                    df.columns[3]: "AUM",
                    df.columns[4]: "Effetto mercato",
                    df.columns[5]: "Var AUM",
                    df.columns[6]: "Flussi netti",
                }
                
                df = df.rename(columns=rename_map)
                df["Data"] = pd.to_datetime(df["Data"])
                
                numeric_cols = ["Performance", "AUM", "Effetto mercato", "Var AUM", "Flussi netti"]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(
                            df[col].astype(str).str.replace(",", "").str.replace(" ", ""),
                            errors="coerce"
                        )
                    else:
                        df[col] = pd.NA
                
                dfs_fondi[sheet] = df
                
            except Exception as e:
                failed_sheets.append(f"{sheet}: {str(e)}")
                logger.warning(f"Fallito caricamento foglio AUM '{sheet}': {e}")
        
        if failed_sheets:
            st.warning(f"⚠️ Impossibile caricare {len(failed_sheets)} fogli AUM")
        
        if dfs_fondi:
            st.success(f"✅ Caricati dati AUM: foglio principale + {len(dfs_fondi)} fondi")
        
        return df_tot, dfs_fondi
        
    except Exception as e:
        logger.error(f"Errore critico caricamento AUM: {e}")
        st.error(f"❌ Errore critico caricamento AUM: {e}")
        return pd.DataFrame(), {}


@st.cache_data(ttl=APP_CONFIG.cache_ttl)
def _load_tev_data_cached() -> pd.DataFrame:
    """Cached function to load TEV data"""
    try:
        if not DATA_PATHS.tev.exists():
            st.error(f"❌ File TEV non trovato: {DATA_PATHS.tev}")
            return pd.DataFrame()
        
        df = pd.read_excel(DATA_PATHS.tev, sheet_name="Giornaliero")
        df.columns = df.columns.map(str)
        df = df.rename(columns={df.columns[0]: "Data"})
        df["Data"] = pd.to_datetime(df["Data"])
        
        dfs = []
        missing_funds = []
        
        for fund_name, abbr in DATA_MAPPINGS.TEV_FUND_MAPPINGS.items():
            col_val = fund_name
            limite = f"Limite {abbr}"
            limite_magg = f"Limite maggiorato {abbr}"
            
            if all(col in df.columns for col in [col_val, limite, limite_magg]):
                temp = df[["Data", col_val, limite, limite_magg]].copy()
                temp = temp.rename(columns={
                    col_val: "TEV", 
                    limite: "Limite", 
                    limite_magg: "Limite maggiorato"
                })
                
                for col in ["TEV", "Limite", "Limite maggiorato"]:
                    temp[col] = pd.to_numeric(temp[col], errors="coerce")
                
                temp["Fondo"] = fund_name
                dfs.append(temp)
            else:
                missing_funds.append(fund_name)
        
        if missing_funds:
            st.warning(f"⚠️ Dati TEV mancanti per: {', '.join(missing_funds[:3])}" + 
                      ("..." if len(missing_funds) > 3 else ""))
        
        if not dfs:
            st.error("❌ Nessun dato TEV caricato.")
            return pd.DataFrame()
        
        result_df = pd.concat(dfs, ignore_index=True)
        st.success(f"✅ Caricati dati TEV per {len(dfs)} fondi")
        
        return result_df
        
    except Exception as e:
        logger.error(f"Errore critico caricamento TEV: {e}")
        st.error(f"❌ Errore critico caricamento TEV: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=APP_CONFIG.cache_ttl)
def _load_fasce_data_cached() -> pd.DataFrame:
    """Cached function to load TEV fasce data"""
    try:
        if not DATA_PATHS.tev.exists():
            st.error(f"❌ File TEV non trovato: {DATA_PATHS.tev}")
            return pd.DataFrame()
        
        df_fasce = pd.read_excel(DATA_PATHS.tev, sheet_name="Fasce")
        return df_fasce.set_index("FONDI ETICA SGR")
        
    except Exception as e:
        logger.error(f"Errore critico caricamento fasce: {e}")
        st.error(f"❌ Errore critico caricamento fasce: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=APP_CONFIG.cache_ttl)
def _load_duration_data_cached() -> pd.DataFrame:
    """Cached function to load duration data"""
    try:
        if not DATA_PATHS.duration.exists():
            st.error(f"❌ File duration non trovato: {DATA_PATHS.duration}")
            return pd.DataFrame()
        
        df = pd.read_excel(DATA_PATHS.duration)
        df["Data"] = pd.to_datetime(df["Data"])
        
        required_cols = ["Data", "Fondo"]
        duration_cols = [col for col in df.columns if "Duration" in col]
        
        if not duration_cols:
            st.error("❌ Nessuna colonna duration trovata")
            return pd.DataFrame()
        
        st.success(f"✅ Caricati dati duration: {len(df)} record")
        return df
        
    except Exception as e:
        logger.error(f"Errore critico caricamento duration: {e}")
        st.error(f"❌ Errore critico caricamento duration: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=APP_CONFIG.cache_ttl)
def _load_limiti_cda_cached() -> pd.DataFrame:
    """Cached function to load CDA limits data"""
    try:
        if not DATA_PATHS.limiti_cda.exists():
            st.error(f"❌ File limiti CDA non trovato: {DATA_PATHS.limiti_cda}")
            return pd.DataFrame()
        
        df = pd.read_excel(DATA_PATHS.limiti_cda)
        st.success("✅ Caricati limiti CDA")
        return df
        
    except Exception as e:
        logger.error(f"Errore critico caricamento limiti CDA: {e}")
        st.error(f"❌ Errore critico caricamento limiti CDA: {e}")
        return pd.DataFrame()


# ===== HELPER FUNCTIONS =====

def _standardize_fund_names(df: pd.DataFrame) -> pd.DataFrame:
    """Apply fund name standardization"""
    if 'Descrizione' in df.columns:
        df['Descrizione'] = df['Descrizione'].astype(str).replace(DATA_MAPPINGS.FUND_MAPPINGS).astype('category')
    return df

def _standardize_asset_classes(df: pd.DataFrame) -> pd.DataFrame:
    """Apply asset class standardization"""
    if 'CodiceTipo' in df.columns:
        df['CodiceTipo'] = df['CodiceTipo'].astype(str).replace(DATA_MAPPINGS.ASSET_CLASS_MAPPINGS).astype('category')
    return df


# ===== MAIN REPOSITORY CLASS =====

class DataRepository:
    """Centralized data access layer with caching and error handling"""
    
    def __init__(self):
        self._cache = {}
        self.validator = DataValidator()
    
    def load_portfolio_data(self) -> pd.DataFrame:
        """Load portfolio data using cached function"""
        return _load_portfolio_data_cached()
    
    def load_depositaria_data(self) -> pd.DataFrame:
        """Load depositaria data using cached function"""
        return _load_depositaria_data_cached()
    
    def load_aum_data(self) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """Load AUM data using cached function"""
        return _load_aum_data_cached()
    
    def load_tev_data(self) -> pd.DataFrame:
        """Load TEV data using cached function"""
        return _load_tev_data_cached()
    
    def load_fasce_data(self) -> pd.DataFrame:
        """Load fasce data using cached function"""
        return _load_fasce_data_cached()
    
    def load_duration_data(self) -> pd.DataFrame:
        """Load duration data using cached function"""
        return _load_duration_data_cached()
    
    def load_limiti_cda(self) -> pd.DataFrame:
        """Load CDA limits data using cached function"""
        return _load_limiti_cda_cached()
    
    def get_fund_data(self, 
                      portfolio_data: pd.DataFrame, 
                      fund_name: str, 
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Get portfolio data for a specific fund with optional date filtering"""
        try:
            fund_name = self.validator.sanitize_fund_name(fund_name)
            fund_data = portfolio_data[portfolio_data['Descrizione'] == fund_name].copy()
            
            if fund_data.empty:
                logger.warning(f"No data found for fund: {fund_name}")
                return fund_data
            
            if start_date:
                fund_data = fund_data[fund_data['DataRiferimento'] >= start_date]
            
            if end_date:
                fund_data = fund_data[fund_data['DataRiferimento'] <= end_date]
            
            return fund_data
            
        except ValidationError as e:
            st.error(f"Validation error: {e}")
            return pd.DataFrame()
        except Exception as e:
            ErrorHandler.handle_calculation_error(e, "fund data retrieval")
            return pd.DataFrame()
    
    def get_available_funds(self, portfolio_data: pd.DataFrame) -> List[str]:
        """Get list of available funds in portfolio data"""
        if portfolio_data.empty or 'Descrizione' not in portfolio_data.columns:
            return []
        
        return sorted(portfolio_data['Descrizione'].unique())
    
    def get_date_range(self, portfolio_data: pd.DataFrame, fund_name: Optional[str] = None) -> Tuple[datetime, datetime]:
        """Get date range for portfolio data, optionally filtered by fund"""
        try:
            data = portfolio_data
            
            if fund_name:
                data = self.get_fund_data(portfolio_data, fund_name)
            
            if data.empty or 'DataRiferimento' not in data.columns:
                today = datetime.now()
                return today - timedelta(days=365), today
            
            return data['DataRiferimento'].min(), data['DataRiferimento'].max()
            
        except Exception as e:
            logger.error(f"Error getting date range: {e}")
            today = datetime.now()
            return today - timedelta(days=365), today
    
    def get_latest_data_date(self, portfolio_data: pd.DataFrame, fund_name: str) -> Optional[datetime]:
        """Get the most recent data date for a specific fund"""
        try:
            fund_data = self.get_fund_data(portfolio_data, fund_name)
            if fund_data.empty:
                return None
            
            return fund_data['DataRiferimento'].max()
            
        except Exception as e:
            logger.error(f"Error getting latest date for {fund_name}: {e}")
            return None
    
    def get_fund_data_for_date(self, 
                               portfolio_data: pd.DataFrame, 
                               fund_name: str, 
                               target_date: datetime) -> pd.DataFrame:
        """Get fund data for a specific date (or closest available date)"""
        try:
            fund_data = self.get_fund_data(portfolio_data, fund_name)
            
            if fund_data.empty:
                return fund_data
            
            # Try exact date match first
            exact_match = fund_data[fund_data['DataRiferimento'] == target_date]
            if not exact_match.empty:
                return exact_match
            
            # Find closest date (preferably before target date)
            available_dates = fund_data['DataRiferimento'].unique()
            past_dates = available_dates[available_dates <= target_date]
            
            if len(past_dates) > 0:
                closest_date = max(past_dates)
            else:
                closest_date = min(available_dates)
            
            return fund_data[fund_data['DataRiferimento'] == closest_date]
            
        except Exception as e:
            ErrorHandler.handle_calculation_error(e, f"data retrieval for {fund_name}")
            return pd.DataFrame()
    
    def clear_cache(self):
        """Clear all cached data"""
        st.cache_data.clear()
        self._cache.clear()
        st.success("🗑️ Cache cleared successfully")


# Global instance
data_repository = DataRepository()
