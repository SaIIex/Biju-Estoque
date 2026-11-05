# =============================================================================
# test_dominio_estoque.py: testes das regras de estoque
# =============================================================================
# Leia junto com estudos/app/dominio/estoque.py.
#
# Três ideias deste arquivo:
# 1. Valores esperados calculados À MÃO a partir da spec (docs/mapas/
#    modelo-dados.md). Nunca rodando o código para "descobrir" o resultado.
#    Se o teste copiar a resposta do código, ele só confirma o bug.
# 2. parametrize: um teste, várias linhas de dados. É o [Theory] +
#    [InlineData] do xUnit.
# 3. Casos de FRONTEIRA: o valor exatamente no limite (saldo 5, venda 5).
#    É ali que mora o bug de ">" vs ">=".
#
# Como provamos que estes testes valem algo: depois que passaram, aplicamos
# 9 bugs de propósito no código (trocar > por >=, média simples no lugar da
# ponderada, arredondar para baixo...). Cada bug fez pelo menos um teste
# falhar. Isso se chama TESTE DE MUTAÇÃO, feito à mão.
# =============================================================================

"""Testes das regras de estoque (R1, R2, R3, R6 de docs/mapas/modelo-dados.md).

Todos os valores esperados foram calculados à mão a partir da spec.
"""

from decimal import Decimal

import pytest

# Import em várias linhas com parênteses. "TipoMovimentacao as T" cria um
# apelido curto, só para os testes ficarem legíveis (T.VENDA em vez de
# TipoMovimentacao.VENDA). Em C#: using T = App.Dominio.TipoMovimentacao;
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

# @pytest.mark.parametrize("nomes, dos, parametros", [linhas]):
# o pytest roda a função uma vez para CADA tupla da lista, preenchendo os
# parâmetros pelo nome. 4 tuplas = 4 testes no relatório.
# ids=[...] dá um nome legível a cada caso, que aparece se falhar.
@pytest.mark.parametrize(
    "saldo, custo_medio, qtd_entrada, custo_entrada, esperado",
    [
        # T1: (2x15 + 2x18) / 4 = 66 / 4
        # Decimal("15") com ASPAS: criar Decimal a partir de texto é exato.
        # Decimal(0.1) sem aspas herdaria o erro do float. Sempre use string.
        (2, Decimal("15"), 2, Decimal("18"), Decimal("16.5000")),
        # T2: (1x15 + 3x18) / 4 = 69 / 4. Aqui média simples daria 16,50:
        # este caso existe para PEGAR quem fizer média simples.
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
    # Lista literal com [ ]: o List<T> do C#, sem precisar declarar o tipo.
    movs = [
        Movimentacao(T.ENTRADA, 10, Decimal("8")),
        # preco_venda=... é argumento NOMEADO, como em C# (PrecoVenda: 25m).
        Movimentacao(T.VENDA, -4, Decimal("8"), preco_venda=Decimal("25")),
        Movimentacao(T.PRESENTE, -1, Decimal("8")),
        Movimentacao(T.AJUSTE, -1, Decimal("8")),
    ]
    assert calcular_saldo(movs) == 4


def test_saldo_sem_movimentacoes_e_zero():
    # T6: caso vazio. Sempre teste a lista vazia; é onde muito código quebra.
    assert calcular_saldo([]) == 0


# --- R1: saída maior que o saldo é bloqueada ----------------------------------

def test_saida_maior_que_saldo_e_bloqueada():
    # T7: saldo 5, tenta tirar 6.
    # pytest.raises = Assert.Throws<EstoqueInsuficienteException>(() => ...)
    with pytest.raises(EstoqueInsuficienteError):
        validar_saida(saldo_atual=5, quantidade_saida=6)


def test_saida_igual_ao_saldo_e_permitida():
    # T8: FRONTEIRA. Vender tudo que tem é válido; não deve lançar erro.
    # Repare: não há assert. Se a função lançar exceção, o teste falha
    # sozinho. "Não explodiu" já é o resultado esperado.
    validar_saida(saldo_atual=5, quantidade_saida=5)


# --- R2: sinal da quantidade por tipo -----------------------------------------

# Uma tabela de casos inválidos: cada linha precisa lançar SinalInvalidoError.
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


# E a tabela espelho: casos válidos não podem lançar nada.
# Testar só o lado "errado" não basta: um código que rejeita TUDO passaria
# na tabela de cima. Esta aqui pega esse bug.
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
    # T13: tabela aprovada na Fase 1. O teste É a tabela da spec.
    assert limite_alerta(ultima_entrada) == limite


@pytest.mark.parametrize(
    "saldo, ultima_entrada, esperado",
    [
        (3, 4, False),   # T14: limite 2, saldo 3 -> ainda não
        (2, 4, True),    #      saldo 2 -> avisa (fronteira!)
        (4, 10, False),  # T15: limite 3, saldo 4 -> ainda não
        (3, 10, True),   #      saldo 3 -> avisa (fronteira!)
        (0, 4, True),    #      zerado também avisa
    ],
)
def test_precisa_alerta(saldo, ultima_entrada, esperado):
    # "is" compara IDENTIDADE, não só igualdade. Com True/False usamos "is"
    # para exigir um bool de verdade. Se a função devolvesse 1 em vez de True,
    # "== True" passaria e "is True" falha. Teste mais rigoroso.
    assert precisa_alerta(saldo, ultima_entrada) is esperado
