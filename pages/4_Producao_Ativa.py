import streamlit as st
import datetime
import pandas as pd
from services import programacao_service, exportador
from database.models import STATUS_PROGRAMACAO

st.set_page_config(page_title="Producao Ativa", layout="wide")

try:
    st.logo("logo.png", size="large")
except Exception:
    pass

from utils.auth import verificar_autenticacao
verificar_autenticacao()

usuario = st.session_state["usuario"]
uid = usuario.get("id")
unome = usuario.get("nome")
perfil = usuario.get("perfil")
nome_upper = unome.upper() if unome else ""

# Acesso total: ADMIN, Amanda ou Erick
pode_editar = perfil == "ADMIN" or nome_upper in ["AMANDA", "ERICK"]
# Visualização: todos os logados podem ver

st.title("Producao Ativa")

if not pode_editar:
    st.info("Voce esta no modo visualizacao. Apenas operadores autorizados podem gerenciar a producao.")

st.caption("Acompanhe o ciclo: Aguardando Inicio -> Em Producao -> Producao Finalizada -> Transferido")

# ── Filtros ───────────────────────────────────────────────────────────
hoje = datetime.date.today()
trinta_dias_atras = hoje - datetime.timedelta(days=30)

col1, col2, col3 = st.columns(3)
with col1:
    datas = st.date_input("Periodo", value=(trinta_dias_atras, hoje), format="DD/MM/YYYY")
    if isinstance(datas, tuple) and len(datas) == 2:
        data_inicio, data_fim = datas
    else:
        data_inicio = data_fim = datas
with col2:
    status_opcoes = [s for s in STATUS_PROGRAMACAO if s != "RASCUNHO"]
    status_default = [s for s in status_opcoes if s != "TRANSFERIDO"]
    status_filtro = st.multiselect("Status", options=status_opcoes, default=status_default)
with col3:
    linha_filtro = st.selectbox("Linha de Producao", ["Todas", "AUTOMATICA", "MANUAL"])

