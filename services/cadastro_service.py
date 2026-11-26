import pandas as pd
from typing import Optional, List, Dict, Any
from sqlalchemy import or_
from database.connection import get_db
from database.models import Produto
from utils.helpers import detectar_volume_ml, detectar_linha_producao, normalizar_nome_produto

def listar_produtos(ativo: bool = True, busca: str = None, linha_producao: str = None) -> List[Produto]:
    """Lista produtos com filtros opcionais."""
    with get_db() as db:
        query = db.query(Produto).filter(Produto.ativo == ativo)
        if busca:
            termo = f"%{busca}%"
            query = query.filter(or_(
                Produto.nome_produto.ilike(termo),
                Produto.sku.ilike(termo),
                Produto.cod_fornecedor.ilike(termo)
            ))
        if linha_producao:
            query = query.filter(Produto.linha_producao == linha_producao)
        return query.all()

def buscar_produto_por_sku(sku: str) -> Optional[Produto]:
    """Busca um produto pelo SKU. Ignora zeros à esquerda (ex: '004729' encontra '4729')."""
    sku = str(sku).strip()
    sku_sem_zeros = sku.lstrip('0') or '0'
    with get_db() as db:
        produto = db.query(Produto).filter(Produto.sku == sku).first()
        if not produto and sku_sem_zeros != sku:
            produto = db.query(Produto).filter(Produto.sku == sku_sem_zeros).first()
        return produto

def buscar_produto_por_nome(nome: str) -> Optional[Produto]:
    """Busca um produto pelo nome, com matching flexível."""
    nome_norm = normalizar_nome_produto(nome)
    with get_db() as db:
        produtos = db.query(Produto).filter(Produto.ativo == True).all()
        
        # 1. Match exato
        for p in produtos:
            if normalizar_nome_produto(p.nome_produto) == nome_norm:
                return p
        
        # 2. Match parcial — nome do cadastro contido no nome buscado ou vice-versa
        for p in produtos:
            p_norm = normalizar_nome_produto(p.nome_produto)
            if p_norm in nome_norm or nome_norm in p_norm:
                return p
        
        # 3. Match por código VIP/FIT/LUX/SPA (ex: "VIP 04" em ambos)
        import re
        match = re.search(r'(VIP\s*\d+|FIT\s+\w+|LUX\s+\w+|SPA\s+\w+)', nome_norm)
        if match:
            chave = match.group(1)
            for p in produtos:
                p_norm = normalizar_nome_produto(p.nome_produto)
                if chave in p_norm:
                    return p
        
        # 4. Match por palavras-chave do nome (BODY SPLASH + VIP XX)
        if "BODY" in nome_norm and "SPLASH" in nome_norm:
            # Buscar por "BODY SPLASH" + código VIP
            vip_match = re.search(r'VIP\s*(\d+)', nome_norm)
            if vip_match:
                vip_code = f"VIP {vip_match.group(1)}"
                vip_code_alt = f"VIP{vip_match.group(1)}"
                for p in produtos:
                    p_norm = normalizar_nome_produto(p.nome_produto)
                    if "BODY" in p_norm and "SPLASH" in p_norm:
                        if vip_code in p_norm or vip_code_alt in p_norm:
                            return p
        
        # 5. Match por TESTER + código do produto
        if "TESTER" in nome_norm:
            vip_match = re.search(r'VIP\s*(\d+)', nome_norm)
            if vip_match:
                vip_code = f"VIP {vip_match.group(1)}"
                for p in produtos:
                    p_norm = normalizar_nome_produto(p.nome_produto)
                    if "TESTER" in p_norm and vip_code in p_norm:
                        return p
        
        return None

def criar_produto(dados: dict) -> Produto:
    """Cria um novo produto."""
    with get_db() as db:
        produto = Produto(**dados)
        db.add(produto)
        db.commit()
        db.refresh(produto)
        
        # Salvar na planilha de SKUs automaticamente
        _adicionar_na_planilha_skus(produto)
        
        return produto


# Caminho da planilha base de SKUs
PLANILHA_SKUS = r"C:\Users\Thobias Andrade\OneDrive - MAS HOLDINGS PARTICIPACOES LTDA\Thobias - NOTEBOOK\PCP\LISTA DE SKUS__DESC.xlsx"


def _adicionar_na_planilha_skus(produto: Produto):
    """Adiciona um produto novo na planilha LISTA DE SKUS__DESC.xlsx."""
    try:
        import openpyxl
        import os
        
        if not os.path.exists(PLANILHA_SKUS):
            return
        
        wb = openpyxl.load_workbook(PLANILHA_SKUS)
        ws = wb['Planilha1']
        
        # Verificar se SKU ja existe
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[2] is not None and str(row[2]).strip() == str(produto.sku).strip():
                wb.close()
                return  # Ja existe
        
        # Adicionar na ultima linha
        proxima_linha = ws.max_row + 1
        ws.cell(row=proxima_linha, column=1, value=produto.linha_comercial or '')
        ws.cell(row=proxima_linha, column=2, value=produto.nome_produto)
        ws.cell(row=proxima_linha, column=3, value=int(produto.sku) if produto.sku and produto.sku.isdigit() else produto.sku)
        
        wb.save(PLANILHA_SKUS)
        wb.close()
    except Exception:
        pass  # Nao falhar se a planilha estiver aberta

