#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGGIORNATORE PARQUET AUTOMATICO PER GITHUB ACTIONS
===================================================
Rileva automaticamente nuovi CSV e aggiorna i file Parquet

Autore: Portfolio Analytics
Data: Ottobre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoParquetUpdater:
    """Aggiorna automaticamente file Parquet con nuovi CSV rilevati"""
    
    def __init__(self, base_dir: Path = Path('.')):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / 'data'
        
        # Path Parquet
        self.portfolio_parquet = self.data_dir / 'consolidated' / 'portfolio_data.parquet'
        self.depositaria_parquet = self.data_dir / 'consolidated' / 'depositaria_data.parquet'
        
        # Path CSV sources
        self.portfolio_csv_dir = self.data_dir / 'portfolios'
        self.depositaria_csv_dir = self.data_dir / 'portfolios_depositaria'
        
        # Colonne portfolio
        self.portfolio_columns = [
            'DataRiferimento', 'CodicePortafoglio', 'Descrizione', 'CodiceTitolo',
            'DesTitolo', 'PesoPort', 'PesoBmk', 'CodiceTipo', 'DescrizioneSector',
            'ISIN', 'Sedol', 'CodiceBloomberg', 'CodicePaeseEsposizione',
            'CodiceDivisaEsposizione', 'TE', 'Rating', 'DataFormattata'
        ]
        
        # Mapping fondi depositaria
        self.fund_mapping = {
            88: "Etica Azionario",
            83: "Etica Bilanciato", 
            98: "Etica Transizione Climatica",
            99: "Etica Obiettivo Sociale",
            89: "Etica Rendita Bilanciata",
            82: "Etica Obbligazionario Misto",
            81: "Etica Obbligazionario Breve Termine"
        }
        
        self.depositaria_col_indices = {
            'CodFondo': 0, 'TipoStrumento': 1, 'ISIN': 3,
            'Descrizione': 4, 'QtaPortafoglio': 10,
            'Controvalore_EUR': 24, 'Peso_NAV': 33,
            'DataRiferimento': 56
        }
    
    def detect_new_files(self) -> Dict[str, List[Path]]:
        """
        Rileva nuovi CSV confrontando con date esistenti nei Parquet
        """
        logger.info("🔍 Rilevamento nuovi CSV...")
        
        new_files = {
            'portfolio': [],
            'depositaria': []
        }
        
        # Rileva portfolio
        if self.portfolio_csv_dir.exists():
            new_files['portfolio'] = self._detect_new_portfolio_files()
        
        # Rileva depositaria
        if self.depositaria_csv_dir.exists():
            new_files['depositaria'] = self._detect_new_depositaria_files()
        
        return new_files
    
    def _detect_new_portfolio_files(self) -> List[Path]:
        """Rileva nuovi CSV portfolio"""
        all_csv = sorted(self.portfolio_csv_dir.glob('*.csv'))
        
        if not self.portfolio_parquet.exists():
            logger.info("📂 Parquet portfolio non esiste, tutti i CSV sono nuovi")
            return all_csv
        
        # Carica date esistenti
        existing = pd.read_parquet(self.portfolio_parquet)
        existing_dates = set(existing['DataRiferimento'].dt.date.unique())
        
        # Filtra solo CSV con date nuove
        new_files = []
        for csv in all_csv:
            # Estrai data dal nome file (assumendo formato YYYYMMDD.csv)
            try:
                date_str = csv.stem  # Nome senza .csv
                file_date = datetime.strptime(date_str, '%Y%m%d').date()
                
                if file_date not in existing_dates:
                    new_files.append(csv)
                    logger.info(f"  ✓ Nuovo: {csv.name} (data: {file_date})")
                else:
                    logger.info(f"  ⊘ Esiste: {csv.name}")
            except ValueError:
                # Se il nome non è una data, carica comunque
                logger.warning(f"  ⚠️ Nome file non standard: {csv.name}, carico comunque")
                new_files.append(csv)
        
        return new_files
    
    def _detect_new_depositaria_files(self) -> List[Path]:
        """Rileva nuovi CSV depositaria"""
        all_csv = sorted(self.depositaria_csv_dir.glob('*.csv'))
        
        if not self.depositaria_parquet.exists():
            logger.info("📂 Parquet depositaria non esiste, tutti i CSV sono nuovi")
            return all_csv
        
        # Carica date esistenti
        existing = pd.read_parquet(self.depositaria_parquet)
        existing_dates = set(existing['DataRiferimento'].dt.date.unique())
        
        # Filtra solo CSV con date nuove
        new_files = []
        for csv in all_csv:
            try:
                date_str = csv.stem
                file_date = datetime.strptime(date_str, '%Y%m%d').date()
                
                if file_date not in existing_dates:
                    new_files.append(csv)
                    logger.info(f"  ✓ Nuovo: {csv.name} (data: {file_date})")
                else:
                    logger.info(f"  ⊘ Esiste: {csv.name}")
            except ValueError:
                logger.warning(f"  ⚠️ Nome file non standard: {csv.name}, carico comunque")
                new_files.append(csv)
        
        return new_files
    
    def update_portfolio_parquet(self, new_files: List[Path]) -> bool:
        """Aggiorna Parquet portfolio con nuovi CSV"""
        if not new_files:
            logger.info("ℹ️ Nessun nuovo CSV portfolio da processare")
            return False
        
        logger.info(f"📥 Processando {len(new_files)} nuovi CSV portfolio...")
        
        try:
            # Carica Parquet esistente
            if self.portfolio_parquet.exists():
                existing_data = pd.read_parquet(self.portfolio_parquet)
                logger.info(f"  Caricati {len(existing_data):,} record esistenti")
            else:
                existing_data = pd.DataFrame()
                logger.info("  Creazione nuovo Parquet")
            
            # Carica e processa nuovi CSV
            all_new_data = []
            for csv_file in new_files:
                logger.info(f"  Processing {csv_file.name}...")
                new_data = self._load_portfolio_csv(csv_file)
                
                if new_data.empty:
                    logger.warning(f"    ⚠️ Nessun dato valido, skip")
                    continue
                
                logger.info(f"    ✓ {len(new_data):,} righe valide")
                all_new_data.append(new_data)
            
            if not all_new_data:
                logger.error("❌ Nessun dato valido da aggiungere")
                return False
            
            # Unisci tutti i nuovi dati
            new_data_combined = pd.concat(all_new_data, ignore_index=True)
            logger.info(f"✓ Totale nuove righe: {len(new_data_combined):,}")
            
            # Unisci con esistenti
            if existing_data.empty:
                combined = new_data_combined
            else:
                combined = pd.concat([existing_data, new_data_combined], ignore_index=True)
            
            # Rimuovi duplicati
            original_len = len(combined)
            combined = combined.drop_duplicates()
            logger.info(f"✓ Rimossi {original_len - len(combined)} duplicati")
            
            # Ordina
            combined = combined.sort_values(['Descrizione', 'DataRiferimento', 'DesTitolo'])
            
            # Ottimizza tipi
            combined = self._optimize_dtypes(combined)
            
            # Salva
            self.portfolio_parquet.parent.mkdir(parents=True, exist_ok=True)
            combined.to_parquet(
                self.portfolio_parquet,
                engine='pyarrow',
                compression='snappy',
                index=False
            )
            
            file_size_mb = self.portfolio_parquet.stat().st_size / 1024 / 1024
            logger.info(f"✅ Parquet portfolio aggiornato: {len(combined):,} righe, {file_size_mb:.2f} MB")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore aggiornamento portfolio: {e}")
            return False
    
    def update_depositaria_parquet(self, new_files: List[Path]) -> bool:
        """Aggiorna Parquet depositaria con nuovi CSV"""
        if not new_files:
            logger.info("ℹ️ Nessun nuovo CSV depositaria da processare")
            return False
        
        logger.info(f"📥 Processando {len(new_files)} nuovi CSV depositaria...")
        
        try:
            # Carica Parquet esistente
            if self.depositaria_parquet.exists():
                existing_data = pd.read_parquet(self.depositaria_parquet)
                logger.info(f"  Caricati {len(existing_data):,} record esistenti")
            else:
                existing_data = pd.DataFrame()
                logger.info("  Creazione nuovo Parquet")
            
            # Carica e processa nuovi CSV
            all_new_data = []
            for csv_file in new_files:
                logger.info(f"  Processing {csv_file.name}...")
                new_data = self._load_depositaria_csv(csv_file)
                
                if new_data.empty:
                    logger.warning(f"    ⚠️ Nessun dato valido, skip")
                    continue
                
                logger.info(f"    ✓ {len(new_data):,} righe valide")
                all_new_data.append(new_data)
            
            if not all_new_data:
                logger.error("❌ Nessun dato valido da aggiungere")
                return False
            
            # Unisci tutti i nuovi dati
            new_data_combined = pd.concat(all_new_data, ignore_index=True)
            logger.info(f"✓ Totale nuove righe: {len(new_data_combined):,}")
            
            # Unisci con esistenti
            if existing_data.empty:
                combined = new_data_combined
            else:
                combined = pd.concat([existing_data, new_data_combined], ignore_index=True)
            
            # Rimuovi duplicati
            original_len = len(combined)
            combined = combined.drop_duplicates()
            logger.info(f"✓ Rimossi {original_len - len(combined)} duplicati")
            
            # Ordina
            combined = combined.sort_values(['NomeFondo', 'DataRiferimento', 'ISIN'])
            
            # Ottimizza tipi
            combined = self._optimize_dtypes(combined)
            
            # Salva
            self.depositaria_parquet.parent.mkdir(parents=True, exist_ok=True)
            combined.to_parquet(
                self.depositaria_parquet,
                engine='pyarrow',
                compression='snappy',
                index=False
            )
            
            file_size_mb = self.depositaria_parquet.stat().st_size / 1024 / 1024
            logger.info(f"✅ Parquet depositaria aggiornato: {len(combined):,} righe, {file_size_mb:.2f} MB")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore aggiornamento depositaria: {e}")
            return False
    
    def _load_portfolio_csv(self, file_path: Path) -> pd.DataFrame:
        """Carica CSV portfolio"""
        df = pd.read_csv(
            file_path,
            names=self.portfolio_columns,
            encoding='utf-8',
            low_memory=False
        )
        
        if df.empty:
            return pd.DataFrame()
        
        # Converti tipi
        df['DataRiferimento'] = pd.to_datetime(df['DataRiferimento'], format='%Y%m%d', errors='coerce')
        df['PesoPort'] = pd.to_numeric(df['PesoPort'], errors='coerce') 
        df['PesoBmk'] = pd.to_numeric(df['PesoBmk'], errors='coerce')
        
        # Rimuovi righe senza data
        df = df.dropna(subset=['DataRiferimento'])
        
        # Aggiungi metadati
        df['SourceFile'] = file_path.name
        
        return df
    
    def _load_depositaria_csv(self, file_path: Path) -> pd.DataFrame:
        """Carica CSV depositaria"""
        df = pd.read_csv(
            file_path,
            sep=';',
            encoding='utf-8',
            low_memory=False,
            dtype=str,
            on_bad_lines='skip'
        )
        
        if df.empty:
            return pd.DataFrame()
        
        processed = pd.DataFrame()
        
        # Data
        processed['DataRiferimento'] = pd.to_datetime(
            df.iloc[:, self.depositaria_col_indices['DataRiferimento']],
            format='%Y%m%d',
            errors='coerce'
        )
        
        # Codice fondo
        cod_fondo = pd.to_numeric(
            df.iloc[:, self.depositaria_col_indices['CodFondo']],
            errors='coerce'
        ).astype('Int64')
        processed['CodFondo'] = cod_fondo
        processed['NomeFondo'] = processed['CodFondo'].map(self.fund_mapping)
        
        # Altri campi
        processed['TipoStrumento'] = df.iloc[:, self.depositaria_col_indices['TipoStrumento']].astype(str).str.strip()
        processed['ISIN'] = df.iloc[:, self.depositaria_col_indices['ISIN']].astype(str).str.strip()
        processed['Descrizione'] = df.iloc[:, self.depositaria_col_indices['Descrizione']].astype(str).str.strip()
        
        # Quantità
        qta_raw = df.iloc[:, self.depositaria_col_indices['QtaPortafoglio']].astype(str)
        qta_raw = qta_raw.str.replace(',', '.').str.replace(' ', '')
        processed['QtaPortafoglio'] = pd.to_numeric(qta_raw, errors='coerce')
        
        # Controvalore
        contro_raw = df.iloc[:, self.depositaria_col_indices['Controvalore_EUR']].astype(str)
        contro_raw = contro_raw.str.replace(',', '.').str.replace(' ', '')
        processed['Controvalore_EUR'] = pd.to_numeric(contro_raw, errors='coerce')
        
        # Peso NAV
        peso_raw = df.iloc[:, self.depositaria_col_indices['Peso_NAV']].astype(str)
        peso_raw = peso_raw.str.replace(',', '.').str.replace(' ', '')
        processed['Peso_NAV'] = pd.to_numeric(peso_raw, errors='coerce')
        
        # Metadati
        processed['SourceFile'] = file_path.name
        
        # Filtra validi
        valid_mask = (
            processed['DataRiferimento'].notna() &
            processed['NomeFondo'].notna() &
            processed['ISIN'].notna() &
            (processed['ISIN'] != '') &
            (processed['ISIN'] != 'nan')
        )
        
        return processed[valid_mask].copy()
    
    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ottimizza tipi dati"""
        for col in df.columns:
            col_type = df[col].dtype
            
            if col_type in ['float64', 'float32']:
                df[col] = df[col].astype('float32')
            
            elif col_type in ['int64', 'int32']:
                c_min = df[col].min()
                c_max = df[col].max()
                
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
            
            elif col_type == 'object':
                num_unique = df[col].nunique()
                num_total = len(df[col])
                
                if num_unique / num_total < 0.5:
                    df[col] = df[col].astype('category')
        
        return df
    
    def run(self) -> bool:
        """
        Esegue l'intero processo di aggiornamento automatico
        
        Returns:
            True se almeno un Parquet è stato aggiornato
        """
        logger.info("=" * 80)
        logger.info("🚀 AVVIO AGGIORNAMENTO AUTOMATICO PARQUET")
        logger.info("=" * 80)
        
        # Rileva nuovi file
        new_files = self.detect_new_files()
        
        total_new = len(new_files['portfolio']) + len(new_files['depositaria'])
        
        if total_new == 0:
            logger.info("✅ Nessun nuovo file da processare. Sistema aggiornato.")
            return False
        
        logger.info(f"📊 Trovati {total_new} nuovi file:")
        logger.info(f"  • Portfolio: {len(new_files['portfolio'])}")
        logger.info(f"  • Depositaria: {len(new_files['depositaria'])}")
        
        # Aggiorna Parquet
        portfolio_updated = False
        depositaria_updated = False
        
        if new_files['portfolio']:
            portfolio_updated = self.update_portfolio_parquet(new_files['portfolio'])
        
        if new_files['depositaria']:
            depositaria_updated = self.update_depositaria_parquet(new_files['depositaria'])
        
        # Riepilogo
        logger.info("=" * 80)
        if portfolio_updated or depositaria_updated:
            logger.info("✅ AGGIORNAMENTO COMPLETATO CON SUCCESSO")
            if portfolio_updated:
                logger.info("  ✓ Portfolio Parquet aggiornato")
            if depositaria_updated:
                logger.info("  ✓ Depositaria Parquet aggiornato")
        else:
            logger.info("❌ AGGIORNAMENTO FALLITO")
        logger.info("=" * 80)
        
        return portfolio_updated or depositaria_updated


def main():
    """Entry point per GitHub Actions"""
    try:
        # Crea updater
        updater = AutoParquetUpdater()
        
        # Esegui aggiornamento
        success = updater.run()
        
        # Exit code per GitHub Actions
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"💥 ERRORE CRITICO: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
