# =============================================================================
# test_servico_estoque.py: testes do serviço, agora COM banco
# =============================================================================
# Diferença para test_dominio_estoque.py: lá testávamos contas puras. Aqui
# testamos o fluxo completo: cadastrar, dar entrada, vender, e conferir o
# que ficou GRAVADO. Cada teste recebe a fixture "session" (veja conftest.py),
# um banco em memória novinho.
#
# Em C#: seriam testes de integração com um banco InMemory/SQLite no xUnit.
#
# Lição deste arquivo: depois de tudo passando, aplicamos 10 bugs de propósito.
# 2 passaram despercebidos (alerta usando a PRIMEIRA entrada; saldo somando
# TODAS as peças). Os testes S11b e S15 nasceram desses buracos.
# Moral: "todos os testes passando" não prova que os testes são bons. Quebrar
# o código de propósito prova.
# =============================================================================

"""Testes do serviço de estoque: regras do domínio aplicadas com o banco.

Valores esperados calculados à mão a partir de docs/mapas/modelo-dados.md.
"""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.dominio.estoque import EstoqueInsuficienteError, TipoMovimentacao as T
from app.modelos import Movimentacao
from app.servicos.estoque import (
    CodigoDuplicadoError,
    PrecoVendaInvalidoError,
    ProdutoNaoEncontradoError,
    cadastrar_produto,
    precisa_alerta,
    registrar_ajuste,
    registrar_entrada,
    registrar_saida,
    saldo,
)


# Funções auxiliares com "_" na frente: não começam com test_, então o pytest
# não as roda como teste. São só atalhos para não repetir código (DRY).
# Em xUnit seriam métodos privados da classe de teste.
def _colar(session, codigo="01521"):
    return cadastrar_produto(
        session, codigo=codigo, nome="Colar Cravejado", preco_venda=Decimal("50")
    )


def _total_movimentacoes(session) -> int:
    # SELECT COUNT(*) FROM movimentacao. Usado para provar que NADA foi
    # gravado depois de um erro.
    return session.scalar(select(func.count()).select_from(Movimentacao))


# --- cadastro -------------------------------------------------------------------

# Repare: o parâmetro "session" não é passado por ninguém. O pytest vê o nome,
# acha a fixture no conftest.py e injeta. Mágica? Não: convenção por nome.
def test_s1_produto_novo_comeca_zerado(session):
    produto = _colar(session)
    assert produto.id is not None          # o flush gerou o id
    assert produto.custo_medio == Decimal("0")
    assert produto.ativo is True
    assert saldo(session, produto.id) == 0


def test_s2_codigo_duplicado_e_rejeitado(session):
    _colar(session, codigo="01521")
    with pytest.raises(CodigoDuplicadoError):
        _colar(session, codigo="01521")


def test_s12_produto_inexistente(session):
    with pytest.raises(ProdutoNaoEncontradoError):
        registrar_entrada(session, produto_id=999, quantidade=1, custo_unitario=Decimal("10"))


# --- entradas e custo médio (R3) ------------------------------------------------

def test_s3_duas_entradas_atualizam_custo_medio(session):
    produto = _colar(session)
    e1 = registrar_entrada(session, produto.id, quantidade=2, custo_unitario=Decimal("15"))
    e2 = registrar_entrada(session, produto.id, quantidade=2, custo_unitario=Decimal("18"))

    assert produto.custo_medio == Decimal("16.5000")       # (2x15 + 2x18) / 4
    assert saldo(session, produto.id) == 4
    # Comparar TUPLAS: (a, b) == (c, d) compara item a item. Atalho para dois
    # asserts numa linha só.
    assert (e1.quantidade, e1.custo_unitario) == (2, Decimal("15"))
    assert (e2.quantidade, e2.custo_unitario) == (2, Decimal("18"))
    assert e1.tipo == T.ENTRADA


