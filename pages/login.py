import streamlit as st
import os
import json
from datetime import datetime
import time

st.set_page_config(page_title="Login - Fantasy Futebol", layout="wide")

# Diretório de perfis
PERFIS_DIR = "users/perfis"
os.makedirs(PERFIS_DIR, exist_ok=True)

# Configurações administrativas (defina em secrets.toml)
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
ADMIN_USER_ID = st.secrets.get("ADMIN_USER_ID", "admin")

# Configurações do olheiro (scout) (defina em secrets.toml)
SCOUT_PASSWORD = st.secrets.get("SCOUT_PASSWORD")
SCOUT_USER_ID = st.secrets.get("SCOUT_USER_ID", "olheiro")

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

def carregar_perfil(user_id: str):
    path = os.path.join(PERFIS_DIR, f"{user_id}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

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
# Limpeza de estado antes de nova tentativa de login
# -----------------------
def limpar_estado_login_residual():
    for k in ["user_id", "perfil", "logged_in", "is_admin", "is_scout", "login_message", "login_time"]:
        if k in st.session_state:
            del st.session_state[k]

# -----------------------
# Mostrar mensagem de login pendente (se houver)
# -----------------------
if st.session_state.get("login_message"):
    st.success(st.session_state.get("login_message"))
    del st.session_state["login_message"]

# -----------------------
# Interface de login
# -----------------------
st.title("🔐 Entrar")

email_or_userid = st.text_input("E‑mail cadastrado ou user_id", placeholder="ex: joao.cogo@unesp.br ou admin")
senha_input = st.text_input("Senha", type="password")

if st.button("Entrar"):
    # limpa flags residuais para evitar herança de estado
    limpar_estado_login_residual()

    identifier = (email_or_userid or "").strip()
    senha = (senha_input or "").strip()

    if not identifier or not senha:
        st.error("Preencha e‑mail/user_id e senha.")
        st.stop()

    # Primeiro tenta interpretar como e-mail (contém @)
    user_id = None
    perfil = None
    if "@" in identifier:
        user_id, perfil = encontrar_userid_por_email(identifier)
    else:
        # tenta carregar perfil por user_id direto
        perfil = carregar_perfil(identifier)
        if perfil:
            user_id = perfil.get("user_id") or identifier

        # se não encontrou por user_id, tenta como e-mail mesmo assim
        if not user_id:
            user_id, perfil = encontrar_userid_por_email(identifier)

    if not user_id:
        st.error("E‑mail/user_id não encontrado nos perfis. Login negado.")
        st.stop()

    # Verifica override de senha admin (se configurado em secrets)
    senha_admin_override = (ADMIN_PASSWORD is not None and senha == ADMIN_PASSWORD and user_id == ADMIN_USER_ID)

    # Verifica override de senha scout (se configurado em secrets)
    senha_scout_override = (SCOUT_PASSWORD is not None and senha == SCOUT_PASSWORD and user_id == SCOUT_USER_ID)

    # Verifica se existe senha configurada para o user_id
    has_pw = user_id in st.secrets.get("USERS_PASSWORDS", {})
    senha_valida_usuario = has_pw and check_password_for_userid_plain(user_id, senha)

    # Se for admin, só aceita se user_id for o admin e senha for a do admin ou a senha do usuário admin em USERS_PASSWORDS
    if user_id == ADMIN_USER_ID:
        if not (senha_valida_usuario or senha_admin_override):
            st.error("Senha incorreta para o administrador.")
            st.stop()
    else:
        # usuário comum: precisa ter senha configurada e válida
        if not has_pw and user_id != SCOUT_USER_ID:
            st.error("Conta sem senha configurada. Contate o administrador.")
            st.stop()
        if not senha_valida_usuario and not senha_scout_override and user_id != SCOUT_USER_ID:
            st.error("Senha incorreta.")
            st.stop()

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
    st.session_state["login_time"] = time.time()

    # define is_admin se for o user_id admin e a senha for válida (ou override)
    st.session_state["is_admin"] = (user_id == ADMIN_USER_ID and (senha_valida_usuario or senha_admin_override))

    # define is_scout se for o user_id do olheiro e a senha for válida (ou override)
    st.session_state["is_scout"] = (user_id == SCOUT_USER_ID and (senha_valida_usuario or senha_scout_override))

    # mensagem de sucesso persistente por uma execução
    st.session_state["login_message"] = f"Bem vindo, {perfil.get('nome_apresentacao', user_id)}!"

    # comportamento após login:
    # - não renderizamos a UI admin aqui; a página admin está em pages/admin.py e exige senha própria
    # - apenas propagamos o estado e deixamos o usuário navegar no menu
    st.success(st.session_state["login_message"])
    st.rerun()
