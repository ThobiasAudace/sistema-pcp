"""
Conexão com banco de dados.
SQLite para desenvolvimento local, PostgreSQL (Supabase) para produção.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# Usa DATABASE_URL do ambiente (PostgreSQL em produção)
# Ou SQLite local para desenvolvimento
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///data/pcp.db"
)

# Render usa "postgres://" mas SQLAlchemy precisa de "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    # SQLite precisa de check_same_thread=False para Streamlit
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


@contextmanager
def get_db() -> Session:
    """Context manager para obter sessão do banco."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_session() -> Session:
    """Retorna uma sessão do banco (para uso direto)."""
    return SessionLocal()
