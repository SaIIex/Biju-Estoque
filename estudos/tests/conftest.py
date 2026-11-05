# =============================================================================
# conftest.py: arquivo ESPECIAL do pytest
# =============================================================================
# O pytest carrega este arquivo sozinho (o nome precisa ser exatamente
# conftest.py). O que estiver aqui fica disponível para todos os testes da
# pasta, sem import.
#
# Uma FIXTURE é uma preparação reutilizável. O teste "pede" a fixture só
# colocando o nome dela como parâmetro:
#     def test_algo(session):   <- o pytest vê "session" e injeta a fixture
# É injeção de dependência por nome. Em xUnit, o equivalente é o construtor
# da classe de teste (setup) + Dispose (teardown), ou uma IClassFixture.
# =============================================================================

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
    # "sqlite://" sem caminho = banco SÓ na memória RAM. Nasce vazio, some
    # quando fecha. Rápido e cada teste começa do zero, sem sujeira do anterior.
    #
    # StaticPool: um banco em memória existe só dentro da sua conexão. Se o
    # pool abrisse uma segunda conexão, ela veria um banco DIFERENTE e vazio.
    # StaticPool força todo mundo a usar a mesma conexão.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)  # cria as tabelas no banco vazio

    # O yield divide a fixture em duas metades:
    #   antes do yield = SETUP    (roda antes do teste)
    #   o valor entregue = o que o teste recebe no parâmetro "session"
    #   depois do yield = TEARDOWN (roda depois do teste, mesmo se ele falhar)
    with Session(engine) as s:
        yield s
    engine.dispose()  # fecha as conexões


# =============================================================================
# Fixtures das telas (adicionadas junto com o login)
# =============================================================================
# Uma fixture pode usar OUTRA fixture: "client" recebe "session" (o banco em
# memória acima) e "monkeypatch" (fixture embutida do pytest).
#
# monkeypatch.setattr(objeto, "atributo", valor): troca um valor SÓ durante
# o teste e desfaz sozinho no final. Aqui trocamos a senha configurada por
# uma conhecida. Em C#, o equivalente seria injetar um IOptions<Settings>
# falso na WebApplicationFactory.
#
# app.dependency_overrides[get_session] = ...: diz ao FastAPI "onde alguma
# rota pedir get_session, entregue ESTA função no lugar". Assim as rotas
# usam o banco em memória do teste sem mudar uma linha do código delas.
# Em C#: builder.ConfigureServices(s => s.Replace(... DbContext de teste ...)).
#
# "logado" é uma fixture em cima de "client": faz o login e devolve o
# cliente com o cookie de sessão. Testes que precisam estar logados só
# pedem "logado" como parâmetro.
#
# (Código completo e atual em tests/conftest.py.)
# =============================================================================
