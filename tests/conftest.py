"""Fixtures compartilhadas pelos testes."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import modelos  # noqa: F401  registra as tabelas
from app.db import Base


@pytest.fixture
def session():
    """Banco SQLite em memória, novo e vazio para cada teste."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


SENHA_TESTE = "senha-de-teste"


@pytest.fixture
def client(session, monkeypatch):
    """App web usando o banco em memória da fixture `session` e uma senha conhecida."""
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.db import get_session
    from app.main import app

    monkeypatch.setattr(settings, "app_senha", SENHA_TESTE)

    def _sessao_de_teste():
        yield session

    app.dependency_overrides[get_session] = _sessao_de_teste
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def logado(client):
    """Cliente já autenticado."""
    resposta = client.post("/login", data={"senha": SENHA_TESTE}, follow_redirects=False)
    assert resposta.status_code == 303, "login da fixture falhou"
    return client
