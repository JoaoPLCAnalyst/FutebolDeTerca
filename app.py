import streamlit as st
import json
import os

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Futebol de Terça", layout="wide")

JOGADORES_FILE = "database/jogadores.json"
IMAGENS_DIR = "imagens/jogadores"

# =========================
# FUNÇÕES AUXILIARES
# =========================
def carregar_jogadores():
    """Carrega jogadores do arquivo local JSON."""
    if not os.path.exists(JOGADORES_FILE):
        return {}
    try:
        with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # garantir formato dict
        if isinstance(data, dict):
            return data
        elif isinstance(data, list):
            return {f"j{idx:04d}": item for idx, item in enumerate(data)}
        else:
            return {}
    except Exception as e:
        st.error(f"Erro ao carregar jogadores.json: {e}")
        return {}

# =========================
# INTERFACE
# =========================
st.title("⚽ Futebol de Terça")

jogadores = carregar_jogadores()

if not jogadores:
    st.warning("Nenhum jogador cadastrado.")
    st.stop()

# Ordena por nome para exibição
sorted_items = sorted(jogadores.items(), key=lambda kv: (kv[1].get("nome") or "").lower())

for jogador_id, j in sorted_items:
    col1, col2 = st.columns([1, 3])
    imagem_path = j.get("imagem", "")
    nome = j.get("nome", "—")
    gols = j.get("gols", 0)
    assistencias = j.get("assistencias", 0)
    valor = j.get("valor", "—")

    with col1:
        if imagem_path:
            # exibe imagem local
            if os.path.exists(imagem_path):
                st.image(imagem_path, width=120)
            else:
                st.warning("Imagem não encontrada.")
        else:
            st.write("")

    with col2:
        st.markdown(f"**{nome}**")
        st.write(f"Gols: **{gols}**")
        st.write(f"Assistências: **{assistencias}**")
        st.write(f"Valor: **{valor}**")
        st.caption(f"ID: {jogador_id}")
        st.divider()
