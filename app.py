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

# =========================
# INTERFACE
# =========================
st.title("⚽ Futebol de Terça")

jogadores = carregar_jogadores()

st.subheader("Jogadores disponíveis")

for id_jogador, dados in jogadores.items():
    col_img, col_info = st.columns([1, 4])

    with col_img:
        if dados.get("foto"):
            st.image(dados["foto"], width=80)
        else:
            st.markdown("❌ Sem foto")

    with col_info:
        st.markdown(f"""
        **{dados["nome"]}**  
        💰 Valor: {dados["preco"]}  
        ⚽ Gols: {dados["gols"]}  
        🎯 Assistências: {dados["assistencias"]}
        """)

    st.divider()

# =========================
# LINK ADMIN
# =========================
st.markdown("🔒 [Acessar área administrativa](./admin)")
