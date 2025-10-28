#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONSOLIDATORE CSV → PARQUET
===========================
Unifica tutti i CSV in file Parquet ottimizzati per GitHub

Autore: Portfolio Analytics
Data: Ottobre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import glob
import logging
from datetime import datetime
from typing import List, Dict, Optional
import pyarrow as pa
import pyarrow.parquet as pq

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('consolidation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CSVConsolidator:
    """Consolidatore CSV → Parquet con ottimizzazioni"""
    
    def __init__(self, source_dir: Path, output_dir: Path):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Colonne portfolio standard
        self.portfolio_columns = [
            'DataRiferimento', 'CodicePortafoglio', 'Descrizione', 'CodiceTitolo',
            'DesTitolo', 'PesoPort', 'PesoBmk', 'CodiceTipo', 'DescrizioneSector',
            'ISIN', 'Sedol', 'CodiceBloomberg', 'CodicePaeseEsposizione',
            'CodiceDivisaEsposizione', 'TE', 'Rating', 'DataFormattata'
        ]
        
        # Colonne depositaria
        self.depositaria_col_indices = {
            'CodFondo': 0,
            'TipoStrumento': 1,
            'ISIN': 3,
            'Descrizione': 4,
            'QtaPortafoglio': 10,
            'Controvalore_EUR': 24,
            'Peso_NAV': 33,
            'DataRiferimento': 56
        }
        
        self.fund_mapping = {
            88: "Etica Azionario",
            83: "Etica Bilanciato", 
            98: "Etica Transizione Climatica",
            99: "Etica Obiettivo Sociale",
            89: "Etica Rendita Bilanciata",
            82: "Etica Obbligazionario Misto",
            81: "Etica Obbligazionario Breve Termine"
        }
        
        # Config aggiuntiva per filtri (da Turnover.py)
        self.EXCLUDE_TYPES = ['2']  # Liquidità e margini
        self.MIN_VALUE_THRESHOLD = 10000  # Euro minimi
    
    def consolidate_portfolio_csvs(self) -> Dict[str, any]:
        """
        Unifica tutti i CSV portfolio in un singolo Parquet
        """
        logger.info("=" * 80)
        logger.info("CONSOLIDAMENTO PORTFOLIO CSV → PARQUET")
        logger.info("=" * 80)
        
        csv_files = sorted(glob.glob(str(self.source_dir / "*.csv")))
        
        if not csv_files:
            logger.error(f"Nessun CSV trovato in {self.source_dir}")
            return {'success': False, 'error': 'No CSV files found'}
        
        logger.info(f"📂 Trovati {len(csv_files)} file CSV")
        
        dfs = []
        failed = []
        total_rows = 0
        
        for i, file in enumerate(csv_files, 1):
            try:
                logger.info(f"[{i}/{len(csv_files)}] Processing {Path(file).name}...")
                
                # Leggi CSV
                df = pd.read_csv(
                    file,
                    names=self.portfolio_columns,
                    encoding='utf-8',
                    low_memory=False
                )
                
                if df.empty:
                    logger.warning(f"  ⚠️  File vuoto, skip")
                    failed.append((Path(file).name, "Empty file"))
                    continue
                
                # Converti tipi
                df['DataRiferimento'] = pd.to_datetime(df['DataRiferimento'], format='%Y%m%d', errors='coerce')
                df['PesoPort'] = pd.to_numeric(df['PesoPort'], errors='coerce')*100
                df['PesoBmk'] = pd.to_numeric(df['PesoBmk'], errors='coerce')
                df['TE'] = pd.to_numeric(df['TE'], errors='coerce')
                
                # Rimuovi righe senza data (header o corrupted)
                df = df.dropna(subset=['DataRiferimento'])
                
                # Aggiungi metadati
                df['SourceFile'] = Path(file).name
                
                rows = len(df)
                total_rows += rows
                logger.info(f"  ✓ {rows:,} righe valide")
                
                dfs.append(df)
                
            except Exception as e:
                logger.error(f"  ✗ Errore: {e}")
                failed.append((Path(file).name, str(e)))
        
        if not dfs:
            logger.error("Nessun dato valido processato!")
            return {'success': False, 'error': 'No valid data'}
        
        # Unifica
        logger.info("\n🔄 Unificazione DataFrame...")
        combined = pd.concat(dfs, ignore_index=True)
        logger.info(f"✓ Totale righe unificate: {len(combined):,}")
        
        # Ottimizza tipi dati per ridurre dimensioni
        logger.info("\n⚙️  Ottimizzazione tipi dati...")
        combined = self._optimize_dtypes(combined)
        
        # Ordina per efficienza query
        logger.info("\n📊 Ordinamento dati...")
        combined = combined.sort_values(['Descrizione', 'DataRiferimento', 'DesTitolo'])
        
        # Salva Parquet con compressione
        output_file = self.output_dir / 'portfolio_data.parquet'
        logger.info(f"\n💾 Salvataggio Parquet: {output_file}")
        
        combined.to_parquet(
            output_file,
            engine='pyarrow',
            compression='snappy',  # Bilanciamento velocità/compressione
            index=False
        )
        
        # Statistiche
        file_size_mb = output_file.stat().st_size / 1024 / 1024
        
        stats = {
            'success': True,
            'output_file': str(output_file),
            'total_files_processed': len(dfs),
            'total_files_found': len(csv_files),
            'failed_files': len(failed),
            'total_rows': len(combined),
            'file_size_mb': round(file_size_mb, 2),
            'unique_funds': combined['Descrizione'].nunique(),
            'date_range': (combined['DataRiferimento'].min(), combined['DataRiferimento'].max()),
            'failed_details': failed
        }
        
        self._print_summary(stats)
        
        return stats
    
    def consolidate_depositaria_csvs(self) -> Dict[str, any]:
        """
        Unifica tutti i CSV depositaria in un singolo Parquet
        """
        logger.info("\n" + "=" * 80)
        logger.info("CONSOLIDAMENTO DEPOSITARIA CSV → PARQUET")
        logger.info("=" * 80)
        
        csv_files = sorted(glob.glob(str(self.source_dir / "*.csv")))
        
        if not csv_files:
            logger.error(f"Nessun CSV trovato in {self.source_dir}")
            return {'success': False, 'error': 'No CSV files found'}
        
        logger.info(f"📂 Trovati {len(csv_files)} file CSV")
        
        dfs = []
        failed = []
        
        for i, file in enumerate(csv_files, 1):
            try:
                logger.info(f"[{i}/{len(csv_files)}] Processing {Path(file).name}...")
                
                df = self._parse_depositaria_csv(Path(file))
                
                if df.empty:
                    logger.warning(f"  ⚠️  Nessun dato valido, skip")
                    failed.append((Path(file).name, "No valid data"))
                    continue
                
                logger.info(f"  ✓ {len(df):,} righe valide")
                dfs.append(df)
                
            except Exception as e:
                logger.error(f"  ✗ Errore: {e}")
                failed.append((Path(file).name, str(e)))
        
        if not dfs:
            logger.error("Nessun dato valido processato!")
            return {'success': False, 'error': 'No valid data'}
        
        # Unifica
        logger.info("\n🔄 Unificazione DataFrame...")
        combined = pd.concat(dfs, ignore_index=True)
        logger.info(f"✓ Totale righe unificate: {len(combined):,}")
        
        # Rimuovi duplicati (chiave: DataRiferimento, NomeFondo, ISIN)
        dup_before = len(combined)
        combined = combined.drop_duplicates(subset=['DataRiferimento', 'NomeFondo', 'ISIN'])
        dup_removed = dup_before - len(combined)
        if dup_removed > 0:
            logger.warning(f"⚠️  Rimossi {dup_removed:,} duplicati basati su (DataRiferimento, NomeFondo, ISIN)")
        else:
            logger.info("✅ Nessun duplicato trovato")
        
        # Ottimizza
        logger.info("\n⚙️  Ottimizzazione tipi dati...")
        combined = self._optimize_dtypes(combined)
        
        # Ordina
        logger.info("\n📊 Ordinamento dati...")
        combined = combined.sort_values(['NomeFondo', 'DataRiferimento', 'ISIN'])
        
        # Salva
        output_file = self.output_dir / 'depositaria_data.parquet'
        logger.info(f"\n💾 Salvataggio Parquet: {output_file}")
        
        combined.to_parquet(
            output_file,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        # Statistiche
        file_size_mb = output_file.stat().st_size / 1024 / 1024
        
        stats = {
            'success': True,
            'output_file': str(output_file),
            'total_files_processed': len(dfs),
            'total_files_found': len(csv_files),
            'failed_files': len(failed),
            'total_rows': len(combined),
            'file_size_mb': round(file_size_mb, 2),
            'unique_funds': combined['NomeFondo'].nunique(),
            'date_range': (combined['DataRiferimento'].min(), combined['DataRiferimento'].max()),
            'failed_details': failed,
            'duplicates_removed': dup_removed  # Aggiunto per tracking
        }
        
        self._print_summary(stats)
        
        return stats
    
    def _parse_depositaria_csv(self, file_path: Path) -> pd.DataFrame:
        """Parse singolo CSV depositaria"""
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
        
        # Quantità - DIVIDI PER 1000 (come commentato in Turnover.py; rimuovi se non necessario)
        qta_raw = df.iloc[:, self.depositaria_col_indices['QtaPortafoglio']].astype(str)
        qta_raw = qta_raw.str.replace(',', '.').str.replace(' ', '')
        processed['QtaPortafoglio'] = pd.to_numeric(qta_raw, errors='coerce') #/ 1000
        
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
        
        # Filtra righe valide (ALLINEATO CON Turnover.py)
        valid_mask = (
            processed['DataRiferimento'].notna() &
            processed['NomeFondo'].notna() &
            processed['ISIN'].notna() &
            (processed['ISIN'] != '') &
            (processed['ISIN'] != 'nan') &
            ~processed['TipoStrumento'].isin(self.EXCLUDE_TYPES) &  # Aggiunto: Escludi liquidità
            (processed['Controvalore_EUR'].abs() >= self.MIN_VALUE_THRESHOLD) &  # Aggiunto: Soglia minima
            (processed['Peso_NAV'].fillna(0) > 0)  # Aggiunto: Peso NAV > 0
        )
        
        excluded_count = len(processed) - len(processed[valid_mask])
        if excluded_count > 0:
            logger.warning(f"⚠️  Escluse {excluded_count:,} righe non valide da {file_path.name}")
        
        return processed[valid_mask].copy()
    
    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ottimizza tipi dati per ridurre memoria/dimensioni"""
        
        for col in df.columns:
            col_type = df[col].dtype
            
            # Ottimizza numerici
            if col_type in ['float64', 'float32']:
                # Usa float32 se possibile
                df[col] = df[col].astype('float32')
            
            elif col_type in ['int64', 'int32']:
                # Usa int più piccolo possibile
                c_min = df[col].min()
                c_max = df[col].max()
                
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
            
            # Converti stringhe ripetute in category
            elif col_type == 'object':
                num_unique = df[col].nunique()
                num_total = len(df[col])
                
                # Se < 50% valori unici, usa category
                if num_unique / num_total < 0.5:
                    df[col] = df[col].astype('category')
        
        return df
    
    def _print_summary(self, stats: Dict):
        """Stampa riepilogo consolidamento"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 RIEPILOGO CONSOLIDAMENTO")
        logger.info("=" * 80)
        logger.info(f"✓ File output: {stats['output_file']}")
        logger.info(f"✓ Dimensione: {stats['file_size_mb']:.2f} MB")
        logger.info(f"✓ File processati: {stats['total_files_processed']}/{stats['total_files_found']}")
        logger.info(f"✓ Righe totali: {stats['total_rows']:,}")
        logger.info(f"✓ Fondi unici: {stats['unique_funds']}")
        
        if stats['date_range']:
            start, end = stats['date_range']
            logger.info(f"✓ Range date: {start.strftime('%d/%m/%Y')} → {end.strftime('%d/%m/%Y')}")
        
        if stats['failed_files'] > 0:
            logger.warning(f"\n⚠️  File falliti: {stats['failed_files']}")
            for fname, error in stats['failed_details'][:5]:
                logger.warning(f"  • {fname}: {error}")
            if len(stats['failed_details']) > 5:
                logger.warning(f"  ... e altri {len(stats['failed_details'])-5}")
        
        if 'duplicates_removed' in stats and stats['duplicates_removed'] > 0:
            logger.warning(f"⚠️  Duplicati rimossi: {stats['duplicates_removed']:,}")
        
        logger.info("=" * 80 + "\n")


def main():
    """Esegui consolidamento completo"""
    
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║   CONSOLIDATORE CSV → PARQUET                              ║
    ║   Portfolio Analytics - Ottimizzazione per GitHub         ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Configurazione
    portfolio_source = Path('data/portfolios')
    depositaria_source = Path('data/portfolios_depositaria')
    output_dir = Path('data/consolidated')
    
    consolidator_portfolio = CSVConsolidator(portfolio_source, output_dir)
    consolidator_depositaria = CSVConsolidator(depositaria_source, output_dir)
    
    # Menu interattivo
    print("\n🎯 Cosa vuoi consolidare?")
    print("1. Portfolio CSV")
    print("2. Depositaria CSV")
    print("3. Entrambi")
    
    choice = input("\nScelta (1/2/3): ").strip()
    
    results = []
    
    if choice in ['1', '3']:
        if portfolio_source.exists():
            print("\n" + "▶️  Consolidamento Portfolio...")
            result = consolidator_portfolio.consolidate_portfolio_csvs()
            results.append(('Portfolio', result))
        else:
            print(f"❌ Cartella non trovata: {portfolio_source}")
    
    if choice in ['2', '3']:
        if depositaria_source.exists():
            print("\n" + "▶️  Consolidamento Depositaria...")
            result = consolidator_depositaria.consolidate_depositaria_csvs()
            results.append(('Depositaria', result))
        else:
            print(f"❌ Cartella non trovata: {depositaria_source}")
    
    # Riepilogo finale
    print("\n" + "=" * 80)
    print("🎉 CONSOLIDAMENTO COMPLETATO")
    print("= " * 80)
    
    total_size = 0
    for name, result in results:
        if result['success']:
            print(f"\n✅ {name}:")
            print(f"   File: {result['output_file']}")
            print(f"   Dimensione: {result['file_size_mb']:.2f} MB")
            print(f"   Righe: {result['total_rows']:,}")
            total_size += result['file_size_mb']
    
    print(f"\n📦 Dimensione totale: {total_size:.2f} MB")
    
    if total_size > 100:
        print("\n⚠️  ATTENZIONE: Dimensione > 100MB!")
        print("   GitHub ha limite 100MB per file. Considera:")
        print("   1. Filtrare solo dati recenti (es. ultimi 2 anni)")
        print("   2. Usare Git LFS (Large File Storage)")
        print("   3. Dividere in file più piccoli per anno")
    elif total_size > 50:
        print("\n⚠️  ATTENZIONE: Dimensione vicina al limite (50-100MB)")
        print("   Monitora la crescita con nuovi dati")
    else:
        print("\n✅ Dimensione OK per GitHub!")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()