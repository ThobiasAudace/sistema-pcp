"""
Modelos de dados do sistema PCP (SQLAlchemy ORM).
"""
import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Date, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Usuario(Base):
    """Usuários do sistema com perfis de acesso."""
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    senha_hash = Column(String(256), nullable=False)
    perfil = Column(String(20), nullable=False)  # ADMIN, DIRETORIA, SUPERVISOR, OPERACIONAL
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)


class Produto(Base):
    """Cadastro de produtos com mapeamento para essência e linha de produção."""
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_produto = Column(String(200), nullable=False)
    marca = Column(String(50))                    # TOUTI, YES
    linha_comercial = Column(String(50))           # TOUTI, SPECIAL, YES, BODY SPLASH
    fornecedor = Column(String(100))               # VOLLMENS, ROBERTET
    sku = Column(String(50))                       # Código SKU
    cod_fornecedor = Column(String(50))            # Código do fornecedor
    essencia = Column(String(200))                 # Nome da essência
    pct_essencia = Column(Float)                   # % de essência (ex: 0.20)
    pct_essencia_yes = Column(Float, nullable=True)  # % para versão YES (null se não tem)
    volume_ml = Column(Integer)                    # Volume do frasco em mL
    linha_producao = Column(String(20))            # AUTOMATICA ou MANUAL
    ativo = Column(Boolean, default=True)

    programacoes = relationship("Programacao", back_populates="produto")


class ProgramacaoSessao(Base):
    """Sessão de programação — agrupa itens de uma mesma rodada de planejamento."""
    __tablename__ = "programacao_sessoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    descricao = Column(String(200), nullable=True)  # Ex: "Programação 09/10/2026"
    status = Column(String(20), default="RASCUNHO")  # RASCUNHO, GERADA, FINALIZADA
    criado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)
    gerado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    gerado_em = Column(DateTime, nullable=True)
    finalizado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    finalizado_em = Column(DateTime, nullable=True)

    itens = relationship("Programacao", back_populates="sessao", cascade="all, delete-orphan")

    criador = relationship("Usuario", foreign_keys=[criado_por])
    gerador = relationship("Usuario", foreign_keys=[gerado_por])
    finalizador = relationship("Usuario", foreign_keys=[finalizado_por])


class Programacao(Base):
    """Programação de produção — cada registro = 1 lote = 1 batelada."""
    __tablename__ = "programacao"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sessao_id = Column(Integer, ForeignKey("programacao_sessoes.id"), nullable=True)
    data_programacao = Column(Date, nullable=False)
    prioridade = Column(Integer)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=True)
    nome_produto = Column(String(200))             # Desnormalizado por conveniência
    essencia = Column(String(200))
    pct_essencia = Column(Float)
    quantidade_un = Column(Integer, nullable=False)
    lote = Column(String(20), nullable=False, unique=True)
    linha_producao = Column(String(20), nullable=False)  # AUTOMATICA ou MANUAL
    volume_ml = Column(Integer)
    num_bateladas = Column(Integer, default=1)
    volume_total_l = Column(Float)                 # Volume total em litros
    qtd_essencia_kg = Column(Float)                # Quantidade de essência em kg
    status = Column(String(30), default="RASCUNHO")
    observacao = Column(Text, nullable=True)
    criado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)
    grupo_importacao = Column(String(50), nullable=True)  # Compatibilidade
    inicio_producao_em = Column(DateTime, nullable=True)   # Quando a produção iniciou
    fim_producao_em = Column(DateTime, nullable=True)      # Quando a produção finalizou

    sessao = relationship("ProgramacaoSessao", back_populates="itens")
    produto = relationship("Produto", back_populates="programacoes")


class ControleLote(Base):
    """Controle do último número de lote sequencial por ano."""
    __tablename__ = "controle_lotes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ano = Column(Integer, nullable=False, unique=True)
    ultimo_lote = Column(Integer, nullable=False, default=0)
    atualizado_em = Column(DateTime, default=datetime.datetime.utcnow)


class EstoqueEssencia(Base):
    """Snapshot do estoque de essências (importado da planilha ou gerenciado no sistema)."""
    __tablename__ = "estoque_essencias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_referencia = Column(Date)
    codigo = Column(Integer, nullable=True)
    fornecedor = Column(String(100))
    perfume = Column(String(200))
    essencia = Column(String(200))
    pct = Column(Float, nullable=True)
    pct_yes = Column(String(20), nullable=True)
    qtd_estoque = Column(Float, default=0)
    separado_ecommerce = Column(Float, default=0)
    op_aberta = Column(Float, default=0)
    qtd_nf = Column(Float, default=0)
    qtd_pedido = Column(Float, default=0)
    total = Column(Float, default=0)


class MovimentacaoEstoque(Base):
    """Movimentações manuais de estoque de essências (entrada/saída)."""
    __tablename__ = "movimentacao_estoque"

    id = Column(Integer, primary_key=True, autoincrement=True)
    essencia = Column(String(200), nullable=False)
    tipo = Column(String(10), nullable=False)      # ENTRADA ou SAIDA
    quantidade = Column(Float, nullable=False)
    referencia = Column(String(100))
    observacao = Column(Text, nullable=True)
    criado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)


class LogModificacao(Base):
    """Log de auditoria — registra todas as modificações no sistema."""
    __tablename__ = "log_modificacoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tabela = Column(String(50), nullable=False)    # Ex: "programacao", "programacao_sessoes"
    registro_id = Column(Integer, nullable=False)   # ID do registro modificado
    acao = Column(String(20), nullable=False)       # CRIAR, EDITAR, EXCLUIR, GERAR, FINALIZAR
    campo = Column(String(50), nullable=True)       # Campo alterado (null para CRIAR/EXCLUIR)
    valor_anterior = Column(Text, nullable=True)
    valor_novo = Column(Text, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario_nome = Column(String(100), nullable=True)  # Desnormalizado
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)


# Status da sessão de programação
STATUS_SESSAO = ["RASCUNHO", "GERADA", "FINALIZADA"]

# Status dos lotes individuais — ciclo de vida da produção
STATUS_PROGRAMACAO = [
    "RASCUNHO",              # Em edição na programação
    "AGUARDANDO INICIO",     # Programação finalizada, aguarda início na fábrica
    "EM PRODUCAO",           # Produção iniciada na fábrica
    "PRODUCAO FINALIZADA",   # Produção finalizada, aguardando transferência
    "TRANSFERIDO",           # Transferido para logística — ciclo encerrado
]

# Perfis de acesso
PERFIS = ["ADMIN", "DIRETORIA", "SUPERVISOR", "OPERACIONAL"]

# Capacidade máxima por batelada (litros)
CAPACIDADE_BATELADA_L = 500

# Mapeamento de volume por tipo de produto
VOLUMES_ML = {
    "50": 50,
    "100": 100,
    "30": 30,
    "25": 25,
    "120": 120,
    "200": 200,
}
