import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime

st.set_page_config(page_title="Indicadores de Producao", layout="wide")

try:
    st.logo("logo.png", size="large")
except Exception:
    pass

from utils.auth import verificar_autenticacao
verificar_autenticacao()

from services.analise_producao_service import obter_indicadores, _formatar_tempo
from utils.helpers import fmt_int, fmt_dec

st.title("Indicadores de Producao")
st.caption("Analise de tempos, produtividade e desempenho da fabrica")

# ── Filtros ──────────────────────────────────────────────────────────
hoje = datetime.date.today()
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    periodo = st.selectbox("Periodo", [
        "Ultimos 7 dias", "Ultimos 30 dias", "Ultimos 90 dias",
        "Este mes", "Mes anterior", "Personalizado"
    ], index=1)

with col_f2:
    if periodo == "Ultimos 7 dias":
        dt_ini = hoje - datetime.timedelta(days=7)
        dt_fim = hoje
    elif periodo == "Ultimos 30 dias":
        dt_ini = hoje - datetime.timedelta(days=30)
        dt_fim = hoje
    elif periodo == "Ultimos 90 dias":
        dt_ini = hoje - datetime.timedelta(days=90)
        dt_fim = hoje
    elif periodo == "Este mes":
        dt_ini = hoje.replace(day=1)
        dt_fim = hoje
    elif periodo == "Mes anterior":
        primeiro_mes = hoje.replace(day=1)
        ultimo_mes_ant = primeiro_mes - datetime.timedelta(days=1)
        dt_ini = ultimo_mes_ant.replace(day=1)
        dt_fim = ultimo_mes_ant
    else:
        datas = st.date_input("Selecione o periodo", value=(hoje - datetime.timedelta(days=30), hoje), format="DD/MM/YYYY")
        if isinstance(datas, tuple) and len(datas) == 2:
            dt_ini, dt_fim = datas
        else:
            dt_ini = dt_fim = hoje

    if periodo != "Personalizado":
        st.caption(f"{dt_ini.strftime('%d/%m/%Y')} a {dt_fim.strftime('%d/%m/%Y')}")

with col_f3:
    linha_filtro = st.selectbox("Linha de Producao", ["Todas", "AUTOMATICA", "MANUAL"])

# ── Carregar dados ───────────────────────────────────────────────────
try:
    ind = obter_indicadores(
        data_inicio=dt_ini,
        data_fim=dt_fim,
        linha_producao=linha_filtro,
    )
except Exception as e:
    st.error(f"Erro ao carregar indicadores: {e}")
    st.stop()

if ind["total_lotes"] == 0:
    st.info("Nenhuma producao encontrada para o periodo selecionado.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════
# KPIs PRINCIPAIS
# ══════════════════════════════════════════════════════════════════════
st.divider()

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">📦</div>
        <div class="kpi-value">{fmt_int(ind['total_lotes'])}</div>
        <div class="kpi-label">Total de Lotes</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">✅</div>
        <div class="kpi-value">{fmt_int(ind['lotes_concluidos'])}</div>
        <div class="kpi-label">Concluidos</div>
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">🏭</div>
        <div class="kpi-value">{fmt_int(ind['un_concluidas'])}</div>
        <div class="kpi-label">Unidades Produzidas</div>
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">⏱️</div>
        <div class="kpi-value">{_formatar_tempo(ind['tempo_medio_min'])}</div>
        <div class="kpi-label">Tempo Medio / Lote</div>
    </div>""", unsafe_allow_html=True)
with k5:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">⚡</div>
        <div class="kpi-value">{fmt_dec(ind['produtividade_un_hora'])}</div>
        <div class="kpi-label">Un / Hora Util</div>
    </div>""", unsafe_allow_html=True)
with k6:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">🧪</div>
        <div class="kpi-value">{fmt_dec(ind['volume_por_hora'])}L</div>
        <div class="kpi-label">Litros / Hora Util</div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TEMPO DE PRODUÇÃO
# ══════════════════════════════════════════════════════════════════════
st.divider()
st.header("Tempo de Producao")

