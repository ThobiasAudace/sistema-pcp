import streamlit as st
import pandas as pd
from services.cadastro_service import listar_produtos, criar_produto, atualizar_produto, buscar_produto_por_sku

st.set_page_config(page_title="Cadastro de Produtos", layout="wide")

# Logo Kiosk Brands no topo
try:
    st.logo("logo.png", size="large")
except Exception:
    pass

from utils.auth import verificar_autenticacao
verificar_autenticacao()

usuario = st.session_state["usuario"]
if usuario["perfil"] not in ["ADMIN", "SUPERVISOR"]:
    st.error("Acesso negado. Apenas ADMIN e SUPERVISOR podem gerenciar cadastros.")
    st.stop()

st.title("Cadastro de Produtos")

# ─── Botão principal: Adicionar Produto Novo ──────────────────────────
col_header1, col_header2 = st.columns([3, 1])
with col_header2:
    adicionar_novo = st.button("➕ Adicionar Produto Novo", use_container_width=True, type="primary")

# ─── Modal de Adicionar Produto ──────────────────────────────────────
if adicionar_novo:
    st.session_state["mostrar_form_novo"] = True

if st.session_state.get("mostrar_form_novo", False):
    st.markdown("---")
    st.subheader("Novo Produto")
    
    with st.form("form_novo_produto", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            n_sku = st.text_input("SKU *", placeholder="Ex: 4730")
            n_nome = st.text_input("Descrição do Produto *", placeholder="Ex: CHARM 30ML")
        
        with col2:
            linhas_opcoes = ["50ML", "30ML", "BODY SPLASH", "SPECIAL", "TESTER", "CORPO", "ECOMMERCE", "MEMORIAS"]
            n_linha = st.selectbox("Linha", linhas_opcoes)
            n_volume = st.selectbox("Volume (mL)", [50, 30, 100, 120, 200, 25], index=0)
        
        with col3:
            n_essencia = st.text_input("Essência", placeholder="(Opcional)")
            n_pct = st.number_input("% Essência", min_value=0.0, max_value=1.0, value=0.0, step=0.01, format="%.2f")
            n_linha_prod = st.selectbox("Linha de Produção", ["AUTOMATICA", "MANUAL"],
                                         index=0 if n_volume == 50 else 1 if 'n_volume' in dir() else 0)
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
        with col_btn1:
            btn_salvar = st.form_submit_button("Salvar Produto", type="primary", use_container_width=True)
        with col_btn2:
            btn_cancelar = st.form_submit_button("Cancelar", use_container_width=True)
        
        if btn_salvar:
            if not n_sku or not n_nome:
                st.error("SKU e Descrição são obrigatórios.")
            else:
                # Verificar se SKU já existe
                existente = buscar_produto_por_sku(n_sku.strip())
                if existente:
                    st.error(f"SKU {n_sku} já existe: {existente.nome_produto}")
                else:
                    try:
                        criar_produto({
                            "sku": n_sku.strip(),
                            "nome_produto": n_nome.strip().upper(),
                            "linha_comercial": n_linha,
                            "volume_ml": n_volume,
                            "linha_producao": n_linha_prod,
                            "essencia": n_essencia.strip() if n_essencia else None,
                            "pct_essencia": n_pct if n_pct > 0 else None,
                            "ativo": True
                        })
                        st.success(f"Produto '{n_nome}' (SKU: {n_sku}) cadastrado com sucesso! Também adicionado na planilha de SKUs.")
                        st.session_state["mostrar_form_novo"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar: {e}")
        
        if btn_cancelar:
            st.session_state["mostrar_form_novo"] = False
            st.rerun()

st.markdown("---")

# ─── Lista de Produtos ───────────────────────────────────────────────
st.subheader("Produtos Cadastrados")

col_busca1, col_busca2 = st.columns(2)
with col_busca1:
    busca_nome = st.text_input("Buscar por SKU ou Nome", placeholder="Digite para filtrar...")
with col_busca2:
    linha_filtro = st.selectbox("Linha de Produção", ["Todas", "AUTOMATICA", "MANUAL"])

try:
    linha_query = None if linha_filtro == "Todas" else linha_filtro
    busca_query = busca_nome if busca_nome else None
    
    produtos = listar_produtos(ativo=True, busca=busca_query, linha_producao=linha_query)
    
    if produtos:
        st.caption(f"{len(produtos)} produtos encontrados")
        
        df_prod = pd.DataFrame([{
            "SKU": p.sku or '-',
            "Produto": p.nome_produto,
            "Linha": p.linha_comercial or '-',
            "Essencia": p.essencia or '-',
            "%": f"{p.pct_essencia*100:.0f}%".replace(".", ",") if p.pct_essencia else '-',
            "Volume (mL)": p.volume_ml or '-',
            "Linha Prod.": p.linha_producao or '-',
        } for p in produtos])
        
        st.dataframe(df_prod, use_container_width=True, hide_index=True, height=500)
    else:
        st.info("Nenhum produto encontrado.")
except Exception as e:
    st.error(f"Erro ao carregar produtos: {e}")
