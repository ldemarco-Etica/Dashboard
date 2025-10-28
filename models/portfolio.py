# applicazione/models/portfolio.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

from config import GEOGRAPHIC_REGIONS, CURRENCY_CONFIG, LIMITS_CONFIG
from validators import safe_divide, safe_percentage, ValidationError

logger = logging.getLogger(__name__)

# ... (AllocationResult and ComplianceResult dataclasses remain unchanged) ...

@dataclass
class AllocationResult:
    """Result structure for allocation calculations"""
    value: float
    percentage: float
    details: Dict[str, Any]
    is_valid: bool = True
    error_message: str = ""

@dataclass
class ComplianceResult:
    """Result structure for compliance checks"""
    rule_name: str
    current_value: float
    limit_min: Optional[float]
    limit_max: Optional[float]
    is_compliant: bool
    details: str
    calculation_date: datetime

class PortfolioAnalyzer:
    """Core business logic for portfolio analysis"""
    
    def __init__(self, portfolio_data: pd.DataFrame):
        self.data = portfolio_data
        self.calculator = LimitsCalculator(portfolio_data)  # FIX: Instantiate LimitsCalculator here
        self.logger = logging.getLogger(__name__)
        
    def calculate_sector_allocation(self, fund_name: str, date: datetime) -> pd.DataFrame:
        """
        Calculate sector allocation for a specific fund and date
        
        Args:
            fund_name: Name of the fund
            date: Target date
            
        Returns:
            DataFrame with sector allocations
        """
        try:
            fund_data = self._get_fund_data_for_date(fund_name, date)
            if fund_data.empty:
                return pd.DataFrame()
            
            sector_data = fund_data.groupby('DescrizioneSector', observed=True)['PesoPort'].sum().reset_index()
            sector_data = sector_data.sort_values('PesoPort', ascending=False)
            
            # Add percentage of total
            total_weight = sector_data['PesoPort'].sum()
            sector_data['Percentage'] = sector_data['PesoPort'].apply(
                lambda x: safe_percentage(x, total_weight)
            )
            
            return sector_data
            
        except Exception as e:
            self.logger.error(f"Error calculating sector allocation: {e}")
            return pd.DataFrame()
    
    def calculate_geographic_allocation(self, fund_name: str, date: datetime) -> pd.DataFrame:
        """Calculate geographic allocation"""
        try:
            fund_data = self._get_fund_data_for_date(fund_name, date)
            if fund_data.empty:
                return pd.DataFrame()
            
            geo_data = fund_data.groupby('CodicePaeseEsposizione', observed=True)['PesoPort'].sum().reset_index()
            geo_data = geo_data.sort_values('PesoPort', ascending=False)
            
            # Add percentage of total
            total_weight = geo_data['PesoPort'].sum()
            geo_data['Percentage'] = geo_data['PesoPort'].apply(
                lambda x: safe_percentage(x, total_weight)
            )
            
            return geo_data
            
        except Exception as e:
            self.logger.error(f"Error calculating geographic allocation: {e}")
            return pd.DataFrame()
    
    def calculate_asset_class_allocation(self, fund_name: str, date: datetime) -> pd.DataFrame:
        """Calculate asset class allocation"""
        try:
            fund_data = self._get_fund_data_for_date(fund_name, date)
            if fund_data.empty:
                return pd.DataFrame()
            
            asset_data = fund_data.groupby('CodiceTipo', observed=True)['PesoPort'].sum().reset_index()
            asset_data = asset_data.sort_values('PesoPort', ascending=False)
            
            # Add percentage and descriptions
            total_weight = asset_data['PesoPort'].sum()
            asset_data['Percentage'] = asset_data['PesoPort'].apply(
                lambda x: safe_percentage(x, total_weight)
            )
            
            # Add asset class descriptions
            asset_descriptions = {
                'AZ ': 'Equity',
                'OB ': 'Bonds', 
                'FO ': 'Funds',
                'LQ ': 'Liquidity',
                'FU ': 'Futures',
                'FW ': 'Forwards'
            }
            
            asset_data['Description'] = asset_data['CodiceTipo'].map(
                asset_descriptions
            ).fillna('Other')
            
            return asset_data
            
        except Exception as e:
            self.logger.error(f"Error calculating asset class allocation: {e}")
            return pd.DataFrame()
    
    def calculate_currency_exposure(self, fund_name: str, date: datetime) -> pd.DataFrame:
        """Calculate currency exposure"""
        try:
            fund_data = self._get_fund_data_for_date(fund_name, date)
            if fund_data.empty:
                return pd.DataFrame()
            
            # Handle special cases for currency mapping
            fund_data = self._apply_currency_exceptions(fund_data)
            
            currency_data = fund_data.groupby('CodiceDivisaEsposizione', observed=True)['PesoPort'].sum().reset_index()
            currency_data = currency_data.sort_values('PesoPort', ascending=False)
            
            # Add percentage of total
            total_weight = currency_data['PesoPort'].sum()
            currency_data['Percentage'] = currency_data['PesoPort'].apply(
                lambda x: safe_percentage(x, total_weight)
            )
            
            return currency_data
            
        except Exception as e:
            self.logger.error(f"Error calculating currency exposure: {e}")
            return pd.DataFrame()
    
    def get_title_evolution(self, fund_name: str, title_name: str) -> pd.DataFrame:
        """
        Get evolution of a specific title within a fund
        
        Args:
            fund_name: Name of the fund
            title_name: Name of the title
            
        Returns:
            DataFrame with title evolution over time
        """
        try:
            fund_data = self.data[
                (self.data['Descrizione'] == fund_name) &
                (self.data['DesTitolo'] == title_name)
            ].copy()
            
            if fund_data.empty:
                return pd.DataFrame()
            
            # Sort by date and remove duplicates (keep last for each date)
            fund_data = fund_data.sort_values('DataRiferimento')
            fund_data = fund_data.drop_duplicates(subset='DataRiferimento', keep='last')
            
            # Filter only periods where the title was present (weight > 0)
            present_data = fund_data[
                (fund_data['PesoPort'].notna()) & (fund_data['PesoPort'] != 0)
            ].copy()
            
            return present_data.sort_values('DataRiferimento')
            
        except Exception as e:
            self.logger.error(f"Error getting title evolution: {e}")
            return pd.DataFrame()
    
    def calculate_title_metrics(self, fund_name: str, title_name: str) -> Dict[str, Any]:
        """Calculate key metrics for a specific title"""
        try:
            evolution_data = self.get_title_evolution(fund_name, title_name)
            
            if evolution_data.empty:
                return {
                    'error': 'No data available for this title',
                    'is_valid': False
                }
            
            metrics = {
                'average_weight': evolution_data['PesoPort'].mean(),
                'max_weight': evolution_data['PesoPort'].max(),
                'min_weight': evolution_data['PesoPort'].min(),
                'current_weight': evolution_data.iloc[-1]['PesoPort'],
                'first_entry': evolution_data['DataRiferimento'].min(),
                'last_presence': evolution_data['DataRiferimento'].max(),
                'days_in_portfolio': (evolution_data['DataRiferimento'].max() - 
                                    evolution_data['DataRiferimento'].min()).days,
                'total_observations': len(evolution_data),
                'is_valid': True
            }
            
            # Additional metadata if available
            if not evolution_data.empty:
                last_record = evolution_data.iloc[-1]
                metrics.update({
                    'sector': last_record.get('DescrizioneSector', 'N/A'),
                    'rating': last_record.get('Rating', 'N/A'),
                    'country': last_record.get('CodicePaeseEsposizione', 'N/A'),
                    'asset_type': last_record.get('CodiceTipo', 'N/A')
                })
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating title metrics: {e}")
            return {'error': str(e), 'is_valid': False}
    
    def detect_title_gaps(self, evolution_data: pd.DataFrame, threshold_days: int = 5) -> List[Dict[str, Any]]:
        """
        Detect gaps in title presence (for discontinuous plotting)
        
        Args:
            evolution_data: DataFrame with title evolution
            threshold_days: Minimum days to consider a gap
            
        Returns:
            List of gap information
        """
        if evolution_data.empty or len(evolution_data) < 2:
            return []
        
        gaps = []
        sorted_data = evolution_data.sort_values('DataRiferimento')
        
        for i in range(1, len(sorted_data)):
            current_date = sorted_data.iloc[i]['DataRiferimento']
            prev_date = sorted_data.iloc[i-1]['DataRiferimento']
            gap_days = (current_date - prev_date).days
            
            if gap_days > threshold_days:
                gaps.append({
                    'start_date': prev_date,
                    'end_date': current_date,
                    'gap_days': gap_days
                })
        
        return gaps
    
    def _get_fund_data_for_date(self, fund_name: str, date: datetime) -> pd.DataFrame:
        """Get fund data for a specific date"""
        fund_data = self.data[
            (self.data['Descrizione'] == fund_name) &
            (self.data['DataRiferimento'] == date)
        ]
        return fund_data
    
    def _apply_currency_exceptions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply currency mapping exceptions"""
        df_copy = df.copy()
        
        for ticker_pattern, currency in CURRENCY_CONFIG.CURRENCY_EXCEPTIONS.items():
            if 'CodiceBloomberg' in df_copy.columns:
                mask = df_copy['CodiceBloomberg'].str.contains(ticker_pattern, na=False)
                df_copy.loc[mask, 'CodiceDivisaEsposizione'] = currency
        
        return df_copy

class LimitsCalculator:
    """Calculator for CDA limits and compliance rules"""
    
    def __init__(self, portfolio_data: pd.DataFrame, duration_data: Optional[pd.DataFrame] = None):
        self.portfolio_data = portfolio_data
        self.duration_data = duration_data
        self.logger = logging.getLogger(__name__)
    
    # ... (Rest of LimitsCalculator and PerformanceAnalyzer classes are unchanged) ...
    def calculate_equity_weight(self, fund_data: pd.DataFrame) -> float:
        """Calculate equity weight (AZ + SE)"""
        equity_instruments = fund_data[
            fund_data['CodiceTipo'].isin(LIMITS_CONFIG.ASSET_CLASSES['EQUITY'])
        ]
        return equity_instruments['PesoPort'].sum()
    
    def calculate_bond_weight(self, fund_data: pd.DataFrame) -> float:
        """Calculate bond weight"""
        bond_instruments = fund_data[
            fund_data['CodiceTipo'].isin(LIMITS_CONFIG.ASSET_CLASSES['BONDS'])
        ]
        return bond_instruments['PesoPort'].sum()
    
    def calculate_oicr_weight(self, fund_data: pd.DataFrame) -> float:
        """Calculate OICR weight"""
        oicr_instruments = fund_data[
            fund_data['CodiceTipo'].isin(LIMITS_CONFIG.ASSET_CLASSES['OICR'])
        ]
        return oicr_instruments['PesoPort'].sum()
    
    def calculate_liquidity_weight(self, fund_data: pd.DataFrame) -> float:
        """Calculate liquidity weight"""
        liquid_instruments = fund_data[
            fund_data['CodiceTipo'].isin(LIMITS_CONFIG.ASSET_CLASSES['LIQUIDITY'])
        ]
        return liquid_instruments['PesoPort'].sum()
    
    def calculate_emerging_markets_exposure(self, fund_data: pd.DataFrame) -> float:
        """Calculate emerging markets exposure among equities"""
        equity_data = fund_data[
            fund_data['CodiceTipo'].isin(LIMITS_CONFIG.ASSET_CLASSES['EQUITY'])
        ]
        
        if equity_data.empty:
            return 0.0
        
        emerging_exposure = equity_data[
            equity_data['CodicePaeseEsposizione'].isin(GEOGRAPHIC_REGIONS.MERCATI_EMERGENTI)
        ]
        
        return emerging_exposure['PesoPort'].sum()
    
    def calculate_eur_currency_exposure(self, fund_data: pd.DataFrame) -> float:
        """Calculate EUR currency exposure"""
        # Apply currency exceptions first
        fund_data = self._apply_currency_exceptions(fund_data)
        
        # Exclude forwards from currency exposure calculation
        relevant_data = fund_data[
            ~fund_data['CodiceTipo'].isin(LIMITS_CONFIG.ASSET_CLASSES['FORWARDS'])
        ]
        
        eur_exposure = relevant_data[
            relevant_data['CodiceDivisaEsposizione'].isin(CURRENCY_CONFIG.EUR_CURRENCIES)
        ]
        
        return eur_exposure['PesoPort'].sum()
    
    def calculate_rating_exposure(self, fund_data: pd.DataFrame, rating_categories: List[str]) -> float:
        """Calculate exposure to specific rating categories"""
        bond_data = fund_data[
            fund_data['CodiceTipo'].isin(LIMITS_CONFIG.ASSET_CLASSES['BONDS'])
        ]
        
        if bond_data.empty:
            return 0.0
        
        rating_exposure = bond_data[
            bond_data['Rating'].isin(rating_categories)
        ]
        
        return rating_exposure['PesoPort'].sum()
    
    def get_duration_value(self, fund_name: str, target_date: datetime) -> Optional[float]:
        """Get duration value for a fund at a specific date"""
        if self.duration_data is None or self.duration_data.empty:
            return None
        
        fund_duration = self.duration_data[
            self.duration_data['Fondo'] == fund_name
        ].copy()
        
        if fund_duration.empty:
            return None
        
        # Find closest date on or before target date
        valid_dates = fund_duration[fund_duration['Data'] <= target_date]
        if valid_dates.empty:
            return None
        
        closest_date = valid_dates['Data'].max()
        duration_record = valid_dates[valid_dates['Data'] == closest_date]
        
        if 'Duration Fondo' in duration_record.columns:
            return duration_record['Duration Fondo'].iloc[0]
        
        return None
    
    def _apply_currency_exceptions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply currency mapping exceptions"""
        df_copy = df.copy()
        
        for ticker_pattern, currency in CURRENCY_CONFIG.CURRENCY_EXCEPTIONS.items():
            if 'CodiceBloomberg' in df_copy.columns:
                mask = df_copy['CodiceBloomberg'].str.contains(ticker_pattern, na=False)
                df_copy.loc[mask, 'CodiceDivisaEsposizione'] = currency
        
        return df_copy

