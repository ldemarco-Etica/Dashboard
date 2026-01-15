# applicazione/utils.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging

from data_repository import data_repository
from config import UI_CONFIG, APP_CONFIG
from validators import ErrorHandler, safe_percentage, safe_divide
from auth_config import get_user_role, get_user_permissions, can_access_page, is_valid_user
import hashlib
import hmac
from auth_manager import auth_manager

logger = logging.getLogger(__name__)

class DataLoadManager:
    """Centralized data loading with progress tracking and error handling"""
    
    def __init__(self):
        self.repository = data_repository
    
    def load_all_data_with_progress(self) -> Dict[str, Any]:
        """
        Load all data sources with progress tracking and comprehensive error handling
        
        Returns:
            Dictionary containing all loaded data
        """
        # ✅ AGGIORNATO: Aggiunto 'depositaria_data'
        data_sources = {
            'portfolio_data': 'Loading portfolio data...',
            'depositaria_data': 'Loading depositaria data...',  # ← NUOVO
            'aum_data': 'Loading AUM data...',
            'tev_data': 'Loading TEV data...',
            'fasce_data': 'Loading TEV bands data...',
            'duration_data': 'Loading duration data...',
            'limiti_data': 'Loading CDA limits data...'
        }
        
        loaded_data = {}
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_sources = len(data_sources)
        
        try:
            for i, (data_key, status_msg) in enumerate(data_sources.items()):
                try:
                    status_text.text(status_msg)
                    
                    if data_key == 'portfolio_data':
                        loaded_data[data_key] = self.repository.load_portfolio_data()
                    # ✅ AGGIUNTO: Caricamento depositaria
                    elif data_key == 'depositaria_data':
                        loaded_data[data_key] = self.repository.load_depositaria_data()
                    elif data_key == 'aum_data':
                        aum_total, aum_funds = self.repository.load_aum_data()
                        loaded_data['aum_data'] = aum_total
                        loaded_data['aum_fondi'] = aum_funds
                    elif data_key == 'tev_data':
                        loaded_data[data_key] = self.repository.load_tev_data()
                    elif data_key == 'fasce_data':
                        loaded_data[data_key] = self.repository.load_fasce_data()
                    elif data_key == 'duration_data':
                        loaded_data[data_key] = self.repository.load_duration_data()
                    elif data_key == 'limiti_data':
                        loaded_data[data_key] = self.repository.load_limiti_cda()

                    
                    progress_bar.progress((i + 1) / total_sources)
                    
                except Exception as e:
                    logger.error(f"Error loading {data_key}: {e}")
                    loaded_data[data_key] = pd.DataFrame() if 'fondi' not in data_key else {}
                    st.warning(f"⚠️ Failed to load {data_key}: {e}")
            
            progress_bar.empty()
            status_text.empty()
            
            # Validate critical data
            portfolio_data = loaded_data.get('portfolio_data', pd.DataFrame())
            if portfolio_data.empty:
                st.error("❌ Critical: Portfolio data could not be loaded. Please check your data files.")
                return loaded_data
            
            # Get data date range for info
            try:
                min_date = portfolio_data['DataRiferimento'].min()
                max_date = portfolio_data['DataRiferimento'].max()
                
                st.success("✅ Data loading completed successfully!")
                st.info(f"📅 Data available from {format_date(min_date)} to {format_date(max_date)}")
                
            except Exception as e:
                st.success("✅ Data loading completed successfully!")
                logger.warning(f"Could not determine date range: {e}")
            
            # Store in session state
            for key, value in loaded_data.items():
                st.session_state[key] = value
            
            return loaded_data
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            ErrorHandler.handle_data_loading_error(e, "data loading process")
            return {}