# ── Carregar dados ────────────────────────────────────────────────────
try:
    linha_param = None if linha_filtro == "Todas" else linha_filtro
    status_param = status_filtro if status_filtro else status_opcoes

    programacoes = programacao_service.listar_programacao(
        data_inicio=data_inicio,
        data_fim=data_fim,
        linha_producao=linha_param,
        status=status_param,
    )

    if not programacoes:
        st.info("Nenhuma producao encontrada para os filtros selecionados.")
    else:
        # KPIs rápidos
        aguardando = sum(1 for p in programacoes if p.status == "AGUARDANDO INICIO")
        em_prod = sum(1 for p in programacoes if p.status == "EM PRODUCAO")
        finalizados = sum(1 for p in programacoes if p.status == "PRODUCAO FINALIZADA")
        transferidos = sum(1 for p in programacoes if p.status == "TRANSFERIDO")

        # Pipeline visual compacto com st.columns
        pc1, pa1, pc2, pa2, pc3, pa3, pc4 = st.columns([1, 0.2, 1, 0.2, 1, 0.2, 1])
        with pc1:
            st.markdown(f"""
            <div style="background:rgba(255,193,7,0.12);border:1px solid rgba(255,193,7,0.3);border-radius:12px;padding:12px;text-align:center;">
                <div style="font-size:20px;">⏳</div>
                <div style="font-size:28px;font-weight:700;color:#ffc107;">{aguardando}</div>
                <div style="font-size:11px;color:rgba(255,193,7,0.8);text-transform:uppercase;letter-spacing:0.5px;">Aguardando</div>
            </div>""", unsafe_allow_html=True)
        with pa1:
            st.markdown('<div style="text-align:center;padding-top:30px;font-size:20px;color:rgba(250,250,250,0.3);">→</div>', unsafe_allow_html=True)
        with pc2:
            st.markdown(f"""
            <div style="background:rgba(0,123,255,0.12);border:1px solid rgba(0,123,255,0.3);border-radius:12px;padding:12px;text-align:center;">
                <div style="font-size:20px;">🏭</div>
                <div style="font-size:28px;font-weight:700;color:#4da3ff;">{em_prod}</div>
                <div style="font-size:11px;color:rgba(77,163,255,0.8);text-transform:uppercase;letter-spacing:0.5px;">Em Producao</div>
            </div>""", unsafe_allow_html=True)
        with pa2:
            st.markdown('<div style="text-align:center;padding-top:30px;font-size:20px;color:rgba(250,250,250,0.3);">→</div>', unsafe_allow_html=True)
        with pc3:
            st.markdown(f"""
            <div style="background:rgba(40,167,69,0.12);border:1px solid rgba(40,167,69,0.3);border-radius:12px;padding:12px;text-align:center;">
                <div style="font-size:20px;">✅</div>
                <div style="font-size:28px;font-weight:700;color:#5cd87e;">{finalizados}</div>
                <div style="font-size:11px;color:rgba(92,216,126,0.8);text-transform:uppercase;letter-spacing:0.5px;">Finalizada</div>
            </div>""", unsafe_allow_html=True)
        with pa3:
            st.markdown('<div style="text-align:center;padding-top:30px;font-size:20px;color:rgba(250,250,250,0.3);">→</div>', unsafe_allow_html=True)
        with pc4:
            st.markdown(f"""
            <div style="background:rgba(108,117,125,0.12);border:1px solid rgba(108,117,125,0.3);border-radius:12px;padding:12px;text-align:center;">
                <div style="font-size:20px;">📦</div>
                <div style="font-size:28px;font-weight:700;color:#adb5bd;">{transferidos}</div>
                <div style="font-size:11px;color:rgba(173,181,189,0.8);text-transform:uppercase;letter-spacing:0.5px;">Transferido</div>
            </div>""", unsafe_allow_html=True)

        st.divider()

        # Separar por linha
        prog_auto = [p for p in programacoes if p.linha_producao == "AUTOMATICA"]
        prog_manual = [p for p in programacoes if p.linha_producao == "MANUAL"]

        tab1, tab2 = st.tabs(["Linha Automatica", "Linha Manual"])

        def render_tab(progs, tab_key):
            if not progs:
                st.info(f"Nenhum lote nesta linha.")
                return

            # Montar DataFrame
            from utils.tempo_producao import calcular_tempo_producao
            from utils.helpers import fmt_int, fmt_dec
            from datetime import datetime as dt

            data = []
            for p in progs:
                # Calcular tempo de produção
                tempo_txt = ""
                if p.inicio_producao_em and p.fim_producao_em:
                    tempo = calcular_tempo_producao(p.inicio_producao_em, p.fim_producao_em)
                    tempo_txt = tempo['texto']
                elif p.inicio_producao_em and p.status == "EM PRODUCAO":
                    tempo = calcular_tempo_producao(p.inicio_producao_em, dt.now())
                    tempo_txt = f"{tempo['texto']} (em andamento)"

                sku = p.produto.sku if p.produto else ""
                data.append({
                    "id": p.id,
                    "Prioridade": p.prioridade,
                    "SKU": sku,
                    "Produto": p.nome_produto,
                    "Qtd": fmt_int(p.quantidade_un),
                    "Lote": p.lote,
                    "Volume(L)": fmt_dec(p.volume_total_l or 0),
                    "Status": p.status,
                    "Tempo Producao": tempo_txt,
                    "OBS": p.observacao or "",
                })
            df = pd.DataFrame(data)

            # Cores por status
            def color_status(val):
                cores = {
                    "AGUARDANDO INICIO": "background-color: #fff3cd; color: #856404",
                    "EM PRODUCAO": "background-color: #cce5ff; color: #004085",
                    "PRODUCAO FINALIZADA": "background-color: #d4edda; color: #155724",
                    "TRANSFERIDO": "background-color: #e2e3e5; color: #383d41",
                }
                return cores.get(val, "")

            st.dataframe(
                df.style.map(color_status, subset=["Status"]),
                use_container_width=True,
                hide_index=True,
                column_config={"id": None},
            )

            # ── Botoes de acao ────────────────────────────────────────
            if not pode_editar:
                return

            st.subheader("Acoes")

            # Agrupar lotes por status para cada acao
            lotes_aguardando = [p for p in progs if p.status == "AGUARDANDO INICIO"]
            lotes_em_prod = [p for p in progs if p.status == "EM PRODUCAO"]
            lotes_finalizados = [p for p in progs if p.status == "PRODUCAO FINALIZADA"]

            # ── INICIAR PRODUCAO ──────────────────────────────────────
            if lotes_aguardando:
                with st.expander(f"Iniciar Producao ({len(lotes_aguardando)} lotes aguardando)", expanded=False):
                    opcoes_inicio = {f"Lote {p.lote} - {p.nome_produto} ({p.quantidade_un}un)": p.id for p in lotes_aguardando}
                    selecionados_inicio = st.multiselect(
                        "Selecione os lotes para iniciar",
                        options=list(opcoes_inicio.keys()),
                        key=f"sel_inicio_{tab_key}",
                    )

                    c1, c2 = st.columns([1, 3])
                    with c1:
                        if st.button("Iniciar Selecionados", key=f"btn_inicio_{tab_key}", type="primary"):
                            if not selecionados_inicio:
                                st.warning("Selecione ao menos um lote.")
                            else:
                                ids = [opcoes_inicio[s] for s in selecionados_inicio]
                                try:
                                    programacao_service.iniciar_producao_em_massa(ids, uid, unome)
                                    st.success(f"{len(ids)} lote(s) iniciado(s)!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")
                    with c2:
                        if st.button("Iniciar TODOS", key=f"btn_inicio_all_{tab_key}"):
                            ids = [p.id for p in lotes_aguardando]
                            try:
                                programacao_service.iniciar_producao_em_massa(ids, uid, unome)
                                st.success(f"{len(ids)} lote(s) iniciado(s)!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")

            # ── FINALIZAR PRODUCAO ────────────────────────────────────
            if lotes_em_prod:
                with st.expander(f"Finalizar Producao ({len(lotes_em_prod)} lotes em producao)", expanded=False):
                    opcoes_finalizar = {f"Lote {p.lote} - {p.nome_produto} ({p.quantidade_un}un)": p.id for p in lotes_em_prod}
                    selecionados_finalizar = st.multiselect(
                        "Selecione os lotes para finalizar",
                        options=list(opcoes_finalizar.keys()),
                        key=f"sel_finalizar_{tab_key}",
                    )

                    c1, c2 = st.columns([1, 3])
                    with c1:
                        if st.button("Finalizar Selecionados", key=f"btn_finalizar_{tab_key}", type="primary"):
                            if not selecionados_finalizar:
                                st.warning("Selecione ao menos um lote.")
                            else:
                                ids = [opcoes_finalizar[s] for s in selecionados_finalizar]
                                try:
                                    programacao_service.finalizar_producao_em_massa(ids, uid, unome)
                                    st.success(f"{len(ids)} lote(s) finalizado(s)!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")
                    with c2:
                        if st.button("Finalizar TODOS", key=f"btn_finalizar_all_{tab_key}"):
                            ids = [p.id for p in lotes_em_prod]
                            try:
                                programacao_service.finalizar_producao_em_massa(ids, uid, unome)
                                st.success(f"{len(ids)} lote(s) finalizado(s)!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")

            # ── TRANSFERIR PRODUTO ────────────────────────────────────
            if lotes_finalizados:
                with st.expander(f"Transferir para Logistica ({len(lotes_finalizados)} lotes prontos)", expanded=False):
                    opcoes_transferir = {f"Lote {p.lote} - {p.nome_produto} ({p.quantidade_un}un)": p.id for p in lotes_finalizados}
                    selecionados_transferir = st.multiselect(
                        "Selecione os lotes para transferir",
                        options=list(opcoes_transferir.keys()),
                        key=f"sel_transferir_{tab_key}",
                    )

                    c1, c2 = st.columns([1, 3])
                    with c1:
                        if st.button("Transferir Selecionados", key=f"btn_transferir_{tab_key}", type="primary"):
                            if not selecionados_transferir:
                                st.warning("Selecione ao menos um lote.")
                            else:
                                ids = [opcoes_transferir[s] for s in selecionados_transferir]
                                try:
                                    programacao_service.transferir_produto_em_massa(ids, uid, unome)
                                    st.success(f"{len(ids)} lote(s) transferido(s) para logistica!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")
                    with c2:
                        if st.button("Transferir TODOS", key=f"btn_transferir_all_{tab_key}"):
                            ids = [p.id for p in lotes_finalizados]
                            try:
                                programacao_service.transferir_produto_em_massa(ids, uid, unome)
                                st.success(f"{len(ids)} lote(s) transferido(s) para logistica!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")

            # ── Editar OBS ────────────────────────────────────────────
            with st.expander("Editar Observacoes", expanded=False):
                lote_obs = st.selectbox(
                    "Selecione o Lote",
                    options=[p.id for p in progs],
                    format_func=lambda x: next(
                        (f"Lote {p.lote} - {p.nome_produto}" for p in progs if p.id == x), str(x)
                    ),
                    key=f"obs_lote_{tab_key}",
                )
                lote_sel = next((p for p in progs if p.id == lote_obs), None)
                nova_obs = st.text_area("Observacao", value=lote_sel.observacao or "" if lote_sel else "", key=f"obs_text_{tab_key}")
                if st.button("Salvar Observacao", key=f"obs_save_{tab_key}"):
                    try:
                        programacao_service.atualizar_observacao(lote_obs, nova_obs, uid, unome)
                        st.success("Observacao salva!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")

        with tab1:
            render_tab(prog_auto, "auto")
        with tab2:
            render_tab(prog_manual, "manual")

        # ── Exportar ──────────────────────────────────────────────────
        st.divider()
        if st.button("Exportar para Excel"):
            try:
                excel_data = exportador.exportar_programacao_excel(programacoes)
                st.download_button(
                    label="Baixar Planilha",
                    data=excel_data,
                    file_name=f"producao_ativa_{hoje.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except Exception as e:
                st.error(f"Erro ao exportar: {e}")

except Exception as e:
    st.error(f"Erro ao carregar a pagina: {e}")
