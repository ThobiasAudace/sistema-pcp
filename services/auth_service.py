import bcrypt
from typing import Optional, List
from database.connection import get_db
from database.models import Usuario, PERFIS

def verificar_login(email: str, senha: str) -> Optional[Usuario]:
    """Verifica as credenciais do usuário."""
    with get_db() as db:
        usuario = db.query(Usuario).filter(Usuario.email == email, Usuario.ativo == True).first()
        if usuario and bcrypt.checkpw(senha.encode('utf-8'), usuario.senha_hash.encode('utf-8')):
            return usuario
        return None

def criar_usuario(nome: str, email: str, senha: str, perfil: str) -> Usuario:
    """Cria um novo usuário."""
    if perfil not in PERFIS:
        raise ValueError(f"Perfil inválido. Deve ser um dos: {', '.join(PERFIS)}")
    
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    with get_db() as db:
        if db.query(Usuario).filter(Usuario.email == email).first():
            raise ValueError("Email já cadastrado.")
            
        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=senha_hash,
            perfil=perfil,
            ativo=True
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

def listar_usuarios() -> List[Usuario]:
    """Lista todos os usuários cadastrados."""
    with get_db() as db:
        return db.query(Usuario).all()

def atualizar_usuario(id: int, **kwargs) -> Usuario:
    """Atualiza dados de um usuário."""
    with get_db() as db:
        usuario = db.query(Usuario).filter(Usuario.id == id).first()
        if not usuario:
            raise ValueError("Usuário não encontrado.")
            
        if 'senha' in kwargs and kwargs['senha']:
            senha = kwargs.pop('senha')
            kwargs['senha_hash'] = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
        for key, value in kwargs.items():
            if hasattr(usuario, key):
                setattr(usuario, key, value)
                
        db.commit()
        db.refresh(usuario)
        return usuario

def desativar_usuario(id: int) -> None:
    """Desativa um usuário."""
    with get_db() as db:
        usuario = db.query(Usuario).filter(Usuario.id == id).first()
        if not usuario:
            raise ValueError("Usuário não encontrado.")
        usuario.ativo = False
        db.commit()

def verificar_permissao(usuario: Usuario, permissao: str) -> bool:
    """Verifica se o usuário tem permissão para uma ação."""
    if usuario.perfil == 'ADMIN':
        return True
    
    permissoes = {
        'DIRETORIA': ['inserir_programacao', 'ver_dashboard'],
        'SUPERVISOR': ['editar', 'confirmar', 'exportar'],
        'OPERACIONAL': ['atualizar_status']
    }
    
    # Hierarquia simples
    if usuario.perfil == 'DIRETORIA' and permissao in permissoes['DIRETORIA']:
        return True
    if usuario.perfil == 'SUPERVISOR' and permissao in permissoes['SUPERVISOR']:
        return True
    if usuario.perfil == 'OPERACIONAL' and permissao in permissoes['OPERACIONAL']:
        return True
        
    return False
