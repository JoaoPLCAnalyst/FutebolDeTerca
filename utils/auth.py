# utils/auth.py
import streamlit as st

def require_login():
    if not st.session_state.get("logged_in"):
        st.info("Faça login para acessar esta página.")
        st.stop()

def require_admin():
    require_login()
    if not st.session_state.get("is_admin"):
        st.error("Acesso negado. Esta área é restrita a administradores.")
        st.stop()
import streamlit as st

def logout():
    """Limpa todas as chaves de sessão relacionadas à autenticação."""
    for k in ["user_id", "perfil", "logged_in", "is_admin", "login_message", "login_time"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()
