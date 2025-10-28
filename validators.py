# applicazione/validators.py

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import streamlit as st
from pathlib import Path
import logging

from config import PORTFOLIO_COLUMNS, DATA_PATHS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class DataValidator:
    """Data validation utilities"""
    
    @staticmethod
    def validate_dataframe_structure(df: pd.DataFrame, required_columns: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate DataFrame structure
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            
        Returns:
            Tuple of (is_valid, list_of_missing_columns)
        """
        if df.empty:
            return False, ["DataFrame is empty"]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        return len(missing_columns) == 0, missing_columns
    
    @staticmethod
    def validate_portfolio_data(df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Comprehensive validation for portfolio data
        
        Returns:
            Tuple of (is_valid, validation_report)
        """
        validation_report = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }
        
        try:
            # Structure validation
            is_valid, missing_cols = DataValidator.validate_dataframe_structure(
                df, PORTFOLIO_COLUMNS.REQUIRED_COLUMNS
            )
            
            if not is_valid:
                validation_report['errors'].extend(missing_cols)
                validation_report['is_valid'] = False
                return False, validation_report
            
            # Data quality checks
            total_rows = len(df)
            validation_report['stats']['total_rows'] = total_rows
            
            # Check for null values in critical columns
            null_checks = {}
            for col in PORTFOLIO_COLUMNS.REQUIRED_COLUMNS:
                null_count = df[col].isnull().sum()
                null_checks[col] = null_count
                if null_count > 0:
                    validation_report['warnings'].append(
                        f"Column '{col}' has {null_count} null values ({null_count/total_rows*100:.1f}%)"
                    )
            
            validation_report['stats']['null_counts'] = null_checks
            
            # Validate date format
            try:
                df['DataRiferimento'] = pd.to_datetime(df['DataRiferimento'])
                date_range = (df['DataRiferimento'].min(), df['DataRiferimento'].max())
                validation_report['stats']['date_range'] = date_range
            except Exception as e:
                validation_report['errors'].append(f"Date validation failed: {e}")
                validation_report['is_valid'] = False
            
            # Validate numeric columns
            numeric_columns = ['PesoPort', 'PesoBmk']
            for col in numeric_columns:
                if col in df.columns:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        invalid_count = df[col].isnull().sum()
                        if invalid_count > 0:
                            validation_report['warnings'].append(
                                f"Column '{col}' has {invalid_count} non-numeric values"
                            )
                    except Exception as e:
                        validation_report['errors'].append(f"Numeric validation failed for {col}: {e}")
            
            # Portfolio weight validation
            if 'PesoPort' in df.columns:
                negative_weights = (df['PesoPort'] < 0).sum()
                if negative_weights > 0:
                    validation_report['warnings'].append(
                        f"Found {negative_weights} negative portfolio weights"
                    )
                
                # Check for funds with weights not summing to ~100%
                fund_weight_sums = df.groupby(['Descrizione', 'DataRiferimento'], observed=True)['PesoPort'].sum()
                outlier_sums = fund_weight_sums[
                    (fund_weight_sums < 95) | (fund_weight_sums > 105)
                ]
                if not outlier_sums.empty:
                    validation_report['warnings'].append(
                        f"Found {len(outlier_sums)} fund/date combinations with suspicious weight sums"
                    )
            
            # Fund name validation
            if 'Descrizione' in df.columns:
                unique_funds = df['Descrizione'].nunique()
                validation_report['stats']['unique_funds'] = unique_funds
                
                if unique_funds == 0:
                    validation_report['errors'].append("No fund names found")
                    validation_report['is_valid'] = False
            
            return validation_report['is_valid'], validation_report
            
        except Exception as e:
            validation_report['errors'].append(f"Validation failed with exception: {e}")
            validation_report['is_valid'] = False
            return False, validation_report
    
    @staticmethod
    def validate_file_path(file_path: Path) -> bool:
        """Validate file path exists and is readable"""
        try:
            return file_path.exists() and file_path.is_file()
        except Exception:
            return False
    
    @staticmethod
    def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
        """Validate date range is logical"""
        return start_date <= end_date
    
    @staticmethod
    def sanitize_fund_name(fund_name: str) -> str:
        """Sanitize fund name input"""
        if not isinstance(fund_name, str):
            raise ValidationError("Fund name must be a string")
        
        sanitized = fund_name.strip()
        if not sanitized:
            raise ValidationError("Fund name cannot be empty")
        
        return sanitized
    
    @staticmethod
    def validate_percentage(value: float, min_val: float = 0, max_val: float = 100) -> bool:
        """Validate percentage value is within expected range"""
        if pd.isna(value):
            return False
        return min_val <= value <= max_val

