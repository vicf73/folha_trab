# -*- coding: utf-8 -*-
import streamlit as st
import logging
from sqlalchemy import text
from database import PostgresDatabaseManager
from views.login import login_page
from views.dashboard import manager_page

# Configuração da página para prevenir erros de interface
st.set_page_config(
    page_title="Sistema de Gestão de Dados - V.Ferreira",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO PARA STREAMLIT.IO COM SECRETS ---
try:
    # Usar st.secrets para configurações sensíveis
    POSTGRES_CONFIG = {
        'host': st.secrets["postgres"]["host"],
        'port': st.secrets["postgres"]["port"],
        'database': st.secrets["postgres"]["database"],
        'user': st.secrets["postgres"]["user"],
        'password': st.secrets["postgres"]["password"]
    }
    
    logger.info(f"Conectando ao Neon.tech: {POSTGRES_CONFIG['host']}")
    
except Exception as e:
    st.error("❌ Erro ao carregar as configurações do banco de dados.")
    st.info("💡 Verifique se as secrets estão configuradas corretamente no Streamlit Cloud.")
    logger.error(f"Erro nas configurações do banco: {e}")
    st.stop()

# Construção da URL de conexão
POSTGRES_URL = f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"

# --- FUNÇÃO PRINCIPAL ---
def main():
    """Função principal do aplicativo Streamlit."""
    
    # Inicialização do Estado de Sessão
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
        st.session_state['user'] = None

    # Configuração do DB
    try:
        db_manager = PostgresDatabaseManager(POSTGRES_URL)
        
        # Mostrar status da conexão no sidebar
        try:
            with db_manager.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                st.sidebar.success(f"✅ Conectado ao Neon.tech")
                
                # Contar registros
                count_result = conn.execute(text("SELECT COUNT(*) FROM bd"))
                record_count = count_result.scalar()
                st.sidebar.info(f"📊 Registros na BD: {record_count:,}")
                
        except Exception as e:
            st.sidebar.error(f"❌ Erro na conexão: {e}")
            
    except Exception as e:
        st.error(f"O aplicativo não pôde se conectar ao banco de dados.")
        logger.error(f"Falha na inicialização do banco de dados: {e}")
        return

    # Roteamento
    if st.session_state['authenticated']:
        manager_page(db_manager)
    else:
        login_page(db_manager)

if __name__ == '__main__':
    main()