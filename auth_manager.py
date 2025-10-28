#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTH MANAGER - Auth0 Integration FIXED v2
==========================================
FIX: Usa URL parameter invece di session_state per lo state
"""

import streamlit as st
import requests
import jwt
from urllib.parse import urlencode, quote_plus, parse_qs
from datetime import datetime, timedelta
import logging
import traceback
from typing import Optional, Dict, Any
import secrets

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class Auth0Manager:
    """Gestisce autenticazione Auth0 con state persistente via URL"""
    
    def __init__(self):
        logger.info("=" * 70)
        logger.info("INIZIALIZZAZIONE AUTH0MANAGER")
        logger.info("=" * 70)
        
        try:
            # Configurazione Auth0
            self.domain = st.secrets["auth0"]["domain"]
            self.client_id = st.secrets["auth0"]["client_id"]
            self.client_secret = st.secrets["auth0"]["client_secret"]
            
            # ✅ FIX: Rimuovi trailing slash
            callback = st.secrets["auth0"]["callback_url"]
            self.callback_url = callback.rstrip("/")
            
            logger.info(f"Domain: {self.domain}")
            logger.info(f"Client ID: {self.client_id}")
            logger.info(f"Callback URL: {self.callback_url}")
            
            # Configurazione sessione
            self.session_secret = st.secrets["session"]["secret_key"]
            
            # Mapping ruoli
            self.role_permissions = {
                'admin': st.secrets["roles"]["admin"],
                'analyst': st.secrets["roles"]["analyst"],
                'viewer': st.secrets["roles"]["viewer"]
            }
            
            # URLs
            self.authorization_endpoint = f"https://{self.domain}/authorize"
            self.token_endpoint = f"https://{self.domain}/oauth/token"
            self.userinfo_endpoint = f"https://{self.domain}/userinfo"
            self.logout_endpoint = f"https://{self.domain}/v2/logout"
            
            logger.info("✅ Inizializzazione completata")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"❌ ERRORE CRITICO: {e}")
            traceback.print_exc()
            st.error("⚠️ Configurazione Auth0 mancante")
            st.stop()
    
    def get_authorization_url(self) -> str:
            """
            Genera URL di login con state JWT STATLESS
            ✅ FIX: Usa un JWT come state invece di st.session_state
            """
            try:
                # Crea un payload per lo state JWT
                payload = {
                    'iat': datetime.now().timestamp(),
                    'exp': (datetime.now() + timedelta(minutes=5)).timestamp(),
                    'aud': self.client_id
                }
                
                # Codifica lo state usando il session_secret
                state = jwt.encode(
                    payload, 
                    self.session_secret, 
                    algorithm='HS256'
                )
                
                logger.info(f"🆕 Nuovo state JWT generato: {state[:30]}...")
                
                params = {
                    'response_type': 'code',
                    'client_id': self.client_id,
                    'redirect_uri': self.callback_url,
                    'scope': 'openid profile email',
                    'state': state  # Usa il JWT come state
                }
                
                url = f"{self.authorization_endpoint}?{urlencode(params)}"
                logger.info(f"🔗 URL di login: {url}")
                
                return url
                
            except Exception as e:
                logger.error(f"❌ Errore generazione URL/state: {e}")
                st.error("Errore durante la preparazione del login.")
                return "#"
        
    def handle_callback(self, query_params: Dict[str, Any]) -> bool:
            """
            Gestisce il callback di Auth0
            ✅ FIX: Valida lo state JWT invece di cercarlo in session_state
            """
            logger.info("=" * 70)
            logger.info("HANDLE CALLBACK")
            logger.info("=" * 70)
            
            try:
                # 1. Verifica state JWT
                received_state = query_params.get('state')
                logger.info(f"State ricevuto: {received_state[:30] if received_state else 'None'}...")
                
                if not received_state:
                    logger.error("❌ State mancante nella query")
                    st.error("⚠️ Parametro state mancante")
                    return False
                
                try:
                    # Tenta di decodificare lo state
                    jwt.decode(
                        received_state,
                        self.session_secret,
                        algorithms=['HS256'],
                        audience=self.client_id
                    )
                    logger.info("✅ State JWT valido e verificato")
                
                except jwt.ExpiredSignatureError:
                    logger.error("❌ STATE JWT SCADUTO")
                    st.error("⚠️ Richiesta di login scaduta. Riprova.")
                    return False
                except jwt.InvalidTokenError as e:
                    logger.error(f"❌ STATE JWT INVALIDO: {e}")
                    st.error("⚠️ Errore di sicurezza: state non valido. Riprova.")
                    return False
                
                # 2. Ottieni code
                code = query_params.get('code')
                logger.info(f"Authorization code: {code[:30] if code else 'None'}...")
                
                if not code:
                    logger.error("❌ Code mancante")
                    st.error("⚠️ Codice di autorizzazione mancante")
                    return False
                
                # 3. Scambia code per token
                logger.info("🔄 Scambio code per token...")
                token_data = self._exchange_code_for_token(code)
                
                if not token_data:
                    logger.error("❌ Token exchange fallito")
                    return False
                
                logger.info("✅ Token ricevuto")
                
                # 4. Decodifica ID token
                user_info = self._decode_token(token_data['id_token'])
                
                if not user_info:
                    logger.error("❌ Decodifica token fallita")
                    return False
                
                # 5. Estrai email e ruoli
                namespace = 'https://eticasgr.it'
                email = user_info.get('email') or user_info.get(f'{namespace}/email')
                roles = user_info.get(f'{namespace}/roles', [])
                
                logger.info(f"✅ Utente autenticato: {email} ({roles})")
                
                # 6. Salva sessione (ora che siamo nella Sessione B)
                self._save_session(user_info, token_data)
                
                # Pulisci solo le chiavi di stato residue (se presenti)
                keys_to_delete = [k for k in st.session_state.keys() if k.startswith('auth_state_')]
                for key in keys_to_delete:
                    st.session_state.pop(key, None)
                st.session_state.pop('current_state_key', None)
                
                logger.info("🗑️  State legacy pulito dopo login")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Eccezione in handle_callback: {e}")
                traceback.print_exc()
                st.error(f"⚠️ Errore durante autenticazione: {e}")
                return False
        
    # ✅ Resto del codice INVARIATO
    def _exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Scambia authorization code per access token"""
        logger.info("-" * 70)
        logger.info("SCAMBIO CODE → TOKEN")
        logger.info("-" * 70)
        
        try:
            payload = {
                'grant_type': 'authorization_code',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'redirect_uri': self.callback_url
            }
            
            logger.info(f"Endpoint: {self.token_endpoint}")
            logger.info(f"Redirect URI: {self.callback_url}")
            
            response = requests.post(
                self.token_endpoint,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=15
            )
            
            logger.info(f"Status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ Auth0 error {response.status_code}")
                logger.error(f"Response: {response.text}")
                st.error(f"⚠️ Auth0 ha rifiutato la richiesta: {response.status_code}")
                with st.expander("🔍 Dettagli Errore"):
                    st.code(response.text)
                return None
            
            token_data = response.json()
            logger.info("✅ Token ricevuto con successo")
            return token_data
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Errore connessione: {e}")
            st.error("⚠️ Impossibile connettersi ad Auth0")
            return None
        except Exception as e:
            logger.error(f"❌ Eccezione: {e}")
            traceback.print_exc()
            return None
    
    def _decode_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Decodifica e valida ID token"""
        logger.info("-" * 70)
        logger.info("DECODIFICA ID TOKEN")
        logger.info("-" * 70)
        
        try:
            jwks_url = f"https://{self.domain}/.well-known/jwks.json"
            logger.info(f"JWKS URL: {jwks_url}")
            
            jwks_client = jwt.PyJWKClient(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            
            decoded = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f"https://{self.domain}/"
            )
            
            logger.info("✅ Token decodificato con successo")
            return decoded
            
        except jwt.ExpiredSignatureError:
            logger.error("❌ Token scaduto")
            st.warning("⚠️ Token scaduto")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ Token invalido: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Errore decodifica: {e}")
            traceback.print_exc()
            return None
    
    def _save_session(self, user_info: Dict[str, Any], token_data: Dict[str, Any]):
        """Salva dati utente in session_state"""
        namespace = 'https://eticasgr.it'
        roles = user_info.get(f'{namespace}/roles', [])
        email = user_info.get(f'{namespace}/email') or user_info.get('email')
        user_role = roles[0] if roles else 'viewer'
        
        st.session_state['auth0_authenticated'] = True
        st.session_state['user_email'] = email
        st.session_state['user_role'] = user_role
        st.session_state['user_permissions'] = self.role_permissions.get(user_role, [])
        st.session_state['access_token'] = token_data.get('access_token')
        st.session_state['id_token'] = token_data.get('id_token')
        st.session_state['login_time'] = datetime.now()
        st.session_state['token_expiry'] = datetime.now() + timedelta(
            seconds=token_data.get('expires_in', 3600)
        )
        st.session_state['auth_initialized'] = True
        
        logger.info(f"💾 Sessione salvata: {email} ({user_role})")
    
    def is_authenticated(self) -> bool:
        """Verifica se l'utente è autenticato"""
        if not st.session_state.get('auth0_authenticated', False):
            return False
        
        # Verifica scadenza token
        token_expiry = st.session_state.get('token_expiry')
        if token_expiry and datetime.now() > token_expiry:
            logger.warning("⏰ Token scaduto")
            self.logout()
            return False
        
        return True
    
    def get_user_info(self) -> Dict[str, Any]:
        """Ottieni informazioni utente corrente"""
        if not self.is_authenticated():
            return {}
        
        return {
            'email': st.session_state.get('user_email'),
            'role': st.session_state.get('user_role'),
            'permissions': st.session_state.get('user_permissions', []),
            'login_time': st.session_state.get('login_time')
        }
    
    def can_access_page(self, page_name: str) -> bool:
        """Verifica se l'utente può accedere a una pagina"""
        if not self.is_authenticated():
            return False
        return page_name in st.session_state.get('user_permissions', [])
    
    def logout(self):
        """Effettua logout e pulisce sessione"""
        logout_url = (
            f"{self.logout_endpoint}?"
            f"client_id={self.client_id}&"
            f"returnTo={quote_plus(self.callback_url)}"
        )
        
        # Pulisci TUTTO lo state
        keys_to_clear = [
            'auth0_authenticated', 'user_email', 'user_role', 
            'user_permissions', 'access_token', 'id_token', 
            'login_time', 'token_expiry', 'auth_initialized'
        ]
        
        # Pulisci anche tutti gli auth_state_*
        keys_to_clear.extend([k for k in st.session_state.keys() if k.startswith('auth_state_')])
        if 'current_state_key' in st.session_state:
            keys_to_clear.append('current_state_key')
        
        for key in keys_to_clear:
            st.session_state.pop(key, None)
        
        logger.info("🚪 Logout → redirect Auth0")
        st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)
        st.stop()
    
    def show_login_button(self):
        """Mostra pulsante login Auth0"""
        st.markdown("### 🔐 Autenticazione Richiesta")
        st.info("Accedi con le tue credenziali aziendali.")
        
        auth_url = self.get_authorization_url()
        
        # Debug info
        if st.checkbox("🐛 Debug Info", value=False):
            st.code(f"State keys in session: {[k for k in st.session_state.keys() if 'state' in k.lower()]}")
            st.code(f"URL completo: {auth_url}")
        
        st.markdown(f'''
        <a href="{auth_url}" target="_blank">
            <button style="
                background:#635BFF;
                color:white;
                padding:12px 24px;
                font-size:16px;
                border:none;
                border-radius:6px;
                cursor:pointer;
                width:100%;
                font-weight:600;
            ">
                🔓 Accedi con Auth0
            </button>
        </a>
        ''', unsafe_allow_html=True)
        
        st.caption("Reindirizzamento sicuro ad Auth0.")




# ✅ Istanza globale
auth_manager = Auth0Manager()
