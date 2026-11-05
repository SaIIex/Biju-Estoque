"""Conexão com o banco: engine, sessões e criação das tabelas."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _criar_engine(url: str):
    # SQLite + servidor web: libera o uso da conexão fora da thread que a criou.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = _criar_engine(settings.database_url)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição."""
    with SessionLocal() as session:
        yield session


def criar_tabelas() -> None:
    from app import modelos  # noqa: F401  registra as tabelas no Base

    Base.metadata.create_all(engine)