tc1, tc2 = st.columns(2)
with tc1:
    st.markdown(f"""
    <div class="kpi-card" style="text-align:left; padding:20px;">
        <div style="font-size:14px; color:rgba(250,250,250,0.6); margin-bottom:12px; text-transform:uppercase; letter-spacing:0.5px;">Resumo de Tempos</div>
        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
            <span style="color:rgba(250,250,250,0.7);">Tempo medio por lote</span>
            <span style="font-weight:700; color:#FAFAFA;">{_formatar_tempo(ind['tempo_medio_min'])}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
            <span style="color:rgba(250,250,250,0.7);">Lote mais rapido</span>
            <span style="font-weight:700; color:#5cd87e;">{_formatar_tempo(ind['tempo_min_min'])}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
            <span style="color:rgba(250,250,250,0.7);">Lote mais lento</span>
            <span style="font-weight:700; color:#ff6b6b;">{_formatar_tempo(ind['tempo_max_min'])}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="color:rgba(250,250,250,0.7);">Tempo total de producao</span>
            <span style="font-weight:700; color:#4da3ff;">{_formatar_tempo(ind['tempo_total_min'])}</span>
        </div>
    </div>""", unsafe_allow_html=True)

with tc2:
    # Comparativo por linha
    por_linha = ind.get("por_linha", {})
    if por_linha:
        linhas_data = []
        for linha, dados in por_linha.items():
            if dados["lotes_concluidos"] > 0:
                linhas_data.append({
                    "Linha": linha,
                    "Tempo Medio (min)": dados["tempo_medio_min"],
                    "Produtividade (un/h)": dados["produtividade_un_hora"],
                    "Lotes": dados["lotes_concluidos"],
                })
        if linhas_data:
            df_linhas = pd.DataFrame(linhas_data)
            fig_linhas = px.bar(
                df_linhas, x="Linha", y="Tempo Medio (min)",
                color="Linha",
                color_discrete_map={"AUTOMATICA": "#4da3ff", "MANUAL": "#ffc107"},
                title="Tempo Medio por Linha (min)",
                text="Tempo Medio (min)",
            )
            fig_linhas.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#FAFAFA", showlegend=False,
            )
            st.plotly_chart(fig_linhas, use_container_width=True)
        else:
            st.info("Sem dados de tempo por linha.")
    else:
        st.info("Sem dados de tempo por linha.")

# ══════════════════════════════════════════════════════════════════════
# GRÁFICOS
# ══════════════════════════════════════════════════════════════════════
st.divider()
st.header("Graficos de Desempenho")

g1, g2 = st.columns(2)

# Produção por dia (timeline)
with g1:
    timeline = ind.get("timeline", [])
    if timeline:
        df_time = pd.DataFrame(timeline)
        fig_time = px.bar(
            df_time, x="dia", y="unidades",
            title="Unidades Produzidas por Dia",
            text="unidades",
            color_discrete_sequence=["#C8102E"],
        )
        fig_time.update_layout(
            xaxis_title="Dia", yaxis_title="Unidades",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FAFAFA",
        )
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("Sem dados de timeline.")

# Status dos lotes
with g2:
    status_map = ind.get("status_map", {})
    if status_map:
        df_status = pd.DataFrame(list(status_map.items()), columns=["Status", "Qtd"])
        cores_status = {
            "AGUARDANDO INICIO": "#ffc107",
            "EM PRODUCAO": "#4da3ff",
            "PRODUCAO FINALIZADA": "#5cd87e",
            "TRANSFERIDO": "#adb5bd",
        }
        df_status["Cor"] = df_status["Status"].map(cores_status).fillna("#888")
        fig_st = px.pie(
            df_status, values="Qtd", names="Status",
            title="Distribuicao por Status",
            color="Status",
            color_discrete_map=cores_status,
        )
        fig_st.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FAFAFA",
        )
        st.plotly_chart(fig_st, use_container_width=True)
    else:
        st.info("Sem dados de status.")

