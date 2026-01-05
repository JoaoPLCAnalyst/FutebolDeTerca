import streamlit as st
import requests
import json
import os
import time
from typing import Dict, Any, Optional

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Futebol de Terça", layout="wide")
JOGADORES_FILE = "database/jogadores.json"  # fallback local
GITHUB_COMMITS_ENDPOINT = "https://api.github.com/repos/{user}/{repo}/commits"

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
# GITHUB: obter SHA do último commit para o arquivo
# =========================
def get_latest_commit_sha_for_path(path: str) -> Optional[str]:
    """
    Retorna o SHA do commit mais recente que modificou `path` na branch configurada.
    Usa a API /commits?path=...&sha=<branch>.
    Retorna None em caso de erro.
    """
    user, repo, branch, token = _repo_parts_from_secrets()
    if not user or not repo or not branch:
        return None

    url = GITHUB_COMMITS_ENDPOINT.format(user=user, repo=repo)
    params = {"path": path, "sha": branch, "per_page": 1}
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        r = requests.get(url, headers=headers, params=params, timeout=8)
    except Exception:
        return None

    if r.status_code != 200:
        return None

    try:
        commits = r.json()
        if isinstance(commits, list) and len(commits) > 0:
            return commits[0].get("sha")
    except Exception:
        return None

    return None

# =========================
# GITHUB: baixar JSON raw (sem cache)
# =========================
def fetch_jogadores_from_github_raw(path: str) -> Optional[Dict[str, dict]]:
    user, repo, branch, token = _repo_parts_from_secrets()
    if not user or not repo or not branch:
        return None

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
        return None

    if r.status_code != 200:
        return None

    try:
        data = r.json()
    except Exception:
        return None

    return normalize_jogadores(data)

# =========================
# LEITURA LOCAL (fallback)
# =========================
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
# FLUXO PRINCIPAL: detectar commit e atualizar
# =========================
def carregar_jogadores_detect_commit(path: str = "database/jogadores.json") -> Dict[str, dict]:
    """
    Verifica o SHA do último commit que modificou `path`. Se for diferente do SHA
    salvo em st.session_state, baixa o JSON do GitHub (raw) e atualiza session_state.
    Se não conseguir usar GitHub, faz fallback para arquivo local.
    """
    # inicializa session_state
    if "_jogadores_sha" not in st.session_state:
        st.session_state["_jogadores_sha"] = None
    if "_jogadores_data" not in st.session_state:
        st.session_state["_jogadores_data"] = {}

    latest_sha = get_latest_commit_sha_for_path(path)

    # Se conseguimos obter SHA e ela é diferente da que temos, buscar o JSON
    if latest_sha and latest_sha != st.session_state["_jogadores_sha"]:
        data = fetch_jogadores_from_github_raw(path)
        if data is not None:
            st.session_state["_jogadores_sha"] = latest_sha
            st.session_state["_jogadores_data"] = data
            return data
        # se falhar ao baixar, tentamos fallback local abaixo

    # Se não conseguimos SHA (erro) ou SHA igual, usamos o que já temos em session_state
    if st.session_state["_jogadores_data"]:
        return st.session_state["_jogadores_data"]

    # Se não há dados em session_state, tentamos baixar do GitHub mesmo sem SHA
    data = fetch_jogadores_from_github_raw(path)
    if data is not None:
        # tentamos obter sha também para sincronizar
        if latest_sha:
            st.session_state["_jogadores_sha"] = latest_sha
        st.session_state["_jogadores_data"] = data
        return data

    # Fallback final: arquivo local
    local = carregar_jogadores_local_no_cache()
    st.session_state["_jogadores_data"] = local
    return local

# =========================
# INTERFACE
# =========================
st.title("⚽ Futebol de Terça")

# Carrega jogadores detectando commits e atualizando automaticamente
jogadores = carregar_jogadores_detect_commit("database/jogadores.json")

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
