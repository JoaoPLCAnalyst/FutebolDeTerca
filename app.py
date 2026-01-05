import streamlit as st
import requests
import json
import os
from typing import Dict, Any

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Futebol de Terça", layout="wide")

# Caminho local (fallback)
JOGADORES_FILE = "database/jogadores.json"

# =========================
# HELPERS
# =========================
def _repo_parts_from_secrets():
    """
    Retorna (user, repo, branch, token) a partir de st.secrets.
    Aceita GITHUB_REPO no formato "user/repo" ou GITHUB_USER + GITHUB_REPO separados.
    """
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
    """
    Monta a URL raw do GitHub para o caminho fornecido.
    """
    if not caminho:
        return ""
    user, repo, branch, _ = _repo_parts_from_secrets()
    if not user or not repo or not branch:
        return ""
    caminho = caminho.lstrip("/")
    return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{caminho}"


def normalize_jogadores(data: Any) -> Dict[str, dict]:
    """
    Garante que o retorno seja um dicionário no formato {id: jogador}.
    Se o arquivo estiver em lista (formato antigo), converte para dict usando índices.
    """
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


@st.cache_data(ttl=30)
def carregar_jogadores_do_github() -> Dict[str, dict]:
    """
    Tenta buscar database/jogadores.json do GitHub (raw).
    Se o repositório for privado e houver GITHUB_TOKEN em st.secrets, usa autenticação.
    Retorna dicionário normalizado ou {} em caso de falha.
    """
    user, repo, branch, token = _repo_parts_from_secrets()
    path = "database/jogadores.json"

    if not user or not repo or not branch:
        return {}

    raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        r = requests.get(raw_url, headers=headers, timeout=8)
        if r.status_code == 200:
            try:
                data = r.json()
                return normalize_jogadores(data)
            except Exception:
                return {}
        else:
            # qualquer status diferente de 200 -> fallback vazio
            return {}
    except Exception:
        return {}


@st.cache_data(ttl=30)
def carregar_jogadores_local() -> Dict[str, dict]:
    """
    Lê o arquivo local JOGADORES_FILE e normaliza para dicionário.
    """
    if not os.path.exists(JOGADORES_FILE):
        return {}
    try:
        with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return normalize_jogadores(data)
    except Exception:
        return {}


def carregar_jogadores(prefer_github: bool = True) -> Dict[str, dict]:
    """
    Tenta carregar do GitHub primeiro (se prefer_github=True).
    Se falhar, faz fallback para o arquivo local.
    Retorna também a origem como string para debug/UX.
    """
    if prefer_github:
        gh = carregar_jogadores_do_github()
        if gh:
            st.session_state["_jogadores_origem"] = "github"
            return gh
        local = carregar_jogadores_local()
        st.session_state["_jogadores_origem"] = "local"
        return local
    else:
        local = carregar_jogadores_local()
        if local:
            st.session_state["_jogadores_origem"] = "local"
            return local
        gh = carregar_jogadores_do_github()
        st.session_state["_jogadores_origem"] = "github" if gh else "none"
        return gh


# =========================
# INTERFACE
# =========================
st.title("⚽ Futebol de Terça")

# Botão para forçar recarregar (limpa cache e rerun)
col_reload, _ = st.columns([1, 9])
with col_reload:
    if st.button("🔄 Recarregar do GitHub"):
        # limpa caches para forçar novo fetch
        st.cache_data.clear()
        st.rerun()

# Carrega jogadores (prefere GitHub)
jogadores = carregar_jogadores(prefer_github=True)

# Indica origem dos dados (apenas para debug/UX)
origem = st.session_state.get("_jogadores_origem", "desconhecida")
if origem == "github":
    st.info("Fonte dos dados: GitHub (raw)")
elif origem == "local":
    st.info("Fonte dos dados: arquivo local")
else:
    st.info("Fonte dos dados: nenhuma (arquivo vazio ou erro)")

if not jogadores:
    st.warning("Nenhum jogador cadastrado.")
    st.stop()

# Ordena por nome para exibição (se disponível)
sorted_items = sorted(
    jogadores.items(),
    key=lambda kv: (kv[1].get("nome") or "").lower()
)

for jogador_id, j in sorted_items:
    col1, col2 = st.columns([1, 3])

    # Suporta chaves antigas e novas:
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
                st.write("")  # espaço reservado
        else:
            st.write("")  # espaço reservado

    with col2:
        st.markdown(f"**{nome}**")
        st.write(f"Gols: **{gols}**")
        st.write(f"Assistências: **{assistencias}**")
        st.write(f"Valor: **{valor}**")
        st.caption(f"ID: {jogador_id}")
        st.divider()
