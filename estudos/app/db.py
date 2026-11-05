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


# Tupla de prefixos. Tupla = lista imutável (parênteses). Em C#: um array readonly.
_PREFIXOS_POSTGRES = ("postgres://", "postgresql://")


def normalizar_url_banco(url: str) -> str:
    """Aponta URLs de PostgreSQL para o driver psycopg 3. Só o prefixo é trocado."""
    # Por que existe: a URL diz QUAL banco e, opcionalmente, QUAL driver usar
    # ("postgresql+psycopg://"). Sem o "+psycopg", o SQLAlchemy escolhe o driver
    # antigo (psycopg2), que não instalamos, e o app quebra SÓ em produção.
    # É parecido com a connection string do .NET, onde o "Provider" decide
    # qual biblioteca conversa com o banco.
    url = url.strip()  # cola do painel às vezes vem com espaço ou "\n" no fim
    for prefixo in _PREFIXOS_POSTGRES:
        if url.startswith(prefixo):
            # url[len(prefixo):] = "tudo depois do prefixo" (Substring).
            # NÃO usamos url.replace(prefixo, ...): replace troca TODAS as
            # ocorrências, inclusive uma que esteja dentro da senha. Esse bug
            # foi aplicado de propósito e o teste B6 NÃO pegou; daí o B7.
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url  # SQLite e outros: não mexe


# O "_" no começo do nome é CONVENÇÃO de "privado, uso interno deste arquivo".
# Python não tem "private" de verdade; é um combinado entre devs.
def _criar_engine(url: str):
    url = normalizar_url_banco(url)
    if url.startswith("sqlite"):
        # O SQLite, por padrão, só deixa usar a conexão na thread que a criou.
        # Um servidor web atende requisições em threads diferentes, então
        # desligamos essa trava.
        return create_engine(url, connect_args={"check_same_thread": False})

    # PostgreSQL no Neon: depois de 5 min parado, o banco "dorme" e derruba as
    # conexões abertas. O app guarda conexões num POOL (reaproveita em vez de
    # abrir uma nova a cada requisição, como o pool do ADO.NET). Sem cuidado,
    # a primeira requisição depois do cochilo pegaria uma conexão morta e daria
    # erro na cara da dona.
    #   pool_pre_ping=True -> antes de usar, manda um "ping"; se estiver morta,
    #                         descarta e abre outra. Custo: milissegundos.
    #   pool_recycle=300   -> conexões com mais de 300 s são renovadas.
    return create_engine(url, pool_pre_ping=True, pool_recycle=300)


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
