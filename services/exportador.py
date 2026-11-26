import pandas as pd
from io import BytesIO
from typing import List
from database.models import Programacao, EstoqueEssencia

def exportar_programacao_excel(programacoes: List[Programacao]) -> bytes:
    """
    Gera um arquivo Excel com a programação, replicando o formato da planilha atual.
    """
    if not programacoes:
        return b""
        
    data = []
    for p in programacoes:
        data.append({
            'DATA': p.data_programacao.strftime('%d/%m/%Y') if p.data_programacao else '',
            'PRIORIDADE': p.prioridade,
            'LINHA': p.linha_producao,
            'LOTE': p.lote,
            'PRODUTO': p.nome_produto,
            'VOLUME (ml)': p.volume_ml,
            'ESSÊNCIA': p.essencia,
            '% ESSÊNCIA': p.pct_essencia,
            'QTD (UN)': p.quantidade_un,
            'BATELADAS': p.num_bateladas,
            'VOLUME TOTAL (L)': p.volume_total_l,
            'QTD ESSÊNCIA (KG)': p.qtd_essencia_kg,
            'STATUS': p.status,
            'OBSERVAÇÃO': p.observacao
        })
        
    df = pd.DataFrame(data)
    
    # Ordenar por data, linha de produção e prioridade
    df = df.sort_values(by=['DATA', 'LINHA', 'PRIORIDADE'])
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='PROGRAMACAO', index=False)
        
        # Formatações adicionais poderiam ser feitas aqui usando xlsxwriter (workbook, worksheet)
        workbook = writer.book
        worksheet = writer.sheets['PROGRAMACAO']
        
        # Ajuste largura das colunas
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            worksheet.set_column(i, i, column_len)
            
    return output.getvalue()

def exportar_estoque_excel(estoques: List[EstoqueEssencia]) -> bytes:
    """Exporta os dados de estoque para Excel."""
    if not estoques:
        return b""
        
    data = []
    for e in estoques:
        data.append({
            'DATA REF': e.data_referencia.strftime('%d/%m/%Y') if e.data_referencia else '',
            'CÓDIGO': e.codigo,
            'FORNECEDOR': e.fornecedor,
            'PERFUME': e.perfume,
            'ESSÊNCIA': e.essencia,
            '%': e.pct,
            '% YES': e.pct_yes,
            'QTD ESTOQUE': e.qtd_estoque,
            'SEP. ECOMMERCE': e.separado_ecommerce,
            'OP ABERTA': e.op_aberta,
            'QTD NF': e.qtd_nf,
            'QTD PEDIDO': e.qtd_pedido,
            'TOTAL': e.total
        })
        
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='ESTOQUE', index=False)
        worksheet = writer.sheets['ESTOQUE']
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            worksheet.set_column(i, i, column_len)
            
    return output.getvalue()


def exportar_programacao_pdf(programacoes: List[Programacao], titulo: str = "Programacao de Producao") -> bytes:
    """
    Gera um PDF com a tabela de programacao para compartilhar no WhatsApp.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    
    if not programacoes:
        return b""
    
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4),
                            leftMargin=10*mm, rightMargin=10*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'],
                                   fontSize=16, alignment=TA_CENTER,
                                   spaceAfter=5*mm)
    subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Heading2'],
                                      fontSize=12, alignment=TA_LEFT,
                                      spaceAfter=3*mm, spaceBefore=5*mm)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'],
                                 fontSize=7, leading=9)
    
    elements = []
    
    # Titulo
    data_prog = ""
    if programacoes[0].data_programacao:
        data_prog = programacoes[0].data_programacao.strftime('%d/%m/%Y')
    elements.append(Paragraph(f"TOUTI - {titulo}", titulo_style))
    elements.append(Paragraph(f"Data: {data_prog}", styles['Normal']))
    elements.append(Spacer(1, 5*mm))
    
    # Separar por linha de producao
    for linha in ["AUTOMATICA", "MANUAL"]:
        lotes = [p for p in programacoes if p.linha_producao == linha]
        if not lotes:
            continue
        
        nome_linha = "LINHA AUTOMATICA" if linha == "AUTOMATICA" else "LINHA MANUAL"
        elements.append(Paragraph(nome_linha, subtitulo_style))
        
        # Cabecalho
        header = ['Prio', 'Produto', 'Essencia', '%', 'Qtd (un)', 'Lote',
                   'Vol (mL)', 'Bat.', 'Vol Total (L)', 'Ess. (kg)', 'Status']
        
        data = [header]
        for p in lotes:
            pct = f"{p.pct_essencia:.0%}" if p.pct_essencia else "-"
            vol_total = f"{p.volume_total_l:.1f}" if p.volume_total_l else "-"
            ess_kg = f"{p.qtd_essencia_kg:.2f}" if p.qtd_essencia_kg else "-"
            qtd = f"{p.quantidade_un:,}".replace(",", ".") if p.quantidade_un else "-"
            
            data.append([
                str(p.prioridade or ''),
                Paragraph(str(p.nome_produto or ''), cell_style),
                Paragraph(str(p.essencia or '-'), cell_style),
                pct,
                qtd,
                str(p.lote or ''),
                str(p.volume_ml or ''),
                str(p.num_bateladas or 1),
                vol_total,
                ess_kg,
                str(p.status or '')
            ])
        
        # Larguras das colunas
        col_widths = [25, 110, 100, 25, 50, 40, 35, 25, 50, 45, 55]
        
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Estilo da tabela
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (2, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ])
        table.setStyle(style)
        elements.append(table)
        elements.append(Spacer(1, 5*mm))
    
    doc.build(elements)
    return output.getvalue()
