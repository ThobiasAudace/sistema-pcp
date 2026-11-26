import streamlit as st
import datetime
import pandas as pd
import traceback

from services.programacao_service import criar_sessao, gerar_programacao
from services.cadastro_service import buscar_produto_por_sku, listar_produtos

st.set_page_config(page_title="Criar Programacao", layout="wide")

try:
    st.logo("logo.png", size="large")
except Exception:
    pass

from utils.auth import verificar_autenticacao
verificar_autenticacao()

usuario = st.session_state['usuario']
perfil = usuario.get('perfil')
nome_usuario = usuario.get('nome', '').upper()

# Acesso: ADMIN, DIRETORIA, ou Vinicius (SUPERVISOR responsavel por criar)
tem_acesso_criar = perfil in ["ADMIN", "DIRETORIA"] or nome_usuario == "VINICIUS"
if not tem_acesso_criar:
    st.error("Acesso negado.")
    st.stop()

st.title("Criar Programacao de Producao")

# Session state
if 'itens_programacao' not in st.session_state:
    st.session_state['itens_programacao'] = []
if 'conflito_sku' not in st.session_state:
    st.session_state['conflito_sku'] = None
if 'temp_produto_add' not in st.session_state:
    st.session_state['temp_produto_add'] = None

# Data e descrição
col1, col2 = st.columns([1, 2])
with col1:
    data_programacao = st.date_input("Data da Programacao", datetime.date.today(), format="DD/MM/YYYY")
with col2:
    descricao_sessao = st.text_input("Descricao", placeholder="Ex: Programacao 09/10/2026")

st.divider()

# ─── Adicionar Produtos ──────────────────────────────────────────────
st.subheader("Adicionar Produtos")

# Carregar lista de SKUs para o selectbox com busca
@st.cache_data(ttl=60)
def _carregar_opcoes_sku():
    produtos = listar_produtos(ativo=True)
    opcoes = [""]  # opção vazia no topo
    for p in sorted(produtos, key=lambda x: x.sku or ""):
        if p.sku:
            opcoes.append(f"{p.sku} — {p.nome_produto}")
    return opcoes

opcoes_sku = _carregar_opcoes_sku()

sku_selecionado = st.selectbox(
    "SKU do Produto (digite para buscar):",
    options=opcoes_sku,
    index=0,
    placeholder="Digite o SKU ou nome do produto...",
)

# Extrair SKU da opção selecionada
produto_encontrado = None
if sku_selecionado and " — " in sku_selecionado:
    sku_extraido = sku_selecionado.split(" — ")[0].strip()
    try:
        produto_encontrado = buscar_produto_por_sku(sku_extraido)
    except Exception:
        pass

# Mostrar detalhes do produto encontrado
if produto_encontrado:
    col_vol, col_linha, col_qtd, col_btn = st.columns([1, 1, 1, 1])
    with col_vol:
        st.metric("Volume", f"{produto_encontrado.volume_ml} mL")
    with col_linha:
        # Todos os perfumes permitem escolha, com padrao pre-selecionado
        default_linha = produto_encontrado.linha_producao or "MANUAL"
        linha_escolhida = st.selectbox(
            "Linha de Producao:",
            ["AUTOMATICA", "MANUAL"],
            index=0 if default_linha == "AUTOMATICA" else 1,
        )
    with col_qtd:
        quantidade_input = st.number_input("Quantidade (un):", min_value=1, value=1, step=1)
    with col_btn:
        st.write("")
        adicionar_clicked = st.button("Adicionar Item", type="primary", use_container_width=True)
elif sku_selecionado and sku_selecionado.strip():
    st.error(f"SKU '{sku_selecionado}' nao encontrado no cadastro.")
    quantidade_input = 1
    adicionar_clicked = False
    linha_escolhida = None
else:
    quantidade_input = 1
    adicionar_clicked = False
    linha_escolhida = None

if adicionar_clicked and produto_encontrado:
    novo_item = {
        "sku": produto_encontrado.sku,
        "nome_produto": produto_encontrado.nome_produto,
        "volume_ml": produto_encontrado.volume_ml,
        "linha_producao": linha_escolhida,
        "quantidade_un": quantidade_input
    }
    
    # Verificar duplicata
    skus_existentes = [item['sku'] for item in st.session_state['itens_programacao']]
    if produto_encontrado.sku in skus_existentes:
        st.session_state['conflito_sku'] = True
        st.session_state['temp_produto_add'] = novo_item
    else:
        st.session_state['itens_programacao'].append(novo_item)
        st.success(f"Adicionado: {produto_encontrado.nome_produto} | {quantidade_input} un")
        st.rerun()

