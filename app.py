import streamlit as st
import json

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Futebol de Terça", layout="wide")

# =========================
# FUNÇÕES
# =========================
def carregar_jogadores():
    with open("jogadores.json", "r", encoding="utf-8") as f:
        return json.load(f)

def imagem_github_url(caminho):
    repo = st.secrets["GITHUB_REPO"]
    return f"https://raw.githubusercontent.com/{repo}/main/{caminho}"

# =========================
# INTERFACE
# =========================
st.title("⚽ Futebol de Terça")

jogadores = carregar_jogadores()

cols = st.columns(4)

for jogador_id, j in jogadores.items():
    with st.container(border=True):
        if j.get("foto"):
            st.image(
                imagem_github_url(j["foto"]),
                width=120
            )

        st.markdown(f"**{j['nome']}**")
        st.write(f"Gols: {j['gols']}")
        st.write(f"Assistências: {j['assistencias']}")
        st.write(f"Valor: {j['preco']}")

    st.divider()

# =========================
# LINK ADMIN
# =========================
st.markdown("🔒 [Acessar área administrativa](./admin)")
