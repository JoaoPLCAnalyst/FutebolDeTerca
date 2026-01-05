import streamlit as st
import os
import json
import re
import uuid
from datetime import datetime
import base64
import requests

# -----------------------
# Configurações
# -----------------------
st.set_page_config(page_title="Login - Fantasy Futebol", layout="wide")

PERFIS_DIR = "users/perfis"
os.makedirs(PERFIS_DIR, exist_ok=True)

# GitHub (opcional) - usar st.secrets se quiser versionar automaticamente
GITHUB_USER = st.secrets.get("GITHUB_USER", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

# -----------------------
# Utilitários
# -----------------------
def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9\-_@\. ]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text

def perfil_path(user_id: str) -> str:
    return os.path.join(PERFIS_DIR, f"{user_id}.json")

def carregar_perfil(user_id: str):
    path = perfil_path(user_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def salvar_perfil_local(user_id: str, perfil: dict):
    path = perfil_path(user_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(perfil, f, indent=2, ensure_ascii=False)
    return path

def github_upload(path_local: str, repo_path: str, message: str):
    """Upload simples para o GitHub. Retorna response ou None se não configurado."""
    if not (GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN):
        return None
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{repo_path}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    with open(path_local, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    # tenta obter sha atual (se existir) para atualizar
    get_file = requests.get(url, headers=headers)
    sha = get_file.json().get("sha") if get_file.status_code == 200 else None
    payload = {"message": message, "content": content_b64, "branch": GITHUB_BRANCH}
    if sha:
        payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload, timeout=30)

# -----------------------
# Interface
# -----------------------
st.title("🔐 Entrar no Fantasy — Futebol de Terça")

st.markdown("Use um **nome**, **apelido** ou **e‑mail** para identificar seu perfil. Esse identificador será usado para salvar seu time em `times/lineups/{user_id}.json` e seu perfil em `users/perfis/{user_id}.json`.")

col1, col2 = st.columns([2, 1])
with col1:
    raw_id = st.text_input("Nome, apelido ou e‑mail", placeholder="ex: joao.silva ou joao@example.com")
with col2:
    if st.button("Entrar / Registrar"):
        user_input = (raw_id or "").strip()
        if user_input == "":
            st.error("Digite um nome, apelido ou e‑mail para continuar.")
        else:
            # normaliza user_id
            user_id = slugify(user_input)

            # tenta carregar perfil existente
            perfil = carregar_perfil(user_id)
            now = datetime.utcnow().isoformat() + "Z"

            if perfil is None:
                # cria novo perfil
                perfil = {
                    "user_id": user_id,
                    "nome_apresentacao": user_input,
                    "email": user_input if "@" in user_input else "",
                    "criado_em": now,
                    "ultimo_login": now,
                    "meta": {}
                }
                # salva localmente
                local_path = salvar_perfil_local(user_id, perfil)

                # upload opcional ao GitHub (mantém histórico)
                try:
                    repo_path = f"users/perfis/{user_id}.json"
                    resp = github_upload(local_path, repo_path, f"Cria perfil {user_id}")
                    if resp is not None and resp.status_code in (200, 201):
                        st.success("Perfil criado e enviado ao GitHub.")
                    elif resp is None:
                        st.info("Perfil criado localmente (upload ao GitHub não configurado).")
                    else:
                        st.warning("Perfil criado localmente, mas upload ao GitHub falhou.")
                except Exception as e:
                    st.warning("Perfil criado localmente. Falha ao enviar ao GitHub.")

            else:
                # atualiza último login
                perfil["ultimo_login"] = now
                local_path = salvar_perfil_local(user_id, perfil)
                # opcional: atualizar no GitHub
                try:
                    repo_path = f"users/perfis/{user_id}.json"
                    github_upload(local_path, repo_path, f"Atualiza último login {user_id}")
                except Exception:
                    pass

            # guarda no session_state e redireciona para a página do fantasy
            st.session_state["user_id"] = user_id
            st.session_state["perfil"] = perfil

            # define query param e redireciona para a página de montagem do time
            try:
                st.experimental_set_query_params(user=user_id)
            except Exception:
                # fallback para compatibilidade
                st.experimental_set_query_params(user=user_id)

            st.success(f"Bem vindo, {perfil.get('nome_apresentacao', user_id)}! Redirecionando...")
            st.experimental_rerun()

# -----------------------
# Links úteis
# -----------------------
st.markdown("---")
st.markdown("**Observações**")
st.markdown("- Seu identificador será usado para salvar seu time em `times/lineups/{user_id}.json`.")
st.markdown("- Se quiser, configure `GITHUB_USER`, `GITHUB_REPO` e `GITHUB_TOKEN` em `st.secrets` para que perfis sejam versionados automaticamente.")
