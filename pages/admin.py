import streamlit as st
import json
import base64
import requests
import io
import re
import uuid
import time
from PIL import Image

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Admin - Futebol de Terça", page_icon="⚽")

# Segredos (defina em st.secrets)
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
# UTILITÁRIOS
# =========================
def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\-_ ]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text

def sanitize_filename(name: str, ext: str) -> str:
    base = slugify(name)
    unique = uuid.uuid4().hex[:8]
    return f"{base}-{unique}.{ext}"

def resize_image_bytes(uploaded_file_bytes: bytes, max_size=(800, 800), quality=85) -> bytes:
    buf = io.BytesIO(uploaded_file_bytes)
    img = Image.open(buf)
    img = img.convert("RGB")
    img.thumbnail(max_size)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality)
    out.seek(0)
    return out.read()

def is_image_mime(mime_type: str) -> bool:
    return mime_type is not None and mime_type.startswith("image/")

def normalize_jogadores_content(content):
    """
    Garante que o retorno seja um dicionário:
    - Se o arquivo estiver vazio ou for 404 -> {}
    - Se for lista -> converte para dict com chaves geradas
    - Se já for dict -> retorna como está
    """
    if content is None:
        return {}
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        result = {}
        for item in content:
            # tenta usar nome como base de id; garante unicidade com uuid
            base = slugify(item.get("nome", "jogador"))
            unique = uuid.uuid4().hex[:8]
            key = f"{base}-{unique}"
            result[key] = item
        return result
    # caso inesperado
    return {}

# =========================
# FUNÇÕES GITHUB
# =========================
def github_read_file(path):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        parsed = json.loads(content)
        normalized = normalize_jogadores_content(parsed)
        return normalized, data["sha"]
    elif r.status_code == 404:
        # Arquivo não existe ainda
        return {}, None
    else:
        st.error(f"Erro ao ler {path}: status {r.status_code}")
        raise RuntimeError(f"GitHub read error {r.status_code}")

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
    if r.status_code in (200, 201):
        return r.json()
    elif r.status_code == 422:
        # validação falhou (ex: arquivo muito grande ou conflito)
        raise RuntimeError("Erro 422: validação falhou (arquivo muito grande ou conflito).")
    else:
        st.error(f"Erro ao salvar {path}: status {r.status_code}")
        raise RuntimeError(f"GitHub save error {r.status_code}")

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
imagem = st.file_uploader("Imagem do jogador (PNG/JPG)", type=["png", "jpg", "jpeg"])

# =========================
# CADASTRAR JOGADOR (AGORA COMO DICIONÁRIO)
# =========================
if st.button("Cadastrar jogador"):
    if not nome or imagem is None:
        st.error("Preencha o nome e envie uma imagem")
        st.stop()

    # Validações básicas da imagem
    try:
        mime = imagem.type
        size_bytes = imagem.size if hasattr(imagem, "size") else len(imagem.getvalue())
    except Exception:
        mime = None
        size_bytes = len(imagem.getvalue())

    if not is_image_mime(mime):
        st.error("Arquivo enviado não parece ser uma imagem válida")
        st.stop()

    if size_bytes > 10 * 1024 * 1024:
        st.error("Imagem muito grande. Limite de 10 MB.")
        st.stop()

    # 1️⃣ Lê jogadores atuais do GitHub (normalizado para dict)
    try:
        jogadores_dict, sha_json = github_read_file(JOGADORES_FILE)
    except Exception:
        st.error("Não foi possível ler jogadores.json no GitHub.")
        st.stop()

    # 2️⃣ Prepara e salva imagem no GitHub
    ext = imagem.name.split(".")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"

    # Gera nome de arquivo seguro e único
    img_filename = sanitize_filename(nome, ext)
    img_path = f"{IMAGENS_DIR}/{img_filename}"

    # Redimensiona/comprime imagem para JPEG
    try:
        raw_bytes = imagem.getvalue()
        processed_bytes = resize_image_bytes(raw_bytes, max_size=(800, 800), quality=85)
    except Exception:
        st.error("Erro ao processar a imagem enviada.")
        st.stop()

    # Faz upload da imagem primeiro
    try:
        github_save_file(
            img_path,
            processed_bytes,
            f"Adiciona imagem do jogador {nome}"
        )
    except Exception:
        st.error("Falha ao salvar a imagem no GitHub.")
        st.stop()

    # 3️⃣ Cria novo jogador e adiciona ao dicionário com ID único
    player_id = f"{slugify(nome)}-{uuid.uuid4().hex[:8]}"
    novo_jogador = {
        "nome": nome,
        "valor": 10,
        "gols": 0,
        "assistencias": 0,
        "imagem": img_path
    }

    # Evita sobrescrever por acidente: se o id já existir (muito improvável), gera outro
    while player_id in jogadores_dict:
        player_id = f"{slugify(nome)}-{uuid.uuid4().hex[:8]}"

    jogadores_dict[player_id] = novo_jogador

    # 4️⃣ Commit do jogadores.json com re-tentativa em caso de conflito
    max_attempts = 3
    attempt = 0
    success = False
    while attempt < max_attempts and not success:
        attempt += 1
        try:
            # Serializa o dicionário para JSON (mantendo chaves)
            github_save_file(
                JOGADORES_FILE,
                json.dumps(jogadores_dict, indent=2, ensure_ascii=False).encode("utf-8"),
                f"Adiciona jogador {nome}",
                sha=sha_json
            )
            success = True
        except RuntimeError:
            # Possível conflito: re-leia o arquivo e tente novamente
            if attempt < max_attempts:
                time.sleep(1)
                try:
                    jogadores_dict, sha_json = github_read_file(JOGADORES_FILE)
                except Exception:
                    st.error("Erro ao re-ler jogadores.json após conflito.")
                    st.stop()
                # Re-aplica a adição se ainda não existir (evita duplicar)
                exists = any(j.get("nome") == novo_jogador["nome"] and j.get("imagem") == novo_jogador["imagem"] for j in jogadores_dict.values())
                if not exists:
                    # Gera novo id se necessário
                    new_id = player_id
                    while new_id in jogadores_dict:
                        new_id = f"{slugify(nome)}-{uuid.uuid4().hex[:8]}"
                    jogadores_dict[new_id] = novo_jogador
                continue
            else:
                st.error("Não foi possível salvar jogadores.json após várias tentativas.")
                st.stop()
        except Exception:
            st.error("Erro inesperado ao salvar jogadores.json.")
            st.stop()

    if success:
        st.success("✅ Jogador cadastrado e salvo no GitHub!")
        st.experimental_rerun()

# =========================
# LISTA DE JOGADORES (LEITURA COMO DICIONÁRIO)
# =========================
st.markdown("### 📋 Jogadores cadastrados")

try:
    jogadores_dict, _ = github_read_file(JOGADORES_FILE)
except Exception:
    st.error("Não foi possível carregar a lista de jogadores.")
    st.stop()

if not jogadores_dict:
    st.info("Nenhum jogador cadastrado")
else:
    # Ordena por nome para exibição (opcional)
    sorted_items = sorted(jogadores_dict.items(), key=lambda kv: kv[1].get("nome", "").lower())
    for player_id, j in sorted_items:
        with st.container():
            col1, col2 = st.columns([1, 4])

            with col1:
                img_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{j['imagem']}"
                st.image(img_url, width=80)

            with col2:
                st.write(f"**{j.get('nome', '—')}**")
                st.write(f"Gols: {j.get('gols', 0)} | Assistências: {j.get('assistencias', 0)}")
                # Exibe o id (útil para operações futuras de edição/remoção)
                st.caption(f"ID: {player_id}")
