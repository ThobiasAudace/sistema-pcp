import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy import or_, func
from io import BytesIO
from database.connection import get_db
from database.models import EstoqueEssencia, MovimentacaoEstoque, Programacao

def importar_estoque_planilha(arquivo_bytes: bytes) -> Dict[str, Any]:
    """Importa os dados da última aba (mais recente) da planilha de estoque."""
    try:
        import openpyxl
        from io import BytesIO
        
        wb = openpyxl.load_workbook(BytesIO(arquivo_bytes), read_only=True, data_only=True)
        ultima_aba = wb.sheetnames[-1]
        ws = wb[ultima_aba]
        
        # Interpretar data do nome da aba (formato: DD-MM-YYYY ou DD/MM/YYYY)
        data_ref = datetime.now().date()
        try:
            partes = ultima_aba.replace('/', '-').split('-')
            if len(partes) >= 3:
                dia = int(partes[0])
                mes = int(partes[1])
                ano = int(partes[2])
                if ano < 100:
                    ano += 2000
                data_ref = date(ano, mes, dia)
        except Exception:
            pass
        
        # Ler todas as linhas
        rows = list(ws.iter_rows(min_row=1, values_only=True))
        wb.close()
        
        if not rows:
            return {'total_importados': 0, 'erro': 'Planilha vazia'}
        
        # Colunas por posição (baseado na estrutura conhecida):
        # 0=CÓDIGO, 1=FORNECEDOR, 2=PERFUME, 3=ESSÊNCIAS, 4=%, 5=% YES,
        # 6=QTD. ESTOQUE, 7=SEPARADO ECOMMERCE, 8=OP ABERTA, 9=QTD. NF,
        # 10=QTD. PEDIDO, 11=TOTAL
        
        total_importados = 0
        essencias_importadas = []
        
        def safe_float(val):
            if val is None:
                return 0.0
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0
        
        def safe_str(val):
            if val is None:
                return None
            s = str(val).strip()
            return s if s and s != 'None' else None
        
        with get_db() as db:
            # Remover estoque anterior da mesma data (para evitar duplicatas)
            db.query(EstoqueEssencia).filter(
                EstoqueEssencia.data_referencia == data_ref
            ).delete()
            
            for row in rows[1:]:  # Pular cabeçalho
                try:
                    if len(row) < 4:
                        continue
                    
                    essencia = safe_str(row[3])
                    if not essencia:
                        continue
                    
                    # % YES pode ser número ou "x"
                    pct_yes_val = row[5] if len(row) > 5 else None
                    pct_yes_str = None
                    if pct_yes_val is not None:
                        if isinstance(pct_yes_val, str) and pct_yes_val.lower() == 'x':
                            pct_yes_str = 0.0
                        else:
                            pct_yes_str = safe_float(pct_yes_val)
                    
                    estoque = EstoqueEssencia(
                        data_referencia=data_ref,
                        codigo=int(row[0]) if row[0] else None,
                        fornecedor=safe_str(row[1]),
                        perfume=safe_str(row[2]),
                        essencia=essencia,
                        pct=safe_float(row[4]) if len(row) > 4 else 0,
                        pct_yes=pct_yes_str,
                        qtd_estoque=safe_float(row[6]) if len(row) > 6 else 0,
                        separado_ecommerce=safe_float(row[7]) if len(row) > 7 else 0,
                        op_aberta=safe_float(row[8]) if len(row) > 8 else 0,
                        qtd_nf=safe_float(row[9]) if len(row) > 9 else 0,
                        qtd_pedido=safe_float(row[10]) if len(row) > 10 else 0,
                        total=safe_float(row[11]) if len(row) > 11 else 0,
                    )
                    db.add(estoque)
                    total_importados += 1
                    essencias_importadas.append(essencia)
                except Exception:
                    continue
            db.commit()
        
        return {
            'data_referencia': data_ref.strftime('%d/%m/%Y'),
            'total_importados': total_importados,
            'essencias': essencias_importadas[:10]
        }
    except Exception as e:
        return {'total_importados': 0, 'erro': str(e)}

