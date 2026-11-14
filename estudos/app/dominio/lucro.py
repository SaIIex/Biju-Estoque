# =============================================================================
# dominio/lucro.py: a regra R7, o "quanto a dona ganhou no mês"
# =============================================================================
# Lembra do exercício da Fase 1? A conta "vendas - tudo que gastei" mostrava
# um mês ruim (12) e outro ótimo (100) só por causa de QUANDO ela comprou.
# Aqui usamos o CMV (custo da mercadoria vendida): de cada venda, desconta só
# o custo DAQUELA peça. Comprar não é prejuízo: a peça continua na gaveta.
#
# Função pura, igual ao estoque.py: recebe uma lista de movimentações e
# devolve números. Nada de banco. Por isso os testes L1 a L6 são rápidos e
# usam valores calculados à mão.
# =============================================================================

"""Regra R7: resultado do mês por CMV (custo da mercadoria vendida). Função pura."""

# Iterable = "qualquer coisa que dá para percorrer com for" (lista, gerador...).
# Em C#: IEnumerable<T>. Aceitar o tipo mais genérico deixa a função flexível.
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.dominio.estoque import Movimentacao, TipoMovimentacao

PERDAS = frozenset(
    {TipoMovimentacao.PRESENTE, TipoMovimentacao.USO_PROPRIO, TipoMovimentacao.DEFEITO}
)


# O resultado é um "objeto de valor": só dados, imutável (frozen).
# Vantagem nos testes: dois Resultado com os mesmos números são IGUAIS (==),
# então o teste L1 compara o objeto inteiro de uma vez.
# Em C#: um record com 7 propriedades.
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
    # Atribuição em cadeia: as 4 variáveis começam com zero.
    # Seguro aqui porque Decimal é imutável (somar cria um Decimal novo).
    receita = cmv = perdas = ajustes_positivos = zero
    unidades = 0

    # Um único for passando por tudo, como um "acumulador". Em C# daria para
    # fazer 4 consultas LINQ (.Where(...).Sum(...)), mas um laço só é mais
    # direto de ler e percorre a lista uma vez.
    for m in movimentacoes:
        pecas = abs(m.quantidade)  # abs = valor absoluto (Math.Abs): -4 vira 4
        if m.tipo == TipoMovimentacao.VENDA:
            # Preço REAL cobrado (com desconto) e custo CONGELADO na hora da venda.
            # Por isso guardamos os dois na movimentação: o relatório não
            # depende do preço/custo de hoje no cadastro.
            receita += m.preco_venda * pecas
            cmv += m.custo_unitario * pecas
            unidades += pecas
        elif m.tipo in PERDAS or (m.tipo == TipoMovimentacao.AJUSTE and m.quantidade < 0):
            # Perda vale o CUSTO, não o preço de venda (decisão da Fase 1:
            # ela perdeu o que pagou, não o que "deixou de ganhar").
            perdas += m.custo_unitario * pecas
        elif m.tipo == TipoMovimentacao.AJUSTE:
            # Ajuste positivo: achou peça na conferência. Volta o custo.
            ajustes_positivos += m.custo_unitario * pecas
        # ENTRADA não entra: compra não é prejuízo, a peça continua no estoque.
        # (Testado no L6. E uma quebra proposital que contava compra como
        # custo foi pega por 4 testes.)

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
