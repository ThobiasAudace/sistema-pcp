import os
from services.cadastro_service import importar_produtos_planilha
from services.estoque_service import importar_estoque_planilha

def importar_dados_iniciais(caminho_planejamento: str, caminho_estoque: str) -> dict:
    """
    Realiza a importação inicial de dados das planilhas existentes (produtos e estoque).
    """
    resultados = {
        'planejamento': None,
        'estoque': None
    }
    
    if os.path.exists(caminho_planejamento):
        print(f"Importando planejamento de {caminho_planejamento}...")
        resultados['planejamento'] = importar_produtos_planilha(caminho_planejamento)
    else:
        resultados['planejamento'] = {'erro': 'Arquivo não encontrado.'}
        
    if os.path.exists(caminho_estoque):
        print(f"Importando estoque de {caminho_estoque}...")
        with open(caminho_estoque, 'rb') as f:
            resultados['estoque'] = importar_estoque_planilha(f.read())
    else:
        resultados['estoque'] = {'erro': 'Arquivo não encontrado.'}
        
    return resultados
