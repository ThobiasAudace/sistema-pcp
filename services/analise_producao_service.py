"""
Serviço de análise e indicadores de produção.
Consulta dados de programação para gerar métricas e KPIs.
"""
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
from sqlalchemy import func, and_, or_
from database.connection import get_db
from database.models import Programacao, Produto
from utils.tempo_producao import calcular_tempo_producao


def obter_indicadores(data_inicio: date = None, data_fim: date = None,
                       linha_producao: str = None) -> Dict[str, Any]:
    """
    Calcula todos os indicadores de produção para o período.
    """
    with get_db() as db:
        query = db.query(Programacao).filter(
            Programacao.status.notin_(["RASCUNHO"])
        )

        if data_inicio:
            query = query.filter(Programacao.data_programacao >= data_inicio)
        if data_fim:
            query = query.filter(Programacao.data_programacao <= data_fim)
        if linha_producao and linha_producao != "Todas":
            query = query.filter(Programacao.linha_producao == linha_producao)

        programacoes = query.all()

        if not programacoes:
            return _indicadores_vazios()

        # --- Lotes concluídos (com inicio e fim) ---
        concluidos = [p for p in programacoes
                      if p.inicio_producao_em and p.fim_producao_em]

        # --- Calcular tempos de produção ---
        tempos = []
        for p in concluidos:
            t = calcular_tempo_producao(p.inicio_producao_em, p.fim_producao_em)
            tempos.append({
                "id": p.id,
                "lote": p.lote,
                "produto": p.nome_produto,
                "linha": p.linha_producao,
                "quantidade_un": p.quantidade_un,
                "volume_ml": p.volume_ml,
                "volume_total_l": p.volume_total_l or 0,
                "minutos_uteis": t["minutos_uteis"],
                "horas_uteis": t["horas_uteis"],
                "tempo_texto": t["texto"],
                "inicio": p.inicio_producao_em,
                "fim": p.fim_producao_em,
                "data_programacao": p.data_programacao,
            })

        # --- KPIs Gerais ---
        total_lotes = len(programacoes)
        lotes_concluidos = len(concluidos)
        total_unidades = sum(p.quantidade_un or 0 for p in programacoes)
        total_volume_l = sum(p.volume_total_l or 0 for p in programacoes)

        un_concluidas = sum(t["quantidade_un"] for t in tempos)
        vol_concluido_l = sum(t["volume_total_l"] for t in tempos)

        # Tempo médio de produção (minutos úteis)
        if tempos:
            tempo_medio_min = sum(t["minutos_uteis"] for t in tempos) / len(tempos)
            tempo_total_min = sum(t["minutos_uteis"] for t in tempos)
            tempo_min = min(t["minutos_uteis"] for t in tempos)
            tempo_max = max(t["minutos_uteis"] for t in tempos)
        else:
            tempo_medio_min = 0
            tempo_total_min = 0
            tempo_min = 0
            tempo_max = 0

        # Produtividade (un/hora útil)
        produtividade_un_hora = (un_concluidas / (tempo_total_min / 60)) if tempo_total_min > 0 else 0

        # Volume por hora (L/hora útil)
        volume_por_hora = (vol_concluido_l / (tempo_total_min / 60)) if tempo_total_min > 0 else 0

        # --- Por Linha ---
        por_linha = {}
        for linha in ["AUTOMATICA", "MANUAL"]:
            t_linha = [t for t in tempos if t["linha"] == linha]
            lotes_linha = [p for p in programacoes if p.linha_producao == linha]
            if t_linha:
                media_min = sum(t["minutos_uteis"] for t in t_linha) / len(t_linha)
                total_min_linha = sum(t["minutos_uteis"] for t in t_linha)
                un_linha = sum(t["quantidade_un"] for t in t_linha)
                prod_hora = (un_linha / (total_min_linha / 60)) if total_min_linha > 0 else 0
            else:
                media_min = 0
                prod_hora = 0
                un_linha = 0

            por_linha[linha] = {
                "total_lotes": len(lotes_linha),
                "lotes_concluidos": len(t_linha),
                "unidades": sum(p.quantidade_un or 0 for p in lotes_linha),
                "un_concluidas": un_linha,
                "tempo_medio_min": round(media_min, 1),
                "produtividade_un_hora": round(prod_hora, 1),
            }

        # --- Por Produto (top 10 mais produzidos) ---
        prod_map = {}
        for t in tempos:
            nome = t["produto"]
            if nome not in prod_map:
                prod_map[nome] = {"lotes": 0, "unidades": 0, "minutos": 0, "volume_l": 0}
            prod_map[nome]["lotes"] += 1
            prod_map[nome]["unidades"] += t["quantidade_un"]
            prod_map[nome]["minutos"] += t["minutos_uteis"]
            prod_map[nome]["volume_l"] += t["volume_total_l"]

        por_produto = []
        for nome, dados in prod_map.items():
            media = dados["minutos"] / dados["lotes"] if dados["lotes"] > 0 else 0
            prod_hora = (dados["unidades"] / (dados["minutos"] / 60)) if dados["minutos"] > 0 else 0
            por_produto.append({
                "produto": nome,
                "lotes": dados["lotes"],
                "unidades": dados["unidades"],
                "volume_l": round(dados["volume_l"], 2),
                "tempo_medio_min": round(media, 1),
                "produtividade_un_hora": round(prod_hora, 1),
            })
        por_produto.sort(key=lambda x: x["unidades"], reverse=True)

        # --- Produção por dia ---
        por_dia = {}
        for t in tempos:
            dia = t["fim"].date() if isinstance(t["fim"], datetime) else t["fim"]
            dia_str = dia.strftime("%d/%m") if dia else "?"
            if dia_str not in por_dia:
                por_dia[dia_str] = {"lotes": 0, "unidades": 0, "data": dia}
            por_dia[dia_str]["lotes"] += 1
            por_dia[dia_str]["unidades"] += t["quantidade_un"]

        timeline = []
        for dia_str, dados in sorted(por_dia.items(), key=lambda x: x[1]["data"]):
            timeline.append({
                "dia": dia_str,
                "lotes": dados["lotes"],
                "unidades": dados["unidades"],
            })

        # --- Status atual ---
        status_map = {}
        for p in programacoes:
            s = p.status
            if s not in status_map:
                status_map[s] = 0
            status_map[s] += 1

        # --- Top 5 mais rápidos e mais lentos ---
        tempos_sorted = sorted(tempos, key=lambda x: x["minutos_uteis"])
        top_rapidos = tempos_sorted[:5] if len(tempos_sorted) >= 5 else tempos_sorted
        top_lentos = tempos_sorted[-5:][::-1] if len(tempos_sorted) >= 5 else tempos_sorted[::-1]

        return {
            "total_lotes": total_lotes,
            "lotes_concluidos": lotes_concluidos,
            "total_unidades": total_unidades,
            "total_volume_l": round(total_volume_l, 2),
            "un_concluidas": un_concluidas,
            "tempo_medio_min": round(tempo_medio_min, 1),
            "tempo_total_min": round(tempo_total_min, 1),
            "tempo_min_min": round(tempo_min, 1),
            "tempo_max_min": round(tempo_max, 1),
            "produtividade_un_hora": round(produtividade_un_hora, 1),
            "volume_por_hora": round(volume_por_hora, 2),
            "por_linha": por_linha,
            "por_produto": por_produto[:15],
            "timeline": timeline,
            "status_map": status_map,
            "top_rapidos": top_rapidos,
            "top_lentos": top_lentos,
            "detalhes": tempos,
        }


def _indicadores_vazios() -> Dict[str, Any]:
    return {
        "total_lotes": 0,
        "lotes_concluidos": 0,
        "total_unidades": 0,
        "total_volume_l": 0,
        "un_concluidas": 0,
        "tempo_medio_min": 0,
        "tempo_total_min": 0,
        "tempo_min_min": 0,
        "tempo_max_min": 0,
        "produtividade_un_hora": 0,
        "volume_por_hora": 0,
        "por_linha": {},
        "por_produto": [],
        "timeline": [],
        "status_map": {},
        "top_rapidos": [],
        "top_lentos": [],
        "detalhes": [],
    }


def _formatar_tempo(minutos: float) -> str:
    """Formata minutos em texto legível."""
    if minutos <= 0:
        return "---"
    dias = int(minutos) // 630
    resto = int(minutos) % 630
    horas = resto // 60
    mins = resto % 60
    partes = []
    if dias > 0:
        partes.append(f"{dias}d")
    if horas > 0:
        partes.append(f"{horas}h")
    if mins > 0 or not partes:
        partes.append(f"{mins}min")
    return " ".join(partes)