class UIComponents:
    """Reusable UI components and utilities"""
    
    @staticmethod
    def create_date_filter_sidebar(portfolio_data: pd.DataFrame, 
                                  fund_name: Optional[str] = None,
                                  key_prefix: str = "default") -> Tuple[datetime, datetime]:
        """
        Create standardized date filter in sidebar
        
        Args:
            portfolio_data: Portfolio DataFrame
            fund_name: Optional fund name for filtering
            key_prefix: Prefix for widget keys to avoid conflicts
            
        Returns:
            Tuple of (start_date, end_date)
        """
        try:
            min_date, max_date = data_repository.get_date_range(portfolio_data, fund_name)
            
            preset = st.sidebar.selectbox(
                "📅 Periodo predefinito",
                ["Tutto", "Ultimi 3 mesi", "Ultimi 6 mesi", "Ultimo anno", "YTD", "Personalizzato"],
                key=f"{key_prefix}_period"
            )
            
            today = max_date
            if preset == "Ultimi 3 mesi":
                start_date, end_date = today - timedelta(days=90), today
            elif preset == "Ultimi 6 mesi":
                start_date, end_date = today - timedelta(days=180), today
            elif preset == "Ultimo anno":
                start_date, end_date = today - timedelta(days=365), today
            elif preset == "YTD":
                start_date, end_date = datetime(year=today.year, month=1, day=1), today
            elif preset == "Tutto":
                start_date, end_date = min_date, max_date
            else:  # Personalizzato
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    start_date = st.date_input(
                        "Da:",
                        value=min_date,
                        min_value=min_date,
                        max_value=max_date,
                        key=f"{key_prefix}_start"
                    )
                with col2:
                    end_date = st.date_input(
                        "A:",
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date,
                        key=f"{key_prefix}_end"
                    )
                
                start_date = datetime.combine(start_date, datetime.min.time())
                end_date = datetime.combine(end_date, datetime.min.time())
            
            return start_date, end_date
            
        except Exception as e:
            logger.error(f"Error creating date filter: {e}")
            today = datetime.now()
            return today - timedelta(days=365), today
    
    @staticmethod
    def create_fund_selector(portfolio_data: pd.DataFrame, 
                            label: str = "📈 Seleziona Fondo:",
                            key: str = "fund_selector") -> str:
        """Create standardized fund selector"""
        try:
            available_funds = data_repository.get_available_funds(portfolio_data)
            
            if not available_funds:
                st.error("❌ No funds available in the data")
                return ""
            
            selected_fund = st.sidebar.selectbox(
                label,
                available_funds,
                key=key
            )
            
            return selected_fund
            
        except Exception as e:
            logger.error(f"Error creating fund selector: {e}")
            st.error(f"Error in fund selector: {e}")
            return ""
    
    @staticmethod
    def display_metrics_grid(metrics: Dict[str, Union[str, float]], 
                            columns: int = 4) -> None:
        """Display metrics in a grid layout"""
        try:
            cols = st.columns(columns)
            
            for i, (label, value) in enumerate(metrics.items()):
                with cols[i % columns]:
                    if isinstance(value, float):
                        if abs(value) < 1000:
                            st.metric(label, f"{value:.2f}")
                        else:
                            st.metric(label, f"{value:,.0f}")
                    else:
                        st.metric(label, str(value))
                        
        except Exception as e:
            logger.error(f"Error displaying metrics: {e}")
            st.error("Error displaying metrics")
    
    @staticmethod
    def display_compliance_status(compliance_results: List[Any]) -> None:
        """Display compliance status with color coding"""
        try:
            if not compliance_results:
                st.warning("No compliance data available")
                return
            
            total_rules = len(compliance_results)
            compliant_rules = sum(1 for r in compliance_results if getattr(r, 'is_compliant', True))
            non_compliant_rules = total_rules - compliant_rules
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📊 Total Rules", total_rules)
            with col2:
                st.metric("✅ Compliant", compliant_rules, 
                         delta=None if compliant_rules == total_rules else f"{compliant_rules}/{total_rules}")
            with col3:
                st.metric("❌ Non-Compliant", non_compliant_rules,
                         delta=None if non_compliant_rules == 0 else f"-{non_compliant_rules}")
            
            # Progress bar for compliance rate
            compliance_rate = safe_percentage(compliant_rules, total_rules)
            
            color = "normal"
            if compliance_rate == 100:
                color = "normal"  # Green
            elif compliance_rate >= 80:
                color = "normal"  # Yellow would be nice but not available
            else:
                color = "inverse"  # Red
            
            st.progress(compliance_rate / 100)
            st.write(f"**Compliance Rate: {compliance_rate:.1f}%**")
            
        except Exception as e:
            logger.error(f"Error displaying compliance status: {e}")
            st.error("Error displaying compliance status")

