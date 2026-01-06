import streamlit as st
import json
import os
import re
import uuid
import io
from PIL import Image
import base64, requests

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Admin - Futebol de Terça", page_icon="⚽")

PASSWORD = st.secrets["ADMIN_PASSWORD"]

JOGADORES_FILE = "database/jogadores.json"
IMAGENS_DIR = "imagens/jogadores"
os.makedirs("database", exist_ok=True)
os.makedirs(IMAGENS_DIR, exist_ok=True)

# =========================
# GITHUB CONFIG (opcional)
# =========================
GITHUB_USER = st.secrets.get("GITHUB_USER", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

def github_upload(path_local, repo_path, message):
    """Envia arquivo local ao GitHub (opcional)."""
    if not GITHUB_USER or not GITHUB_REPO or not GITHUB_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{repo_path}"
    with open(path_local, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    get_file = requests.get(url, headers=headers)
    sha = get_file.json().get("sha") if get_file.status_code == 200 else None
    payload = {"message": message, "content": content_b64}
    if sha:
        payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload)

# =========================
# UTILITÁRIOS
# =========================
def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\-_ ]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text

def resize_image_bytes(uploaded_file_bytes: bytes, max_size=(800, 800), quality=85) -> bytes:
    buf = io.BytesIO(uploaded_file_bytes)
    img = Image.open(buf)
    img = img.convert("RGB")
    img.thumbnail(max_size)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality)
    out.seek(0)
    return out.read()

def carregar_jogadores():
    if not os.path.exists(JOGADORES_FILE):
        return {}
    with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_jogadores(jogadores_dict):
    with open(JOGADORES_FILE, "w", encoding="utf-8") as f:
        json.dump(jogadores_dict, f, indent=2, ensure_ascii=False)

# =========================
# REQUISITO: estar logado como admin (global)
# =========================
# A página só será exibida se a flag global de admin estiver presente.
# Se você usa outra página de login que define st.session_state["is_admin"] = True,
# o acesso será liberado. Caso contrário, a execução é interrompida.
if not st.session_state.get("is_admin"):
    st.title("🔐 Área Administrativa")
    st.warning("Acesso restrito: faça login com o usuário administrador na página de login para acessar esta área.")
    st.stop()

# =========================
# LOGIN LOCAL (mantido conforme solicitado)
# =========================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Área Administrativa (login local)")
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
# CADASTRAR JOGADOR
# =========================
if st.button("Cadastrar jogador"):
    if not nome or imagem is None:
        st.error("Preencha o nome e envie uma imagem")
        st.stop()

    # Processar imagem
    ext = imagem.name.split(".")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"
    img_filename = f"{slugify(nome)}-{uuid.uuid4().hex[:8]}.jpg"
    img_path = os.path.join(IMAGENS_DIR, img_filename)

    raw_bytes = imagem.getvalue()
    processed_bytes = resize_image_bytes(raw_bytes)

    with open(img_path, "wb") as f:
        f.write(processed_bytes)

    # Atualizar jogadores.json
    jogadores_dict = carregar_jogadores()
    player_id = f"{slugify(nome)}-{uuid.uuid4().hex[:8]}"
    novo_jogador = {
        "nome": nome,
        "valor": 10,
        "gols": 0,
        "assistencias": 0,
        "imagem": img_path
    }
    jogadores_dict[player_id] = novo_jogador
    salvar_jogadores(jogadores_dict)

    # Upload opcional ao GitHub
    github_upload(img_path, f"{IMAGENS_DIR}/{img_filename}", f"Adiciona imagem do jogador {nome}")
    github_upload(JOGADORES_FILE, JOGADORES_FILE, f"Atualiza jogadores.json com {nome}")

    st.success("✅ Jogador cadastrado!")
    st.rerun()

# =========================
# LISTA DE JOGADORES
# =========================
st.markdown("### 📋 Jogadores cadastrados")

jogadores_dict = carregar_jogadores()

if not jogadores_dict:
    st.info("Nenhum jogador cadastrado")
else:
    sorted_items = sorted(jogadores_dict.items(), key=lambda kv: kv[1].get("nome", "").lower())
    for player_id, j in sorted_items:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if os.path.exists(j["imagem"]):
                st.image(j["imagem"], width=80)
        with col2:
            st.write(f"**{j.get('nome', '—')}**")
            st.write(f"Gols: {j.get('gols', 0)} | Assistências: {j.get('assistencias', 0)}")
            st.caption(f"ID: {player_id}")
        with col3:
            if st.button("🗑️ Excluir", key=f"del-{player_id}"):
                jogadores_dict.pop(player_id)
                salvar_jogadores(jogadores_dict)
                try:
                    os.remove(j["imagem"])
                except Exception:
                    pass
                github_upload(JOGADORES_FILE, JOGADORES_FILE, f"Remove jogador {j['nome']}")
                st.success(f"Jogador {j['nome']} excluído!")
                st.rerun()