def test_s13_entrada_com_estoque_zerado_usa_so_o_novo_custo(session):
    # Caso de borda: o estoque zerou. O custo antigo (15) não pode "contaminar"
    # a média, porque não há mais nenhuma peça daquele preço na gaveta.
    produto = _colar(session)
    registrar_entrada(session, produto.id, quantidade=2, custo_unitario=Decimal("15"))
    registrar_saida(session, produto.id, T.VENDA, quantidade=2, preco_venda=Decimal("50"))
    registrar_entrada(session, produto.id, quantidade=1, custo_unitario=Decimal("20"))

    assert saldo(session, produto.id) == 1
    assert produto.custo_medio == Decimal("20.0000")       # (0x15 + 1x20) / 1


# --- saídas (R1, R4, R5) --------------------------------------------------------

def test_s4_venda_grava_custo_do_momento_e_preco_real(session):
    produto = _colar(session)
    registrar_entrada(session, produto.id, quantidade=2, custo_unitario=Decimal("15"))
    registrar_entrada(session, produto.id, quantidade=2, custo_unitario=Decimal("18"))

    # Vendeu por 45 com desconto, mesmo o cadastro dizendo 50.
    venda = registrar_saida(session, produto.id, T.VENDA, quantidade=1, preco_venda=Decimal("45"))

    assert venda.quantidade == -1                          # informou 1, gravou -1
    assert venda.custo_unitario == Decimal("16.5000")
    assert venda.preco_venda == Decimal("45")              # preço real, não o do cadastro (50)
    assert saldo(session, produto.id) == 3
    assert produto.custo_medio == Decimal("16.5000")       # saída não muda custo médio


def test_s5_venda_acima_do_saldo_nao_grava_nada(session):
    # A "segunda metade" do T7 do domínio. Lá só dava para testar o erro.
    # Aqui, com banco, testamos o EFEITO: depois do erro, nada mudou.
    produto = _colar(session)
    registrar_entrada(session, produto.id, quantidade=5, custo_unitario=Decimal("10"))
    antes = _total_movimentacoes(session)

    with pytest.raises(EstoqueInsuficienteError):
        registrar_saida(session, produto.id, T.VENDA, quantidade=6, preco_venda=Decimal("50"))

    # Estes asserts ficam FORA do with (lembra da verificação da Fase 1?).
    assert saldo(session, produto.id) == 5
    assert _total_movimentacoes(session) == antes


@pytest.mark.parametrize(
    "tipo, preco",
    [
        (T.VENDA, None),              # venda sem preço
        (T.PRESENTE, Decimal("50")),  # não-venda com preço
        (T.DEFEITO, Decimal("50")),
    ],
)
def test_s6_preco_venda_so_e_so_em_venda(session, tipo, preco):
    # parametrize + fixture juntos: o pytest injeta "session" E os parâmetros.
    produto = _colar(session)
    registrar_entrada(session, produto.id, quantidade=3, custo_unitario=Decimal("10"))
    with pytest.raises(PrecoVendaInvalidoError):
        registrar_saida(session, produto.id, tipo, quantidade=1, preco_venda=preco)


@pytest.mark.parametrize("tipo", [T.PRESENTE, T.USO_PROPRIO, T.DEFEITO])
def test_s7_perdas_gravam_custo_medio_e_sem_preco(session, tipo):
    produto = _colar(session)
    registrar_entrada(session, produto.id, quantidade=3, custo_unitario=Decimal("12"))

    mov = registrar_saida(session, produto.id, tipo, quantidade=1)

    assert mov.quantidade == -1
    assert mov.custo_unitario == Decimal("12.0000")  # a perda vale o CUSTO (Fase 1)
    assert mov.preco_venda is None
    assert saldo(session, produto.id) == 2


# --- ajustes --------------------------------------------------------------------

def test_s8_ajuste_negativo_alem_do_saldo_e_bloqueado(session):
    produto = _colar(session)
    registrar_entrada(session, produto.id, quantidade=2, custo_unitario=Decimal("10"))

    ajuste = registrar_ajuste(session, produto.id, quantidade=-1, observacao="conferência")
    assert ajuste.custo_unitario == Decimal("10.0000")
    assert saldo(session, produto.id) == 1

    with pytest.raises(EstoqueInsuficienteError):
        registrar_ajuste(session, produto.id, quantidade=-2)
    assert saldo(session, produto.id) == 1


