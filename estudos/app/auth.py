# =============================================================================
# auth.py: o porteiro do sistema
# =============================================================================
# Login de UMA usuária. Não existe tabela de usuários: a senha fica numa
# variável de ambiente (APP_SENHA) no servidor. Para o MVP de uma loja com
# uma dona só, isso é suficiente e tem muito menos pontos de falha.
#
# Como o servidor "lembra" que ela fez login? Por um COOKIE DE SESSÃO
# assinado (configurado no main.py). Analogia: é a pulseira de festa. Na
# entrada (login) você ganha a pulseira; nas outras portas (páginas) o
# segurança só olha a pulseira. A pulseira é ASSINADA com um segredo
# (SESSION_SECRET): se alguém tentar falsificar, a assinatura não bate.
# Em ASP.NET: é o Cookie Authentication.
# =============================================================================

"""Login de uma usuária só: senha em variável de ambiente, sessão em cookie assinado."""

# hmac: módulo de criptografia da biblioteca padrão.
import hmac

from fastapi import Request

from app.config import settings


class NaoAutenticadoError(Exception):
    """Lançada quando uma página interna é acessada sem login."""


def senha_confere(senha: str) -> bool:
    esperada = settings.app_senha

    # PADRÃO SEGURO (fail closed): se esqueceram de configurar a senha no
    # servidor, o sistema fica FECHADO, não aberto. O erro contrário seria
    # "sem senha configurada = qualquer um entra", e aí um deploy mal feito
    # expõe tudo. Na dúvida, a porta fica trancada.
    if not esperada:  # sem senha configurada, ninguém entra
        return False

    # Por que não "return senha == esperada"?
    # O == compara letra por letra e PARA na primeira diferença. Então uma
    # senha com a 1ª letra certa demora um tiquinho mais para ser recusada que
    # uma com a 1ª letra errada. Medindo esse tempo milhares de vezes, um
    # atacante descobre a senha letra por letra (ataque de TEMPO).
    # compare_digest sempre leva o mesmo tempo, acerte ou erre.
    # Em C#: CryptographicOperations.FixedTimeEquals.
    # .encode() transforma str em bytes, que é o que a função compara.
    return hmac.compare_digest(senha.encode(), esperada.encode())


def exigir_login(request: Request) -> None:
    """Dependência das rotas internas."""
    # request.session é um dict guardado no cookie assinado.
    # .get("logado") devolve None se a chave não existir (sem erro).
    # Em C#: o [Authorize] do controller. Aqui é uma dependência que roda
    # antes de cada rota; se lançar exceção, a rota nem executa.
    if not request.session.get("logado"):
        # A exceção é convertida em "redireciona para /login" lá no main.py.
        raise NaoAutenticadoError