# Conflito de SKU duplicado
if st.session_state.get('conflito_sku'):
    item_temp = st.session_state['temp_produto_add']
    st.warning(f"SKU {item_temp['sku']} ({item_temp['nome_produto']}) ja esta na lista. O que deseja fazer?")
    
    col_sep, col_agl, col_canc = st.columns(3)
    with col_sep:
        if st.button("Lote Separado"):
            st.session_state['itens_programacao'].append(st.session_state['temp_produto_add'])
            st.session_state['conflito_sku'] = False
            st.session_state['temp_produto_add'] = None
            st.rerun()
    with col_agl:
        if st.button("Aglutinar (Somar)"):
            novo_item = st.session_state['temp_produto_add']
            for item in st.session_state['itens_programacao']:
                if item['sku'] == novo_item['sku']:
                    item['quantidade_un'] += novo_item['quantidade_un']
                    break
            st.session_state['conflito_sku'] = False
            st.session_state['temp_produto_add'] = None
            st.rerun()
    with col_canc:
        if st.button("Cancelar"):
            st.session_state['conflito_sku'] = False
            st.session_state['temp_produto_add'] = None
            st.rerun()

st.divider()

# ─── Lista de Itens com Reordenação ──────────────────────────────────
st.subheader("Itens da Programacao")

itens = st.session_state['itens_programacao']

if not itens:
    st.info("Nenhum item adicionado ainda.")
else:
    # Tabela com prioridades
    for i, item in enumerate(itens):
        col_prio, col_prod, col_qtd_i, col_vol, col_linha, col_acoes = st.columns([0.5, 3, 1, 1, 1.5, 2])
        
        with col_prio:
            st.markdown(f"**{i+1}**")
        with col_prod:
            st.markdown(f"**{item['nome_produto']}**")
            st.caption(f"SKU: {item['sku']}")
        with col_qtd_i:
            st.markdown(f"{item['quantidade_un']:,} un".replace(",", "."))
        with col_vol:
            st.markdown(f"{item['volume_ml']} mL")
        with col_linha:
            st.markdown(f"{item['linha_producao']}")
        with col_acoes:
            c1, c2, c3 = st.columns(3)
            with c1:
                if i > 0 and st.button("⬆", key=f"up_{i}", help="Subir"):
                    itens[i], itens[i-1] = itens[i-1], itens[i]
                    st.rerun()
            with c2:
                if i < len(itens)-1 and st.button("⬇", key=f"down_{i}", help="Descer"):
                    itens[i], itens[i+1] = itens[i+1], itens[i]
                    st.rerun()
            with c3:
                if st.button("🗑", key=f"del_{i}", help="Remover"):
                    itens.pop(i)
                    st.rerun()
    
    st.caption(f"Total: {len(itens)} itens | {sum(i['quantidade_un'] for i in itens):,} unidades".replace(",", "."))

st.divider()

# ─── Gerar Programação ──────────────────────────────────────────────
if itens:
    if st.button("GERAR PROGRAMACAO", type="primary", use_container_width=True):
        if not descricao_sessao:
            st.error("Preencha a Descricao da programacao.")
        else:
            with st.spinner("Gerando..."):
                try:
                    sessao = criar_sessao(
                        descricao=descricao_sessao,
                        usuario_id=usuario.get('id'),
                        usuario_nome=usuario.get('nome')
                    )
                    resultado = gerar_programacao(
                        sessao_id=sessao.id,
                        itens=itens,
                        data_programacao=data_programacao,
                        usuario_id=usuario.get('id'),
                        usuario_nome=usuario.get('nome')
                    )
                    
                    st.success(f"Programacao gerada! {resultado.get('total_itens')} itens → {resultado.get('total_lotes')} lotes")
                    
                    if resultado.get('erros'):
                        for erro in resultado['erros']:
                            st.warning(f"Aviso: {erro}")
                    
                    st.session_state['itens_programacao'] = []
                    st.session_state['ultima_sessao_id'] = resultado.get('sessao_id')
                    
                except Exception as e:
                    st.error(f"Erro: {e}")
                    st.error(traceback.format_exc())
