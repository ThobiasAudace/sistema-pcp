"""
Funções auxiliares e utilitárias.
"""
import re
import math
from database.models import CAPACIDADE_BATELADA_L


# ─── Formatação numérica BR (ponto milhar, vírgula decimal) ──────────

def fmt_int(valor) -> str:
    """Formata inteiro com separador de milhar brasileiro. Ex: 1.000"""
    if valor is None:
        return "0"
    return f"{int(valor):,}".replace(",", ".")


def fmt_dec(valor, casas: int = 1) -> str:
    """Formata decimal no padrão BR. Ex: 1.234,5"""
    if valor is None:
        return "0"
    txt = f"{float(valor):,.{casas}f}"
    # Trocar , por TEMP, depois . por , e TEMP por .
    txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
    return txt


def detectar_volume_ml(nome_produto: str, linha_comercial: str = None) -> int:
    """
    Detecta o volume do produto em mL baseado no nome e linha comercial.

    Regras:
    - Linha TOUTI (VIP, FIT, LUX, SPA sem mL no nome) → 50mL (Automática)
    - "200ML" ou "BODY SPLASH" sem mL → 200mL
    - "120ML" → 120mL
    - "100ML" → 100mL
    - "30ML" → 30mL
    - "25ML" ou "15ML" → 25mL / 15mL
    - Linha YES → 100mL
    """
    nome_upper = nome_produto.upper().strip()

    # Buscar volume explícito no nome (ex: "100ML", "30 ML", "200ML")
    match = re.search(r'(\d+)\s*ML', nome_upper)
    if match:
        return int(match.group(1))

    # Buscar volume na linha comercial (ex: "50ML", "30ML", "100ML")
    if linha_comercial:
        lc = linha_comercial.upper().strip()
        match_lc = re.search(r'(\d+)\s*ML', lc)
        if match_lc:
            return int(match_lc.group(1))

    # Body Splash sem volume explícito → 200mL
    if "BODY SPLASH" in nome_upper or "BODY\xa0SPLASH" in nome_upper:
        return 200

    # Linha YES → 100mL
    if linha_comercial and linha_comercial.upper().strip() == "YES":
        return 100

    # Linha TOUTI (VIP, FIT, LUX, SPA) → 50mL
    if linha_comercial and linha_comercial.upper().strip() == "TOUTI":
        return 50

    # SPECIAL sem volume explícito → 100mL
    if linha_comercial and linha_comercial.upper().strip() == "SPECIAL":
        return 100

    # Default → 100mL
    return 100


def detectar_linha_producao(volume_ml: int) -> str:
    """
    Determina a linha de produção com base no volume.
    50mL → AUTOMATICA, demais → MANUAL.
    """
    return "AUTOMATICA" if volume_ml == 50 else "MANUAL"


def calcular_bateladas(quantidade_un: int, volume_ml: int) -> dict:
    """
    Calcula o número de bateladas e divide a produção.

    Args:
        quantidade_un: Quantidade total em unidades
        volume_ml: Volume de cada frasco em mL

    Returns:
        dict com:
        - volume_total_l: Volume total em litros
        - num_bateladas: Número de bateladas necessárias
        - lotes: Lista de dicts com quantidade por lote
    """
    volume_total_l = (quantidade_un * volume_ml) / 1000
    capacidade_batelada_un = int((CAPACIDADE_BATELADA_L * 1000) / volume_ml)
    num_bateladas = math.ceil(volume_total_l / CAPACIDADE_BATELADA_L)

    lotes = []
    restante = quantidade_un
    for i in range(num_bateladas):
        qtd_lote = min(restante, capacidade_batelada_un)
        vol_lote = (qtd_lote * volume_ml) / 1000
        lotes.append({
            "quantidade_un": qtd_lote,
            "volume_l": vol_lote,
            "num_bateladas": 1,
        })
        restante -= qtd_lote

    return {
        "volume_total_l": volume_total_l,
        "num_bateladas": num_bateladas,
        "capacidade_batelada_un": capacidade_batelada_un,
        "lotes": lotes,
    }


def calcular_essencia_kg(volume_l: float, pct_essencia: float) -> float:
    """Calcula a quantidade de essência em kg para um dado volume e %."""
    if pct_essencia and volume_l:
        return round(volume_l * pct_essencia, 2)
    return 0


def formatar_lote(numero: int, ano: int) -> str:
    """Formata o número do lote como 'NNNN/AA'. Ex: 1236/26."""
    return f"{numero}/{str(ano)[2:]}"


def normalizar_nome_produto(nome: str) -> str:
    """Normaliza o nome do produto para busca (remove espaços extras, upper)."""
    if not nome:
        return ""
    # Remove espaços extras e non-breaking spaces
    nome = nome.replace("\xa0", " ")
    nome = re.sub(r'\s+', ' ', nome)
    return nome.strip().upper()
