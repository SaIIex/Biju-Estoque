# =============================================================================
# dominio/estoque.py: as regras de negócio do estoque, e SÓ elas
# =============================================================================
# Este é o arquivo mais importante do projeto. Repare no que ele NÃO tem:
# nenhum import de FastAPI, nenhum banco, nenhum HTML. São funções puras:
# recebem valores, devolvem valores (ou lançam erro). Mais nada.
#
# Por que separar assim? Pensa numa calculadora. Você testa se 2 + 2 = 4 sem
# precisar ligar a impressora nem a internet. As regras do estoque são a
# calculadora do sistema. Se misturar regra com banco, todo teste de
# "custo médio" vai precisar subir um banco, e aí os testes ficam lentos,
# frágeis e ninguém roda.
#
# Comparação com C#: é a camada Domain de uma Clean Architecture, ou a pasta
# de "Services" que não depende de DbContext.
#
# A spec de cada função está em docs/mapas/modelo-dados.md (regras R1 a R8).
# =============================================================================

# dataclass: gera construtor, __repr__ e __eq__ sozinho. É o "record" do C#.
from dataclasses import dataclass

# Decimal: número decimal EXATO. É o "decimal" do C# (não o double).
# Regra de ouro: dinheiro NUNCA em float. Em Python, 0.1 + 0.2 dá
# 0.30000000000000004. Em Decimal("0.1") + Decimal("0.2") dá Decimal("0.3").
# ROUND_HALF_UP é o arredondamento "de escola": 0,5 sobe.
from decimal import ROUND_HALF_UP, Decimal

from enum import Enum

# Constante (convenção: nome em MAIÚSCULAS; Python não tem "const", é combinado).
# Decimal("0.0001") é o "molde" de 4 casas usado no quantize lá embaixo.
CASAS_CUSTO = Decimal("0.0001")


# Enum que também é str. Por que herdar de str? Porque assim
# TipoMovimentacao.VENDA == "venda" é True. Facilita salvar no banco e
# receber de formulário HTML, onde tudo chega como texto.
# Em C#: um enum, mas que serializa como string em vez de número.
class TipoMovimentacao(str, Enum):
    ENTRADA = "entrada"
    VENDA = "venda"
    PRESENTE = "presente"
    USO_PROPRIO = "uso_proprio"
    DEFEITO = "defeito"
    AJUSTE = "ajuste"


# frozenset: um conjunto IMUTÁVEL. Ninguém consegue adicionar um tipo aqui
# por acidente em tempo de execução. Em C#: IReadOnlySet<T> / ImmutableHashSet.
# Usamos conjunto porque a pergunta é "esse tipo É uma saída?" (operador in),
# e conjunto responde isso em tempo constante.
TIPOS_SAIDA = frozenset(
    {
        TipoMovimentacao.VENDA,
        TipoMovimentacao.PRESENTE,
        TipoMovimentacao.USO_PROPRIO,
        TipoMovimentacao.DEFEITO,
    }
)


# Exceções PRÓPRIAS do domínio. Em vez de um genérico "Exception", cada erro
# de negócio tem nome. Vantagem: quem chama pode tratar cada caso de um jeito
# (ex.: a tela mostra "Estoque insuficiente" em vermelho), e o teste pode
# exigir exatamente ESSE erro com pytest.raises(EstoqueInsuficienteError).
# Em C#: public class EstoqueInsuficienteException : Exception { }
class EstoqueInsuficienteError(Exception):
    """Saída maior que o saldo disponível (R1)."""


# Herda de ValueError (o ArgumentException do Python): é um valor inválido.
class SinalInvalidoError(ValueError):
    """Quantidade com sinal incompatível com o tipo da movimentação (R2)."""


# frozen=True: depois de criado, não muda. Uma movimentação é um FATO que
# aconteceu; fato não se edita. Se errou, lança um ajuste. É o mesmo
# raciocínio de um extrato bancário.
@dataclass(frozen=True)
class Movimentacao:
    tipo: TipoMovimentacao
    quantidade: int  # com sinal: + entra, - sai
    custo_unitario: Decimal
    # "Decimal | None = None": pode ser Decimal ou nada, e por padrão é nada.
    # Em C#: decimal? PrecoVenda = null;
    preco_venda: Decimal | None = None


