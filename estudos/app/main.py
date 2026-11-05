# =============================================================================
# main.py: o ponto de entrada (versão com login e telas)
# =============================================================================
# Comparação com C#: o Program.cs. Aqui montamos o "pipeline":
#   1. lifespan    -> o que roda ao LIGAR o servidor (criar tabelas)
#   2. middleware  -> camadas por onde TODA requisição passa (sessão/cookie)
#   3. handlers    -> como transformar certas exceções em respostas
#   4. routers     -> os grupos de rotas (login, peças)
# =============================================================================

# asynccontextmanager: transforma uma função com yield num "antes/depois".
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.auth import NaoAutenticadoError
from app.config import settings
from app.db import criar_tabelas
from app.rotas import auth, pecas


# LIFESPAN: antes do yield roda quando o servidor LIGA; depois do yield,
# quando DESLIGA. Em ASP.NET: código no Program.cs antes do app.Run(), ou
# um IHostedService. "async def" é uma função assíncrona (como async Task
# no C#); o FastAPI exige esse formato aqui.
@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_tabelas()  # garante que as tabelas existem (EnsureCreated)
    yield


app = FastAPI(title="Biju Estoque", lifespan=lifespan)

# MIDDLEWARE de sessão: lê o cookie em toda requisição (vira request.session)
# e grava de volta na resposta, ASSINADO com secret_key.
# Em ASP.NET: app.UseSession() / app.UseAuthentication().
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    # same_site="lax": o navegador NÃO envia o cookie em POSTs vindos de
    # OUTROS sites. Isso bloqueia o ataque CSRF mais comum (um site malicioso
    # com um formulário escondido que "vende" peças no seu sistema).
    same_site="lax",
    max_age=60 * 60 * 24 * 30,  # 30 dias logada no celular
)


# Quando qualquer rota lançar NaoAutenticadoError (via exigir_login), em vez
# de erro 500, redirecionamos para o login. Em ASP.NET é o que o
# Cookie Authentication faz com o LoginPath.
@app.exception_handler(NaoAutenticadoError)
def _redirecionar_para_login(request: Request, exc: NaoAutenticadoError):
    return RedirectResponse("/login", status_code=303)


@app.get("/saude")
def saude():
    # Fica FORA do login de propósito: o Render precisa acessar sem senha.
    return {"status": "ok"}


# Pluga os grupos de rotas. Em ASP.NET: app.MapControllers().
app.include_router(auth.router)
app.include_router(pecas.router)
