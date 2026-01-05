import streamlit as st
import json

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Futebol de Terça",
    layout="wide"
)

# =========================
# FUNÇÕES
# =========================
def carregar_jogadores():
    with open("database/jogadores.json", "r", encoding="utf-8") as f:
        return json.load(f)


def imagem_github_url(caminho):
    owner = st.secrets["GITHUB_OWNER"]
    repo = st.secrets["GITHUB_REPO"]
    branch = st.secrets.get("GITHUB_BRANCH", "main")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{caminho}"

# =========================
# INTERFACE
# =========================
st.title("⚽ Futebol de Terça")

jogadores = carregar_jogadores()

if not jogadores:
    st.info("Nenhum jogador cadastrado ainda.")
    st.stop()

# Grid visual
cols = st.columns(4)
col_index = 0

for jogador_id, j in jogadores.items():
    with cols[col_index]:
        with st.container(border=True):

            if j.get("foto"):
                st.image(
                    imagem_github_url(j["foto"]),
                    width=120
                )

            st.markdown(f"### {j['nome']}")
            st.write(f"⚽ Gols: {j['gols']}")
            st.write(f"🎯 Assistências: {j['assistencias']}")
            st.write(f"💰 Valor: {j['preco']}")

    col_index = (col_index + 1) % 4

st.divider()

