"""Testes das regras de estoque (R1, R2, R3, R6 de docs/mapas/modelo-dados.md).

Todos os valores esperados foram calculados à mão a partir da spec.
"""

from decimal import Decimal

import pytest

from app.dominio.estoque import (
    EstoqueInsuficienteError,
    Movimentacao,
    SinalInvalidoError,
    TipoMovimentacao as T,
    calcular_saldo,
    limite_alerta,
    novo_custo_medio,
    precisa_alerta,
    validar_saida,
    validar_sinal,
)


# --- R3: custo médio ponderado ------------------------------------------------

@pytest.mark.parametrize(
    "saldo, custo_medio, qtd_entrada, custo_entrada, esperado",
    [
        # T1: (2x15 + 2x18) / 4 = 66 / 4
        (2, Decimal("15"), 2, Decimal("18"), Decimal("16.5000")),
        # T2: (1x15 + 3x18) / 4 = 69 / 4
        (1, Decimal("15"), 3, Decimal("18"), Decimal("17.2500")),
        # T3: primeira compra, sem estoque anterior
        (0, Decimal("0"), 3, Decimal("15"), Decimal("15.0000")),
        # T4: (1x15 + 2x16) / 3 = 47 / 3 = 15,6666... -> 4 casas, arredonda para cima
        (1, Decimal("15"), 2, Decimal("16"), Decimal("15.6667")),
    ],
    ids=["T1-2a15+2a18", "T2-1a15+3a18", "T3-primeira-compra", "T4-dizima-4-casas"],
)
def test_novo_custo_medio(saldo, custo_medio, qtd_entrada, custo_entrada, esperado):
    assert novo_custo_medio(saldo, custo_medio, qtd_entrada, custo_entrada) == esperado


# --- R1: saldo = soma das movimentações ---------------------------------------

def test_saldo_soma_movimentacoes():
    # T5: o exercício da Fase 1. Entrou 10, vendeu 4, presente 1, ajuste -1 -> 4
    movs = [
        Movimentacao(T.ENTRADA, 10, Decimal("8")),
        Movimentacao(T.VENDA, -4, Decimal("8"), preco_venda=Decimal("25")),
        Movimentacao(T.PRESENTE, -1, Decimal("8")),
        Movimentacao(T.AJUSTE, -1, Decimal("8")),
    ]
    assert calcular_saldo(movs) == 4


def test_saldo_sem_movimentacoes_e_zero():
    # T6
    assert calcular_saldo([]) == 0


# --- R1: saída maior que o saldo é bloqueada ----------------------------------

def test_saida_maior_que_saldo_e_bloqueada():
    # T7: saldo 5, tenta tirar 6
    with pytest.raises(EstoqueInsuficienteError):
        validar_saida(saldo_atual=5, quantidade_saida=6)


def test_saida_igual_ao_saldo_e_permitida():
    # T8: fronteira. Vender tudo que tem é válido; não deve lançar erro.
    validar_saida(saldo_atual=5, quantidade_saida=5)


# --- R2: sinal da quantidade por tipo -----------------------------------------

@pytest.mark.parametrize(
    "tipo, quantidade",
    [
        (T.ENTRADA, -2),   # T9: entrada precisa ser positiva
        (T.ENTRADA, 0),
        (T.VENDA, 3),      # T10: saídas precisam ser negativas
        (T.PRESENTE, 1),
        (T.USO_PROPRIO, 1),
        (T.DEFEITO, 1),
        (T.VENDA, 0),
        (T.AJUSTE, 0),     # T11: ajuste não pode ser zero
    ],
)
def test_sinal_invalido_e_rejeitado(tipo, quantidade):
    with pytest.raises(SinalInvalidoError):
        validar_sinal(tipo, quantidade)


@pytest.mark.parametrize(
    "tipo, quantidade",
    [
        (T.ENTRADA, 3),
        (T.VENDA, -1),
        (T.PRESENTE, -1),
        (T.USO_PROPRIO, -1),
        (T.DEFEITO, -1),
        (T.AJUSTE, -1),    # T12: ajuste aceita os dois sinais
        (T.AJUSTE, 1),
    ],
)
def test_sinal_valido_e_aceito(tipo, quantidade):
    validar_sinal(tipo, quantidade)


# --- R6: alerta em ceil(30% da última entrada) --------------------------------

@pytest.mark.parametrize(
    "ultima_entrada, limite",
    [
        (10, 3),  # 3,0
        (4, 2),   # 1,2 -> 2
        (3, 1),   # 0,9 -> 1
        (2, 1),   # 0,6 -> 1
        (1, 1),   # 0,3 -> 1
    ],
)
def test_limite_alerta(ultima_entrada, limite):
    # T13: tabela aprovada na Fase 1
    assert limite_alerta(ultima_entrada) == limite


@pytest.mark.parametrize(
    "saldo, ultima_entrada, esperado",
    [
        (3, 4, False),   # T14: limite 2, saldo 3 -> ainda não
        (2, 4, True),    #      saldo 2 -> avisa
        (4, 10, False),  # T15: limite 3, saldo 4 -> ainda não
        (3, 10, True),   #      saldo 3 -> avisa
        (0, 4, True),    #      zerado também avisa
    ],
)
def test_precisa_alerta(saldo, ultima_entrada, esperado):
    assert precisa_alerta(saldo, ultima_entrada) is esperado
