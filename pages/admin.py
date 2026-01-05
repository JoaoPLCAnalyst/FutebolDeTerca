import streamlit as st
import json
import uuid
import base64
from github import Github

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Administração - Futebol de Terça",
    layout="wide"
)

# ======================================================
# SEGURANÇA
# ======================================================
st.title("🔒 Área Administrativa")

senha = st.text_input("Senha de administrador", type="password")

if senha != st.secrets["ADMIN_PASSWORD"]:
    if senha:
        st.error("Senha incorreta")
    st.stop()

st.success("Acesso autorizado")

# ======================================================
# FUNÇÕES AUXILIARES
# ======================================================

def carregar_jogadores():
    with open("jogadores.json", "r", encoding="utf-8") as f:
        return json.load(f)


def conectar_github():
    g = Github(st.secrets["GITHUB_TOKEN"])
    return g.get_repo(st.secrets["GITHUB_REPO"])


def salvar_jogadores_no_github(repo, jogadores, mensagem):
    conteudo = json.dumps(jogadores, indent=4, ensure_ascii=False)
    arquivo = repo.get_contents("jogadores.json")

    repo.update_file(
        path="jogadores.json",
        message=mensagem,
        content=conteudo,
        sha=arquivo.sha
    )


def upload_imagem_github(repo, caminho, uploaded_file):
    conteudo = uploaded_file.read()
    conteudo_b64 = base64.b64encode(conteudo).decode("utf-8")

    try:
        arquivo = repo.get_contents(caminho)
        repo.update_file(
            path=caminho,
            message=f"Atualiza imagem {caminho}",
            content=conteudo_b64,
            sha=arquivo.sha
        )
    except:
        repo.create_file(
            path=caminho,
            message=f"Adiciona imagem {caminho}",
            content=conteudo_b64
        )

# ======================================================
# CADASTRO DE NOVO JOGADOR
# ======================================================

st.divider()
st.subheader("➕ Cadastrar novo jogador")

with st.form("form_cadastro_jogador"):
    nome = st.text_input("Nome do jogador")
    foto = st.file_uploader(
        "Foto do jogador",
        type=["png", "jpg", "jpeg"]
    )

    submit = st.form_submit_button("Cadastrar jogador")

if submit:
    if not nome or not foto:
        st.error("Preencha o nome e envie uma foto.")
        st.stop()

    jogadores = carregar_jogadores()
    repo = conectar_github()

    jogador_id = str(uuid.uuid4())[:8]
    ext = foto.name.split(".")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"

    caminho_imagem = f"images/jogadores/{jogador_id}.{ext}"

    # Upload da imagem
    upload_imagem_github(repo, caminho_imagem, foto)

    # Registro no JSON
    jogadores[jogador_id] = {
        "nome": nome,
        "preco": 10,
        "gols": 0,
        "assistencias": 0,
        "foto": caminho_imagem
    }

    salvar_jogadores_no_github(
        repo,
        jogadores,
        f"Adiciona jogador {nome} ({jogador_id})"
    )

    st.success("Jogador cadastrado e salvo no GitHub com sucesso!")
    st.rerun()

# ======================================================
# LISTA DE JOGADORES CADASTRADOS
# ======================================================

st.divider()
st.subheader("📋 Jogadores cadastrados")

jogadores = carregar_jogadores()

if not jogadores:
    st.info("Nenhum jogador cadastrado.")
    st.stop()

cols = st.columns(4)

for jogador_id, j in jogadores.items():
    with st.container(border=True):
        if j.get("foto"):
            repo_nome = st.secrets["GITHUB_REPO"]
            st.image(
                f"https://raw.githubusercontent.com/{repo_nome}/main/{j['foto']}",
                width=120
            )

        st.markdown(f"**{j['nome']}**")
        st.write(f"Gols: {j['gols']}")
        st.write(f"Assistências: {j['assistencias']}")
        st.write(f"Valor: {j['preco']}")
        st.caption(f"ID: {jogador_id}")
