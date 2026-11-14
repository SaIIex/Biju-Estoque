# =============================================================================
# servicos/relatorio.py: busca as movimentações do mês e chama a regra R7
# =============================================================================
# O ponto mais traiçoeiro deste arquivo é o FUSO HORÁRIO.
# O banco guarda tudo em UTC (3 horas à frente de Brasília). Uma venda feita
# dia 30/11 às 23h30 em Brasília fica gravada como 01/12 02h30 UTC.
# Se filtrássemos "o mês" em UTC, essa venda cairia em DEZEMBRO, e o
# relatório de novembro sairia menor. Toda virada de mês, as vendas das
# últimas 3 horas mudariam de mês sem ninguém perceber.
# Solução: calcular o começo e o fim do mês NO HORÁRIO DE BRASÍLIA e só
# depois converter para UTC para consultar o banco. (Teste R2.)
# =============================================================================

"""Relatório de lucro do mês, com o mês contado no horário de Brasília."""

# defaultdict: dicionário que cria o valor sozinho na primeira vez que você
# acessa uma chave. defaultdict(list) -> chave nova já começa com [].
# Em C#: seria o "if (!dict.ContainsKey(k)) dict[k] = new List<T>();".
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dominio import estoque as dominio
from app.dominio.lucro import Resultado, calcular_resultado
from app.modelos import Movimentacao, Produto

BRASILIA = timezone(timedelta(hours=-3))


@dataclass(frozen=True)
class PecaNoRelatorio:
    produto_id: int
    nome: str
    unidades_vendidas: int
    receita: Decimal
    resultado: Decimal


@dataclass
class RelatorioMes:
    ano: int
    mes: int
    total: Resultado
    # field(default_factory=list): cada relatório ganha a SUA lista vazia.
    # Nunca escreva "por_peca: list = []" num dataclass: a mesma lista seria
    # compartilhada por todos os objetos (o Python inclusive proíbe isso).
    por_peca: list[PecaNoRelatorio] = field(default_factory=list)


def intervalo_utc(ano: int, mes: int) -> tuple[datetime, datetime]:
    """Início e fim (exclusivo) do mês de Brasília, em UTC sem fuso (como o banco guarda)."""
    if not 1 <= mes <= 12:  # comparação encadeada: 1 <= mes E mes <= 12
        raise ValueError(f"Mês inválido: {mes}")
    inicio = datetime(ano, mes, 1, tzinfo=BRASILIA)
    # Dezembro é especial: o mês seguinte é janeiro do ANO SEGUINTE. (Teste R3.)
    fim = datetime(ano + 1, 1, 1, tzinfo=BRASILIA) if mes == 12 else datetime(ano, mes + 1, 1, tzinfo=BRASILIA)

    # Função dentro de função, usada só aqui.
    def utc_sem_fuso(d: datetime) -> datetime:
        # astimezone converte para UTC; replace(tzinfo=None) tira o "carimbo"
        # de fuso, porque a coluna do banco não guarda fuso.
        return d.astimezone(timezone.utc).replace(tzinfo=None)

    # Devolve uma TUPLA (dois valores). Quem chama faz: inicio, fim = intervalo_utc(...)
    # Em C#: return (inicio, fim); com tuple deconstruction.
    return utc_sem_fuso(inicio), utc_sem_fuso(fim)


def _para_dominio(m: Movimentacao) -> dominio.Movimentacao:
    # Converte a linha do banco (classe do SQLAlchemy) para a classe pura do
    # domínio. Assim a regra R7 não sabe que existe banco. É o mapeamento
    # Entity -> objeto de domínio que você faria com AutoMapper ou à mão em C#.
    return dominio.Movimentacao(m.tipo, m.quantidade, m.custo_unitario, m.preco_venda)


def relatorio_do_mes(session: Session, ano: int, mes: int) -> RelatorioMes:
    inicio, fim = intervalo_utc(ano, mes)

    # JOIN com produto para já trazer o nome da peça (uma consulta só, sem N+1).
    # Intervalo "meio aberto": >= início E < fim. O fim é EXCLUSIVO.
    # Com "<=", uma venda feita exatamente à meia-noite do dia 1º contaria nos
    # DOIS meses. Esse bug foi aplicado de propósito e nenhum teste pegou;
    # daí nasceu a proposta do teste R9 (venda à meia-noite).
    linhas = session.execute(
        select(Movimentacao, Produto.nome)
        .join(Produto, Produto.id == Movimentacao.produto_id)
        .where(Movimentacao.criado_em >= inicio, Movimentacao.criado_em < fim)
    ).all()

    # "for m, _ in linhas": cada linha é uma tupla (movimentacao, nome).
    # O "_" é convenção para "valor que não vou usar".
    todas = [_para_dominio(m) for m, _ in linhas]

    # Agrupa por peça. Em C#: linhas.GroupBy(l => l.ProdutoId).
    por_produto: dict[int, list] = defaultdict(list)
    nomes: dict[int, str] = {}
    for m, nome in linhas:
        por_produto[m.produto_id].append(_para_dominio(m))
        nomes[m.produto_id] = nome

    pecas = []
    # .items() percorre pares (chave, valor) do dicionário.
    for produto_id, movs in por_produto.items():
        r = calcular_resultado(movs)   # a MESMA regra do total, aplicada por peça
        if r.unidades_vendidas:        # só entra no ranking quem vendeu (teste R5)
            pecas.append(
                PecaNoRelatorio(produto_id, nomes[produto_id], r.unidades_vendidas, r.receita, r.resultado)
            )
    # Ordena pelo maior lucro primeiro: o "-" inverte a ordem dos números.
    # Empate? Desempata pelo nome. A tupla (a, b) compara a primeiro, depois b.
    # Em C#: .OrderByDescending(p => p.Resultado).ThenBy(p => p.Nome).
    pecas.sort(key=lambda p: (-p.resultado, p.nome))

    return RelatorioMes(ano=ano, mes=mes, total=calcular_resultado(todas), por_peca=pecas)
