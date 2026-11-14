"""Relatório de lucro do mês, com o mês contado no horário de Brasília."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dominio import estoque as dominio
from app.dominio.lucro import Resultado, calcular_resultado
from app.modelos import Movimentacao, Produto

BRASILIA = timezone(timedelta(hours=-3))


@dataclass(frozen=True)
class PecaNoRelatorio:
    produto_id: int
    nome: str
    unidades_vendidas: int
    receita: Decimal
    resultado: Decimal


@dataclass
class RelatorioMes:
    ano: int
    mes: int
    total: Resultado
    por_peca: list[PecaNoRelatorio] = field(default_factory=list)


def intervalo_utc(ano: int, mes: int) -> tuple[datetime, datetime]:
    """Início e fim (exclusivo) do mês de Brasília, em UTC sem fuso (como o banco guarda)."""
    if not 1 <= mes <= 12:
        raise ValueError(f"Mês inválido: {mes}")
    inicio = datetime(ano, mes, 1, tzinfo=BRASILIA)
    fim = datetime(ano + 1, 1, 1, tzinfo=BRASILIA) if mes == 12 else datetime(ano, mes + 1, 1, tzinfo=BRASILIA)

    def utc_sem_fuso(d: datetime) -> datetime:
        return d.astimezone(timezone.utc).replace(tzinfo=None)

    return utc_sem_fuso(inicio), utc_sem_fuso(fim)


def _para_dominio(m: Movimentacao) -> dominio.Movimentacao:
    return dominio.Movimentacao(m.tipo, m.quantidade, m.custo_unitario, m.preco_venda)


def relatorio_do_mes(session: Session, ano: int, mes: int) -> RelatorioMes:
    inicio, fim = intervalo_utc(ano, mes)
    linhas = session.execute(
        select(Movimentacao, Produto.nome)
        .join(Produto, Produto.id == Movimentacao.produto_id)
        .where(Movimentacao.criado_em >= inicio, Movimentacao.criado_em < fim)
    ).all()

    todas = [_para_dominio(m) for m, _ in linhas]
    por_produto: dict[int, list] = defaultdict(list)
    nomes: dict[int, str] = {}
    for m, nome in linhas:
        por_produto[m.produto_id].append(_para_dominio(m))
        nomes[m.produto_id] = nome

    pecas = []
    for produto_id, movs in por_produto.items():
        r = calcular_resultado(movs)
        if r.unidades_vendidas:
            pecas.append(
                PecaNoRelatorio(produto_id, nomes[produto_id], r.unidades_vendidas, r.receita, r.resultado)
            )
    pecas.sort(key=lambda p: (-p.resultado, p.nome))

    return RelatorioMes(ano=ano, mes=mes, total=calcular_resultado(todas), por_peca=pecas)
