"""Conversão de dinheiro entre texto brasileiro (formulário/tela) e Decimal."""

import re
from decimal import ROUND_HALF_UP, Decimal


class ValorInvalidoError(ValueError):
    pass


# Formatos aceitos (sem sinal, então negativo é recusado):
_INTEIRO = re.compile(r"\d+")                         # 15
_DECIMAL = re.compile(r"\d+[.,]\d+")                  # 15,50 ou 15.50
_MILHAR_BR = re.compile(r"\d{1,3}(\.\d{3})+(,\d+)?")  # 1.234,56


def ler_dinheiro(texto: str) -> Decimal:
    s = (texto or "").strip()
    if s.upper().startswith("R$"):
        s = s[2:].strip()

    if _INTEIRO.fullmatch(s):
        normalizado = s
    elif _DECIMAL.fullmatch(s):
        normalizado = s.replace(",", ".")
    elif _MILHAR_BR.fullmatch(s):
        normalizado = s.replace(".", "").replace(",", ".")
    else:
        raise ValorInvalidoError(f"Valor inválido: {texto!r}. Use, por exemplo, 15,50.")

    return Decimal(normalizado)


def brl(valor: Decimal) -> str:
    centavos = Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    americano = f"{centavos:,.2f}"  # 1,234.50
    return "R$ " + americano.replace(",", "_").replace(".", ",").replace("_", ".")
