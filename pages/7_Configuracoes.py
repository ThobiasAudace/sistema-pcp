import streamlit as st
import pandas as pd
from services.auth_service import listar_usuarios, criar_usuario, desativar_usuario, atualizar_usuario
from database.models import PERFIS

st.set_page_config(page_title="Configurações", page_icon="⚙️", layout="wide")

# Logo Kiosk Brands no topo
try:
    st.logo("logo.png", size="large")
except Exception:
    pass


from utils.auth import verificar_autenticacao
verificar_autenticacao()

usuario = st.session_state["usuario"]
if usuario["perfil"] != "ADMIN":
    st.error("Acesso negado. Apenas o perfil ADMIN pode acessar as configurações.")
    st.stop()

st.title("⚙️ Configurações do Sistema")

tab_usuarios, tab_parametros = st.tabs(["Gerenciamento de Usuários", "Parâmetros do Sistema"])

with tab_usuarios:
    st.header("Usuários Cadastrados")
    
    try:
        usuarios = listar_usuarios()
        if usuarios:
            df_users = pd.DataFrame([{
                "ID": u.id,
                "Nome": u.nome,
                "E-mail": u.email,
                "Perfil": u.perfil,
                "Ativo": u.ativo
            } for u in usuarios])
            
            editado = st.data_editor(
                df_users,
                use_container_width=True,
                hide_index=True,
                disabled=["ID", "Nome", "E-mail"],
                column_config={
                    "Ativo": st.column_config.CheckboxColumn("Ativo", help="Marque/desmarque para ativar/desativar o usuario"),
                    "Perfil": st.column_config.SelectboxColumn("Perfil", options=PERFIS, help="Selecione o perfil do usuario"),
                },
                key="editor_usuarios",
            )

            # Detectar mudanças nas colunas Ativo e Perfil e salvar
            mudou = not df_users["Ativo"].equals(editado["Ativo"]) or not df_users["Perfil"].equals(editado["Perfil"])
            if mudou:
                alterados = 0
                for idx, row in editado.iterrows():
                    ativo_orig = df_users.loc[idx, "Ativo"]
                    perfil_orig = df_users.loc[idx, "Perfil"]
                    ativo_novo = row["Ativo"]
                    perfil_novo = row["Perfil"]
                    user_id = int(row["ID"])

                    if ativo_orig != ativo_novo or perfil_orig != perfil_novo:
                        if user_id == usuario["id"] and ativo_orig != ativo_novo:
                            st.error("Voce nao pode desativar a si mesmo!")
                        else:
                            kwargs = {}
                            if ativo_orig != ativo_novo:
                                kwargs["ativo"] = ativo_novo
                            if perfil_orig != perfil_novo:
                                kwargs["perfil"] = perfil_novo
                            if kwargs:
                                atualizar_usuario(user_id, **kwargs)
                                alterados += 1
                if alterados > 0:
                    st.success(f"{alterados} usuario(s) atualizado(s)!")
                    st.rerun()
        else:
            st.info("Nenhum usuario cadastrado.")
    except Exception as e:
        st.error(f"Erro ao carregar usuarios: {e}")
        
    st.divider()
    st.header("Novo Usuário")
    with st.form("form_novo_usuario"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome")
            email = st.text_input("E-mail")
        with col2:
            senha = st.text_input("Senha", type="password")
            perfil = st.selectbox("Perfil", PERFIS)
            
        if st.form_submit_button("Criar Usuário"):
            if not nome or not email or not senha:
                st.error("Todos os campos são obrigatórios.")
            else:
                try:
                    criar_usuario(nome, email, senha, perfil)
                    st.success("Usuário criado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao criar usuário: {e}")

with tab_parametros:
    st.header("Parâmetros Gerais")
    st.info("Aqui você pode configurar variáveis globais do sistema, como número inicial de lote e capacidade do misturador.")
    
    # Estes valores geralmente viriam do banco de dados (tabela de configurações)
    # Como não foi especificado um serviço exato para isso, usamos session_state para demonstrar
    if "param_ultimo_lote" not in st.session_state:
        st.session_state["param_ultimo_lote"] = 1000
    if "param_capacidade" not in st.session_state:
        st.session_state["param_capacidade"] = 500
        
    with st.form("form_parametros"):
        novo_lote = st.number_input("Último Número de Lote", value=st.session_state["param_ultimo_lote"], min_value=1)
        nova_cap = st.number_input("Capacidade do Misturador (Litros)", value=st.session_state["param_capacidade"], min_value=1)
        
        if st.form_submit_button("Salvar Parâmetros"):
            st.session_state["param_ultimo_lote"] = novo_lote
            st.session_state["param_capacidade"] = nova_cap
            st.success("Parâmetros atualizados com sucesso!")
