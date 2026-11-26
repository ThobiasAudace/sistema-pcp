import streamlit as st
import pandas as pd
from services.estoque_service import importar_estoque_planilha, listar_estoque, registrar_entrada, registrar_saida, listar_movimentacoes

st.set_page_config(page_title="Controle de Estoque", page_icon="📦", layout="wide")

# Logo Kiosk Brands no topo
try:
    st.logo("logo.png", size="large")
except Exception:
    pass


from utils.auth import verificar_autenticacao
verificar_autenticacao()

usuario = st.session_state["usuario"]
if usuario["perfil"] not in ["ADMIN", "SUPERVISOR"]:
    st.error("Acesso negado. Apenas ADMIN e SUPERVISOR podem gerenciar estoque.")
    st.stop()

st.title("📦 Controle de Estoque de Essências")

tab_importar, tab_manual = st.tabs(["Importar Planilha", "Controle Manual"])

with tab_importar:
    st.header("Importar Estoque Base")
    arquivo_upload = st.file_uploader("Selecione a planilha de Estoque de Essências (.xlsx)", type=['xlsx'])
    
    if st.button("Importar Estoque"):
        if arquivo_upload is not None:
            with st.spinner("Importando dados..."):
                try:
                    bytes_data = arquivo_upload.getvalue()
                    resultado = importar_estoque_planilha(bytes_data)
                    st.success(f"Estoque importado com sucesso! {resultado.get('total_importados', 0)} itens atualizados.")
                except Exception as e:
                    st.error(f"Erro ao importar estoque: {e}")
        else:
            st.warning("Selecione um arquivo primeiro.")
            
    st.divider()
    st.subheader("Estoque Atual")
    
    busca = st.text_input("Buscar essência")
    
    try:
        from utils.helpers import fmt_dec
        estoque_atual = listar_estoque(busca=busca if busca else None)
        if estoque_atual:
            df_estoque = pd.DataFrame([{
                "Essencia": e.essencia,
                "Perfume": e.perfume or '-',
                "%": e.pct or 0,
                "Qtd Estoque (kg)": fmt_dec(e.qtd_estoque or 0),
                "OP Aberta": fmt_dec(e.op_aberta or 0),
                "Qtd NF": fmt_dec(e.qtd_nf or 0),
                "Total": fmt_dec(e.total or 0),
                "Data Ref.": e.data_referencia
            } for e in estoque_atual])
            
            st.dataframe(
                df_estoque,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhum dado de estoque encontrado.")
    except Exception as e:
        st.error(f"Erro ao buscar estoque: {e}")

with tab_manual:
    st.header("Registrar Movimentação Manual")
    
    try:
        estoque_lista = listar_estoque()
        opcoes_essencia = [e.essencia for e in estoque_lista] if estoque_lista else ["Sem essências cadastradas"]
    except:
        opcoes_essencia = ["Erro ao carregar essências"]
        
    with st.form("form_movimentacao"):
        col1, col2 = st.columns(2)
        with col1:
            essencia_sel = st.selectbox("Essência", opcoes_essencia)
            tipo_mov = st.radio("Tipo de Movimentação", ["ENTRADA", "SAIDA"])
            qtd = st.number_input("Quantidade (kg)", min_value=0.01, format="%.2f")
        with col2:
            referencia = st.text_input("Referência (Lote/NF)")
            obs = st.text_area("Observação")
            
        btn_salvar = st.form_submit_button("Registrar")
        
        if btn_salvar:
            if essencia_sel == "Sem essências cadastradas" or essencia_sel == "Erro ao carregar essências":
                st.error("Selecione uma essência válida.")
            else:
                try:
                    if tipo_mov == "ENTRADA":
                        registrar_entrada(essencia_sel, qtd, referencia, obs, usuario["id"])
                    else:
                        registrar_saida(essencia_sel, qtd, referencia, obs, usuario["id"])
                    st.success("Movimentação registrada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao registrar movimentação: {e}")
                    
    st.divider()
    st.subheader("Histórico de Movimentações")
    
    try:
        movimentacoes = listar_movimentacoes(limit=50)
        if movimentacoes:
            from utils.helpers import fmt_dec
            df_mov = pd.DataFrame([{
                "Data": m.criado_em,
                "Essencia": m.essencia,
                "Tipo": m.tipo,
                "Qtd (kg)": fmt_dec(m.quantidade, 2),
                "Referencia": m.referencia or '',
                "OBS": m.observacao or ''
            } for m in movimentacoes])
            st.dataframe(df_mov, use_container_width=True)
        else:
            st.info("Nenhuma movimentação registrada.")
    except Exception as e:
        st.error(f"Erro ao buscar movimentações: {e}")
