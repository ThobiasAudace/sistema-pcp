"""
Serviço de programação — novo fluxo: Criar → Gerar → Revisar → Finalizar.
"""
import datetime
import uuid
from typing import List, Dict, Optional
from sqlalchemy import func
from database.connection import get_db
from database.models import (
    Programacao, ProgramacaoSessao, Produto,
    STATUS_PROGRAMACAO, STATUS_SESSAO
)
from services.batelada_calculator import processar_item_programacao
from services.log_service import registrar_log


# ─── Sessões de programação ────────────────────────────────────────────

def criar_sessao(descricao: str, usuario_id: int, usuario_nome: str) -> ProgramacaoSessao:
    """Cria uma nova sessão de programação em rascunho."""
    with get_db() as db:
        sessao = ProgramacaoSessao(
            descricao=descricao,
            status="RASCUNHO",
            criado_por=usuario_id,
            criado_em=datetime.datetime.now()
        )
        db.add(sessao)
        db.commit()
        db.refresh(sessao)
        
        registrar_log("programacao_sessoes", sessao.id, "CRIAR",
                       usuario_id=usuario_id, usuario_nome=usuario_nome,
                       valor_novo=descricao, db=db)
        db.commit()
        return sessao


def obter_sessao(sessao_id: int) -> Optional[ProgramacaoSessao]:
    """Obtém uma sessão pelo ID."""
    with get_db() as db:
        return db.query(ProgramacaoSessao).filter(
            ProgramacaoSessao.id == sessao_id
        ).first()


def listar_sessoes(status: str = None) -> List[ProgramacaoSessao]:
    """Lista sessões de programação, opcionalmente filtradas por status."""
    with get_db() as db:
        query = db.query(ProgramacaoSessao)
        if status:
            query = query.filter(ProgramacaoSessao.status == status)
        return query.order_by(ProgramacaoSessao.criado_em.desc()).all()


def gerar_programacao(sessao_id: int, itens: List[Dict], 
                       data_programacao, usuario_id: int,
                       usuario_nome: str) -> Dict:
    """
    Gera a programação a partir dos itens inseridos pelo usuário.
    
    Cada item em 'itens' tem: {sku, quantidade_un}
    
    Retorna: {total_itens, total_lotes, duplicados, erros, lotes_gerados}
    """
    from services.cadastro_service import buscar_produto_por_sku
    
    total_itens = 0
    total_lotes = 0
    erros = []
    lotes_gerados = []
    ano_atual = data_programacao.year if hasattr(data_programacao, 'year') else datetime.date.today().year
    
    with get_db() as db:
        sessao = db.query(ProgramacaoSessao).filter(
            ProgramacaoSessao.id == sessao_id
        ).first()
        
        if not sessao:
            return {"total_itens": 0, "total_lotes": 0, "erros": ["Sessao nao encontrada"]}
        
        prioridade = 0
        
        for item in itens:
            sku = str(item.get("sku", "")).strip()
            qtd = item.get("quantidade_un", 0)
            
            if not sku or qtd <= 0:
                continue
            
            produto = buscar_produto_por_sku(sku)
            if not produto:
                erros.append(f"SKU {sku} nao encontrado no cadastro")
                continue
            
            prioridade += 1
            total_itens += 1
            
            lotes_dados = processar_item_programacao(produto, qtd, ano_atual, db)
            
            for lote_dict in lotes_dados:
                prog = Programacao(
                    sessao_id=sessao_id,
                    data_programacao=data_programacao,
                    prioridade=prioridade,
                    status="RASCUNHO",
                    criado_por=usuario_id,
                    **lote_dict
                )
                db.add(prog)
                db.flush()  # Garante que prog.id seja gerado
                total_lotes += 1
                lotes_gerados.append(lote_dict['lote'])
                
                registrar_log("programacao", prog.id, "CRIAR",
                              usuario_id=usuario_id, usuario_nome=usuario_nome,
                              valor_novo=f"{produto.nome_produto} | {qtd}un | Lote {lote_dict['lote']}",
                              db=db)
        
        # Atualizar status da sessão para GERADA
        sessao.status = "GERADA"
        sessao.gerado_por = usuario_id
        sessao.gerado_em = datetime.datetime.now()
        
        registrar_log("programacao_sessoes", sessao_id, "GERAR",
                       usuario_id=usuario_id, usuario_nome=usuario_nome,
                       campo="status", valor_anterior="RASCUNHO", valor_novo="GERADA",
                       db=db)
        
        db.commit()
    
    return {
        "total_itens": total_itens,
        "total_lotes": total_lotes,
        "erros": erros,
        "lotes_gerados": lotes_gerados,
        "sessao_id": sessao_id
    }