def novo_custo_medio(
    saldo_atual: int,
    custo_medio_atual: Decimal,
    qtd_entrada: int,
    custo_entrada: Decimal,
) -> Decimal:  # "-> Decimal" = tipo de retorno. Só dica, como as outras.
    """R3: custo médio ponderado após uma entrada.

    A conta é feita inteira em Decimal; só o resultado é arredondado para 4 casas.
    """
    # Guard clauses: validar a entrada logo no começo e sair com erro.
    # Evita aninhar if dentro de if. Mesma prática que você usaria em C#.
    if qtd_entrada <= 0:
        raise SinalInvalidoError("A quantidade da entrada precisa ser positiva.")
    if saldo_atual < 0:
        raise ValueError("Saldo atual não pode ser negativo.")

    # Pensa num saco de colares: o custo médio é o total pago por TUDO que
    # está no saco dividido pela quantidade de colares no saco.
    # int * Decimal = Decimal. Python converte o int sem perder precisão.
    total_atual = saldo_atual * custo_medio_atual   # o que já estava no saco
    total_entrada = qtd_entrada * custo_entrada     # o que acabou de chegar
    quantidade_final = saldo_atual + qtd_entrada

    # A divisão é feita com precisão total. Nada de arredondar aqui no meio.
    custo = (total_atual + total_entrada) / quantidade_final

    # quantize = "encaixe no molde de 4 casas". Só o RESULTADO é arredondado.
    # Ex.: 47 / 3 = 15,666666... -> 15,6667
    return custo.quantize(CASAS_CUSTO, rounding=ROUND_HALF_UP)


def calcular_saldo(movimentacoes: list[Movimentacao]) -> int:
    """R1: saldo é a soma das quantidades (com sinal)."""
    # Isto é uma generator expression: "para cada m da lista, pegue
    # m.quantidade", e o sum() soma tudo. Em C# com LINQ seria:
    #   movimentacoes.Sum(m => m.Quantidade);
    # Como saídas já são negativas, somar tudo dá o saldo direto.
    # Lista vazia: sum([]) = 0. O caso T6 sai de graça.
    return sum(m.quantidade for m in movimentacoes)


def validar_saida(saldo_atual: int, quantidade_saida: int) -> None:
    """R1: bloqueia saída maior que o saldo. quantidade_saida é positiva (nº de peças)."""
    # "-> None" = não retorna nada (o void do C#). A função só "reclama"
    # (lança erro) se algo estiver errado. Se passar, segue o jogo.
    #
    # Atenção ao ">" e não ">=": vender TODAS as 5 peças com saldo 5 é válido.
    # O teste T8 existe justamente para pegar quem trocar por ">=".
    if quantidade_saida > saldo_atual:
        # f-string: texto com variáveis dentro de {}. É a interpolação
        # $"..." do C#.
        raise EstoqueInsuficienteError(
            f"Estoque insuficiente: saldo {saldo_atual}, saída de {quantidade_saida}."
        )


def validar_sinal(tipo: TipoMovimentacao, quantidade: int) -> None:
    """R2: entrada > 0; saídas < 0; ajuste != 0."""
    # if / elif / else: o elif é o "else if" do C#.
    if tipo == TipoMovimentacao.ENTRADA:
        valido = quantidade > 0
    elif tipo in TIPOS_SAIDA:
        valido = quantidade < 0
    elif tipo == TipoMovimentacao.AJUSTE:
        valido = quantidade != 0
    else:
        # Programação defensiva: se alguém criar um tipo novo no Enum e
        # esquecer de colocar a regra aqui, o sistema RECLAMA em vez de
        # aceitar qualquer coisa calado. "Falhe alto" é melhor que bug silencioso.
        raise SinalInvalidoError(f"Tipo desconhecido: {tipo}")

    if not valido:  # "not" = o "!" do C#
        raise SinalInvalidoError(f"Quantidade {quantidade} inválida para {tipo.value}.")


def limite_alerta(qtd_ultima_entrada: int) -> int:
    """R6: teto de 30% da última entrada, em aritmética inteira (sem float)."""
    if qtd_ultima_entrada <= 0:
        return 0
    # Truque clássico: teto de (a / b) com inteiros = (a + b - 1) // b.
    # Aqui: teto(3n / 10) = (3n + 9) // 10.
    # "//" é divisão INTEIRA (descarta a parte decimal). Em C#, int / int já
    # faz isso; em Python, "/" sempre devolve float, por isso existe o "//".
    # Exemplos: n=4 -> (12+9)//10 = 2 ; n=3 -> (9+9)//10 = 1 ; n=10 -> 39//10 = 3
    # Por que não math.ceil(0.3 * n)? Funcionaria nesses números, mas
    # inteiros não têm surpresa de arredondamento nenhuma. Regra de negócio
    # crítica, sem float.
    return (3 * qtd_ultima_entrada + 9) // 10


def precisa_alerta(saldo: int, qtd_ultima_entrada: int) -> bool:
    """R6: avisa quando o saldo chega ao limite ou abaixo dele."""
    # "<=" e não "<": com base 4 o limite é 2, e saldo 2 JÁ deve avisar.
    # A função reaproveita limite_alerta em vez de repetir a conta
    # (uma regra, um lugar só).
    return saldo <= limite_alerta(qtd_ultima_entrada)
