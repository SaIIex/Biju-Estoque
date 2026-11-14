# =============================================================================
# test_dominio_lucro.py: a regra R7 com valores calculados à mão
# =============================================================================
# O L1 é literalmente o exercício que você fez na Fase 1 (resultado R$ 52).
# Quando um teste reproduz um exemplo que o usuário/negócio já validou, ele
# vira uma "spec executável": se alguém mudar a regra sem querer, o exemplo
# combinado com a dona para de bater.
# D = Decimal: apelido curto só para os testes ficarem legíveis.
# =============================================================================

"""Regra R7: resultado do mês por CMV. Valores calculados à mão."""

from decimal import Decimal

from app.dominio.estoque import Movimentacao, TipoMovimentacao as T
from app.dominio.lucro import Resultado, calcular_resultado

D = Decimal


def test_l1_exercicio_da_fase_1():
    # Entrou 10 a R$ 8, vendeu 4 a R$ 25, 1 presente, ajuste -1 (sumiu na conferência).
    # Receita 4x25 = 100 · CMV 4x8 = 32 · lucro bruto 68 · perdas 2x8 = 16 · resultado 52
    movs = [
        Movimentacao(T.ENTRADA, 10, D("8")),
        Movimentacao(T.VENDA, -4, D("8"), preco_venda=D("25")),
        Movimentacao(T.PRESENTE, -1, D("8")),
        Movimentacao(T.AJUSTE, -1, D("8")),
    ]
    assert calcular_resultado(movs) == Resultado(
        receita=D("100"), cmv=D("32"), lucro_bruto=D("68"),
        perdas=D("16"), ajustes_positivos=D("0"), resultado=D("52"),
        unidades_vendidas=4,
    )


def test_l2_mes_seguinte_sem_compra():
    # Vende as 4 restantes a R$ 25 com custo 8: 100 - 32 = 68 (e não 100).
    movs = [Movimentacao(T.VENDA, -4, D("8"), preco_venda=D("25"))]
    r = calcular_resultado(movs)
    assert (r.receita, r.cmv, r.resultado) == (D("100"), D("32"), D("68"))


def test_l3_venda_com_desconto_e_custo_medio_quebrado():
    # Custo médio 16,5 (2 a 15 + 2 a 18), vendeu 1 por 45 em vez de 50: 45 - 16,5 = 28,5
    movs = [Movimentacao(T.VENDA, -1, D("16.5000"), preco_venda=D("45"))]
    assert calcular_resultado(movs).resultado == D("28.5")


def test_l4_ajuste_positivo_soma_e_perdas_subtraem():
    # Achou 1 na gaveta (custo 10): +10 · uso próprio 1 (custo 12) e defeito 2 (custo 12): -36
    movs = [
        Movimentacao(T.AJUSTE, 1, D("10")),
        Movimentacao(T.USO_PROPRIO, -1, D("12")),
        Movimentacao(T.DEFEITO, -2, D("12")),
    ]
    r = calcular_resultado(movs)
    assert r.ajustes_positivos == D("10")
    assert r.perdas == D("36")
    assert r.resultado == D("-26")


def test_l5_mes_vazio_e_tudo_zero():
    r = calcular_resultado([])
    assert r == Resultado(D("0"), D("0"), D("0"), D("0"), D("0"), D("0"), 0)


def test_l6_compras_nao_mexem_no_resultado():
    # Comprar não é prejuízo: a peça continua na gaveta (diferença entre lucro e caixa).
    movs = [Movimentacao(T.ENTRADA, 5, D("20")), Movimentacao(T.ENTRADA, 3, D("30"))]
    assert calcular_resultado(movs).resultado == D("0")
