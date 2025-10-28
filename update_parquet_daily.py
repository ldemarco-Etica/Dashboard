#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 08:48:41 2025

@author: lucademarco
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGGIORNATORE PARQUET INCREMENTALE
==================================
Aggiunge nuovi CSV ai file Parquet esistenti

Uso:
    python update_parquet_daily.py --new-csv data/portfolios/20251022.csv
    python update_parquet_daily.py --new-dir data/portfolios/new/ --type portfolio

Autore: Portfolio Analytics
Data: Ottobre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import logging
from datetime import datetime
from typing import Optional, List
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ParquetUpdater:
    """Aggiorna file Parquet con nuovi CSV"""
    
    def __init__(self, parquet_file: Path, data_type: str = 'portfolio'):
        self.parquet_file = Path(parquet_file)
        self.data_type = data_type
        
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
    
    def update_with_csv(self, csv_file: Path) -> dict:
        """
        Aggiorna Parquet con un nuovo CSV
        """
        logger.info(f"📥 Caricamento CSV: {csv_file.name}")
        
        # Carica nuovo CSV
        if self.data_type == 'portfolio':
            new_data = self._load_portfolio_csv(csv_file)
        else:  # depositaria
            new_data = self._load_depositaria_csv(csv_file)
        
        if new_data.empty:
            logger.error("❌ Nessun dato valido nel CSV")
            return {'success': False, 'error': 'No valid data in CSV'}
        
        logger.info(f"✓ Caricate {len(new_data):,} righe dal CSV")
        
        # Carica Parquet esistente
        if not self.parquet_file.exists():
            logger.warning("⚠️  File Parquet non esistente, lo creerò")
            existing_data = pd.DataFrame()
        else:
            logger.info(f"📂 Caricamento Parquet esistente: {self.parquet_file}")
            existing_data = pd.read_parquet(self.parquet_file)
            logger.info(f"✓ Caricate {len(existing_data):,} righe esistenti")
        
        # Controlla duplicati (stessa data)
        if not existing_data.empty:
            new_dates = new_data['DataRiferimento'].unique()
            existing_dates = existing_data['DataRiferimento'].unique()
            
            duplicates = set(new_dates) & set(existing_dates)
            
            if duplicates:
                logger.warning(f"⚠️  Trovate {len(duplicates)} date duplicate")
                logger.warning(f"   Date: {sorted([d.strftime('%d/%m/%Y') for d in duplicates])}")
                
                response = input("Vuoi sovrascrivere i dati esistenti per queste date? (s/n): ")
                
                if response.lower() == 's':
                    # Rimuovi date duplicate dal dataset esistente
                    existing_data = existing_data[
                        ~existing_data['DataRiferimento'].isin(duplicates)
                    ]
                    logger.info("✓ Date duplicate rimosse dal dataset esistente")
                else:
                    logger.info("ℹ️  Mantengo dati esistenti, rimuovo nuovi dati per date duplicate")
                    new_data = new_data[
                        ~new_data['DataRiferimento'].isin(duplicates)
                    ]
                    
                    if new_data.empty:
                        logger.warning("⚠️  Nessun nuovo dato da aggiungere dopo rimozione duplicati")
                        return {'success': False, 'error': 'All data duplicated'}
        
        # Unisci dati
        logger.info("🔄 Unione dataset...")
        combined = pd.concat([existing_data, new_data], ignore_index=True)
        
        # Rimuovi eventuali duplicati completi
        original_len = len(combined)
        combined = combined.drop_duplicates()
        duplicates_removed = original_len - len(combined)
        
        if duplicates_removed > 0:
            logger.info(f"✓ Rimossi {duplicates_removed} duplicati completi")
        
        # Ordina
        logger.info("📊 Ordinamento dataset...")
        if self.data_type == 'portfolio':
            combined = combined.sort_values(['Descrizione', 'DataRiferimento', 'DesTitolo'])
        else:
            combined = combined.sort_values(['NomeFondo', 'DataRiferimento', 'ISIN'])
        
        # Ottimizza tipi
        logger.info("⚙️  Ottimizzazione tipi dati...")
        combined = self._optimize_dtypes(combined)
        
        # Backup vecchio file
        if self.parquet_file.exists():
            backup_file = self.parquet_file.with_suffix('.parquet.backup')
            logger.info(f"💾 Backup file esistente: {backup_file}")
            self.parquet_file.rename(backup_file)
        
        # Salva nuovo Parquet
        logger.info(f"💾 Salvataggio Parquet aggiornato...")
        combined.to_parquet(
            self.parquet_file,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        # Statistiche
        file_size_mb = self.parquet_file.stat().st_size / 1024 / 1024
        
        stats = {
            'success': True,
            'rows_before': len(existing_data) if not existing_data.empty else 0,
            'rows_added': len(new_data),
            'rows_after': len(combined),
            'file_size_mb': round(file_size_mb, 2),
            'new_dates': sorted(new_data['DataRiferimento'].unique()),
            'date_range': (combined['DataRiferimento'].min(), combined['DataRiferimento'].max())
        }
        
        self._print_update_summary(stats)
        
        return stats
    
    def update_with_directory(self, csv_dir: Path) -> dict:
        """
        Aggiorna Parquet con tutti i CSV in una directory
        """
        csv_dir = Path(csv_dir)
        
        if not csv_dir.exists():
            logger.error(f"❌ Directory non trovata: {csv_dir}")
            return {'success': False, 'error': 'Directory not found'}
        
        csv_files = sorted(csv_dir.glob('*.csv'))
        
        if not csv_files:
            logger.error(f"❌ Nessun CSV trovato in {csv_dir}")
            return {'success': False, 'error': 'No CSV files found'}
        
        logger.info(f"📂 Trovati {len(csv_files)} file CSV da processare")
        
        # Carica Parquet esistente
        if not self.parquet_file.exists():
            logger.warning("⚠️  File Parquet non esistente, lo creerò")
            existing_data = pd.DataFrame()
        else:
            logger.info(f"📂 Caricamento Parquet esistente: {self.parquet_file}")
            existing_data = pd.read_parquet(self.parquet_file)
            logger.info(f"✓ Caricate {len(existing_data):,} righe esistenti")
        
        # Processa tutti i CSV
        all_new_data = []
        failed = []
        
        for i, csv_file in enumerate(csv_files, 1):
            try:
                logger.info(f"[{i}/{len(csv_files)}] Processing {csv_file.name}...")
                
                if self.data_type == 'portfolio':
                    new_data = self._load_portfolio_csv(csv_file)
                else:
                    new_data = self._load_depositaria_csv(csv_file)
                
                if new_data.empty:
                    logger.warning(f"  ⚠️  Nessun dato valido, skip")
                    failed.append((csv_file.name, "No valid data"))
                    continue
                
                logger.info(f"  ✓ {len(new_data):,} righe valide")
                all_new_data.append(new_data)
                
            except Exception as e:
                logger.error(f"  ✗ Errore: {e}")
                failed.append((csv_file.name, str(e)))
        
        if not all_new_data:
            logger.error("❌ Nessun dato valido da aggiungere")
            return {'success': False, 'error': 'No valid data to add'}
        
        # Unisci tutti i nuovi dati
        logger.info("\n🔄 Unione nuovi dati...")
        new_data_combined = pd.concat(all_new_data, ignore_index=True)
        logger.info(f"✓ Totale nuove righe: {len(new_data_combined):,}")
        
        # Gestisci duplicati
        if not existing_data.empty:
            new_dates = new_data_combined['DataRiferimento'].unique()
            existing_dates = existing_data['DataRiferimento'].unique()
            duplicates = set(new_dates) & set(existing_dates)
            
            if duplicates:
                logger.warning(f"⚠️  Trovate {len(duplicates)} date duplicate")
                response = input("Sovrascrivere dati esistenti per date duplicate? (s/n): ")
                
                if response.lower() == 's':
                    existing_data = existing_data[
                        ~existing_data['DataRiferimento'].isin(duplicates)
                    ]
                else:
                    new_data_combined = new_data_combined[
                        ~new_data_combined['DataRiferimento'].isin(duplicates)
                    ]
        
        # Unisci tutto
        logger.info("🔄 Unione dataset completo...")
        combined = pd.concat([existing_data, new_data_combined], ignore_index=True)
        
        # Rimuovi duplicati completi
        original_len = len(combined)
        combined = combined.drop_duplicates()
        logger.info(f"✓ Rimossi {original_len - len(combined)} duplicati completi")
        
        # Ordina
        logger.info("📊 Ordinamento...")
        if self.data_type == 'portfolio':
            combined = combined.sort_values(['Descrizione', 'DataRiferimento', 'DesTitolo'])
        else:
            combined = combined.sort_values(['NomeFondo', 'DataRiferimento', 'ISIN'])
        
        # Ottimizza
        logger.info("⚙️  Ottimizzazione...")
        combined = self._optimize_dtypes(combined)
        
        # Backup
        if self.parquet_file.exists():
            backup_file = self.parquet_file.with_suffix('.parquet.backup')
            self.parquet_file.rename(backup_file)
            logger.info(f"💾 Backup: {backup_file}")
        
        # Salva
        logger.info("💾 Salvataggio...")
        combined.to_parquet(
            self.parquet_file,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        # Stats
        file_size_mb = self.parquet_file.stat().st_size / 1024 / 1024
        
        stats = {
            'success': True,
            'files_processed': len(all_new_data),
            'files_failed': len(failed),
            'rows_before': len(existing_data) if not existing_data.empty else 0,
            'rows_added': len(new_data_combined),
            'rows_after': len(combined),
            'file_size_mb': round(file_size_mb, 2),
            'failed_details': failed
        }
        
        self._print_update_summary(stats)
        
        return stats
    
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
        df['PesoPort'] = pd.to_numeric(df['PesoPort'], errors='coerce')*100
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
    
    def _print_update_summary(self, stats: dict):
        """Stampa riepilogo aggiornamento"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 RIEPILOGO AGGIORNAMENTO")
        logger.info("=" * 80)
        logger.info(f"✓ Righe prima: {stats['rows_before']:,}")
        logger.info(f"✓ Righe aggiunte: {stats['rows_added']:,}")
        logger.info(f"✓ Righe dopo: {stats['rows_after']:,}")
        logger.info(f"✓ Dimensione file: {stats['file_size_mb']:.2f} MB")
        
        if 'new_dates' in stats:
            logger.info(f"✓ Nuove date aggiunte: {len(stats['new_dates'])}")
            if len(stats['new_dates']) <= 5:
                for date in stats['new_dates']:
                    logger.info(f"  • {date.strftime('%d/%m/%Y')}")
        
        logger.info("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Aggiorna file Parquet con nuovi CSV'
    )
    
    parser.add_argument(
        '--parquet',
        type=str,
        required=True,
        help='Path al file Parquet da aggiornare'
    )
    
    parser.add_argument(
        '--type',
        type=str,
        choices=['portfolio', 'depositaria'],
        default='portfolio',
        help='Tipo di dati (default: portfolio)'
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--csv',
        type=str,
        help='Path al singolo CSV da aggiungere'
    )
    group.add_argument(
        '--csv-dir',
        type=str,
        help='Path alla directory con CSV da aggiungere'
    )
    
    args = parser.parse_args()
    
    # Crea updater
    updater = ParquetUpdater(
        parquet_file=Path(args.parquet),
        data_type=args.type
    )
    
    # Esegui aggiornamento
    if args.csv:
        logger.info(f"🔄 Aggiornamento con singolo CSV: {args.csv}")
        result = updater.update_with_csv(Path(args.csv))
    else:
        logger.info(f"🔄 Aggiornamento con directory: {args.csv_dir}")
        result = updater.update_with_directory(Path(args.csv_dir))
    
    # Risultato
    if result['success']:
        logger.info("✅ Aggiornamento completato con successo!")
    else:
        logger.error(f"❌ Aggiornamento fallito: {result.get('error')}")
        exit(1)


if __name__ == "__main__":
    main()