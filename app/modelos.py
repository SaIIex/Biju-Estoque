"""Tabelas do banco (ER v3 em docs/mapas/modelo-dados.md)."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.dominio.estoque import TipoMovimentacao


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class Produto(Base):
    __tablename__ = "produto"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str | None] = mapped_column(Text)
    tamanho: Mapped[str | None] = mapped_column(String(20))
    preco_venda: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    custo_medio: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    foto_url: Mapped[str | None] = mapped_column(String(500))
    ativo: Mapped[bool] = mapped_column(default=True)
    criado_em: Mapped[datetime] = mapped_column(default=_agora)

    movimentacoes: Mapped[list["Movimentacao"]] = relationship(back_populates="produto")


class Movimentacao(Base):
    __tablename__ = "movimentacao"
    __table_args__ = (CheckConstraint("quantidade <> 0", name="ck_quantidade_nao_zero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id"), index=True)
    tipo: Mapped[TipoMovimentacao] = mapped_column(
        Enum(
            TipoMovimentacao,
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda tipos: [t.value for t in tipos],
        )
    )
    quantidade: Mapped[int]  # com sinal: + entra, - sai
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    preco_venda: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    transacao_id: Mapped[str | None] = mapped_column(String(36))
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(default=_agora)

    produto: Mapped[Produto] = relationship(back_populates="movimentacoes")
