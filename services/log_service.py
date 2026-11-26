"""
Serviço de log de modificações — registra toda alteração feita no sistema.
"""
import datetime
from typing import Optional
from database.connection import get_db
from database.models import LogModificacao


def registrar_log(tabela: str, registro_id: int, acao: str,
                  usuario_id: int = None, usuario_nome: str = None,
                  campo: str = None, valor_anterior: str = None,
                  valor_novo: str = None, db=None):
    """Registra uma entrada no log de modificações."""
    log = LogModificacao(
        tabela=tabela,
        registro_id=registro_id,
        acao=acao,
        campo=campo,
        valor_anterior=str(valor_anterior) if valor_anterior is not None else None,
        valor_novo=str(valor_novo) if valor_novo is not None else None,
        usuario_id=usuario_id,
        usuario_nome=usuario_nome,
        criado_em=datetime.datetime.now()
    )
    
    if db:
        db.add(log)
    else:
        with get_db() as session:
            session.add(log)
            session.commit()


def listar_logs(tabela: str = None, registro_id: int = None, 
                usuario_id: int = None, limit: int = 100):
    """Lista logs de modificações com filtros opcionais."""
    with get_db() as db:
        query = db.query(LogModificacao)
        if tabela:
            query = query.filter(LogModificacao.tabela == tabela)
        if registro_id:
            query = query.filter(LogModificacao.registro_id == registro_id)
        if usuario_id:
            query = query.filter(LogModificacao.usuario_id == usuario_id)
        return query.order_by(LogModificacao.criado_em.desc()).limit(limit).all()


def listar_logs_sessao(sessao_id: int):
    """Lista todos os logs relacionados a uma sessão de programação."""
    with get_db() as db:
        # Logs da sessão em si
        logs_sessao = db.query(LogModificacao).filter(
            LogModificacao.tabela == "programacao_sessoes",
            LogModificacao.registro_id == sessao_id
        ).all()
        
        # Logs dos itens da sessão
        from database.models import Programacao
        itens = db.query(Programacao.id).filter(Programacao.sessao_id == sessao_id).all()
        ids_itens = [i[0] for i in itens]
        
        logs_itens = []
        if ids_itens:
            logs_itens = db.query(LogModificacao).filter(
                LogModificacao.tabela == "programacao",
                LogModificacao.registro_id.in_(ids_itens)
            ).all()
        
        todos = logs_sessao + logs_itens
        todos.sort(key=lambda x: x.criado_em, reverse=True)
        return todos
