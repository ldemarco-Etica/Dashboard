# applicazione/Home_improved.py

import streamlit as st
import logging
from datetime import datetime

# Import improved modules
from config import APP_CONFIG, DATA_PATHS
from utils import (
    data_loader, session_manager, create_info_box, format_date, trigger_hard_restart,
    hide_unauthorized_pages, display_user_info_sidebar, check_page_access, initialize_user_session,
    display_user_info_sidebar_auth0, hide_unauthorized_pages_auth0  # <-- AGGIUNTE QUESTE
)
from validators import ErrorHandler
from auth_manager import auth_manager  

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title=APP_CONFIG.page_title,
    page_icon=APP_CONFIG.page_icon,
    layout=APP_CONFIG.layout,
    initial_sidebar_state="expanded"
)

def display_main_content():
    """Display main dashboard content"""
    st.title(f"{APP_CONFIG.page_icon} {APP_CONFIG.page_title}")
    
    # Welcome section
    st.markdown("""
    ### 🎯 Benvenuto nella Dashboard di Analisi Portafoglio di Etica SGR
    
    Questa applicazione ti permette di analizzare in modo completo e interattivo 
    diversi aspetti dei portafogli di investimento con funzionalità avanzate di 
    monitoraggio e compliance.
    """)
    
    # Navigation info
    create_info_box(
        "📋 Come Navigare",
        "Utilizza il menu laterale per accedere alle diverse sezioni di analisi. "
        "Ogni sezione è completamente interattiva e personalizzabile con filtri avanzati.",
        "info"
    )
    
    # Features overview
    st.subheader("🚀 Funzionalità Disponibili")
    
    features = [
        {
            "title": "📊 AUM (Asset Under Management)",
            "description": "Analisi completa dello storico AUM con decomposizione delle variazioni, confronti tra fondi e analisi dei flussi netti.",
            "highlights": ["Serie storiche", "Decomposizione variazioni", "Confronti multi-fondo"]
        },
        {
            "title": "📈 TEV (Tracking Error Volatility)", 
            "description": "Monitoraggio del TEV rispetto ai limiti normativi, visualizzazioni a semaforo e analisi delle tendenze.",
            "highlights": ["Monitoraggio limiti", "Visualizzazione fasce", "Alert automatici"]
        },
        {
            "title": "⏳ Duration",
            "description": "Analisi della duration dei fondi con confronto benchmark e evoluzione temporale.",
            "highlights": ["Confronto con benchmark", "Serie storiche", "Analisi deviazioni"]
        },
        {
            "title": "🎯 Allocazioni di Portafoglio",
            "description": "Esplorazione dettagliata della composizione per settore, geografia, valuta e asset class.",
            "highlights": ["Snapshot interattivi", "Evoluzione temporale", "Drill-down dettagliato"]
        },
        {
            "title": "🔍 Analisi Singolo Titolo",
            "description": "Studio approfondito dell'andamento di singoli titoli con metriche avanzate e visualizzazioni dinamiche.",
            "highlights": ["Metriche di performance", "Analisi gap temporali", "Storico completo"]
        },
        {
            "title": "⚖️ Compliance Normativa",
            "description": "Sistema avanzato di monitoraggio automatico delle regole di compliance con dashboard dedicata.",
            "highlights": ["Controlli automatici", "Report dettagliati", "Alerting intelligente"]
        },
        {
            "title": "📋 Limiti Regolamentari",
            "description": "Monitoraggio comprehensive dei limiti CDA con visualizzazioni gauge e trend analysis.",
            "highlights": ["Dashboard limiti", "Visualizzazioni gauge", "Storico evoluzione"]
        }
    ]
    
    # Display features in columns
    for i in range(0, len(features), 2):
        col1, col2 = st.columns(2)
        
        with col1:
            if i < len(features):
                feature = features[i]
                with st.container():
                    st.markdown(f"#### {feature['title']}")
                    st.write(feature['description'])
                    
                    if feature['highlights']:
                        st.markdown("**Highlights:**")
                        for highlight in feature['highlights']:
                            st.markdown(f"• {highlight}")
        
        with col2:
            if i + 1 < len(features):
                feature = features[i + 1]
                with st.container():
                    st.markdown(f"#### {feature['title']}")
                    st.write(feature['description'])
                    
                    if feature['highlights']:
                        st.markdown("**Highlights:**")
                        for highlight in feature['highlights']:
                            st.markdown(f"• {highlight}")

