from typing import List, Dict
from sqlalchemy.orm import Session
from datetime import datetime
from database.models import ControleLote, Produto
from utils.helpers import calcular_bateladas, calcular_essencia_kg, formatar_lote

def proximo_lote(ano: int, db: Session) -> int:
    """Obtém o próximo número de lote e incrementa o contador."""
    controle = db.query(ControleLote).filter(ControleLote.ano == ano).first()
    if not controle:
        controle = ControleLote(ano=ano, ultimo_lote=0)
        db.add(controle)
        db.flush()
        
    controle.ultimo_lote += 1
    controle.atualizado_em = datetime.now()
    db.flush()
    return controle.ultimo_lote

def reservar_lotes(ano: int, quantidade: int, db: Session) -> List[str]:
    """Reserva N números de lotes sequenciais e retorna as strings formatadas."""
    controle = db.query(ControleLote).filter(ControleLote.ano == ano).first()
    if not controle:
        controle = ControleLote(ano=ano, ultimo_lote=0)
        db.add(controle)
        
    lotes = []
    for _ in range(quantidade):
        controle.ultimo_lote += 1
        lotes.append(formatar_lote(controle.ultimo_lote, ano))
        
    controle.atualizado_em = datetime.now()
    db.flush()
    return lotes

def processar_item_programacao(produto: Produto, quantidade_un: int, ano: int, db: Session) -> List[Dict]:
    """
    Dado um produto e quantidade, calcula bateladas e gera os dados 
    prontos para criar registros de Programacao.
    """
    calc = calcular_bateladas(quantidade_un, produto.volume_ml)
    num_lotes = len(calc['lotes'])
    
    # Reservar os lotes sequenciais necessários
    lotes_formatados = reservar_lotes(ano, num_lotes, db)
    
    resultados = []
    for i, info_lote in enumerate(calc['lotes']):
        vol_total = info_lote['volume_l']
        qtd_essencia = calcular_essencia_kg(vol_total, produto.pct_essencia)
        
        resultados.append({
            'produto_id': produto.id,
            'nome_produto': produto.nome_produto,
            'essencia': produto.essencia,
            'pct_essencia': produto.pct_essencia,
            'quantidade_un': info_lote['quantidade_un'],
            'lote': lotes_formatados[i],
            'linha_producao': produto.linha_producao,
            'volume_ml': produto.volume_ml,
            'num_bateladas': 1,
            'volume_total_l': vol_total,
            'qtd_essencia_kg': qtd_essencia
        })
        
    return resultados
