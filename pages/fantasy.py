import streamlit as st
from utils.storage import carregar_lineup, salvar_lineup

# proteção: só continua se estiver logado
if not st.session_state.get("logged_in"):
    st.info("Acesse com sua conta para ver e editar seu time.")
    st.stop()

user_id = st.session_state.get("user_id")
if not user_id:
    st.error("Erro de sessão. Faça login novamente.")
    st.stop()

# carregar lineup do usuário autenticado
lineup = carregar_lineup(user_id)

st.title(f"Montar Time — {st.session_state.get('perfil', {}).get('nome_apresentacao', user_id)}")

# UI para editar lineup (exemplo simplificado)
# ... sua lógica de seleção de jogadores aqui ...
# suponha que `novo_lineup` seja o dicionário final a salvar

if st.button("Salvar Time"):
    # validações adicionais (ex.: número de jogadores, posições)
    try:
        salvar_lineup(user_id, novo_lineup)
        st.success("Time salvo com sucesso.")
    except Exception as e:
        st.error("Erro ao salvar o time.")
