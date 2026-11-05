from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.auth import NaoAutenticadoError
from app.config import settings
from app.db import criar_tabelas
from app.rotas import auth, pecas


@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_tabelas()
    yield


app = FastAPI(title="Biju Estoque", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    max_age=60 * 60 * 24 * 30,  # 30 dias logada no celular
)


@app.exception_handler(NaoAutenticadoError)
def _redirecionar_para_login(request: Request, exc: NaoAutenticadoError):
    return RedirectResponse("/login", status_code=303)


@app.get("/saude")
def saude():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(pecas.router)
