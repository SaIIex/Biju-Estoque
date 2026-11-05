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
