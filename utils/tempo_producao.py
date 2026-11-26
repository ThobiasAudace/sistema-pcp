"""
Cálculo de tempo útil de produção.

Regras da fábrica:
- Funciona das 07:00 às 19:00 (12h), domingo a domingo
- 1h de almoço (12:00-13:00)
- 15 min intervalo manhã (10:00-10:15)
- 15 min intervalo tarde (16:00-16:15)
- Tempo útil por dia: 10h30min (630 minutos)

Intervalos de trabalho efetivo:
  07:00 - 10:00  (3h00 = 180 min)
  10:15 - 12:00  (1h45 = 105 min)
  13:00 - 16:00  (3h00 = 180 min)
  16:15 - 19:00  (2h45 = 165 min)
  Total: 630 min = 10h30
"""
from datetime import datetime, timedelta, time as dtime


# Blocos de trabalho no dia (inicio, fim) em minutos desde meia-noite
BLOCOS_TRABALHO = [
    (dtime(7, 0), dtime(10, 0)),    # 07:00-10:00
    (dtime(10, 15), dtime(12, 0)),   # 10:15-12:00
    (dtime(13, 0), dtime(16, 0)),    # 13:00-16:00
    (dtime(16, 15), dtime(19, 0)),   # 16:15-19:00
]

MINUTOS_UTEIS_DIA = 630  # 10h30


def _time_to_minutes(t: dtime) -> int:
    return t.hour * 60 + t.minute


def _minutos_uteis_no_dia(hora_inicio: dtime, hora_fim: dtime) -> int:
    """Calcula minutos úteis entre duas horas no MESMO dia."""
    total = 0
    ini_min = _time_to_minutes(hora_inicio)
    fim_min = _time_to_minutes(hora_fim)

    for bloco_ini, bloco_fim in BLOCOS_TRABALHO:
        b_ini = _time_to_minutes(bloco_ini)
        b_fim = _time_to_minutes(bloco_fim)

        # Interseção do intervalo pedido com o bloco de trabalho
        real_ini = max(ini_min, b_ini)
        real_fim = min(fim_min, b_fim)

        if real_fim > real_ini:
            total += real_fim - real_ini

    return total


def calcular_tempo_producao(inicio: datetime, fim: datetime) -> dict:
    """
    Calcula o tempo útil de produção entre dois datetimes.

    Retorna:
        {
            'minutos_uteis': int,
            'horas_uteis': float,
            'texto': str  (ex: '2d 3h 15min')
        }
    """
    if not inicio or not fim or fim <= inicio:
        return {'minutos_uteis': 0, 'horas_uteis': 0.0, 'texto': '---'}

    # Garantir que são datetime (não date)
    import datetime as _dt
    if isinstance(inicio, _dt.date) and not isinstance(inicio, _dt.datetime):
        inicio = _dt.datetime.combine(inicio, dtime(7, 0))
    if isinstance(fim, _dt.date) and not isinstance(fim, _dt.datetime):
        fim = _dt.datetime.combine(fim, dtime(19, 0))

    total_minutos = 0
    inicio_dia = inicio.date()
    fim_dia = fim.date()
    inicio_hora = inicio.time()
    fim_hora = fim.time()

    dia_atual = inicio_dia

    while dia_atual <= fim_dia:
        if dia_atual == inicio_dia and dia_atual == fim_dia:
            # Mesmo dia
            h_ini = inicio_hora
            h_fim = fim_hora
        elif dia_atual == inicio_dia:
            # Primeiro dia: do horário de início até 19:00
            h_ini = inicio_hora
            h_fim = dtime(19, 0)
        elif dia_atual == fim_dia:
            # Último dia: de 07:00 até horário de fim
            h_ini = dtime(7, 0)
            h_fim = fim_hora
        else:
            # Dia inteiro
            h_ini = dtime(7, 0)
            h_fim = dtime(19, 0)

        total_minutos += _minutos_uteis_no_dia(h_ini, h_fim)
        dia_atual += timedelta(days=1)

    # Formatar texto
    horas_uteis = total_minutos / 60
    dias = total_minutos // MINUTOS_UTEIS_DIA
    resto = total_minutos % MINUTOS_UTEIS_DIA
    horas = resto // 60
    minutos = resto % 60

    partes = []
    if dias > 0:
        partes.append(f"{dias}d")
    if horas > 0:
        partes.append(f"{horas}h")
    if minutos > 0 or not partes:
        partes.append(f"{minutos}min")

    return {
        'minutos_uteis': total_minutos,
        'horas_uteis': round(horas_uteis, 2),
        'texto': ' '.join(partes),
    }
