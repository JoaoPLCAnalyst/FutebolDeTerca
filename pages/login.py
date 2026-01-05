import streamlit as st
import os
import json
import re
from datetime import datetime

st.set_page_config(page_title="Login - Fantasy Futebol", layout="wide")

PERFIS_DIR = "users/perfis"
os.makedirs(PERFIS_DIR, exist_ok=True)

# -----------------------
# Utilitários
# -----------------------
def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9\-_@\. ]", "", text)
    return re.sub(r"\s+", "_", text)

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
    """
    Busca st.secrets['USERS_PASSWORDS'][user_id] e compara texto puro.
    Retorna False se não houver entrada em st.secrets para esse user_id.
    """
    pw_store = st.secrets.get("USERS_PASSWORDS", {}).get(user_id)
    if pw_store is None:
        return False
    return password == pw_store

# -----------------------
# Interface
# -----------------------
st.title("🔐 Entrar no Fantasy — Futebol de Terça")

st.markdown(
    "Informe o **e‑mail** cadastrado e a **senha**. "
    "O sistema só permite login se o e‑mail existir em `users/perfis` e a senha corresponder ao valor em `st.secrets`."
)

email_input = st.text_input("E‑mail cadastrado", placeholder="ex: joao.cogo@unesp.br")
senha_input = st.text_input("Senha", type="password")

# botão de depuração opcional (remova em produção)
if st.checkbox("Mostrar chaves de USERS_PASSWORDS (apenas para depuração)"):
    try:
        keys = list(st.secrets.get("USERS_PASSWORDS", {}).keys())
        st.info(f"Chaves em st.secrets['USERS_PASSWORDS']: {keys}")
    except Exception as e:
        st.warning("Não foi possível ler st.secrets['USERS_PASSWORDS'].")

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
            # exige que exista uma entrada em st.secrets para esse user_id
            if user_id not in st.secrets.get("USERS_PASSWORDS", {}):
                st.error(
                    "Conta sem senha configurada em st.secrets. "
                    "Verifique se existe a chave correspondente ao user_id do perfil."
                )
            else:
                if not check_password_for_userid_plain(user_id, senha):
                    st.error("Senha incorreta.")
                else:
                    now = datetime.utcnow().isoformat() + "Z"
                    perfil = perfil or {}
                    perfil["user_id"] = user_id
                    perfil["ultimo_login"] = now
                    saved = salvar_perfil(user_id, perfil)
                    if not saved:
                        st.warning("Login efetuado, mas não foi possível atualizar último_login no arquivo de perfil.")
                    st.session_state["user_id"] = user_id
                    st.session_state["perfil"] = perfil
                    st.success(f"Bem vindo, {perfil.get('nome_apresentacao', user_id)}!")
                    st.experimental_set_query_params(user=user_id)
                    st.experimental_rerun()

st.markdown("---")
st.markdown("**Observações**")
st.markdown("- As senhas devem estar definidas em `st.secrets['USERS_PASSWORDS']` com chaves iguais aos `user_id` (slug).")
st.markdown("- Exemplo de `secrets.toml`:")
st.code(
    '[USERS_PASSWORDS]\n'
    'joao_cogo_unesp_br = "senhaTeste"\n'
    'eudes02_gmail_com = "outraSenha"\n',
    language="toml"
)
