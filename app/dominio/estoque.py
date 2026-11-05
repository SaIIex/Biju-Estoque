"""Regras de estoque puras: sem banco, sem HTTP.

Spec: regras R1, R2, R3 e R6 em docs/mapas/modelo-dados.md.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

# Custo médio é guardado com 4 casas (decisão de 04/11). Exibição usa 2.
CASAS_CUSTO = Decimal("0.0001")


class TipoMovimentacao(str, Enum):
    ENTRADA = "entrada"
    VENDA = "venda"
    PRESENTE = "presente"
    USO_PROPRIO = "uso_proprio"
    DEFEITO = "defeito"
    AJUSTE = "ajuste"


TIPOS_SAIDA = frozenset(
    {
        TipoMovimentacao.VENDA,
        TipoMovimentacao.PRESENTE,
        TipoMovimentacao.USO_PROPRIO,
        TipoMovimentacao.DEFEITO,
    }
)


class EstoqueInsuficienteError(Exception):
    """Saída maior que o saldo disponível (R1)."""


class SinalInvalidoError(ValueError):
    """Quantidade com sinal incompatível com o tipo da movimentação (R2)."""


@dataclass(frozen=True)
class Movimentacao:
    tipo: TipoMovimentacao
    quantidade: int  # com sinal: + entra, - sai
    custo_unitario: Decimal
    preco_venda: Decimal | None = None


def novo_custo_medio(
    saldo_atual: int,
    custo_medio_atual: Decimal,
    qtd_entrada: int,
    custo_entrada: Decimal,
) -> Decimal:
    """R3: custo médio ponderado após uma entrada.

    A conta é feita inteira em Decimal; só o resultado é arredondado para 4 casas.
    """
    if qtd_entrada <= 0:
        raise SinalInvalidoError("A quantidade da entrada precisa ser positiva.")
    if saldo_atual < 0:
        raise ValueError("Saldo atual não pode ser negativo.")

    total_atual = saldo_atual * custo_medio_atual
    total_entrada = qtd_entrada * custo_entrada
    quantidade_final = saldo_atual + qtd_entrada

    custo = (total_atual + total_entrada) / quantidade_final
    return custo.quantize(CASAS_CUSTO, rounding=ROUND_HALF_UP)


def calcular_saldo(movimentacoes: list[Movimentacao]) -> int:
    """R1: saldo é a soma das quantidades (com sinal)."""
    return sum(m.quantidade for m in movimentacoes)


def validar_saida(saldo_atual: int, quantidade_saida: int) -> None:
    """R1: bloqueia saída maior que o saldo. quantidade_saida é positiva (nº de peças)."""
    if quantidade_saida > saldo_atual:
        raise EstoqueInsuficienteError(
            f"Estoque insuficiente: saldo {saldo_atual}, saída de {quantidade_saida}."
        )


def validar_sinal(tipo: TipoMovimentacao, quantidade: int) -> None:
    """R2: entrada > 0; saídas < 0; ajuste != 0."""
    if tipo == TipoMovimentacao.ENTRADA:
        valido = quantidade > 0
    elif tipo in TIPOS_SAIDA:
        valido = quantidade < 0
    elif tipo == TipoMovimentacao.AJUSTE:
        valido = quantidade != 0
    else:  # tipo novo esquecido aqui: falha alto em vez de aceitar em silêncio
        raise SinalInvalidoError(f"Tipo desconhecido: {tipo}")

    if not valido:
        raise SinalInvalidoError(f"Quantidade {quantidade} inválida para {tipo.value}.")


def limite_alerta(qtd_ultima_entrada: int) -> int:
    """R6: teto de 30% da última entrada, em aritmética inteira (sem float)."""
    if qtd_ultima_entrada <= 0:
        return 0
    return (3 * qtd_ultima_entrada + 9) // 10


def precisa_alerta(saldo: int, qtd_ultima_entrada: int) -> bool:
    """R6: avisa quando o saldo chega ao limite ou abaixo dele."""
    return saldo <= limite_alerta(qtd_ultima_entrada)