def test_s9_ajuste_positivo_nao_muda_custo_medio(session):
    produto = _colar(session)
    registrar_entrada(session, produto.id, quantidade=2, custo_unitario=Decimal("15"))
    registrar_entrada(session, produto.id, quantidade=2, custo_unitario=Decimal("18"))

    registrar_ajuste(session, produto.id, quantidade=1, observacao="achou na gaveta")

    assert saldo(session, produto.id) == 5
    assert produto.custo_medio == Decimal("16.5000")


# --- alerta (R6) com o banco ----------------------------------------------------

def test_s10_alerta_com_base_na_entrada(session):
    produto = _colar(session)
    registrar_entrada(session, produto.id, quantidade=4, custo_unitario=Decimal("10"))
    registrar_saida(session, produto.id, T.VENDA, quantidade=1, preco_venda=Decimal("50"))
    assert precisa_alerta(session, produto.id) is False    # saldo 3, limite 2

    registrar_saida(session, produto.id, T.VENDA, quantidade=1, preco_venda=Decimal("50"))
    assert precisa_alerta(session, produto.id) is True     # saldo 2, limite 2


def test_s11_alerta_usa_a_ultima_entrada(session):
    produto = _colar(session)
    registrar_entrada(session, produto.id, quantidade=10, custo_unitario=Decimal("10"))
    registrar_saida(session, produto.id, T.VENDA, quantidade=7, preco_venda=Decimal("50"))
    assert precisa_alerta(session, produto.id) is True     # saldo 3, limite 3 (base 10)

    registrar_entrada(session, produto.id, quantidade=4, custo_unitario=Decimal("10"))
    assert precisa_alerta(session, produto.id) is False    # saldo 7, limite 2 (base 4)
    # ATENÇÃO: este teste parecia testar "a última entrada", mas com a base
    # errada (10, limite 3) o saldo 7 também daria False. Ele não distinguia
    # os dois casos. Só descobrimos isso quebrando o código. Daí o S11b.


def test_s14_produto_sem_entrada_nao_alerta(session):
    produto = _colar(session)
    assert precisa_alerta(session, produto.id) is False


def test_s11b_base_e_a_ultima_entrada_nao_a_primeira(session):
    # Pega o bug M4: usar a primeira entrada como base do alerta.
    # Truque para escrever um teste que DISTINGUE dois comportamentos:
    # escolha um saldo que fica ENTRE os dois limites possíveis.
    #   base certa  = 1  -> limite 1
    #   base errada = 10 -> limite 3
    #   saldo 3: maior que 1 (não avisa) e igual a 3 (avisaria). Distinguiu.
    produto = _colar(session)
    registrar_entrada(session, produto.id, quantidade=10, custo_unitario=Decimal("10"))
    registrar_saida(session, produto.id, T.VENDA, quantidade=8, preco_venda=Decimal("50"))
    registrar_entrada(session, produto.id, quantidade=1, custo_unitario=Decimal("10"))
    assert precisa_alerta(session, produto.id) is False


# --- isolamento entre peças -----------------------------------------------------

def test_s15_saldo_e_isolado_por_peca(session):
    # Pega o bug M10: saldo somando o estoque de todas as peças.
    # Lição: se TODO teste usa um item só, bugs de "misturar itens" são
    # invisíveis. Sempre tenha pelo menos um teste com dois.
    colar = _colar(session, codigo="C1")
    brinco = cadastrar_produto(session, codigo="B1", nome="Brinco", preco_venda=Decimal("20"))
    registrar_entrada(session, colar.id, quantidade=4, custo_unitario=Decimal("15"))
    registrar_entrada(session, brinco.id, quantidade=2, custo_unitario=Decimal("8"))

    assert saldo(session, colar.id) == 4
    assert saldo(session, brinco.id) == 2