def atualizar_produto(id: int, dados: dict) -> Produto:
    """Atualiza dados de um produto."""
    with get_db() as db:
        produto = db.query(Produto).filter(Produto.id == id).first()
        if not produto:
            raise ValueError("Produto não encontrado.")
        for key, value in dados.items():
            if hasattr(produto, key):
                setattr(produto, key, value)
        db.commit()
        db.refresh(produto)
        return produto

def importar_produtos_planilha(filepath: str) -> Dict[str, Any]:
    """Importa produtos da aba 'PROD. ESSENCIA ATUAL...' de uma planilha."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(filepath, data_only=True)
        
        # Busca aba que contém "PROD" e "ESSENCIA" no nome
        sheet_name = None
        for sn in wb.sheetnames:
            if "PROD" in sn.upper() and "ESSENCIA" in sn.upper():
                sheet_name = sn
                break
        
        if not sheet_name:
            return {'importados': 0, 'atualizados': 0, 'erros': ["Aba 'PROD. ESSENCIA ATUAL' nao encontrada na planilha."]}
        
        ws = wb[sheet_name]
        
        # Ler cabeçalhos da primeira linha
        headers_raw = [cell.value for cell in ws[1] if cell.value is not None]
        
        # Mapear colunas por posição (baseado na estrutura conhecida)
        # ITEM(0), MARCA(1), LINHA(2), FORNECEDOR(3), SKU(4), COD.FOR(5), ESSÊNCIA(6), %(7)
        col_map = {
            0: 'nome_produto',
            1: 'marca',
            2: 'linha_comercial',
            3: 'fornecedor',
            4: 'sku',
            5: 'cod_fornecedor',
            6: 'essencia',
            7: 'pct_essencia'
        }
        
        importados = 0
        atualizados = 0
        erros = []

        with get_db() as db:
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True), start=2):
                try:
                    # Extrair valores por posição
                    nome = str(row[0]).strip() if row[0] else None
                    marca = str(row[1]).strip() if row[1] else None
                    linha_com = str(row[2]).strip() if row[2] else None
                    fornecedor = str(row[3]).strip() if row[3] else None
                    sku = str(row[4]).strip() if row[4] else None
                    cod_for = str(row[5]).strip() if row[5] else None
                    essencia = str(row[6]).strip() if row[6] else None
                    pct_raw = row[7] if len(row) > 7 else None
                    
                    if not nome or nome == 'None':
                        continue
                    
                    # Limpar SKU
                    if sku == 'None' or sku == 'X' or sku == 'x':
                        sku = None
                    
                    # Tratar percentual
                    pct = 0.0
                    if pct_raw is not None:
                        try:
                            pct = float(pct_raw)
                        except (ValueError, TypeError):
                            pct = 0.0

                    volume_ml = detectar_volume_ml(nome, linha_com)
                    linha_prod = detectar_linha_producao(volume_ml)
                    
                    dados_prod = {
                        'nome_produto': nome,
                        'marca': marca if marca != 'None' else None,
                        'linha_comercial': linha_com if linha_com != 'None' else None,
                        'fornecedor': fornecedor if fornecedor != 'None' else None,
                        'sku': sku,
                        'cod_fornecedor': cod_for if cod_for != 'None' else None,
                        'essencia': essencia if essencia != 'None' else None,
                        'pct_essencia': pct,
                        'volume_ml': volume_ml,
                        'linha_producao': linha_prod,
                        'ativo': True
                    }

                    # Busca produto existente por SKU ou nome
                    produto = None
                    if sku:
                        produto = db.query(Produto).filter(Produto.sku == sku).first()
                    if not produto and nome:
                        nome_norm = normalizar_nome_produto(nome)
                        for p in db.query(Produto).all():
                            if normalizar_nome_produto(p.nome_produto) == nome_norm:
                                produto = p
                                break
                    
                    if produto:
                        for k, v in dados_prod.items():
                            setattr(produto, k, v)
                        atualizados += 1
                    else:
                        novo_produto = Produto(**dados_prod)
                        db.add(novo_produto)
                        importados += 1
                        
                except Exception as e:
                    erros.append(f"Linha {row_idx}: {str(e)}")
            
            db.commit()
            
        return {
            'importados': importados,
            'atualizados': atualizados,
            'erros': erros
        }
    except Exception as e:
        return {'importados': 0, 'atualizados': 0, 'erros': [f"Erro ao ler arquivo: {str(e)}"]}
