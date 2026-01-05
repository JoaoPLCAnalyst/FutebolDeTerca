import streamlit as st
import json
import uuid
from utils.images import img_to_base64

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Admin - Futebol de Terça", layout="wide")

ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

# =========================
# FUNÇÕES
# =========================
def carregar_jogadores():
    with open("jogadores.json", "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_jogadores(jogadores):
    with open("jogadores.json", "w", encoding="utf-8") as f:
        json.dump(jogadores, f, indent=4, ensure_ascii=False)

# =========================
# LOGIN
# =========================
st.title("🔒 Área Administrativa")

senha = st.text_input("Senha", type="password")

if senha != ADMIN_PASSWORD:
    st.stop()

st.success("Acesso autorizado")

# =========================
# ADICIONAR JOGADOR
# =========================
st.subheader("➕ Adicionar novo jogador")

nome = st.text_input("Nome do jogador")
foto_upload = st.file_uploader("Foto do jogador", type=["png", "jpg", "jpeg"])

if st.button("Adicionar jogador"):
    if nome.strip() == "":
        st.error("Nome é obrigatório")
    else:
        jogadores = carregar_jogadores()

        novo_id = str(uuid.uuid4())[:8]

        jogadores[novo_id] = {
            "nome": nome,
            "preco": 10,
            "gols": 0,
            "assistencias": 0,
            "foto": img_to_base64(foto_upload)
        }

        salvar_jogadores(jogadores)

        st.success("Jogador adicionado com sucesso")
        st.rerun()

# =========================
# LISTA ADMIN (CONFIRMAÇÃO VISUAL)
# =========================
st.divider()
st.subheader("📋 Jogadores cadastrados")

jogadores = carregar_jogadores()

for id_jogador, dados in jogadores.items():
    col_img, col_info = st.columns([1, 4])

    with col_img:
        if dados.get("foto"):
            st.image(dados["foto"], width=60)
        else:
            st.markdown("❌")

    with col_info:
        st.write(f"{dados['nome']} — Valor: {dados['preco']}")
