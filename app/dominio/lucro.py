"""Regra R7: resultado do mês por CMV (custo da mercadoria vendida). Função pura."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.dominio.estoque import Movimentacao, TipoMovimentacao

PERDAS = frozenset(
    {TipoMovimentacao.PRESENTE, TipoMovimentacao.USO_PROPRIO, TipoMovimentacao.DEFEITO}
)


@dataclass(frozen=True)
class Resultado:
    receita: Decimal            # soma do preço real cobrado
    cmv: Decimal                # custo congelado das peças vendidas
    lucro_bruto: Decimal        # receita - cmv
    perdas: Decimal             # presente, uso próprio, defeito e ajuste negativo (pelo custo)
    ajustes_positivos: Decimal  # peças achadas na conferência (pelo custo)
    resultado: Decimal          # lucro_bruto - perdas + ajustes_positivos
    unidades_vendidas: int


def calcular_resultado(movimentacoes: Iterable[Movimentacao]) -> Resultado:
    zero = Decimal("0")
    receita = cmv = perdas = ajustes_positivos = zero
    unidades = 0

    for m in movimentacoes:
        pecas = abs(m.quantidade)
        if m.tipo == TipoMovimentacao.VENDA:
            receita += m.preco_venda * pecas
            cmv += m.custo_unitario * pecas
            unidades += pecas
        elif m.tipo in PERDAS or (m.tipo == TipoMovimentacao.AJUSTE and m.quantidade < 0):
            perdas += m.custo_unitario * pecas
        elif m.tipo == TipoMovimentacao.AJUSTE:
            ajustes_positivos += m.custo_unitario * pecas
        # ENTRADA não entra: compra não é prejuízo, a peça continua no estoque.

    lucro_bruto = receita - cmv
    return Resultado(
        receita=receita,
        cmv=cmv,
        lucro_bruto=lucro_bruto,
        perdas=perdas,
        ajustes_positivos=ajustes_positivos,
        resultado=lucro_bruto - perdas + ajustes_positivos,
        unidades_vendidas=unidades,
    )
