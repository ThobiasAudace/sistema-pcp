"""
Criação e migração de tabelas do banco de dados.
"""
import os
import bcrypt
from database.models import Base, Usuario, ControleLote, PERFIS
from database.connection import engine, get_db


def criar_tabelas():
    """Cria todas as tabelas no banco de dados."""
    # Garante que o diretório data/ existe (para SQLite)
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)


def criar_usuario_admin():
    """Cria o usuário admin padrão se não existir."""
    with get_db() as db:
        admin = db.query(Usuario).filter(Usuario.email == "admin@pcp.com").first()
        if not admin:
            senha_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt())
            admin = Usuario(
                nome="Administrador",
                email="admin@pcp.com",
                senha_hash=senha_hash.decode("utf-8"),
                perfil="ADMIN",
                ativo=True,
            )
            db.add(admin)
            db.commit()
            print("[OK] Usuario admin criado (admin@pcp.com / admin123)")


def inicializar_controle_lotes(ano: int = 2026, ultimo_lote: int = 1235):
    """Inicializa o controle de lotes com o último lote conhecido."""
    with get_db() as db:
        controle = db.query(ControleLote).filter(ControleLote.ano == ano).first()
        if not controle:
            controle = ControleLote(ano=ano, ultimo_lote=ultimo_lote)
            db.add(controle)
            db.commit()
            print(f"[OK] Controle de lotes inicializado: ultimo lote = {ultimo_lote}/{str(ano)[2:]}")


def inicializar_banco():
    """Executa todas as migrações e inicializações."""
    print("[INIT] Inicializando banco de dados...")
    criar_tabelas()
    criar_usuario_admin()
    inicializar_controle_lotes()
    print("[OK] Banco de dados pronto!")


if __name__ == "__main__":
    inicializar_banco()
