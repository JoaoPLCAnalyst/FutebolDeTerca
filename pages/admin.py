import streamlit as st
import json
import base64
import requests
from datetime import datetime

st.set_page_config(page_title="Admin", page_icon="⚙️")

# ===============================
# CONFIGURAÇÕES
# ===============================
JOGADORES_FILE = "database/jogadores.json"
IMAGENS_DIR = "imagens/jogadores"

GITHUB_USER = st.secrets["GITHUB_USER"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# ===============================
# FUNÇÕES GITHUB
# ===============================

def github_get_file(path):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    return None


def github_put_file(path, content_bytes, message, sha=None):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode(),
        "branch": GITHUB_BRANCH
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=HEADERS, json=payload)
    if r.status_code not in [200, 201]:
        st.error(f"Erro GitHub ({path}): {r.json()}")
        st.stop()


# ===============================
# INTERFACE
# ===============================

st.title("⚙️ Admin - Cadastro de Jogador")

nome = st.text_input("Nome do jogador")
posicao = st.text_input("Posição")
imagem = st.file_uploader("Foto do jogador", type=["png", "jpg", "jpeg"])

if st.button("Cadastrar jogador"):

    if not nome or not posicao or not imagem:
        st.warning("Preencha todos os campos")
        st.stop()

    # ===============================
    # 1️⃣ CARREGA JOGADORES.JSON
    # ===============================
    file_data = github_get_file(JOGADORES_FILE)

    if file_data:
        jogadores = json.loads(base64.b64decode(file_data["content"]))
        sha_json = file_data["sha"]
    else:
        jogadores = []
        sha_json = None

    # ===============================
    # 2️⃣ SALVA IMAGEM
    # ===============================
    ext = imagem.name.split(".")[-1]
    img_filename = f"{nome.lower().replace(' ', '_')}.{ext}"
    img_path = f"{IMAGENS_DIR}/{img_filename}"

    github_put_file(
        img_path,
        imagem.getvalue(),
        f"Adiciona imagem do jogador {nome}"
    )

    # ===============================
    # 3️⃣ ATUALIZA JSON
    # ===============================
    jogador = {
        "nome": nome,
        "posicao": posicao,
        "imagem": img_path,
        "criado_em": datetime.now().isoformat()
    }

    jogadores.append(jogador)

    github_put_file(
        JOGADORES_FILE,
        json.dumps(jogadores, indent=2).encode(),
        f"Adiciona jogador {nome}",
        sha=sha_json
    )

    # ===============================
    # 4️⃣ SUCESSO
    # ===============================
    st.success("✅ Jogador cadastrado e commitado no GitHub!")
