import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Revisar Programacao", layout="wide")

try:
    st.logo("logo.png", size="large")
except Exception:
    pass

from utils.auth import verificar_autenticacao
verificar_autenticacao()

usuario = st.session_state['usuario']
perfil = usuario.get('perfil')
nome_usuario = usuario.get('nome', '').upper()

# Acesso: ADMIN ou Erick/Amanda (revisores)
tem_acesso_revisar = perfil in ['ADMIN'] or nome_usuario in ['ERICK', 'AMANDA']
if not tem_acesso_revisar:
    st.error("Acesso negado. Voce nao tem permissao para revisar programacoes.")
    st.stop()

try:
    from services.programacao_service import (
        listar_sessoes, listar_itens_sessao, finalizar_programacao,
        atualizar_prioridades_em_massa, atualizar_quantidade,
        atualizar_observacao, excluir_programacao, obter_sessao
    )
    from services.log_service import listar_logs_sessao
    from services.exportador import exportar_programacao_excel
except ImportError as e:
    st.error(f"Erro ao importar servicos: {e}")
    st.stop()

st.title("Revisar Programacao")

tab_geradas, tab_finalizadas = st.tabs(["Pendentes de Revisao", "Finalizadas"])

# ─── Função reutilizável: tabela editável ────────────────────────────
def renderizar_tabela_edicao(itens_linha, linha_nome, sessao_id):
    from utils.helpers import fmt_int, fmt_dec
    if not itens_linha:
        st.info("Nenhum item nesta linha.")
        return
    
    dados = []
    for item in itens_linha:
        dados.append({
            'ID': item.id,
            'Prioridade': item.prioridade,
            'Produto': item.nome_produto,
            'Qtd (un)': item.quantidade_un,
            'Lote': item.lote,
            'Volume (mL)': item.volume_ml,
            'Vol Total (L)': fmt_dec(item.volume_total_l) if item.volume_total_l else "0",
            'Bateladas': item.num_bateladas,
            'OBS': item.observacao or ""
        })
    
    df = pd.DataFrame(dados)
    
    # Colunas não editáveis
    colunas_fixas = ['ID', 'Produto', 'Lote', 'Volume (mL)', 'Vol Total (L)', 'Bateladas']
    
    with st.form(f"form_{linha_nome}_{sessao_id}"):
        df_editado = st.data_editor(
            df,
            disabled=colunas_fixas,
            hide_index=True,
            use_container_width=True,
            key=f"editor_{linha_nome}_{sessao_id}",
            column_config={
                "ID": st.column_config.NumberColumn(width="small"),
                "Prioridade": st.column_config.NumberColumn(width="small"),
                "Produto": st.column_config.TextColumn(width="large"),
                "Qtd (un)": st.column_config.NumberColumn(width="small"),
                "Lote": st.column_config.TextColumn(width="small"),
                "OBS": st.column_config.TextColumn(width="medium"),
            }
        )
        
        if st.form_submit_button("Salvar Alteracoes", type="primary"):
            try:
                atualizacoes_prio = []
                for _, row in df_editado.iterrows():
                    original = next((x for x in itens_linha if x.id == row['ID']), None)
                    if not original:
                        continue
                    
                    if original.prioridade != row['Prioridade']:
                        atualizacoes_prio.append({'id': row['ID'], 'prioridade': int(row['Prioridade'])})
                    
                    if original.quantidade_un != row['Qtd (un)']:
                        atualizar_quantidade(row['ID'], int(row['Qtd (un)']), usuario['id'], usuario['nome'])
                    
                    obs_edit = row['OBS'] if pd.notna(row['OBS']) else ""
                    obs_orig = original.observacao or ""
                    if obs_orig != obs_edit:
                        atualizar_observacao(row['ID'], str(obs_edit), usuario['id'], usuario['nome'])
                
                if atualizacoes_prio:
                    atualizar_prioridades_em_massa(atualizacoes_prio, usuario['id'], usuario['nome'])
                
                st.success("Alteracoes salvas!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")
    
    # Reordenar por botões
    st.markdown("**Reordenar:**")
    col_mover, col_excluir = st.columns(2)
    
    with col_mover:
        lotes_opcoes = {f"{item.lote} - {item.nome_produto}": item for item in itens_linha}
        lote_sel = st.selectbox("Lote:", [""] + list(lotes_opcoes.keys()), key=f"mover_{linha_nome}_{sessao_id}")
        nova_pos = st.number_input("Mover para posicao:", min_value=1, max_value=len(itens_linha), value=1, key=f"pos_{linha_nome}_{sessao_id}")
        
        if st.button("Mover", key=f"btn_mover_{linha_nome}_{sessao_id}"):
            if lote_sel and lote_sel in lotes_opcoes:
                item_mover = lotes_opcoes[lote_sel]
                # Recalcular prioridades
                outros = [i for i in itens_linha if i.id != item_mover.id]
                outros.sort(key=lambda x: x.prioridade or 0)
                outros.insert(int(nova_pos) - 1, item_mover)
                atualizacoes = [{'id': it.id, 'prioridade': idx + 1} for idx, it in enumerate(outros)]
                atualizar_prioridades_em_massa(atualizacoes, usuario['id'], usuario['nome'])
                st.success("Ordem atualizada!")
                st.rerun()
    
    with col_excluir:
        lote_del = st.selectbox("Excluir lote:", [""] + list(lotes_opcoes.keys()), key=f"excluir_{linha_nome}_{sessao_id}")
        if st.button("Excluir Lote", type="primary", key=f"btn_del_{linha_nome}_{sessao_id}"):
            if lote_del and lote_del in lotes_opcoes:
                try:
                    excluir_programacao(lotes_opcoes[lote_del].id, usuario['id'], usuario['nome'])
                    st.success("Lote excluido!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")


