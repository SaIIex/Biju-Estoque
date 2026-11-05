"""Conexão com o banco: engine, sessões e criação das tabelas."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


_PREFIXOS_POSTGRES = ("postgres://", "postgresql://")


def normalizar_url_banco(url: str) -> str:
    """Aponta URLs de PostgreSQL para o driver psycopg 3. Só o prefixo é trocado."""
    url = url.strip()
    for prefixo in _PREFIXOS_POSTGRES:
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


def _criar_engine(url: str):
    url = normalizar_url_banco(url)
    if url.startswith("sqlite"):
        # SQLite + servidor web: libera o uso da conexão fora da thread que a criou.
        return create_engine(url, connect_args={"check_same_thread": False})
    # PostgreSQL (Neon): o banco "dorme" e derruba conexões paradas.
    # pre_ping testa a conexão antes de usar; recycle renova as antigas.
    return create_engine(url, pool_pre_ping=True, pool_recycle=300)


engine = _criar_engine(settings.database_url)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição."""
    with SessionLocal() as session:
        yield session


def criar_tabelas() -> None:
    from app import modelos  # noqa: F401  registra as tabelas no Base

    Base.metadata.create_all(engine)