def finalizar_programacao(sessao_id: int, usuario_id: int, usuario_nome: str) -> bool:
    """
    Finaliza a programação: muda status da sessão para FINALIZADA
    e todos os lotes para AGUARDANDO INICIO.
    """
    with get_db() as db:
        sessao = db.query(ProgramacaoSessao).filter(
            ProgramacaoSessao.id == sessao_id
        ).first()
        
        if not sessao or sessao.status not in ("GERADA", "RASCUNHO"):
            return False
        
        status_anterior = sessao.status
        sessao.status = "FINALIZADA"
        sessao.finalizado_por = usuario_id
        sessao.finalizado_em = datetime.datetime.now()
        
        registrar_log("programacao_sessoes", sessao_id, "FINALIZAR",
                       usuario_id=usuario_id, usuario_nome=usuario_nome,
                       campo="status", valor_anterior=status_anterior,
                       valor_novo="FINALIZADA", db=db)
        
        # Mudar todos os lotes para AGUARDANDO INICIO
        itens = db.query(Programacao).filter(Programacao.sessao_id == sessao_id).all()
        for item in itens:
            item.status = "AGUARDANDO INICIO"
            registrar_log("programacao", item.id, "FINALIZAR",
                           usuario_id=usuario_id, usuario_nome=usuario_nome,
                           campo="status", valor_anterior="RASCUNHO",
                           valor_novo="AGUARDANDO INICIO", db=db)
        
        db.commit()
        return True


def iniciar_producao(lote_id: int, usuario_id: int = None, usuario_nome: str = None) -> Programacao:
    """Inicia a produção de um lote na fábrica."""
    with get_db() as db:
        prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
        if not prog:
            raise ValueError("Lote nao encontrado.")
        if prog.status != "AGUARDANDO INICIO":
            raise ValueError(f"Lote {prog.lote} nao esta aguardando inicio (status atual: {prog.status}).")
        
        prog.status = "EM PRODUCAO"
        prog.inicio_producao_em = datetime.datetime.now()
        registrar_log("programacao", lote_id, "EDITAR",
                       usuario_id=usuario_id, usuario_nome=usuario_nome,
                       campo="status", valor_anterior="AGUARDANDO INICIO",
                       valor_novo="EM PRODUCAO", db=db)
        db.commit()
        return prog


def finalizar_producao(lote_id: int, usuario_id: int = None, usuario_nome: str = None) -> Programacao:
    """Finaliza a produção de um lote — produto pronto, aguarda transferência."""
    with get_db() as db:
        prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
        if not prog:
            raise ValueError("Lote nao encontrado.")
        if prog.status != "EM PRODUCAO":
            raise ValueError(f"Lote {prog.lote} nao esta em producao (status atual: {prog.status}).")
        
        prog.status = "PRODUCAO FINALIZADA"
        prog.fim_producao_em = datetime.datetime.now()
        registrar_log("programacao", lote_id, "EDITAR",
                       usuario_id=usuario_id, usuario_nome=usuario_nome,
                       campo="status", valor_anterior="EM PRODUCAO",
                       valor_novo="PRODUCAO FINALIZADA", db=db)
        db.commit()
        return prog


def transferir_produto(lote_id: int, usuario_id: int = None, usuario_nome: str = None) -> Programacao:
    """Transfere o produto para logística — encerra o ciclo."""
    with get_db() as db:
        prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
        if not prog:
            raise ValueError("Lote nao encontrado.")
        if prog.status != "PRODUCAO FINALIZADA":
            raise ValueError(f"Lote {prog.lote} nao esta com producao finalizada (status atual: {prog.status}).")
        
        prog.status = "TRANSFERIDO"
        registrar_log("programacao", lote_id, "EDITAR",
                       usuario_id=usuario_id, usuario_nome=usuario_nome,
                       campo="status", valor_anterior="PRODUCAO FINALIZADA",
                       valor_novo="TRANSFERIDO", db=db)
        db.commit()
        return prog


def iniciar_producao_em_massa(lote_ids: List[int], usuario_id: int = None, usuario_nome: str = None):
    """Inicia produção de múltiplos lotes."""
    with get_db() as db:
        for lote_id in lote_ids:
            prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
            if prog and prog.status == "AGUARDANDO INICIO":
                prog.status = "EM PRODUCAO"
                prog.inicio_producao_em = datetime.datetime.now()
                registrar_log("programacao", lote_id, "EDITAR",
                               usuario_id=usuario_id, usuario_nome=usuario_nome,
                               campo="status", valor_anterior="AGUARDANDO INICIO",
                               valor_novo="EM PRODUCAO", db=db)
        db.commit()