def renderizar_tabela_leitura(itens_linha):
    from utils.helpers import fmt_int, fmt_dec
    if not itens_linha:
        st.info("Nenhum item nesta linha.")
        return
    dados = [{
        'Prioridade': item.prioridade,
        'Produto': item.nome_produto,
        'Qtd (un)': fmt_int(item.quantidade_un),
        'Lote': item.lote,
        'Volume (mL)': item.volume_ml,
        'Vol Total (L)': fmt_dec(item.volume_total_l) if item.volume_total_l else "0",
        'Bateladas': item.num_bateladas,
        'Status': item.status,
        'OBS': item.observacao or ""
    } for item in itens_linha]
    st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)


# ─── Tab: Sessões Pendentes ──────────────────────────────────────────
with tab_geradas:
    try:
        sessoes_geradas = listar_sessoes(status='GERADA')
    except Exception as e:
        st.error(f"Erro: {e}")
        sessoes_geradas = []

    if not sessoes_geradas:
        st.info("Nenhuma sessao pendente de revisao.")
    else:
        opcoes = {f"ID {s.id} - {s.descricao} - {s.criado_em.strftime('%d/%m/%Y %H:%M') if s.criado_em else ''}": s for s in sessoes_geradas}
        sel = st.selectbox("Sessao para revisar:", list(opcoes.keys()))

        if sel:
            sessao_obj = opcoes[sel]
            sessao_id = sessao_obj.id
            
            try:
                itens = listar_itens_sessao(sessao_id)
            except Exception as e:
                st.error(f"Erro: {e}")
                itens = []
            
            if itens:
                tab_auto, tab_manual = st.tabs(["Linha Automatica", "Linha Manual"])
                
                itens_auto = sorted([i for i in itens if i.linha_producao == 'AUTOMATICA'], key=lambda x: x.prioridade or 0)
                itens_manual = sorted([i for i in itens if i.linha_producao == 'MANUAL'], key=lambda x: x.prioridade or 0)
                
                with tab_auto:
                    renderizar_tabela_edicao(itens_auto, "auto", sessao_id)
                with tab_manual:
                    renderizar_tabela_edicao(itens_manual, "manual", sessao_id)

                st.divider()
                
                # Finalizar + Exportar
                col_fin, col_excel, col_pdf = st.columns([2, 1, 1])
                
                with col_fin:
                    if st.button("FINALIZAR PROGRAMACAO", type="primary", use_container_width=True):
                        try:
                            ok = finalizar_programacao(sessao_id, usuario['id'], usuario['nome'])
                            if ok:
                                st.success("Programacao finalizada!")
                                st.rerun()
                            else:
                                st.error("Erro ao finalizar.")
                        except Exception as e:
                            st.error(f"Erro: {e}")
                
                with col_excel:
                    try:
                        excel_data = exportar_programacao_excel(itens)
                        st.download_button("Exportar Excel", data=excel_data,
                                            file_name=f"programacao_{sessao_id}.xlsx",
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro Excel: {e}")
                
                with col_pdf:
                    try:
                        from services.exportador import exportar_programacao_pdf
                        pdf_data = exportar_programacao_pdf(itens, titulo=sessao_obj.descricao or "Programacao")
                        st.download_button("Baixar PDF", data=pdf_data,
                                            file_name=f"programacao_{sessao_id}.pdf",
                                            mime="application/pdf",
                                            use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro PDF: {e}")
                
                # Log
                with st.expander("Historico de Modificacoes"):
                    try:
                        logs = listar_logs_sessao(sessao_id)
                        if logs:
                            dados_log = [{
                                "Data/Hora": lg.criado_em.strftime("%d/%m/%Y %H:%M:%S") if lg.criado_em else "",
                                "Usuario": lg.usuario_nome,
                                "Acao": lg.acao,
                                "Campo": lg.campo,
                                "Anterior": lg.valor_anterior,
                                "Novo": lg.valor_novo
                            } for lg in logs]
                            st.dataframe(pd.DataFrame(dados_log), use_container_width=True, hide_index=True)
                        else:
                            st.caption("Nenhuma modificacao registrada.")
                    except Exception as e:
                        st.error(f"Erro: {e}")


# ─── Tab: Sessões Finalizadas ────────────────────────────────────────
with tab_finalizadas:
    try:
        sessoes_fin = listar_sessoes(status='FINALIZADA')
    except Exception as e:
        st.error(f"Erro: {e}")
        sessoes_fin = []

    if not sessoes_fin:
        st.info("Nenhuma sessao finalizada.")
    else:
        opcoes_fin = {f"ID {s.id} - {s.descricao} - {s.criado_em.strftime('%d/%m/%Y %H:%M') if s.criado_em else ''}": s for s in sessoes_fin}
        sel_fin = st.selectbox("Sessao para visualizar:", list(opcoes_fin.keys()), key="sel_fin")

        if sel_fin:
            sessao_fin = opcoes_fin[sel_fin]
            
            try:
                itens_fin = listar_itens_sessao(sessao_fin.id)
            except Exception:
                itens_fin = []
            
            if sessao_fin.finalizado_em:
                st.caption(f"Finalizada em: {sessao_fin.finalizado_em.strftime('%d/%m/%Y %H:%M')}")
            
            if itens_fin:
                tab_af, tab_mf = st.tabs(["Linha Automatica", "Linha Manual"])
                with tab_af:
                    renderizar_tabela_leitura([i for i in itens_fin if i.linha_producao == 'AUTOMATICA'])
                with tab_mf:
                    renderizar_tabela_leitura([i for i in itens_fin if i.linha_producao == 'MANUAL'])
                
                try:
                    excel_fin = exportar_programacao_excel(itens_fin)
                    st.download_button("Exportar Excel", data=excel_fin,
                                        file_name=f"programacao_fin_{sessao_fin.id}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key="exp_fin")
                except Exception:
                    pass
                
                with st.expander("Historico de Modificacoes"):
                    try:
                        logs = listar_logs_sessao(sessao_fin.id)
                        if logs:
                            st.dataframe(pd.DataFrame([{
                                "Data/Hora": lg.criado_em.strftime("%d/%m/%Y %H:%M:%S") if lg.criado_em else "",
                                "Usuario": lg.usuario_nome, "Acao": lg.acao,
                                "Campo": lg.campo, "Anterior": lg.valor_anterior, "Novo": lg.valor_novo
                            } for lg in logs]), use_container_width=True, hide_index=True)
                        else:
                            st.caption("Nenhuma modificacao.")
                    except Exception:
                        pass
