import streamlit as st
import os
import json
import re
from datetime import datetime

st.set_page_config(page_title="Login - Fantasy Futebol", layout="wide")

# Diretório de perfis
PERFIS_DIR = "users/perfis"
os.makedirs(PERFIS_DIR, exist_ok=True)

# Leitura de configurações administrativas (coloque em secrets.toml)
# Exemplo secrets.toml:
# ADMIN_PASSWORD = "SV2024"
# ADMIN_USER_ID = "admin_user_id"
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
ADMIN_USER_ID = st.secrets.get("ADMIN_USER_ID", "admin")

# -----------------------
# Utilitários de perfil
# -----------------------
def listar_perfis():
    perfis = {}
    if not os.path.exists(PERFIS_DIR):
        return perfis
    for fname in os.listdir(PERFIS_DIR):
        if not fname.lower().endswith(".json"):
            continue
        path = os.path.join(PERFIS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                uid = data.get("user_id") or fname[:-5]
                perfis[uid] = data
        except Exception:
            continue
    return perfis

def encontrar_userid_por_email(email: str):
    perfis = listar_perfis()
    email_norm = (email or "").strip().lower()
    for uid, perfil in perfis.items():
        if (perfil.get("email") or "").strip().lower() == email_norm:
            return uid, perfil
    return None, None

def salvar_perfil(user_id: str, perfil: dict):
    path = os.path.join(PERFIS_DIR, f"{user_id}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(perfil, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

# -----------------------
# Verificação de senha (texto puro)
# -----------------------
def check_password_for_userid_plain(user_id: str, password: str) -> bool:
    pw_store = st.secrets.get("USERS_PASSWORDS", {}).get(user_id)
    if pw_store is None:
        return False
    return password == pw_store

# -----------------------
# Mostrar mensagem de login pendente (se houver)
# -----------------------
if st.session_state.get("login_message"):
    st.success(st.session_state.get("login_message"))
    # remover para não repetir em execuções subsequentes
    del st.session_state["login_message"]

# -----------------------
# Interface de login
# -----------------------
st.title("🔐 Entrar")

email_input = st.text_input("E‑mail cadastrado", placeholder="ex: joao.cogo@unesp.br")
senha_input = st.text_input("Senha", type="password")

if st.button("Entrar"):
    email = (email_input or "").strip()
    senha = (senha_input or "").strip()

    if not email or not senha:
        st.error("Preencha e‑mail e senha.")
    else:
        user_id, perfil = encontrar_userid_por_email(email)

        if not user_id:
            st.error("E‑mail não encontrado nos perfis. Login negado.")
        else:
            # Verifica se existe senha configurada para o user_id
            has_pw = user_id in st.secrets.get("USERS_PASSWORDS", {})
            senha_valida_usuario = has_pw and check_password_for_userid_plain(user_id, senha)

            # Verifica override de senha admin (se configurado em secrets)
            senha_admin_override = (ADMIN_PASSWORD is not None and senha == ADMIN_PASSWORD)

            if not has_pw and not senha_admin_override:
                st.error("Conta sem senha configurada. Contate o administrador.")
            elif not senha_valida_usuario and not senha_admin_override:
                st.error("Senha incorreta.")
            else:
                # login OK
                now = datetime.utcnow().isoformat() + "Z"
                perfil = perfil or {}
                perfil["user_id"] = user_id
                perfil["ultimo_login"] = now
                saved = salvar_perfil(user_id, perfil)
                if not saved:
                    st.warning("Login efetuado, mas não foi possível atualizar último_login no arquivo de perfil.")

                # sinaliza sessão
                st.session_state["user_id"] = user_id
                st.session_state["perfil"] = perfil
                st.session_state["logged_in"] = True

                # define is_admin se for o user_id admin ou se usou a senha admin override
                if user_id == ADMIN_USER_ID or senha_admin_override:
                    st.session_state["is_admin"] = True
                else:
                    st.session_state["is_admin"] = False

                # mensagem de sucesso persistente por uma execução
                st.session_state["login_message"] = f"Bem vindo, {perfil.get('nome_apresentacao', user_id)}!"

                # mostra confirmação imediata e reinicia para propagar session_state
                st.success(st.session_state["login_message"])
                st.rerun()