def finalizar_producao_em_massa(lote_ids: List[int], usuario_id: int = None, usuario_nome: str = None):
    """Finaliza produção de múltiplos lotes."""
    with get_db() as db:
        for lote_id in lote_ids:
            prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
            if prog and prog.status == "EM PRODUCAO":
                prog.status = "PRODUCAO FINALIZADA"
                prog.fim_producao_em = datetime.datetime.now()
                registrar_log("programacao", lote_id, "EDITAR",
                               usuario_id=usuario_id, usuario_nome=usuario_nome,
                               campo="status", valor_anterior="EM PRODUCAO",
                               valor_novo="PRODUCAO FINALIZADA", db=db)
        db.commit()


def transferir_produto_em_massa(lote_ids: List[int], usuario_id: int = None, usuario_nome: str = None):
    """Transfere múltiplos lotes para logística."""
    with get_db() as db:
        for lote_id in lote_ids:
            prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
            if prog and prog.status == "PRODUCAO FINALIZADA":
                prog.status = "TRANSFERIDO"
                registrar_log("programacao", lote_id, "EDITAR",
                               usuario_id=usuario_id, usuario_nome=usuario_nome,
                               campo="status", valor_anterior="PRODUCAO FINALIZADA",
                               valor_novo="TRANSFERIDO", db=db)
        db.commit()


# ─── Itens de programação (CRUD) ──────────────────────────────────────

def listar_itens_sessao(sessao_id: int) -> List[Programacao]:
    """Lista todos os itens de uma sessão de programação."""
    with get_db() as db:
        return db.query(Programacao).filter(
            Programacao.sessao_id == sessao_id
        ).order_by(Programacao.prioridade).all()


def listar_programacao(data_inicio=None, data_fim=None, 
                       linha_producao=None, status=None, 
                       grupo=None, sessao_id=None) -> List[Programacao]:
    """Lista programações com filtros opcionais."""
    with get_db() as db:
        query = db.query(Programacao)
        if data_inicio:
            query = query.filter(Programacao.data_programacao >= data_inicio)
        if data_fim:
            query = query.filter(Programacao.data_programacao <= data_fim)
        if linha_producao:
            query = query.filter(Programacao.linha_producao == linha_producao)
        if status:
            if isinstance(status, list):
                query = query.filter(Programacao.status.in_(status))
            else:
                query = query.filter(Programacao.status == status)
        if grupo:
            query = query.filter(Programacao.grupo_importacao == grupo)
        if sessao_id:
            query = query.filter(Programacao.sessao_id == sessao_id)
        return query.order_by(Programacao.data_programacao, Programacao.prioridade).all()


def atualizar_status(lote_id: int, novo_status: str,
                     usuario_id: int = None, usuario_nome: str = None) -> Programacao:
    """Atualiza o status de um lote."""
    if novo_status not in STATUS_PROGRAMACAO:
        raise ValueError(f"Status invalido. Deve ser um dos: {', '.join(STATUS_PROGRAMACAO)}")
    with get_db() as db:
        prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
        if not prog:
            raise ValueError("Programacao nao encontrada.")
        
        antigo = prog.status
        prog.status = novo_status
        
        registrar_log("programacao", lote_id, "EDITAR",
                       usuario_id=usuario_id, usuario_nome=usuario_nome,
                       campo="status", valor_anterior=antigo, valor_novo=novo_status,
                       db=db)
        db.commit()
        return prog


def atualizar_status_em_massa(lote_ids: List[int], novo_status: str,
                               usuario_id: int = None, usuario_nome: str = None):
    """Atualiza o status de múltiplos lotes."""
    if novo_status not in STATUS_PROGRAMACAO:
        raise ValueError(f"Status invalido.")
    with get_db() as db:
        for lote_id in lote_ids:
            prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
            if prog:
                antigo = prog.status
                prog.status = novo_status
                registrar_log("programacao", lote_id, "EDITAR",
                               usuario_id=usuario_id, usuario_nome=usuario_nome,
                               campo="status", valor_anterior=antigo,
                               valor_novo=novo_status, db=db)
        db.commit()