class PerformanceAnalyzer:
    """Analyzer for performance metrics and trends"""
    
    def __init__(self, portfolio_data: pd.DataFrame):
        self.data = portfolio_data
        self.logger = logging.getLogger(__name__)
    
    def calculate_allocation_evolution(self, fund_name: str, 
                                     allocation_type: str = 'sector',
                                     start_date: Optional[datetime] = None,
                                     end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Calculate evolution of allocations over time
        
        Args:
            fund_name: Name of the fund
            allocation_type: Type of allocation ('sector', 'geography', 'asset_class', 'currency')
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            DataFrame with allocation evolution
        """
        try:
            fund_data = self.data[self.data['Descrizione'] == fund_name].copy()
            
            if fund_data.empty:
                return pd.DataFrame()
            
            # Apply date filters
            if start_date:
                fund_data = fund_data[fund_data['DataRiferimento'] >= start_date]
            if end_date:
                fund_data = fund_data[fund_data['DataRiferimento'] <= end_date]
            
            # Choose grouping column based on allocation type
            group_column_map = {
                'sector': 'DescrizioneSector',
                'geography': 'CodicePaeseEsposizione', 
                'asset_class': 'CodiceTipo',
                'currency': 'CodiceDivisaEsposizione'
            }
            
            if allocation_type not in group_column_map:
                raise ValueError(f"Invalid allocation type: {allocation_type}")
            
            group_col = group_column_map[allocation_type]
            
            if group_col not in fund_data.columns:
                return pd.DataFrame()
            
            # Group by date and allocation category
            evolution_data = fund_data.groupby(['DataRiferimento', group_col], observed=True)['PesoPort'].sum().reset_index()
            
            return evolution_data
            
        except Exception as e:
            self.logger.error(f"Error calculating allocation evolution: {e}")
            return pd.DataFrame()
    
    def calculate_concentration_metrics(self, fund_name: str, date: datetime) -> Dict[str, float]:
        """Calculate concentration metrics (Herfindahl index, etc.)"""
        try:
            analyzer = PortfolioAnalyzer(self.data)
            fund_data = analyzer._get_fund_data_for_date(fund_name, date)
            
            if fund_data.empty:
                return {}
            
            weights = fund_data['PesoPort'].values
            total_weight = weights.sum()
            
            if total_weight == 0:
                return {}
            
            # Normalize weights
            normalized_weights = weights / total_weight
            
            # Calculate Herfindahl-Hirschman Index
            hhi = np.sum(normalized_weights ** 2)
            
            # Number of effective positions
            effective_positions = 1 / hhi if hhi > 0 else 0
            
            # Top 5 concentration
            top_5_weight = np.sum(np.sort(weights)[-5:]) if len(weights) >= 5 else total_weight
            top_5_concentration = safe_percentage(top_5_weight, total_weight)
            
            return {
                'herfindahl_index': hhi,
                'effective_positions': effective_positions,
                'top_5_concentration': top_5_concentration,
                'total_positions': len(weights),
                'largest_position': weights.max() if len(weights) > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating concentration metrics: {e}")
            return {}