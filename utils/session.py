"""
Gerenciador de sessão persistente.
Armazena sessões em memória (cache) e usa query_params para sobreviver ao refresh.
"""
import uuid
import streamlit as st


@st.cache_resource
def _sessoes_ativas():
    """Dict global de sessões ativas (persiste enquanto o servidor roda)."""
    return {}


def salvar_sessao(usuario_dict: dict) -> str:
    """Salva sessão e retorna o token."""
    token = str(uuid.uuid4())
    _sessoes_ativas()[token] = usuario_dict
    return token


def recuperar_sessao(token: str) -> dict:
    """Recupera dados do usuário pelo token."""
    return _sessoes_ativas().get(token)


def remover_sessao(token: str):
    """Remove uma sessão ativa."""
    _sessoes_ativas().pop(token, None)


def restaurar_login():
    """Tenta restaurar o login a partir do token na URL."""
    if "usuario" not in st.session_state:
        params = st.query_params
        token = params.get("session")
        if token:
            usuario = recuperar_sessao(token)
            if usuario:
                st.session_state["usuario"] = usuario
                st.session_state["session_token"] = token


def verificar_autenticacao():
    """Verifica se o usuário está autenticado. Se não, mostra aviso e para."""
    restaurar_login()
    if "usuario" not in st.session_state:
        st.warning("Por favor, faça login na página principal para acessar.")
        st.stop()
    return st.session_state["usuario"]
