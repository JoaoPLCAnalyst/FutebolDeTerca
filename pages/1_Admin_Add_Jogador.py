import json
import streamlit as st
from github import Github
from PIL import Image
import os

# =========================
# CONFIGURAÇÃO
# =========================

st.set_page_config(page_title="Admin - Adicionar Jogador")

ARQUIVO_JOGADORES = "jogadores.json"
PASTA_IMAGENS = "imagens/jogadores"

# =========================
# FUNÇÕES AUXILIARES
# =========================

def carregar_jogadores():
    with open(ARQUIVO_JOGADORES, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_jogadores_local(jogadores):
    with open(ARQUIVO_JOGADORES, "w", encoding="utf-8") as f:
        json.dump(jogadores, f, indent=4, ensure_ascii=False)


def conectar_github():
    g = Github(st.secrets["GITHUB_TOKEN"])
    return g.get_repo(st.secrets["GITHUB_REPO"])


def salvar_no_github(jogadores, mensagem):
    repo = conectar_github()
    arquivo = repo.get_contents(ARQUIVO_JOGADORES)

    repo.update_file(
        path=ARQUIVO_JOGADORES,
        message=mensagem,
        content=json.dumps(jogadores, indent=4, ensure_ascii=False),
        sha=arquivo.sha
    )


def salvar_imagem_local(id_jogador, imagem):
    os.makedirs(PASTA_IMAGENS, exist_ok=True)

    ext = imagem.name.split(".")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"

    caminho = f"{PASTA_IMAGENS}/{id_jogador}.{ext}"

    img = Image.open(imagem)
    img.save(caminho)

    return caminho

# =========================
# INTERFACE ADMIN
# =========================

st.title("🔒 Administração - Adicionar Jogador")

senha = st.text_input("Senha de administrador", type="password")

if senha != st.secrets["ADMIN_PASSWORD"]:
    if senha:
        st.error("Senha incorreta")
    st.stop()

st.success("Acesso autorizado")

st.divider()

nome = st.text_input("Nome do jogador")
foto = st.file_uploader("Foto do jogador", type=["png", "jpg", "jpeg"])

if st.button("➕ Adicionar jogador"):
    if not nome:
        st.error("Informe o nome do jogador")
        st.stop()

    jogadores = carregar_jogadores()

    # Gera novo ID incremental
    novo_id = str(max(map(int, jogadores.keys()), default=0) + 1)

    caminho_foto = None
    if foto:
        caminho_foto = salvar_imagem_local(novo_id, foto)

    jogadores[novo_id] = {
        "nome": nome,
        "preco": 10,
        "gols": 0,
        "assistencias": 0,
        "foto": caminho_foto
    }

    salvar_jogadores_local(jogadores)

    salvar_no_github(
        jogadores,
        f"Adiciona jogador {nome} (ID {novo_id})"
    )

    st.success(f"Jogador {nome} adicionado com sucesso!")
    st.rerun()
