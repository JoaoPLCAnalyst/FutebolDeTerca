import streamlit as st
import requests
import json
import os
import time
from typing import Dict, Any

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Futebol de Terça", layout="wide")
JOGADORES_FILE = "database/jogadores.json"  # fallback local

# =========================
# HELPERS
# =========================
def _repo_parts_from_secrets():
    repo_full = st.secrets.get("GITHUB_REPO", "")
    user = st.secrets.get("GITHUB_USER", "")
    branch = st.secrets.get("GITHUB_BRANCH", "main")
    token = st.secrets.get("GITHUB_TOKEN", None)

    if "/" in repo_full:
        parts = repo_full.split("/", 1)
        user = parts[0]
        repo = parts[1]
    else:
        repo = repo_full or st.secrets.get("GITHUB_REPO_NAME", "")

    return user, repo, branch, token


def imagem_github_url(caminho: str) -> str:
    if not caminho:
        return ""
    user, repo, branch, _ = _repo_parts_from_secrets()
    if not user or not repo or not branch:
        return ""
    caminho = caminho.lstrip("/")
    ts = int(time.time())
    return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{caminho}?t={ts}"


def normalize_jogadores(data: Any) -> Dict[str, dict]:
    if data is None:
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        result = {}
        for idx, item in enumerate(data):
            key = item.get("id") or f"j{idx:04d}"
            if key in result:
                key = f"{key}-{idx}"
            result[key] = item
        return result
    return {}

# =========================
# LEITURA DO GITHUB SEM CACHE
# =========================
def carregar_jogadores_do_github_no_cache() -> Dict[str, dict]:
    user, repo, branch, token = _repo_parts_from_secrets()
    path = "database/jogadores.json"

    if not user or not repo or not branch:
        return {}

    ts = int(time.time())
    raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}?t={ts}"

    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        r = requests.get(raw_url, headers=headers, timeout=10)
    except Exception:
        return {}

    if r.status_code != 200:
        return {}

    try:
        data = r.json()
    except Exception:
        return {}

    return normalize_jogadores(data)


def carregar_jogadores_local_no_cache() -> Dict[str, dict]:
    if not os.path.exists(JOGADORES_FILE):
        return {}
    try:
        with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return normalize_jogadores(data)
    except Exception:
        return {}

# =========================
# FUNÇÃO PRINCIPAL DE CARREGAMENTO
# =========================
def carregar_jogadores(prefer_github: bool = True) -> Dict[str, dict]:
    if prefer_github:
        gh = carregar_jogadores_do_github_no_cache()
        if gh:
            return gh
        local = carregar_jogadores_local_no_cache()
        return local
    else:
        local = carregar_jogadores_local_no_cache()
        if local:
            return local
        gh = carregar_jogadores_do_github_no_cache()
        return gh

# =========================
# INTERFACE
# =========================
st.title("⚽ Futebol de Terça")

# Sempre busca dados frescos do GitHub (sem cache)
jogadores = carregar_jogadores(prefer_github=True)

if not jogadores:
    st.warning("Nenhum jogador cadastrado.")
    st.stop()

# Ordena por nome para exibição
sorted_items = sorted(jogadores.items(), key=lambda kv: (kv[1].get("nome") or "").lower())

for jogador_id, j in sorted_items:
    col1, col2 = st.columns([1, 3])

    imagem_path = j.get("imagem") or j.get("foto") or ""
    nome = j.get("nome", "—")
    gols = j.get("gols", 0)
    assistencias = j.get("assistencias", 0) or j.get("assistências", 0) or 0
    valor = j.get("valor", j.get("preco", j.get("preço", "—")))

    with col1:
        if imagem_path:
            url = imagem_github_url(imagem_path)
            if url:
                st.image(url, width=120)
            else:
                st.write("")
        else:
            st.write("")

    with col2:
        st.markdown(f"**{nome}**")
        st.write(f"Gols: **{gols}**")
        st.write(f"Assistências: **{assistencias}**")
        st.write(f"Valor: **{valor}**")
        st.caption(f"ID: {jogador_id}")
        st.divider()
