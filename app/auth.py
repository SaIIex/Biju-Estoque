"""Login de uma usuária só: senha em variável de ambiente, sessão em cookie assinado."""

import hmac

from fastapi import Request

from app.config import settings


class NaoAutenticadoError(Exception):
    """Lançada quando uma página interna é acessada sem login."""


def senha_confere(senha: str) -> bool:
    esperada = settings.app_senha
    if not esperada:  # sem senha configurada, ninguém entra
        return False
    # Comparação em tempo constante: não dá pistas pelo tempo de resposta.
    return hmac.compare_digest(senha.encode(), esperada.encode())


def exigir_login(request: Request) -> None:
    """Dependência das rotas internas."""
    if not request.session.get("logado"):
        raise NaoAutenticadoError