class ChartFactory:
    """Factory class for creating standardized charts"""
    
    @staticmethod
    def create_pie_chart(data: pd.DataFrame,
                        values_col: str,
                        names_col: str,
                        title: str = "",
                        color_sequence: Optional[List[str]] = None,
                        custom_hover_col: Optional[str] = None) -> go.Figure:
        """Create standardized pie chart"""
        try:
            fig = px.pie(
                data,
                values=values_col,
                names=names_col,
                title=title,
                color_discrete_sequence=color_sequence,
                custom_data=[custom_hover_col] if custom_hover_col else None
            )
    
            if custom_hover_col:
                hovertemplate = '<b>%{label}</b><br>Peso Reale: %{customdata[0]:.2f}%<extra></extra>'
            else:
                hovertemplate = '<b>%{label}</b><br>Peso: %{value:.2f}%<extra></extra>'
    
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate=hovertemplate
            )
    
            fig.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
    
            return fig
    
        except Exception as e:
            logger.error(f"Error creating pie chart: {e}")
            return go.Figure().add_annotation(
                text=f"Error creating chart: {e}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
    
    @staticmethod
    def create_bar_chart(data: pd.DataFrame,
                        x_col: str,
                        y_col: str,
                        title: str = "",
                        color_col: Optional[str] = None,
                        orientation: str = 'v') -> go.Figure:
        """Create standardized bar chart"""
        try:
            if orientation == 'v':
                fig = px.bar(
                    data, 
                    x=x_col, 
                    y=y_col, 
                    title=title,
                    color=color_col or y_col,
                    color_continuous_scale='viridis'
                )
            else:
                fig = px.bar(
                    data, 
                    x=y_col, 
                    y=x_col, 
                    title=title,
                    color=color_col or y_col,
                    color_continuous_scale='viridis',
                    orientation='h'
                )
            
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>Value: %{y:.2f}%<extra></extra>'
            )
            
            fig.update_layout(
                xaxis_tickangle=-45,
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating bar chart: {e}")
            return go.Figure().add_annotation(
                text=f"Error creating chart: {e}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
    
    @staticmethod
    def create_line_chart(data: pd.DataFrame,
                         x_col: str,
                         y_col: Union[str, List[str]],
                         title: str = "",
                         markers: bool = True,
                         color: str = None) -> go.Figure:
        """Create standardized line chart"""
        try:
            if isinstance(y_col, str):
                y_col = [y_col]
            
            fig = px.line(
                data,
                x=x_col,
                y=y_col,
                title=title,
                markers=markers,
                color=color
            )
            
            fig.update_layout(
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating line chart: {e}")
            return go.Figure().add_annotation(
                text=f"Error creating chart: {e}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
    
    @staticmethod
    def create_gauge_chart(current_value: float,
                          min_limit: Optional[float] = None,
                          max_limit: Optional[float] = None,
                          title: str = "",
                          unit: str = "%") -> go.Figure:
        """Create gauge chart for limits monitoring"""
        try:
            # Determine gauge range
            if min_limit is not None and max_limit is not None:
                gauge_min = max(0, min_limit - 10)
                gauge_max = max_limit + 10
            elif max_limit is not None:
                gauge_min = 0
                gauge_max = max_limit + 10
            elif min_limit is not None:
                gauge_min = max(0, min_limit - 10)
                gauge_max = min_limit + 20
            else:
                gauge_min = 0
                gauge_max = 100
            
            # Determine color based on compliance
            color = "green"
            if min_limit is not None and current_value < min_limit:
                color = "red"
            elif max_limit is not None and current_value > max_limit:
                color = "red"
            
            # Create colored steps
            steps = []
            if min_limit is not None:
                steps.append(dict(range=[gauge_min, min_limit], color="lightgray"))
                if max_limit is not None:
                    steps.append(dict(range=[min_limit, max_limit], color="lightgreen"))
                    steps.append(dict(range=[max_limit, gauge_max], color="lightcoral"))
                else:
                    steps.append(dict(range=[min_limit, gauge_max], color="lightgreen"))
            elif max_limit is not None:
                steps.append(dict(range=[gauge_min, max_limit], color="lightgreen"))
                steps.append(dict(range=[max_limit, gauge_max], color="lightcoral"))
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=current_value,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': title},
                number={'suffix': unit},
                gauge={
                    'axis': {'range': [gauge_min, gauge_max]},
                    'bar': {'color': color},
                    'steps': steps,
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': max_limit if max_limit else min_limit
                    }
                }
            ))
            
            fig.update_layout(height=300)
            return fig
            
        except Exception as e:
            logger.error(f"Error creating gauge chart: {e}")
            return go.Figure().add_annotation(
                text=f"Error creating gauge: {e}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )

class DataExporter:
    """Utilities for data export"""
    
    @staticmethod
    def to_excel_download(data: Union[pd.DataFrame, Dict[str, pd.DataFrame]], 
                         filename: str = "export.xlsx") -> bytes:
        """Convert DataFrame(s) to Excel download"""
        try:
            from io import BytesIO
            import xlsxwriter
            
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                if isinstance(data, pd.DataFrame):
                    data.to_excel(writer, sheet_name='Data', index=False)
                elif isinstance(data, dict):
                    for sheet_name, df in data.items():
                        if isinstance(df, pd.DataFrame) and not df.empty:
                            df.to_excel(writer, sheet_name=sheet_name[:30], index=False)
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating Excel export: {e}")
            raise e
    
    @staticmethod
    def create_download_button(data: Union[pd.DataFrame, Dict[str, pd.DataFrame]], 
                              filename: str,
                              button_text: str = "📥 Download Excel",
                              key: Optional[str] = None) -> None:
        """Create download button for data"""
        try:
            excel_data = DataExporter.to_excel_download(data, filename)
            
            st.download_button(
                label=button_text,
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=key
            )
            
        except Exception as e:
            logger.error(f"Error creating download button: {e}")
            st.error(f"Error creating download: {e}")

class SessionStateManager:
    """Manage Streamlit session state efficiently"""
    
    @staticmethod
    def initialize_session_state():
        """Initialize session state with default values"""
        # ✅ AGGIORNATO: Aggiunto 'depositaria_data'
        defaults = {
            'data_loaded': False,
            'portfolio_data': pd.DataFrame(),
            'depositaria_data': pd.DataFrame(),  # ← NUOVO
            'aum_data': pd.DataFrame(),
            'aum_fondi': {},
            'tev_data': pd.DataFrame(),
            'fasce_data': pd.DataFrame(),
            'duration_data': pd.DataFrame(),
            'limiti_data': pd.DataFrame(),
            'last_update': None,
            'user_preferences': {}
        }
        
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    @staticmethod
    def clear_cache_and_state():
        """Clear cache and reset session state"""
        # Clear Streamlit cache
        st.cache_data.clear()
        
        # Reset session state
        for key in list(st.session_state.keys()):
            if key not in ['user_preferences']:  # Keep user preferences
                del st.session_state[key]
        
        SessionStateManager.initialize_session_state()
        st.success("🗑️ Cache and session state cleared!")
    
    @staticmethod
    def is_data_stale(max_age_hours: int = 24) -> bool:
        """Check if data is stale and needs refresh"""
        if 'last_update' not in st.session_state or st.session_state['last_update'] is None:
            return True
        
        last_update = st.session_state['last_update']
        if isinstance(last_update, str):
            last_update = datetime.fromisoformat(last_update)
        
        return datetime.now() - last_update > timedelta(hours=max_age_hours)

def format_number(value: Union[int, float], 
                 format_type: str = "auto",
                 decimal_places: int = 2) -> str:
    """Format numbers for display"""
    try:
        if pd.isna(value):
            return "N/A"
        
        if format_type == "percentage":
            return f"{value:.{decimal_places}f}%"
        elif format_type == "currency":
            return f"€{value:,.{decimal_places}f}"
        elif format_type == "number":
            if abs(value) >= 1_000_000:
                return f"{value/1_000_000:.1f}M"
            elif abs(value) >= 1_000:
                return f"{value/1_000:.1f}K"
            else:
                return f"{value:.{decimal_places}f}"
        else:  # auto
            if isinstance(value, int):
                return f"{value:,}"
            else:
                return f"{value:.{decimal_places}f}"
                
    except Exception as e:
        logger.error(f"Error formatting number {value}: {e}")
        return str(value)

def format_date(date: Union[datetime, pd.Timestamp, str], 
               format_str: str = UI_CONFIG.DATE_FORMAT) -> str:
    """Format dates for display"""
    try:
        if isinstance(date, str):
            date = pd.to_datetime(date)
        elif isinstance(date, pd.Timestamp):
            date = date.to_pydatetime()
        
        return date.strftime(format_str)
        
    except Exception as e:
        logger.error(f"Error formatting date {date}: {e}")
        return str(date)

def create_info_box(title: str, content: str, box_type: str = "info") -> None:
    """Create styled info box"""
    color_map = {
        "info": "blue",
        "success": "green", 
        "warning": "orange",
        "error": "red"
    }
    
    color = color_map.get(box_type, "blue")
    
    st.markdown(f"""
    <div style="
        padding: 1rem;
        border-left: 5px solid {color};
        background-color: rgba(0,0,0,0.05);
        border-radius: 5px;
        margin: 1rem 0;
    ">
        <h4 style="margin: 0 0 0.5rem 0; color: {color};">{title}</h4>
        <p style="margin: 0;">{content}</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================
# AUTENTICAZIONE CON LOGIN MANUALE
# ============================================

def create_session_token(email: str) -> str:
    """Crea un token di sessione sicuro"""
    try:
        secret = st.secrets.get('auth', {}).get('session_secret', 'default_secret')
        timestamp = datetime.now().isoformat()
        message = f"{email}:{timestamp}"
        token = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        return token
    except Exception:
        return hashlib.sha256(f"{email}:{datetime.now()}".encode()).hexdigest()

def show_login_form():
    """Mostra form di login con verifica password"""
    from auth_config import verify_password, get_user_role, get_user_permissions
    
    st.markdown("### 🔐 Autenticazione Richiesta")
    st.info("Inserisci le tue credenziali per accedere alla dashboard.")
    
    with st.form("login_form"):
        email = st.text_input(
            "Email",
            placeholder="nome.cognome@eticasgr.it",
            help="Email aziendale registrata"
        )
        
        password = st.text_input(
            "Password",
            type="password",
            help="Password personale"
        )
        
        submitted = st.form_submit_button("🔓 Accedi", type="primary")
        
        if submitted:
            if not email or '@' not in email:
                st.error("❌ Inserisci un'email valida")
                return None
            
            if not password:
                st.error("❌ Inserisci la password")
                return None
            
            email = email.lower().strip()
            
            # Verifica credenziali
            if verify_password(email, password):
                # Crea sessione
                st.session_state['user_email'] = email
                st.session_state['user_role'] = get_user_role(email)
                st.session_state['user_permissions'] = get_user_permissions(email)
                st.session_state['is_authenticated'] = True
                st.session_state['auth_initialized'] = True
                st.session_state['is_dev_mode'] = False
                st.session_state['session_token'] = create_session_token(email)
                st.session_state['login_time'] = datetime.now()
                
                st.success(f"✅ Accesso effettuato come **{st.session_state['user_role'].upper()}**")
                st.rerun()
            else:
                st.error("❌ Credenziali non valide")
                st.caption(f"Email inserita: `{email}`")
                return None
    
    return None

def check_session_validity():
    """Verifica se la sessione è ancora valida (timeout dopo 8 ore)"""
    if 'login_time' not in st.session_state:
        return False
    
    login_time = st.session_state['login_time']
    if datetime.now() - login_time > timedelta(hours=8):
        return False
    
    return True

def initialize_user_session():
    """
    Inizializza la sessione utente con login form
    """
    # Se già autenticato e sessione valida, skip
    if st.session_state.get('auth_initialized', False) and check_session_validity():
        return True
    
    # Reset se sessione scaduta
    if st.session_state.get('auth_initialized', False) and not check_session_validity():
        st.warning("⏰ Sessione scaduta. Effettua nuovamente il login.")
        for key in ['user_email', 'user_role', 'user_permissions', 'is_authenticated', 
                    'auth_initialized', 'session_token', 'login_time']:
            if key in st.session_state:
                del st.session_state[key]
    
    # Mostra form di login
    show_login_form()
    
    # Se non autenticato, blocca
    if not st.session_state.get('is_authenticated', False):
        st.stop()
    
    return True

def logout():
    """Effettua logout"""
    for key in ['user_email', 'user_role', 'user_permissions', 'is_authenticated',
                'auth_initialized', 'session_token', 'login_time', 'is_dev_mode']:
        if key in st.session_state:
            del st.session_state[key]
    st.success("✅ Logout effettuato")
    st.rerun()

def display_user_info_sidebar():
    """Mostra informazioni utente nella sidebar con pulsante logout"""
    
    if 'user_email' not in st.session_state:
        return
    
    with st.sidebar:
        st.divider()
        st.markdown("### 👤 Info Utente")
        
        user_email = st.session_state['user_email']
        user_role = st.session_state['user_role']
        
        # Emoji per ruolo
        role_emoji = {
            'admin': '👑',
            'analyst': '📊',
            'viewer': '👁️'
        }
        
        st.write(f"{role_emoji.get(user_role, '👤')} **Ruolo:** {user_role.upper()}")
        st.caption(f"📧 {user_email}")
        
        # Tempo di sessione
        if 'login_time' in st.session_state:
            elapsed = datetime.now() - st.session_state['login_time']
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            st.caption(f"⏱️ Sessione: {hours}h {minutes}m")
        
        # Mostra pagine accessibili
        with st.expander("📄 Pagine Accessibili"):
            permissions = st.session_state.get('user_permissions', [])
            for page in permissions:
                st.write(f"✅ {page}")
        
        # Pulsante logout
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            logout()

def check_page_access(page_name: str) -> bool:
    """Verifica se l'utente corrente può accedere alla pagina"""
    # Assicura inizializzazione
    if 'auth_initialized' not in st.session_state or not st.session_state['auth_initialized']:
        st.error("⛔ Sessione non inizializzata. Torna alla Home.")
        st.stop()
        return False
    
    # Verifica validità sessione
    if not check_session_validity():
        st.error("⏰ Sessione scaduta. Torna alla Home per effettuare nuovamente il login.")
        st.stop()
        return False
    
    user_email = st.session_state.get('user_email')
    user_permissions = st.session_state.get('user_permissions', [])
    
    # Se la pagina è accessibile, ritorna True
    if page_name in user_permissions:
        return True
    
    # ACCESSO NEGATO
    st.error(f"⛔ **Accesso Negato alla Pagina: {page_name}**")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.info(f"""
        **👤 Il Tuo Profilo:**
        - Email: `{user_email}`
        - Ruolo: **{st.session_state.get('user_role', 'Non definito').upper()}**
        """)
    
    with col2:
        st.success(f"""
        **✅ Pagine Accessibili:**
        {chr(10).join(['• ' + p for p in user_permissions])}
        """)
    
    st.markdown("---")
    st.caption("💡 Contatta l'amministratore per richiedere accesso a questa pagina.")
    
    if st.button("🏠 Torna alla Home"):
        st.switch_page("Home.py")
    
    st.stop()
    return False

def hide_unauthorized_pages():
    """Nasconde pagine non autorizzate dalla sidebar"""
    if 'user_permissions' not in st.session_state:
        return
    
    page_mapping = {
        'AUM': 'AUM',
        'TEV': 'TEV',
        'Duration': 'Duration',
        'Allocazioni': 'Allocazioni',
        'Analisi titoli': 'Analisi titoli',
        'Lookthrough': 'Lookthrough',
        'Movimentazioni': 'Movimentazioni',
        'Limiti Regolamentari': 'Limiti Regolamentari',
        'Limiti da CDA': 'Limiti da CDA',
        'Turnover': 'Turnover'
    }
    
    allowed = st.session_state['user_permissions']
    
    pages_to_hide = [
        page_name for page_name in page_mapping.keys()
        if page_name not in allowed
    ]
    
    if not pages_to_hide:
        return
    
    css = """
    <style>
    """
    
    for page_name in pages_to_hide:
        page_variants = [
            page_name,
            page_name.replace(' ', '_'),
            page_name.replace(' ', '%20'),
            page_name.replace(' ', '-').lower()
        ]
        
        for variant in page_variants:
            css += f"""
    section[data-testid="stSidebar"] a[href*="{variant}"] {{
        display: none !important;
    }}
    """
    
    css += """
    </style>
    """
    
    st.markdown(css, unsafe_allow_html=True)



def display_user_info_sidebar_auth0():
    """Mostra info utente Auth0 con logout"""
    user_info = auth_manager.get_user_info()
    
    if not user_info:
        return
    
    with st.sidebar:
        st.divider()
        st.markdown("### 👤 Info Utente")
        
        role_emoji = {
            'admin': '👑',
            'analyst': '📊',
            'viewer': '👁️'
        }
        
        user_role = user_info['role']
        st.write(f"{role_emoji.get(user_role, '👤')} **Ruolo:** {user_role.upper()}")
        st.caption(f"📧 {user_info['email']}")
        
        # Tempo sessione
        if user_info['login_time']:
            elapsed = datetime.now() - user_info['login_time']
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            st.caption(f"⏱️ Sessione: {hours}h {minutes}m")
        
        # Pagine accessibili
        with st.expander("📄 Pagine Accessibili"):
            for page in user_info['permissions']:
                st.write(f"✅ {page}")
        
        # Pulsante logout
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            auth_manager.logout()


def check_page_access_auth0(page_name: str) -> bool:
    """Verifica accesso pagina con Auth0"""
   
    if not auth_manager.is_authenticated():
        st.error("⛔ Sessione non valida. Torna alla Home per autenticarti.")
        if st.button("🏠 Vai alla Home"):
            st.switch_page("Home.py")
        st.stop()
        return False
    
    if not auth_manager.can_access_page(page_name):
        user_info = auth_manager.get_user_info()
        
        st.error(f"⛔ **Accesso Negato alla Pagina: {page_name}**")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.info(f"""
            **👤 Il Tuo Profilo:**
            - Email: `{user_info['email']}`
            - Ruolo: **{user_info['role'].upper()}**
            """)
        
        with col2:
            st.success(f"""
            **✅ Pagine Accessibili:**
            {chr(10).join(['• ' + p for p in user_info['permissions']])}
            """)
        
        if st.button("🏠 Torna alla Home"):
            st.switch_page("Home.py")
        
        st.stop()
        return False
    
    return True


def hide_unauthorized_pages_auth0():
    """Nasconde pagine non autorizzate (Auth0 version)"""
    
    if not auth_manager.is_authenticated():
        return
    
    user_info = auth_manager.get_user_info()
    allowed = user_info.get('permissions', [])
    
    page_mapping = {
        'AUM': 'AUM',
        'TEV': 'TEV',
        'Duration': 'Duration',
        'Allocazioni': 'Allocazioni',
        'Analisi titoli': 'Analisi titoli',
        'Lookthrough': 'Lookthrough',
        'Movimentazioni': 'Movimentazioni',
        'Limiti Regolamentari': 'Limiti Regolamentari',
        'Limiti da CDA': 'Limiti da CDA',
        'Turnover': 'Turnover'
    }
    
    pages_to_hide = [
        page_name for page_name in page_mapping.keys()
        if page_name not in allowed
    ]
    
    if not pages_to_hide:
        return
    
    css = "<style>"
    for page_name in pages_to_hide:
        page_variants = [
            page_name,
            page_name.replace(' ', '_'),
            page_name.replace(' ', '%20'),
            page_name.replace(' ', '-').lower()
        ]
        
        for variant in page_variants:
            css += f"""
    section[data-testid="stSidebar"] a[href*="{variant}"] {{
        display: none !important;
    }}
    """
    
    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)


# Global instances
data_loader = DataLoadManager()
ui_components = UIComponents()
chart_factory = ChartFactory()
data_exporter = DataExporter()
session_manager = SessionStateManager()