def atualizar_observacao(lote_id: int, observacao: str,
                          usuario_id: int = None, usuario_nome: str = None):
    """Atualiza a observação de um lote."""
    with get_db() as db:
        prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
        if prog:
            antigo = prog.observacao
            prog.observacao = observacao
            registrar_log("programacao", lote_id, "EDITAR",
                           usuario_id=usuario_id, usuario_nome=usuario_nome,
                           campo="observacao", valor_anterior=antigo,
                           valor_novo=observacao, db=db)
            db.commit()


def atualizar_prioridade(lote_id: int, nova_prioridade: int,
                          usuario_id: int = None, usuario_nome: str = None):
    """Atualiza a prioridade de um lote."""
    with get_db() as db:
        prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
        if prog:
            antigo = prog.prioridade
            prog.prioridade = nova_prioridade
            registrar_log("programacao", lote_id, "EDITAR",
                           usuario_id=usuario_id, usuario_nome=usuario_nome,
                           campo="prioridade", valor_anterior=str(antigo),
                           valor_novo=str(nova_prioridade), db=db)
            db.commit()


def atualizar_prioridades_em_massa(atualizacoes: List[Dict],
                                    usuario_id: int = None, usuario_nome: str = None):
    """Atualiza prioridades de múltiplos lotes."""
    with get_db() as db:
        for item in atualizacoes:
            prog = db.query(Programacao).filter(Programacao.id == item['id']).first()
            if prog:
                prog.prioridade = item['prioridade']
        db.commit()


def atualizar_quantidade(lote_id: int, nova_quantidade: int,
                          usuario_id: int = None, usuario_nome: str = None):
    """Atualiza a quantidade de um lote e recalcula volume e essência."""
    from utils.helpers import calcular_essencia_kg
    
    with get_db() as db:
        prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
        if prog:
            antigo = prog.quantidade_un
            prog.quantidade_un = nova_quantidade
            # Recalcular volume
            prog.volume_total_l = (nova_quantidade * prog.volume_ml) / 1000
            prog.num_bateladas = max(1, int((prog.volume_total_l + 499) / 500))
            prog.qtd_essencia_kg = calcular_essencia_kg(prog.volume_total_l, prog.pct_essencia)
            
            registrar_log("programacao", lote_id, "EDITAR",
                           usuario_id=usuario_id, usuario_nome=usuario_nome,
                           campo="quantidade_un", valor_anterior=str(antigo),
                           valor_novo=str(nova_quantidade), db=db)
            db.commit()


def excluir_programacao(lote_id: int, usuario_id: int = None, usuario_nome: str = None):
    """Exclui um lote da programação."""
    with get_db() as db:
        prog = db.query(Programacao).filter(Programacao.id == lote_id).first()
        if prog:
            registrar_log("programacao", lote_id, "EXCLUIR",
                           usuario_id=usuario_id, usuario_nome=usuario_nome,
                           valor_anterior=f"{prog.nome_produto} | Lote {prog.lote}",
                           db=db)
            db.delete(prog)
            db.commit()


def obter_resumo_programacao() -> Dict:
    """Retorna estatísticas da programação (somente itens finalizados/em andamento)."""
    resumo = {
        'total_lotes': 0,
        'volume_total_l': 0,
        'lotes_por_status': {},
        'lotes_por_linha': {},
        'ultimos_lotes': []
    }
    with get_db() as db:
        # Filtrar apenas lotes em produção (não rascunhos)
        base = db.query(Programacao).filter(Programacao.status != "RASCUNHO")
        
        total = base.with_entities(
            func.count(Programacao.id), 
            func.sum(Programacao.volume_total_l)
        ).first()
        resumo['total_lotes'] = total[0] or 0
        resumo['volume_total_l'] = total[1] or 0
        
        status_counts = base.with_entities(
            Programacao.status, func.count(Programacao.id)
        ).group_by(Programacao.status).all()
        for status, count in status_counts:
            resumo['lotes_por_status'][status] = count
        
        linha_counts = base.with_entities(
            Programacao.linha_producao, func.count(Programacao.id)
        ).group_by(Programacao.linha_producao).all()
        for linha, count in linha_counts:
            resumo['lotes_por_linha'][linha] = count
        
        resumo['ultimos_lotes'] = base.order_by(
            Programacao.criado_em.desc()
        ).limit(10).all()
    
    return resumo


def listar_grupos_importacao() -> List[str]:
    """Lista todos os grupos distintos de importação."""
    with get_db() as db:
        grupos = db.query(Programacao.grupo_importacao).distinct().filter(
            Programacao.grupo_importacao != None
        ).all()
        return [g[0] for g in grupos]
