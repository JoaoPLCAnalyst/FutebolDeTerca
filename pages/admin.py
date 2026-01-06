# pages/admin.py
import streamlit as st
import os
import json
import re
import uuid
import io
import tempfile
from datetime import datetime
from PIL import Image

st.set_page_config(page_title="Admin - Futebol de Terça", page_icon="⚽")

# -----------------------
# Config
# -----------------------
JOGADORES_FILE = "database/jogadores.json"
IMAGENS_DIR = "imagens/jogadores"
os.makedirs(os.path.dirname(JOGADORES_FILE) or ".", exist_ok=True)
os.makedirs(IMAGENS_DIR, exist_ok=True)

# -----------------------
# Utilitários
# -----------------------
def slugify(text: str) -> str:
    text = (text or "").lower().strip()
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

def save_image_bytes_safe(raw_bytes: bytes, imagens_dir: str, base_name: str) -> str:
    """
    Salva bytes de imagem de forma atômica em imagens_dir com nome base_name.jpg.
    Retorna o caminho final do arquivo salvo.
    """
    os.makedirs(imagens_dir, exist_ok=True)
    filename = f"{base_name}.jpg"
    final_path = os.path.join(imagens_dir, filename)

    # cria arquivo temporário no mesmo diretório e substitui atomically
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=imagens_dir)
    os.close(tmp_fd)
    try:
        with open(tmp_path, "wb") as f:
            f.write(raw_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, final_path)
        return final_path
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        raise

def carregar_jogadores() -> dict:
    if not os.path.exists(JOGADORES_FILE):
        return {}
    try:
        with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def salvar_jogadores_atomic(jogadores_dict: dict, path: str) -> None:
    """
    Salva o JSON de jogadores de forma atômica (escreve em tmp e replace).
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=os.path.dirname(path) or ".")
    os.close(tmp_fd)
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(jogadores_dict, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        raise

# -----------------------
# Proteção: só expor se login global for admin
# -----------------------
if not st.session_state.get("is_admin"):
    st.title("Área Administrativa")
    st.warning("Acesso restrito: faça login com o usuário administrador para acessar esta página.")
    st.stop()

# -----------------------
# UI administrativa (autenticado globalmente)
# -----------------------
st.title("Área Administrativa — Cadastro de Jogadores")
st.markdown("Você está autenticado como administrador.")

# Formulário simples
with st.form(key="form_cadastro_jogador", clear_on_submit=False):
    nome = st.text_input("Nome do jogador")
    imagem = st.file_uploader("Imagem do jogador (PNG/JPG)", type=["png", "jpg", "jpeg"])
    submit = st.form_submit_button("Cadastrar jogador")

if submit:
    if not nome or imagem is None:
        st.error("Preencha o nome e envie uma imagem.")
    else:
        try:
            # 1) leia bytes imediatamente (obrigatório)
            raw_bytes = imagem.getvalue()

            # 2) opcional: redimensiona/processa antes de salvar
            processed_bytes = resize_image_bytes(raw_bytes)

            # 3) gere nome de arquivo seguro e salve de forma atômica
            base = f"{slugify(nome)}-{uuid.uuid4().hex[:8]}"
            img_path = save_image_bytes_safe(processed_bytes, IMAGENS_DIR, base)

            # 4) atualize jogadores em memória e salve atômico
            jogadores_dict = carregar_jogadores()
            player_id = f"{slugify(nome)}-{uuid.uuid4().hex[:8]}"
            novo_jogador = {
                "nome": nome,
                "valor": 10,
                "gols": 0,
                "assistencias": 0,
                "imagem": img_path,
                "criado_em": datetime.utcnow().isoformat() + "Z"
            }
            jogadores_dict[player_id] = novo_jogador
            salvar_jogadores_atomic(jogadores_dict, JOGADORES_FILE)

            # 5) reafirme sessão admin e atualize UI localmente (evita rerun desnecessário)
            st.session_state["is_admin"] = True
            st.success("✅ Jogador cadastrado com sucesso.")
            # atualiza variável local para refletir mudança sem forçar rerun
            jogadores = jogadores_dict

        except Exception as e:
            st.exception(e)
            st.error("Erro ao salvar jogador. Veja o detalhe acima.")

st.markdown("---")
st.markdown("### 📋 Jogadores cadastrados")

jogadores_dict = carregar_jogadores()

if not jogadores_dict:
    st.info("Nenhum jogador cadastrado")
else:
    sorted_items = sorted(jogadores_dict.items(), key=lambda kv: kv[1].get("nome", "").lower())
    for player_id, j in sorted_items:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            try:
                img_path = j.get("imagem", "")
                if img_path and os.path.exists(img_path):
                    st.image(img_path, width=80)
            except Exception:
                pass
        with col2:
            st.write(f"**{j.get('nome', '—')}**")
            st.write(f"Gols: {j.get('gols', 0)} | Assistências: {j.get('assistencias', 0)}")
            st.caption(f"ID: {player_id}")
        with col3:
            if st.button("🗑️ Excluir", key=f"del-{player_id}"):
                try:
                    nome_excl = j.get("nome", player_id)
                    jogadores_dict.pop(player_id, None)
                    salvar_jogadores_atomic(jogadores_dict, JOGADORES_FILE)
                    # remove imagem associada se existir
                    try:
                        img_to_remove = j.get("imagem", "")
                        if img_to_remove and os.path.exists(img_to_remove):
                            os.remove(img_to_remove)
                    except Exception:
                        pass
                    st.success(f"Jogador {nome_excl} excluído.")
                    # reafirma admin e rerun para atualizar lista
                    st.session_state["is_admin"] = True
                    st.rerun()
                except Exception as e:
                    st.exception(e)
                    st.error("Erro ao excluir jogador.")

st.markdown("---")
if st.button("Sair (admin)"):
    # logout local da página: remove apenas a flag admin
    if "is_admin" in st.session_state:
        del st.session_state["is_admin"]
    st.success("Logout efetuado.")
    st.rerun()
