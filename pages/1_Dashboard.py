import streamlit as st
import plotly.express as px
import pandas as pd
from services.programacao_service import obter_resumo_programacao
from services.estoque_service import listar_estoque
from database.models import STATUS_PROGRAMACAO

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

# Logo Kiosk Brands no topo
try:
    st.logo("logo.png", size="large")
except Exception:
    pass


from utils.auth import verificar_autenticacao
verificar_autenticacao()

st.title("Dashboard de Producao")

try:
    from utils.helpers import fmt_int, fmt_dec
    resumo = obter_resumo_programacao()
    estoque = listar_estoque()

    # KPIs com cards visuais
    total = fmt_int(resumo.get("total_lotes", 0))
    lotes_status = resumo.get("lotes_por_status", {})
    aguardando = fmt_int(lotes_status.get("AGUARDANDO INICIO", 0))
    em_prod = fmt_int(lotes_status.get("EM PRODUCAO", 0))
    finalizado = fmt_int(lotes_status.get("PRODUCAO FINALIZADA", 0) + lotes_status.get("TRANSFERIDO", 0))
    vol = fmt_dec(resumo.get("volume_total_l", 0))

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-icon">📊</div><div class="kpi-value">{total}</div><div class="kpi-label">Total Lotes</div></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-icon">⏳</div><div class="kpi-value">{aguardando}</div><div class="kpi-label">Aguardando</div></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-icon">🏭</div><div class="kpi-value">{em_prod}</div><div class="kpi-label">Em Producao</div></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-icon">✅</div><div class="kpi-value">{finalizado}</div><div class="kpi-label">Finalizados</div></div>', unsafe_allow_html=True)
    with k5:
        st.markdown(f'<div class="kpi-card"><div class="kpi-icon">🧪</div><div class="kpi-value">{vol}L</div><div class="kpi-label">Volume Total</div></div>', unsafe_allow_html=True)

    st.divider()
    
    # Gráficos
    st.header("Análise Gráfica")
    col_graf1, col_graf2 = st.columns(2)
    
    lotes_por_status = resumo.get("lotes_por_status", {})
    lotes_por_linha = resumo.get("lotes_por_linha", {})
    
    with col_graf1:
        if lotes_por_status:
            df_status = pd.DataFrame(list(lotes_por_status.items()), columns=['Status', 'Quantidade'])
            fig_status = px.bar(df_status, x='Status', y='Quantidade', title="Lotes por Status", color='Status')
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("Sem dados para o gráfico de Status.")
            
    with col_graf2:
        if lotes_por_linha:
            df_linha = pd.DataFrame(list(lotes_por_linha.items()), columns=['Linha', 'Quantidade'])
            fig_linha = px.pie(df_linha, values='Quantidade', names='Linha', title="Lotes por Linha de Produção")
            st.plotly_chart(fig_linha, use_container_width=True)
        else:
            st.info("Sem dados para o gráfico de Linha de Produção.")
            
    st.divider()
    
    # Lotes Recentes e Estoque Crítico
    col_tabela1, col_tabela2 = st.columns(2)
    
    with col_tabela1:
        st.subheader("Últimos Lotes")
        lotes_recentes = resumo.get("ultimos_lotes", [])
        if lotes_recentes:
            df_recentes = pd.DataFrame([{
                'Lote': l.lote,
                'Produto': l.nome_produto,
                'Status': l.status
            } for l in lotes_recentes])
            st.dataframe(df_recentes, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum lote recente encontrado.")
            
    with col_tabela2:
        st.subheader("Estoque Crítico (Menor Quantidade)")
        if estoque:
            df_estoque = pd.DataFrame([{
                'Essencia': e.essencia,
                'Qtd Disponivel (kg)': fmt_dec(e.qtd_estoque, 2)
            } for e in estoque])
            df_estoque_critico = df_estoque.sort_values(by='Qtd Disponivel (kg)').head(5)
            st.dataframe(df_estoque_critico, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado de estoque encontrado.")
            
except Exception as e:
    st.error(f"Erro ao carregar o dashboard: {e}")