# ══════════════════════════════════════════════════════════════════════
# COMPARATIVO POR LINHA
# ══════════════════════════════════════════════════════════════════════
if por_linha and any(d["lotes_concluidos"] > 0 for d in por_linha.values()):
    st.divider()
    st.header("Comparativo por Linha")

    cl1, cl2 = st.columns(2)
    for col_ref, (linha, dados) in zip([cl1, cl2], por_linha.items()):
        emoji = "🤖" if linha == "AUTOMATICA" else "🔧"
        cor = "#4da3ff" if linha == "AUTOMATICA" else "#ffc107"
        with col_ref:
            st.markdown(f"""
            <div class="kpi-card" style="border-color:{cor}; text-align:left; padding:20px;">
                <div style="font-size:18px; font-weight:700; color:{cor}; margin-bottom:12px;">{emoji} Linha {linha}</div>
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="color:rgba(250,250,250,0.7);">Total de lotes</span>
                    <span style="font-weight:600; color:#FAFAFA;">{fmt_int(dados['total_lotes'])}</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="color:rgba(250,250,250,0.7);">Lotes concluidos</span>
                    <span style="font-weight:600; color:#FAFAFA;">{fmt_int(dados['lotes_concluidos'])}</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="color:rgba(250,250,250,0.7);">Unidades produzidas</span>
                    <span style="font-weight:600; color:#FAFAFA;">{fmt_int(dados['un_concluidas'])}</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="color:rgba(250,250,250,0.7);">Tempo medio / lote</span>
                    <span style="font-weight:600; color:#FAFAFA;">{_formatar_tempo(dados['tempo_medio_min'])}</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:rgba(250,250,250,0.7);">Produtividade</span>
                    <span style="font-weight:600; color:#FAFAFA;">{fmt_dec(dados['produtividade_un_hora'])} un/h</span>
                </div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# RANKING POR PRODUTO
# ══════════════════════════════════════════════════════════════════════
por_produto = ind.get("por_produto", [])
if por_produto:
    st.divider()
    st.header("Desempenho por Produto")

    df_prod = pd.DataFrame(por_produto)
    df_prod.columns = ["Produto", "Lotes", "Unidades", "Volume (L)",
                       "Tempo Medio (min)", "Produtividade (un/h)"]

    # Formatar
    df_prod["Volume (L)"] = df_prod["Volume (L)"].apply(lambda x: fmt_dec(x))
    df_prod["Tempo Medio (min)"] = df_prod["Tempo Medio (min)"].apply(lambda x: _formatar_tempo(x))
    df_prod["Produtividade (un/h)"] = df_prod["Produtividade (un/h)"].apply(lambda x: fmt_dec(x))
    df_prod["Unidades"] = df_prod["Unidades"].apply(lambda x: fmt_int(x))

    st.dataframe(df_prod, use_container_width=True, hide_index=True)

    # Gráfico top produtos por unidades
    df_graf = pd.DataFrame(por_produto[:10])
    if not df_graf.empty:
        fig_prod = px.bar(
            df_graf, x="unidades", y="produto",
            orientation="h",
            title="Top 10 Produtos por Unidades Produzidas",
            color_discrete_sequence=["#C8102E"],
            text="unidades",
        )
        fig_prod.update_layout(
            yaxis={"autorange": "reversed"},
            xaxis_title="Unidades", yaxis_title="",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FAFAFA", height=400,
        )
        st.plotly_chart(fig_prod, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════
# TOP RÁPIDOS / LENTOS
# ══════════════════════════════════════════════════════════════════════
top_rapidos = ind.get("top_rapidos", [])
top_lentos = ind.get("top_lentos", [])

if top_rapidos or top_lentos:
    st.divider()
    st.header("Ranking de Velocidade")

    tr1, tr2 = st.columns(2)
    with tr1:
        st.subheader("⚡ Lotes Mais Rapidos")
        if top_rapidos:
            df_rap = pd.DataFrame([{
                "Lote": t["lote"],
                "Produto": t["produto"],
                "Tempo": t["tempo_texto"],
                "Qtd (un)": fmt_int(t["quantidade_un"]),
            } for t in top_rapidos])
            st.dataframe(df_rap, use_container_width=True, hide_index=True)
        else:
            st.info("Sem dados.")

    with tr2:
        st.subheader("🐢 Lotes Mais Lentos")
        if top_lentos:
            df_len = pd.DataFrame([{
                "Lote": t["lote"],
                "Produto": t["produto"],
                "Tempo": t["tempo_texto"],
                "Qtd (un)": fmt_int(t["quantidade_un"]),
            } for t in top_lentos])
            st.dataframe(df_len, use_container_width=True, hide_index=True)
        else:
            st.info("Sem dados.")

# ══════════════════════════════════════════════════════════════════════
# TABELA DETALHADA
# ══════════════════════════════════════════════════════════════════════
detalhes = ind.get("detalhes", [])
if detalhes:
    st.divider()
    with st.expander("Tabela Detalhada de Producao", expanded=False):
        df_det = pd.DataFrame([{
            "Lote": t["lote"],
            "Produto": t["produto"],
            "Linha": t["linha"],
            "Qtd (un)": fmt_int(t["quantidade_un"]),
            "Volume (L)": fmt_dec(t["volume_total_l"]),
            "Inicio": t["inicio"].strftime("%d/%m/%Y %H:%M") if t["inicio"] else "",
            "Fim": t["fim"].strftime("%d/%m/%Y %H:%M") if t["fim"] else "",
            "Tempo Util": t["tempo_texto"],
            "Min Uteis": t["minutos_uteis"],
        } for t in detalhes])

        st.dataframe(df_det, use_container_width=True, hide_index=True,
                     column_config={"Min Uteis": None})

        # Download
        csv = df_det.to_csv(index=False, sep=";", decimal=",")
        st.download_button(
            "Exportar CSV",
            data=csv,
            file_name=f"indicadores_producao_{hoje.strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
