"""
Utilitário de autenticação compartilhado entre todas as páginas.
"""
from utils.session import verificar_autenticacao, restaurar_login

__all__ = ['verificar_autenticacao', 'restaurar_login']
