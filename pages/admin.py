import streamlit as st
import json
import base64
import requests
from PIL import Image

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Admin - Futebol de Terça", page_icon="⚽")

PASSWORD = st.secrets["ADMIN_PASSWORD"]

JOGADORES_FILE = "database/jogadores.json"
IMAGENS_DIR = "imagens/jogadores"

# =========================
# GITHUB CONFIG
# =========================
GITHUB_USER = st.secrets["GITHUB_USER"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# =========================
# FUNÇÕES GITHUB
# =========================
def github_read_file(path):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=HEADERS)

    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]

    return [], None


def github_save_file(path, content_bytes, message, sha=None):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}"

    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": GITHUB_BRANCH
    }

    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=HEADERS, json=payload)

    if r.status_code not in [200, 201]:
        st.error(f"Erro ao salvar {path}")
        st.json(r.json())
        st.stop()

# =========================
# LOGIN
# =========================
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

# =========================
# INTERFACE
# =========================
st.title("⚽ Cadastro de Jogadores")

nome = st.text_input("Nome do jogador")
imagem = st.file_uploader("Imagem do jogador", type=["png", "jpg", "jpeg"])

# =========================
# CADASTRAR JOGADOR
# =========================
if st.button("Cadastrar jogador"):
    if not nome or imagem is None:
        st.error("Preencha o nome e envie uma imagem")
        st.stop()

    # 1️⃣ Lê jogadores atuais do GitHub
    jogadores, sha_json = github_read_file(JOGADORES_FILE)

    # 2️⃣ Salva imagem no GitHub
    ext = imagem.name.split(".")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"

    img_filename = f"{nome.lower().replace(' ', '_')}.{ext}"
    img_path = f"{IMAGENS_DIR}/{img_filename}"

    github_save_file(
        img_path,
        imagem.getvalue(),
        f"Adiciona imagem do jogador {nome}"
    )

    # 3️⃣ Adiciona jogador no JSON
    novo_jogador = {
        "nome": nome,
        "valor": 10,
        "gols": 0,
        "assistencias": 0,
        "imagem": img_path
    }

    jogadores.append(novo_jogador)

    # 4️⃣ Commit do jogadores.json
    github_save_file(
        JOGADORES_FILE,
        json.dumps(jogadores, indent=2, ensure_ascii=False).encode("utf-8"),
        f"Adiciona jogador {nome}",
        sha=sha_json
    )

    st.success("✅ Jogador cadastrado e salvo no GitHub!")
    st.rerun()

# =========================
# LISTA DE JOGADORES
# =========================
st.markdown("### 📋 Jogadores cadastrados")

jogadores, _ = github_read_file(JOGADORES_FILE)

if not jogadores:
    st.info("Nenhum jogador cadastrado")
else:
    for j in jogadores:
        with st.container(border=True):
            col1, col2 = st.columns([1, 4])

            with col1:
                img_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{j['imagem']}"
                st.image(img_url, width=80)

            with col2:
                st.write(f"**{j['nome']}**")
                st.write(f"Gols: {j['gols']} | Assistências: {j['assistencias']}")
