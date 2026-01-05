import json
import streamlit as st
from github import Github

# =========================
# CONFIGURAÇÃO INICIAL
# =========================

st.set_page_config(
    page_title="Futebol de Terça",
    layout="wide"
)

# =========================
# FUNÇÕES DE DADOS
# =========================

def carregar_jogadores():
    with open("jogadores.json", "r", encoding="utf-8") as f:
        return json.load(f)


def conectar_github():
    g = Github(st.secrets["GITHUB_TOKEN"])
    repo = g.get_repo(st.secrets["GITHUB_REPO"])
    return repo


def salvar_jogadores_no_github(jogadores, mensagem_commit):
    repo = conectar_github()

    arquivo = repo.get_contents("jogadores.json")
    conteudo = json.dumps(jogadores, indent=4, ensure_ascii=False)

    repo.update_file(
        path="jogadores.json",
        message=mensagem_commit,
        content=conteudo,
        sha=arquivo.sha
    )

# =========================
# INTERFACE - APP PÚBLICO
# =========================

st.title("⚽ Futebol de Terça")

jogadores = carregar_jogadores()

st.subheader("Jogadores disponíveis")

dados_tabela = []

for id_jogador, dados in jogadores.items():
    dados_tabela.append({
        "ID": id_jogador,
        "Nome": dados["nome"],
        "Posição": dados["posicao"],
        "Valor": dados["valor"],
        "Gols": dados["gols"],
        "Assistências": dados["assistencias"]
    })

st.dataframe(dados_tabela, use_container_width=True)

# =========================
# ÁREA ADMIN
# =========================

st.divider()
st.subheader("🔒 Área Administrativa")

senha = st.text_input("Senha de administrador", type="password")

if senha == st.secrets["ADMIN_PASSWORD"]:

    st.success("Acesso autorizado")

    ids = list(jogadores.keys())
    id_selecionado = st.selectbox("Selecione o jogador", ids)

    jogador = jogadores[id_selecionado]

    col1, col2 = st.columns(2)

    with col1:
        gols = st.number_input(
            "Gols",
            min_value=0,
            value=jogador["gols"]
        )

    with col2:
        assistencias = st.number_input(
            "Assistências",
            min_value=0,
            value=jogador["assistencias"]
        )

    if st.button("💾 Salvar alterações"):
        jogadores[id_selecionado]["gols"] = gols
        jogadores[id_selecionado]["assistencias"] = assistencias

        salvar_jogadores_no_github(
            jogadores,
            f"Atualiza estatísticas - Jogador {id_selecionado}"
        )

        st.success("Dados atualizados e commitados no GitHub")

elif senha:
    st.error("Senha incorreta")
