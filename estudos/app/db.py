# =============================================================================
# db.py: a "tomada" do banco de dados
# =============================================================================
# Três peças, e cada uma tem um par no Entity Framework:
#   engine        -> a conexão física (connection string + pool de conexões)
#   SessionLocal  -> a FÁBRICA de sessões (o DbContextFactory)
#   Session       -> uma conversa com o banco (o DbContext). Rastreia objetos
#                    novos/alterados e só grava no commit (SaveChanges).
#
# SQLAlchemy é o ORM mais usado do Python: o "Entity Framework" de lá.
# =============================================================================

# Iterator[Session]: tipo de retorno de uma função que usa "yield" (abaixo).
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# Classe-mãe de todas as tabelas. Toda classe que herdar de Base vira tabela.
# Ela também guarda o "catálogo" (Base.metadata) com todas as tabelas
# conhecidas, que é usado para criá-las no banco.
# "pass" = corpo vazio (Python não aceita bloco vazio; pass é o "{}" do C#).
class Base(DeclarativeBase):
    pass


# O "_" no começo do nome é CONVENÇÃO de "privado, uso interno deste arquivo".
# Python não tem "private" de verdade; é um combinado entre devs.
def _criar_engine(url: str):
    # O SQLite, por padrão, só deixa usar a conexão na thread que a criou.
    # Um servidor web atende requisições em threads diferentes, então
    # desligamos essa trava. Para PostgreSQL não precisa de nada: dict vazio.
    # Isto é um "if ternário": valor_se_verdade if condição else valor_se_falso
    # Em C#: var connectArgs = url.StartsWith("sqlite") ? new {...} : new {};
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = _criar_engine(settings.database_url)

# expire_on_commit=False: depois do commit, os objetos continuam com os
# valores carregados em memória (sem ir ao banco de novo só para ler).
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição."""
    # "yield" transforma a função num GERADOR: ela entrega a sessão, PAUSA,
    # e quando a requisição termina, continua daqui e sai do "with", que
    # fecha a sessão. Em ASP.NET isso é o DbContext registrado como Scoped:
    # um por requisição, descartado no final automaticamente.
    #
    # "with X as y:" = o "using (var y = X) { }" do C#: garante o fechamento
    # mesmo se der exceção no meio.
    with SessionLocal() as session:
        yield session


def criar_tabelas() -> None:
    # Import DENTRO da função, de propósito: modelos.py importa Base deste
    # arquivo. Se importássemos modelos lá em cima, um arquivo dependeria do
    # outro em círculo (import circular) e o Python quebraria ao iniciar.
    # Importar aqui só acontece quando a função é chamada, quando os dois
    # arquivos já estão carregados.
    from app import modelos  # noqa: F401  registra as tabelas no Base
    # "noqa: F401" avisa ao linter: "sei que parece um import não usado, é
    # intencional". O efeito colateral do import (registrar tabelas) é o objetivo.

    # Cria as tabelas que ainda não existem. É o EnsureCreated() do EF.
    # (Mais tarde, para mudar tabelas existentes, o equivalente das Migrations
    # do EF é o Alembic.)
    Base.metadata.create_all(engine)