class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def handle_data_loading_error(error: Exception, context: str = "") -> None:
        """Handle data loading errors gracefully"""
        error_msg = f"Data loading error"
        if context:
            error_msg += f" in {context}"
        error_msg += f": {str(error)}"
        
        logger.error(error_msg)
        st.error(error_msg)
        st.info("Please check your data files and configuration, then refresh the page.")
    
    @staticmethod
    def handle_calculation_error(error: Exception, calculation_type: str = "") -> None:
        """Handle calculation errors gracefully"""
        error_msg = f"Calculation error"
        if calculation_type:
            error_msg += f" in {calculation_type}"
        error_msg += f": {str(error)}"
        
        logger.error(error_msg)
        st.error(error_msg)
        st.info("This might be due to missing or invalid data. Please check your inputs.")
    
    @staticmethod
    def handle_file_not_found(file_path: str, suggestion: str = "") -> None:
        """Handle file not found errors"""
        error_msg = f"File not found: {file_path}"
        
        logger.error(error_msg)
        st.error(error_msg)
        
        if suggestion:
            st.info(suggestion)
        else:
            st.info("Please ensure the file exists and the path is correct.")
    
    @staticmethod
    def show_validation_report(validation_report: Dict[str, Any], show_warnings: bool = True) -> None:
        """Display validation report to user"""
        if not validation_report['is_valid']:
            st.error("❌ Data validation failed!")
            for error in validation_report['errors']:
                st.error(f"• {error}")
        else:
            st.success("✅ Data validation passed!")
        
        if show_warnings and validation_report.get('warnings'):
            with st.expander("⚠️ Validation Warnings"):
                for warning in validation_report['warnings']:
                    st.warning(f"• {warning}")
        
        if validation_report.get('stats'):
            with st.expander("📊 Data Statistics"):
                stats = validation_report['stats']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'total_rows' in stats:
                        st.metric("Total Rows", f"{stats['total_rows']:,}")
                    
                    if 'unique_funds' in stats:
                        st.metric("Unique Funds", stats['unique_funds'])
                
                with col2:
                    if 'date_range' in stats:
                        start_date, end_date = stats['date_range']
                        st.write(f"**Date Range:** {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
                    
                    if 'null_counts' in stats:
                        null_counts = stats['null_counts']
                        total_nulls = sum(null_counts.values())
                        st.metric("Total Null Values", f"{total_nulls:,}")

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero"""
    if denominator == 0 or pd.isna(denominator) or pd.isna(numerator):
        return default
    return numerator / denominator

def safe_percentage(value: float, total: float, default: float = 0.0) -> float:
    """Safely calculate percentage, handling edge cases"""
    if total == 0 or pd.isna(total) or pd.isna(value):
        return default
    return (value / total) * 100

def validate_and_clean_data(df: pd.DataFrame, data_type: str = "portfolio") -> pd.DataFrame:
    """
    Validate and clean DataFrame based on data type
    
    Args:
        df: Input DataFrame
        data_type: Type of data ('portfolio', 'aum', 'duration', etc.)
        
    Returns:
        Cleaned DataFrame
    """
    if df.empty:
        logger.warning(f"Empty DataFrame provided for {data_type} data")
        return df
    
    try:
        if data_type == "portfolio":
            # Remove rows with zero or null portfolio weights
            initial_rows = len(df)
            df = df.dropna(subset=['PesoPort'])
            df = df[df['PesoPort'] != 0]
            
            # Convert percentage weights if needed (assuming they're in decimal format)
            if df['PesoPort'].max() <= 1.0:
                df['PesoPort'] = df['PesoPort'] * 100
            
            logger.info(f"Cleaned {data_type} data: {initial_rows} -> {len(df)} rows")
        
        return df
        
    except Exception as e:
        logger.error(f"Error cleaning {data_type} data: {e}")
        return df