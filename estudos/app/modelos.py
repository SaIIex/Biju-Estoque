# =============================================================================
# modelos.py: as tabelas do banco, escritas como classes Python
# =============================================================================
# Cada classe = uma tabela. Cada atributo com Mapped[...] = uma coluna.
# É exatamente o "Code First" do Entity Framework: você escreve a classe e o
# ORM gera o CREATE TABLE. Compare com o ER v3 em docs/mapas/modelo-dados.md.
# =============================================================================

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.dominio.estoque import TipoMovimentacao


def _agora() -> datetime:
    # Sempre guardar data/hora em UTC (fuso universal). Converter para o
    # horário de Brasília só na hora de MOSTRAR. Evita confusão com horário
    # de verão e servidores em outro país (o Render roda fora do Brasil).
    # Em C#: DateTime.UtcNow.
    return datetime.now(timezone.utc)


class Produto(Base):
    # Nome da tabela no banco. Em EF: [Table("produto")].
    __tablename__ = "produto"

    # Mapped[int] = coluna do tipo inteiro, NOT NULL (porque não tem "| None").
    # primary_key=True -> chave primária com autoincremento. EF: [Key].
    id: Mapped[int] = mapped_column(primary_key=True)

    # String(30) = VARCHAR(30). unique=True = não deixa repetir (o 01521).
    # EF: [MaxLength(30)] + índice único.
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nome: Mapped[str] = mapped_column(String(120))

    # "str | None" = coluna que ACEITA nulo. Em C#: string? Descricao.
    # Esse é o jeito de dizer "campo opcional".
    descricao: Mapped[str | None] = mapped_column(Text)
    tamanho: Mapped[str | None] = mapped_column(String(20))

    # Numeric(10, 2) = DECIMAL(10,2): até 10 dígitos, 2 depois da vírgula.
    # Preço com 2 casas (centavos). EF: [Column(TypeName = "decimal(10,2)")].
    preco_venda: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    # Custo médio com 4 casas (decisão de 04/11, para dízimas como 47/3).
    # default= é o valor usado se ninguém informar.
    custo_medio: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    foto_url: Mapped[str | None] = mapped_column(String(500))
    ativo: Mapped[bool] = mapped_column(default=True)

    # default=_agora SEM parênteses: passamos a FUNÇÃO, não o resultado.
    # Assim ela é chamada a cada INSERT. Com parênteses, todo produto teria
    # a mesma data: a hora em que o servidor ligou. Bug clássico.
    # Em C#: é passar um delegate (() => DateTime.UtcNow) e não o valor.
    criado_em: Mapped[datetime] = mapped_column(default=_agora)

    # relationship = propriedade de NAVEGAÇÃO, não é coluna.
    # produto.movimentacoes devolve a lista de movimentações dessa peça.
    # EF: public List<Movimentacao> Movimentacoes { get; set; }
    # "Movimentacao" entre aspas porque essa classe é definida mais abaixo
    # (referência adiantada). back_populates liga os dois lados da relação.
    movimentacoes: Mapped[list["Movimentacao"]] = relationship(back_populates="produto")


class Movimentacao(Base):
    __tablename__ = "movimentacao"

    # Regra no próprio BANCO: quantidade nunca zero. É uma segunda linha de
    # defesa. Mesmo que um bug passe pelo código Python, o banco recusa.
    # (A tupla com vírgula no final "(x,)" é obrigatória: sem a vírgula,
    # Python leria só um parêntese comum.)
    __table_args__ = (CheckConstraint("quantidade <> 0", name="ck_quantidade_nao_zero"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    # ForeignKey("produto.id") = FK para a tabela produto.
    # index=True cria índice: buscar movimentações de uma peça fica rápido.
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id"), index=True)

    # Guardamos o Enum como TEXTO ("venda"), não número (2).
    # native_enum=False: usa VARCHAR comum (funciona igual em SQLite e Postgres).
    # create_constraint=True: o banco só aceita os 6 valores válidos.
    # values_callable: salva o VALOR ("uso_proprio") e não o NOME ("USO_PROPRIO").
    # lambda = função anônima de uma linha. Em C#: tipos => tipos.Select(t => t.Value)
    # [t.value for t in tipos] é uma "list comprehension": monta uma lista
    # percorrendo outra. É o .Select(...).ToList() do LINQ.
    tipo: Mapped[TipoMovimentacao] = mapped_column(
        Enum(
            TipoMovimentacao,
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda tipos: [t.value for t in tipos],
        )
    )

    # Sem mapped_column: o SQLAlchemy deduz tudo só pelo tipo (int NOT NULL).
    quantidade: Mapped[int]  # com sinal: + entra, - sai
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    preco_venda: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    transacao_id: Mapped[str | None] = mapped_column(String(36))
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(default=_agora)

    # O outro lado da relação: mov.produto devolve o Produto dono.
    produto: Mapped[Produto] = relationship(back_populates="movimentacoes")
