import streamlit as st
import json
import os
from typing import Dict, Any

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Futebol de Terça", layout="wide")

JOGADORES_FILE = "database/jogadores.json"

# =========================
# HELPERS
# =========================
def _repo_parts_from_secrets():
    """
    Retorna (user, repo, branch) a partir de st.secrets.
    Aceita tanto:
      - GITHUB_REPO = "user/repo"
    quanto:
      - GITHUB_USER e GITHUB_REPO separados.
    """
    repo_full = st.secrets.get("GITHUB_REPO", "")
    user = st.secrets.get("GITHUB_USER", "")
    branch = st.secrets.get("GITHUB_BRANCH", "main")

    if "/" in repo_full:
        parts = repo_full.split("/", 1)
        user = parts[0]
        repo = parts[1]
    else:
        repo = repo_full or st.secrets.get("GITHUB_REPO_NAME", "")

    return user, repo, branch


def imagem_github_url(caminho: str) -> str:
    """
    Monta a URL raw do GitHub para o caminho fornecido.
    Exemplo: https://raw.githubusercontent.com/user/repo/branch/path/to/file.jpg
    """
    if not caminho:
        return ""
    user, repo, branch = _repo_parts_from_secrets()
    # Se algum dado estiver faltando, retorna string vazia para evitar URL inválida
    if not user or not repo or not branch:
        return ""
    # Remove eventual barra inicial
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
            # evita sobrescrever se chave já existir
            if key in result:
                key = f"{key}-{idx}"
            result[key] = item
        return result
    return {}


@st.cache_data(ttl=60)
def carregar_jogadores() -> Dict[str, dict]:
    """
    Lê o arquivo JOGADORES_FILE e retorna um dicionário de jogadores.
    Usa normalize_jogadores para compatibilidade com formatos antigos.
    """
    if not os.path.exists(JOGADORES_FILE):
        return {}

    try:
        with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # Em caso de erro de leitura/parse, retorna vazio para não quebrar a UI
        return {}

    return normalize_jogadores(data)


# =========================
# INTERFACE
# =========================
st.title("⚽ Futebol de Terça")

jogadores = carregar_jogadores()

if not jogadores:
    st.warning("Nenhum jogador cadastrado.")
    st.stop()

# Ordena por nome para exibição (se disponível)
sorted_items = sorted(
    jogadores.items(),
    key=lambda kv: (kv[1].get("nome") or "").lower()
)

for jogador_id, j in sorted_items:
    # Layout: imagem à esquerda, detalhes à direita
    col1, col2 = st.columns([1, 3])

    # Suporta chaves antigas e novas:
    # imagem pode estar em "imagem" ou "foto"
    imagem_path = j.get("imagem") or j.get("foto") or ""
    nome = j.get("nome", "—")
    gols = j.get("gols", 0)
    assistencias = j.get("assistencias", 0) or j.get("assistências", 0) or 0
    # valor pode estar em "valor" ou "preco" ou "preço"
    valor = j.get("valor", j.get("preco", j.get("preço", "—")))

    with col1:
        if imagem_path:
            url = imagem_github_url(imagem_path)
            if url:
                # st.image aceita URL; se houver problema, Streamlit mostra placeholder
                st.image(url, width=120)
            else:
                st.write("")  # espaço reservado
        else:
            st.write("")  # espaço reservado quando não há imagem

    with col2:
        st.markdown(f"**{nome}**")
        st.write(f"Gols: **{gols}**")
        st.write(f"Assistências: **{assistencias}**")
        st.write(f"Valor: **{valor}**")
        st.divider()
