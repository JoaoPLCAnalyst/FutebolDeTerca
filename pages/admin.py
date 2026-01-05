import streamlit as st
import json
import os
import base64
import requests
import uuid
from PIL import Image

# ===========================
# CONFIGURAÇÕES
# ===========================
st.set_page_config(page_title="Admin - Futebol de Terça", layout="wide")

PASSWORD = st.secrets["ADMIN_PASSWORD"]

JOGADORES_FILE = "jogadores.json"
IMAGENS_DIR = "imagens/jogadores"

os.makedirs(IMAGENS_DIR, exist_ok=True)

# ===========================
# FUNÇÕES AUXILIARES
# ===========================
def carregar_jogadores():
    if not os.path.exists(JOGADORES_FILE):
        return {}
    with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_jogadores(jogadores):
    with open(JOGADORES_FILE, "w", encoding="utf-8") as f:
        json.dump(jogadores, f, indent=4, ensure_ascii=False)

def github_upload(path_local, repo_path, message):
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
    GITHUB_USER = st.secrets["GITHUB_USER"]

    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{repo_path}"

    with open(path_local, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()

    get_file = requests.get(url, headers=headers)
    sha = get_file.json().get("sha") if get_file.status_code == 200 else None

    payload = {
        "message": message,
        "content": content_b64
    }
    if sha:
        payload["sha"] = sha

    return requests.put(url, headers=headers, json=payload)

# ===========================
# LOGIN
# ===========================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Área Administrativa")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if senha == PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

# ===========================
# CADASTRO DE JOGADOR
# ===========================
st.title("⚽ Cadastro de Jogadores")

nome = st.text_input("Nome do jogador")
foto = st.file_uploader("Foto do jogador", type=["png", "jpg", "jpeg"])

if st.button("💾 Cadastrar jogador"):
    if not nome or foto is None:
        st.error("Preencha o nome e envie a foto.")
        st.stop()

    jogadores = carregar_jogadores()

    jogador_id = str(uuid.uuid4())[:8]
    ext = foto.name.split(".")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"

    img_filename = f"{jogador_id}.{ext}"
    img_path = os.path.join(IMAGENS_DIR, img_filename)

    image = Image.open(foto)
    image.save(img_path)

    jogadores[jogador_id] = {
        "nome": nome,
        "preco": 10,
        "gols": 0,
        "assistencias": 0,
        "imagem": f"{IMAGENS_DIR}/{img_filename}"
    }

    salvar_jogadores(jogadores)

    # Upload imagem
    github_upload(
        img_path,
        f"{IMAGENS_DIR}/{img_filename}",
        f"Adiciona imagem do jogador {nome}"
    )

    # Upload jogadores.json
    github_upload(
        JOGADORES_FILE,
        JOGADORES_FILE,
        f"Adiciona jogador {nome}"
    )

    st.success("Jogador cadastrado e salvo no GitHub!")
    st.rerun()

# ===========================
# LISTA DE JOGADORES
# ===========================
st.divider()
st.subheader("📋 Jogadores cadastrados")

jogadores = carregar_jogadores()

if not jogadores:
    st.info("Nenhum jogador cadastrado.")
else:
    for jid, j in jogadores.items():
        with st.container(border=True):
            cols = st.columns([1, 4])
            with cols[0]:
                if os.path.exists(j["imagem"]):
                    st.image(j["imagem"], width=120)
            with cols[1]:
                st.markdown(f"**{j['nome']}**")
                st.write(f"Gols: {j['gols']}")
                st.write(f"Assistências: {j['assistencias']}")
                st.write(f"Valor: {j['preco']}")
                st.caption(f"ID: {jid}")
