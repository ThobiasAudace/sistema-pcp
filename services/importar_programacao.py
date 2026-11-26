import pandas as pd
import uuid
from typing import Dict, Any, List
from datetime import date
from io import BytesIO
from database.connection import get_db
from database.models import Programacao
from services.cadastro_service import buscar_produto_por_sku, buscar_produto_por_nome
from services.batelada_calculator import processar_item_programacao
from utils.helpers import detectar_volume_ml

def importar_planilha_diretoria(arquivo_bytes: bytes, data_programacao: date, usuario_id: int) -> Dict[str, Any]:
    """
    Importa arquivo Excel (abas AUTO e MANUAL) para gerar programação.
    """
    total_itens = 0
    total_lotes = 0
    itens_nao_encontrados = []
    lotes_gerados = []
    grupo_importacao = str(uuid.uuid4())
    ano_atual = data_programacao.year
    
    try:
        xls = pd.ExcelFile(BytesIO(arquivo_bytes))
        abas = [aba for aba in xls.sheet_names if aba.upper() in ['AUTO', 'MANUAL']]
        
        with get_db() as db:
            for aba in abas:
                prioridade_counter = 0
                df = pd.read_excel(xls, sheet_name=aba)
                
                # Assume-se que col B=ITEM, C=SKU, D=QTD baseado na descrição 
                # (isso pode variar, então ajustaremos via posições ou nomes de colunas, 
                # usaremos posições baseadas em 0 index, onde B=1, C=2, D=3, 
                # mas o ideal é procurar o cabeçalho)
                
                # Tentar achar a linha de cabeçalho
                header_idx = None
                for i in range(min(10, len(df))):
                    row_vals = [str(x).upper() for x in df.iloc[i].values if pd.notna(x)]
                    if any('ITEM' in val for val in row_vals) or any('SKU' in val for val in row_vals):
                        header_idx = i
                        break
                        
                if header_idx is not None:
                    df = pd.read_excel(xls, sheet_name=aba, header=header_idx+1)
                
                # Mapeamento simplificado caso o df não tenha nomes exatos
                col_item = None
                col_sku = None
                col_qtd = None
                
                for col in df.columns:
                    col_str = str(col).upper()
                    if 'ITEM' in col_str or 'PRODUTO' in col_str or 'DESCRI' in col_str:
                        col_item = col
                    elif 'SKU' in col_str or 'CODIGO' in col_str:
                        col_sku = col
                    elif 'QTD' in col_str or 'QUANTIDADE' in col_str:
                        col_qtd = col
                        
                if not col_item or not col_qtd:
                    # Fallback posições (B=1, C=2, D=3)
                    if len(df.columns) > 3:
                        col_item = df.columns[1]
                        col_sku = df.columns[2]
                        col_qtd = df.columns[3]
                    else:
                        continue
                        
                for index, row in df.iterrows():
                    item = row.get(col_item)
                    sku = row.get(col_sku) if col_sku else None
                    qtd = row.get(col_qtd)
                    
                    if pd.isna(item) or pd.isna(qtd):
                        continue
                        
                    try:
                        qtd = int(qtd)
                        if qtd <= 0:
                            continue
                    except ValueError:
                        continue
                        
                    produto = None
                    if pd.notna(sku):
                        produto = buscar_produto_por_sku(str(sku).strip())
                    
                    if not produto and pd.notna(item):
                        produto = buscar_produto_por_nome(str(item).strip())
                        
                    if not produto:
                        itens_nao_encontrados.append(f"{item} (SKU: {sku})")
                        continue
                        
                    # Processar de acordo com a aba
                    if aba.upper() == 'AUTO':
                        produto.volume_ml = 50
                        produto.linha_producao = 'AUTOMATICA'
                    else:
                        # MANUAL - tenta detectar volume do nome
                        produto.volume_ml = detectar_volume_ml(str(item), produto.linha_comercial)
                        produto.linha_producao = 'MANUAL'
                        
                    total_itens += 1
                    prioridade_counter += 1
                    
                    lotes_dados = processar_item_programacao(produto, qtd, ano_atual, db)
                    
                    for lote_dict in lotes_dados:
                        prog = Programacao(
                            data_programacao=data_programacao,
                            prioridade=prioridade_counter,
                            grupo_importacao=grupo_importacao,
                            status='PENDENTE',
                            criado_por=usuario_id,
                            **lote_dict
                        )
                        db.add(prog)
                        total_lotes += 1
                        lotes_gerados.append(lote_dict['lote'])
                        
            db.commit()
            
        return {
            'total_itens': total_itens,
            'total_lotes': total_lotes,
            'itens_nao_encontrados': itens_nao_encontrados,
            'lotes_gerados': lotes_gerados,
            'grupo_importacao': grupo_importacao
        }
    except Exception as e:
        return {
            'total_itens': 0,
            'total_lotes': 0,
            'itens_nao_encontrados': [],
            'lotes_gerados': [],
            'grupo_importacao': None,
            'erro': str(e)
        }