def listar_estoque(data_referencia: date = None, busca: str = None) -> List[EstoqueEssencia]:
    """Lista o estoque, preferencialmente filtrado pela data mais recente."""
    with get_db() as db:
        if not data_referencia:
            # Buscar a data mais recente disponível
            recente = db.query(func.max(EstoqueEssencia.data_referencia)).scalar()
            data_referencia = recente
            
        query = db.query(EstoqueEssencia)
        if data_referencia:
            query = query.filter(EstoqueEssencia.data_referencia == data_referencia)
            
        if busca:
            termo = f"%{busca}%"
            query = query.filter(or_(
                EstoqueEssencia.essencia.ilike(termo),
                EstoqueEssencia.perfume.ilike(termo),
                EstoqueEssencia.codigo.ilike(termo)
            ))
            
        return query.all()

def verificar_disponibilidade_essencia(essencia: str, qtd_necessaria: float) -> Dict:
    """Verifica se há estoque suficiente para uma essência específica."""
    with get_db() as db:
        # Pega o registro mais recente para a essência
        recente = db.query(EstoqueEssencia).filter(
            EstoqueEssencia.essencia == essencia
        ).order_by(EstoqueEssencia.data_referencia.desc()).first()
        
        qtd_disponivel = recente.total if recente else 0.0
        
        if qtd_disponivel >= qtd_necessaria:
            status = 'DISPONIVEL'
            deficit = 0.0
        elif qtd_disponivel > 0:
            status = 'PARCIAL'
            deficit = qtd_necessaria - qtd_disponivel
        else:
            status = 'INDISPONIVEL'
            deficit = qtd_necessaria
            
        return {
            'essencia': essencia,
            'qtd_necessaria': round(qtd_necessaria, 2),
            'qtd_disponivel': round(qtd_disponivel, 2),
            'status': status,
            'deficit': round(deficit, 2)
        }

def verificar_estoque_programacao(programacao_ids: List[int]) -> List[Dict]:
    """Cruza lotes programados com o estoque para verificar disponibilidade."""
    resultados = []
    
    with get_db() as db:
        # Agrupa necessidades por essência
        necessidades = db.query(
            Programacao.essencia, 
            func.sum(Programacao.qtd_essencia_kg).label('total_necessario')
        ).filter(
            Programacao.id.in_(programacao_ids),
            Programacao.essencia != None
        ).group_by(Programacao.essencia).all()
        
        for essencia, total_necessario in necessidades:
            disp = verificar_disponibilidade_essencia(essencia, float(total_necessario))
            resultados.append(disp)
            
    return resultados

def registrar_entrada(essencia: str, quantidade: float, referencia: str, 
                      observacao: str, usuario_id: int) -> None:
    """Registra uma entrada manual de estoque."""
    with get_db() as db:
        mov = MovimentacaoEstoque(
            essencia=essencia,
            tipo='ENTRADA',
            quantidade=quantidade,
            referencia=referencia,
            observacao=observacao,
            criado_por=usuario_id
        )
        db.add(mov)
        # Idealmente, também atualizaria o saldo na tabela EstoqueEssencia,
        # mas como ela é baseada na importação da planilha, a movimentação 
        # atua como um ajuste/log.
        db.commit()

def registrar_saida(essencia: str, quantidade: float, referencia: str, 
                    observacao: str, usuario_id: int) -> None:
    """Registra uma saída manual de estoque."""
    with get_db() as db:
        mov = MovimentacaoEstoque(
            essencia=essencia,
            tipo='SAIDA',
            quantidade=quantidade,
            referencia=referencia,
            observacao=observacao,
            criado_por=usuario_id
        )
        db.add(mov)
        db.commit()

def listar_movimentacoes(essencia: str = None, tipo: str = None, limit: int = 50) -> List[MovimentacaoEstoque]:
    """Lista o histórico de movimentações."""
    with get_db() as db:
        query = db.query(MovimentacaoEstoque)
        if essencia:
            query = query.filter(MovimentacaoEstoque.essencia == essencia)
        if tipo:
            query = query.filter(MovimentacaoEstoque.tipo == tipo)
            
        return query.order_by(MovimentacaoEstoque.criado_em.desc()).limit(limit).all()