def display_system_status():
    """Display system status and data information"""
    with st.expander("🔧 System Status & Data Info", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📁 Data Sources")
            
            data_sources = [
                ("Portfolio Data", DATA_PATHS.portfolios, "CSV files"),
                ("AUM Data", DATA_PATHS.aum, "Excel file"),
                ("TEV Data", DATA_PATHS.tev, "Excel file"),
                ("Duration Data", DATA_PATHS.duration, "Excel file")
            ]
            
            for name, path, file_type in data_sources:
                if path.exists():
                    st.success(f"✅ {name} ({file_type})")
                    try:
                        if path.is_file():
                            mod_time = datetime.fromtimestamp(path.stat().st_mtime)
                            st.caption(f"Last modified: {format_date(mod_time)}")
                        elif path.is_dir():
                            files = list(path.glob("*.csv" if "CSV" in file_type else "*.xlsx"))
                            st.caption(f"Files found: {len(files)}")
                    except Exception as e:
                        st.caption(f"Info not available: {e}")
                else:
                    st.error(f"❌ {name} - Path not found: {path}")
        
        with col2:
            st.subheader("💾 Session Info")
            
            # Session state information
            if 'data_loaded' in st.session_state and st.session_state['data_loaded']:
                st.success("✅ Data loaded in session")
                
                if 'last_update' in st.session_state and st.session_state['last_update']:
                    last_update = st.session_state['last_update']
                    if isinstance(last_update, str):
                        last_update = datetime.fromisoformat(last_update)
                    st.caption(f"Last data load: {format_date(last_update, '%d/%m/%Y %H:%M:%S')}")
                
                # Data statistics
                portfolio_data = st.session_state.get('portfolio_data')
                if portfolio_data is not None and not portfolio_data.empty:
                    st.info(f"📊 Portfolio records: {len(portfolio_data):,}")
                    
                    unique_funds = portfolio_data['Descrizione'].nunique() if 'Descrizione' in portfolio_data.columns else 0
                    st.info(f"📈 Unique funds: {unique_funds}")
                    
                    if 'DataRiferimento' in portfolio_data.columns:
                        date_range = portfolio_data['DataRiferimento'].agg(['min', 'max'])
                        st.info(f"📅 Date range: {format_date(date_range['min'])} - {format_date(date_range['max'])}")
            else:
                st.warning("⚠️ No data loaded in session")
            
            # Memory usage info
            try:
                import sys
                total_size = sum(sys.getsizeof(v) for v in st.session_state.values())
                st.caption(f"Session state size: {total_size / 1024 / 1024:.1f} MB")
            except:
                pass

def display_sidebar_controls():
    """Display sidebar controls"""
    with st.sidebar:
        st.header("🔧 System Controls")
        
        # Data loading section
        st.subheader("📊 Data Management")
        
        # Check if data is stale
        data_stale = session_manager.is_data_stale()
        
        if data_stale:
            st.warning("⚠️ Data may be outdated")
        
        # Load/Reload data button (Standard)
        if st.button("🔄 Refresh Data (Soft)", 
                    help="Aggiorna i dati senza riavviare l'app"):
            try:
                with st.spinner("Loading data..."):
                    loaded_data = data_loader.load_all_data_with_progress()
                    if loaded_data:
                        st.session_state['data_loaded'] = True
                        st.session_state['last_update'] = datetime.now().isoformat()
                        st.success("✅ Data loaded!")
                        st.rerun()
            except Exception as e:
                ErrorHandler.handle_data_loading_error(e, "manual data reload")
        
        # --- PULSANTE MODIFICATO: HARD RESET ---
        if st.button("🚀 Hard Reset & Azure Sync", 
                    help="FORZA il riavvio dell'app per leggere i nuovi file dal Blob Storage"):
            trigger_hard_restart()
        # ---------------------------------------
        
        st.divider()
        
        # Application info
        st.subheader("ℹ️ Application Info")
        
        info_data = {
            "Version": "2.0.1 (Auto-Sync)",
            "Last Auto-Restart": st.session_state.get("last_auto_restart", "Never"),
            "Cache TTL": f"{APP_CONFIG.cache_ttl // 3600}h"
        }
        
        for key, value in info_data.items():
            st.caption(f"**{key}:** {value}")
        
        st.divider()
        
        # Debug section (lasciata invariata come da tuo snippet)
        with st.expander("🐛 Auth Debug", expanded=False):
            st.json({
                'email': st.session_state.get('user_email', 'N/A'),
                'is_authenticated': st.session_state.get('is_authenticated', False),
                'last_restart_trigger': st.session_state.get('last_auto_restart', 'N/A')
            })
            
        # Help section
        st.subheader("❓ Help & Support")
        with st.expander("📚 Quick Help"):
            st.markdown("""
            **Risoluzione Problemi Dati:**
            Se i file nel Cloud sono aggiornati ma non li vedi:
            1. Usa il tasto **🚀 Hard Reset**.
            2. Il sistema si riavvia automaticamente alle **07:30** e **17:30**.
            """)

def main():
    """Main application entry point"""
    try:
        # --- LOGICA DI RIAVVIO PROGRAMMATO ---
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # Orari di riavvio (07:30 e 17:30)
        scheduled_times = ["07:30","11:40", "17:30"]
        
        # Usiamo una variabile di stato per evitare un loop infinito di riavvii nello stesso minuto
        if current_time in scheduled_times:
            if st.session_state.get("last_auto_restart") != current_time:
                st.session_state["last_auto_restart"] = current_time
                st.info(f"🔄 Riavvio programmato delle {current_time} in corso...")
                trigger_hard_restart()
        # ---------------------------------------
        # ============================================
        # 🔐 AUTENTICAZIONE AUTH0
        # ============================================

        
        # Gestisci callback Auth0
        query_params = st.query_params
        if 'code' in query_params:
            # Siamo in fase di callback dopo login
            with st.spinner("🔄 Completamento autenticazione..."):
                success = auth_manager.handle_callback(query_params)
                
                if success:
                    # Pulisci URL rimuovendo parametri callback
                    st.query_params.clear()
                    st.success("✅ Accesso effettuato con successo!")
                    st.rerun()
                else:
                    st.error("❌ Autenticazione fallita. Riprova.")
                    st.stop()
        
        # Verifica autenticazione
        if not auth_manager.is_authenticated():
            # Mostra pulsante login
            auth_manager.show_login_button()
            st.stop()
        
        # ============================================
        # 📊 UTENTE AUTENTICATO - Mostra Dashboard
        # ============================================
        
        # Inizializza session state
        session_manager.initialize_session_state()
        
        # Sidebar controls
        display_sidebar_controls()
        
        # ✅ CORREZIONE: Usa le funzioni Auth0
        display_user_info_sidebar_auth0()  
        hide_unauthorized_pages_auth0()    
        
        # Auto-load data (resto del codice rimane uguale...)
        if not st.session_state.get('data_loaded', False):
            with st.spinner("🚀 Initializing application..."):
                try:
                    loaded_data = data_loader.load_all_data_with_progress()
                    
                    if loaded_data and loaded_data.get('portfolio_data') is not None:
                        if not loaded_data['portfolio_data'].empty:
                            st.session_state['data_loaded'] = True
                            st.session_state['last_update'] = datetime.now().isoformat()
                            st.success("✅ Application initialized successfully!")
                        else:
                            st.warning("⚠️ Portfolio data is empty. Please check your data files.")
                    else:
                        st.error("❌ Failed to initialize application. Please check your data configuration.")
                        
                except Exception as e:
                    logger.error(f"Error in auto-initialization: {e}")
                    st.error(f"❌ Auto-initialization failed: {e}")
                    st.info("💡 Try using the 'Load/Reload All Data' button in the sidebar.")
        
        # Contenuto principale
        display_main_content()
        display_system_status()
        
        # Footer
        st.divider()
        st.markdown("""
        <div style="text-align: center; color: gray; font-size: 0.8em;">
            Dashboard di Analisi Portafoglio - Etica SGR | Versione 2.0 Migliorata
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        logger.error(f"Error in main application: {e}")
        st.error("❌ Application error occurred")
        
        with st.expander("🔍 Error Details"):
            st.error(f"Error: {e}")
            st.info("Try refreshing the page or clearing the cache.")
        
        if st.button("🆘 Emergency Reset"):
            session_manager.clear_cache_and_state()
            st.rerun()


if __name__ == "__main__":
    main()