# ------------------------
# Iniciar rodada (Admin)
# ------------------------
import tempfile
from datetime import datetime, timezone

def _write_atomic(path, data_bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    os.close(fd)
    with open(tmp, "wb") as f:
        f.write(data_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def next_rodada_id_for_date(base_dir, date_str, prefix="rodada", pad=2):
    """
    Gera um id do tipo YYYY-MM-DD-rodada-XX garantindo unicidade por tentativa.
    """
    os.makedirs(base_dir, exist_ok=True)
    existing = [n for n in os.listdir(base_dir) if n.startswith(f"{date_str}-{prefix}-")]
    start = len(existing) + 1
    for n in range(start, start + 1000):
        seq = str(n).zfill(pad)
        rodada_id = f"{date_str}-{prefix}-{seq}"
        path = os.path.join(base_dir, rodada_id)
        # tenta criar a pasta de forma exclusiva
        try:
            os.makedirs(path)
            # removemos a pasta criada para que a função chamadora crie a estrutura completa
            os.rmdir(path)
            return rodada_id
        except FileExistsError:
            continue
        except Exception:
            # se não conseguir criar, continua tentando
            continue
    raise RuntimeError("Não foi possível gerar rodada_id único")

def create_rodada(base_dir, nome, admin_user=None, github_upload_enabled=False):
    """
    Cria a estrutura:
      database/rodadas/<rodada_id>/meta.json
      database/rodadas/<rodada_id>/matches/  (diretório)
    Retorna (ok, rodada_id, mensagem)
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    try:
        rodada_id = next_rodada_id_for_date(base_dir, date_str)
    except Exception as e:
        return False, None, f"Erro ao gerar id da rodada: {e}"

    rodada_dir = os.path.join(base_dir, rodada_id)
    matches_dir = os.path.join(rodada_dir, "matches")
    os.makedirs(matches_dir, exist_ok=True)

    meta = {
        "id": rodada_id,
        "nome": nome or f"Rodada {date_str}",
        "admin": admin_user or "",
        "inicio": datetime.now(timezone.utc).isoformat(),
        "fim": None,
        "status": "open",
        "matches": []
    }

    meta_path = os.path.join(rodada_dir, "meta.json")
    try:
        _write_atomic(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
    except Exception as e:
        return False, None, f"Falha ao gravar meta.json: {e}"

    # opcional: upload para GitHub
    if github_upload_enabled and GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN:
        try:
            ok, out = github_upload(meta_path, f"database/rodadas/{rodada_id}/meta.json", f"Cria rodada {rodada_id}")
            if not ok:
                return True, rodada_id, f"Rodada criada localmente, mas falha ao enviar para GitHub: {out}"
        except Exception as e:
            return True, rodada_id, f"Rodada criada localmente, mas erro no upload GitHub: {e}"

    return True, rodada_id, "Rodada criada com sucesso"

# UI para iniciar rodada
st.markdown("---")
st.subheader("🟢 Iniciar nova rodada")
rodada_nome = st.text_input("Nome da rodada (opcional)", value="")
admin_user = st.session_state.get("user_id") or st.session_state.get("perfil") or "admin"
github_enabled = bool(GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN)

if st.button("Iniciar rodada"):
    ok, rodada_id, msg = create_rodada(os.path.join("database", "rodadas"), rodada_nome, admin_user=admin_user, github_upload_enabled=github_enabled)
    if ok:
        st.success(f"Rodada iniciada: **{rodada_id}**")
        st.info(msg)
    else:
        st.error(msg)
    st.rerun()

# Lista rápida de rodadas abertas (informativa)
st.markdown("Rodadas abertas")
rodadas_base = os.path.join("database", "rodadas")
if os.path.exists(rodadas_base):
    rows = []
    for name in sorted(os.listdir(rodadas_base)):
        meta_path = os.path.join(rodadas_base, name, "meta.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("status") == "open":
                    rows.append((name, meta.get("nome"), meta.get("inicio"), len(meta.get("matches", []))))
            except Exception:
                continue
    if not rows:
        st.write("Nenhuma rodada aberta")
    else:
        for r in rows:
            st.write(f"- **{r[0]}** — {r[1]} — início: {r[2]} — partidas: {r[3]}")
else:
    st.write("Nenhuma rodada encontrada")
