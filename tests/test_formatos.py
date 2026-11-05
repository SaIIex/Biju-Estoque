"""Conversão de dinheiro entre o formulário (texto brasileiro) e Decimal."""

from decimal import Decimal

import pytest

from app.formatos import ValorInvalidoError, brl, ler_dinheiro


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("15", Decimal("15")),          # F1: inteiro
        ("15,50", Decimal("15.50")),    # F2: vírgula, como a dona digita
        ("15.50", Decimal("15.50")),    # F3: ponto, teclado numérico do celular
        (" 15,5 ", Decimal("15.5")),    # F4: espaços em volta
        ("1.234,56", Decimal("1234.56")),  # F5: milhar com ponto e centavos com vírgula
        ("R$ 50", Decimal("50")),       # F6: com símbolo
    ],
)
def test_ler_dinheiro_aceita_formatos_brasileiros(texto, esperado):
    assert ler_dinheiro(texto) == esperado


@pytest.mark.parametrize("texto", ["", "abc", "-5", "1,2,3", "NaN", "Infinity"])
def test_ler_dinheiro_rejeita_lixo_e_negativo(texto):
    # F7: vazio, texto, negativo, ambíguo e valores especiais do Decimal
    with pytest.raises(ValorInvalidoError):
        ler_dinheiro(texto)


@pytest.mark.parametrize(
    "valor, esperado",
    [
        (Decimal("16.5"), "R$ 16,50"),        # F8
        (Decimal("15.6667"), "R$ 15,67"),     # F9: custo médio de 4 casas exibido com 2
        (Decimal("1234.5"), "R$ 1.234,50"),   # F10: separador de milhar
        (Decimal("0"), "R$ 0,00"),
    ],
)
def test_brl_formata_em_reais(valor, esperado):
    assert brl(valor) == esperado
