# =============================================================================
# servicos/estoque.py: onde regra de negócio encontra o banco
# =============================================================================
# Lembra das camadas?
#   rota (HTTP)  ->  SERVIÇO (este arquivo)  ->  domínio (regras puras)
#                                            ->  banco (SQLAlchemy)
#
# O domínio sabe CALCULAR (custo médio, saldo, alerta), mas não sabe de onde
# vêm os números. O serviço busca os números no banco, pede ao domínio para
# validar/calcular, e prepara a gravação.
#
# Em C#: é a classe EstoqueService que recebe o DbContext por injeção.
#
# Decisão importante: o serviço NÃO faz commit. Ele faz flush (manda o SQL
# para o banco dentro da transação, sem confirmar). Quem confirma é a rota,
# no fim da requisição. Se algo falhar no meio, nada fica gravado pela metade.
# É o padrão Unit of Work, o mesmo do SaveChanges() no fim do request no EF.
# =============================================================================

"""Serviço de estoque: aplica as regras do domínio sobre o banco.

Não faz commit: quem chama (a rota) decide quando salvar. Assim, uma operação
que falha no meio não deixa nada gravado pela metade.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

# "import ... as dominio": importa o MÓDULO inteiro com um apelido.
# Motivo: este arquivo também tem uma função chamada precisa_alerta. Usando
# dominio.precisa_alerta(...) fica claro qual é qual, sem conflito de nomes.
from app.dominio import estoque as dominio
from app.dominio.estoque import TIPOS_SAIDA, SinalInvalidoError, TipoMovimentacao
from app.modelos import Movimentacao, Produto


class ProdutoNaoEncontradoError(Exception):
    pass


class CodigoDuplicadoError(Exception):
    pass


class PrecoVendaInvalidoError(ValueError):
    """R5: preço de venda é obrigatório em venda e proibido nos demais tipos."""


def _buscar_produto(session: Session, produto_id: int) -> Produto:
    # session.get(Classe, id) = busca pela chave primária. EF: context.Produtos.Find(id).
    produto = session.get(Produto, produto_id)
    # Em Python, compare com None usando "is", não "==". None é único.
    if produto is None:
        raise ProdutoNaoEncontradoError(f"Produto {produto_id} não encontrado.")
    return produto


def cadastrar_produto(
    session: Session,
    codigo: str,
    nome: str,
    preco_venda: Decimal,
    # Parâmetros com valor padrão = opcionais. C#: string? tamanho = null
    tamanho: str | None = None,
    descricao: str | None = None,
    foto_url: str | None = None,
) -> Produto:
    # select(Produto.id).where(...) monta um SELECT. É o LINQ do SQLAlchemy:
    #   context.Produtos.Where(p => p.Codigo == codigo).Select(p => p.Id)
    # session.scalar(...) executa e devolve UM valor (ou None se não achar).
    #
    # Por que checar antes em vez de deixar o banco recusar (unique)?
    # O banco recusaria, mas com um erro genérico (IntegrityError) e deixaria
    # a sessão num estado que precisa de rollback. Checando antes, damos um
    # erro com nome e mensagem clara para a dona. O unique no banco continua
    # lá como rede de segurança.
    if session.scalar(select(Produto.id).where(Produto.codigo == codigo)) is not None:
        raise CodigoDuplicadoError(f"Já existe uma peça com o código {codigo}.")

    # Cria o objeto com argumentos nomeados. EF: new Produto { Codigo = codigo, ... }
    produto = Produto(
        codigo=codigo,
        nome=nome,
        preco_venda=preco_venda,
        tamanho=tamanho,
        descricao=descricao,
        foto_url=foto_url,
        custo_medio=Decimal("0"),
        ativo=True,
    )
    session.add(produto)  # EF: context.Produtos.Add(produto)
    # flush envia o INSERT agora (sem commit). Precisamos disso para o banco
    # gerar o id, que quem chamou provavelmente vai usar em seguida.
    session.flush()
    return produto


def saldo(session: Session, produto_id: int) -> int:
    """R1: soma das quantidades das movimentações da peça."""
    # SELECT COALESCE(SUM(quantidade), 0) FROM movimentacao WHERE produto_id = ?
    # COALESCE: SUM de nenhuma linha dá NULL; coalesce troca NULL por 0.
    # Em C#: context.Movimentacoes.Where(m => m.ProdutoId == id).Sum(m => (int?)m.Quantidade) ?? 0
    #
    # O WHERE por produto_id é crucial: sem ele, o saldo de UMA peça seria a
    # soma do estoque da loja inteira. Quando aplicamos esse bug de propósito,
    # NENHUM teste falhou: todos usavam uma peça só. Foi assim que descobrimos
    # que faltava um teste com duas peças (S15).
    total = session.scalar(
        select(func.coalesce(func.sum(Movimentacao.quantidade), 0)).where(
            Movimentacao.produto_id == produto_id
        )
    )
    return int(total)


def registrar_entrada(
    session: Session, produto_id: int, quantidade: int, custo_unitario: Decimal
) -> Movimentacao:
    """Compra de peças: atualiza o custo médio (R3) e grava a entrada."""
    produto = _buscar_produto(session, produto_id)
    dominio.validar_sinal(TipoMovimentacao.ENTRADA, quantidade)

    # A ORDEM importa: calculamos o novo custo médio com o saldo de ANTES
    # da entrada ser gravada. Se gravássemos primeiro, o saldo já incluiria
    # as peças novas e a conta sairia errada.
    produto.custo_medio = dominio.novo_custo_medio(
        saldo(session, produto_id), produto.custo_medio, quantidade, custo_unitario
    )
    # Alterar produto.custo_medio basta: a sessão "rastreia" o objeto e gera
    # o UPDATE sozinha no flush. Igual ao change tracking do EF.
    mov = Movimentacao(
        produto_id=produto_id,
        tipo=TipoMovimentacao.ENTRADA,
        quantidade=quantidade,
        custo_unitario=custo_unitario,
    )
    session.add(mov)
    session.flush()
    return mov


def registrar_saida(
    session: Session,
    produto_id: int,
    tipo: TipoMovimentacao,
    quantidade: int,
    preco_venda: Decimal | None = None,
) -> Movimentacao:
    """Venda, presente, uso próprio ou defeito. `quantidade` é o nº de peças (positivo)."""
    produto = _buscar_produto(session, produto_id)

    # Decisão de interface: quem chama informa "vendi 2" (positivo), que é como
    # a dona pensa. O sinal negativo é detalhe interno, aplicado aqui embaixo.
    if tipo not in TIPOS_SAIDA:
        raise ValueError(f"{tipo.value} não é uma saída.")
    if quantidade <= 0:
        raise SinalInvalidoError("Informe quantas peças saíram (número positivo).")

    # R5: venda EXIGE preço; os outros tipos NÃO podem ter preço.
    if tipo == TipoMovimentacao.VENDA:
        if preco_venda is None or preco_venda < 0:
            raise PrecoVendaInvalidoError("Venda precisa do preço real cobrado.")
    elif preco_venda is not None:
        raise PrecoVendaInvalidoError(f"{tipo.value} não tem preço de venda.")

    # R1: valida ANTES de criar qualquer objeto. Se der erro aqui, nada foi
    # adicionado à sessão, então nada pode ser gravado por engano.
    dominio.validar_saida(saldo(session, produto_id), quantidade)

    mov = Movimentacao(
        produto_id=produto_id,
        tipo=tipo,
        quantidade=-quantidade,               # saída grava negativo
        custo_unitario=produto.custo_medio,   # R4: "congela" o custo do momento
        preco_venda=preco_venda,
    )
    # Por que congelar o custo? Se amanhã ela comprar mais caro, o custo médio
    # muda, mas o lucro da venda de HOJE tem que continuar o mesmo. É como a
    # nota fiscal: o preço que estava valendo no dia fica registrado nela.
    session.add(mov)
    session.flush()
    return mov


def registrar_ajuste(
    session: Session, produto_id: int, quantidade: int, observacao: str | None = None
) -> Movimentacao:
    """Correção da conferência. `quantidade` com sinal; não muda o custo médio."""
    produto = _buscar_produto(session, produto_id)
    dominio.validar_sinal(TipoMovimentacao.AJUSTE, quantidade)
    if quantidade < 0:
        # Ajuste negativo também não pode deixar o saldo abaixo de zero.
        # -quantidade transforma -2 em 2 (o validar_saida trabalha com positivo).
        dominio.validar_saida(saldo(session, produto_id), -quantidade)

    mov = Movimentacao(
        produto_id=produto_id,
        tipo=TipoMovimentacao.AJUSTE,
        quantidade=quantidade,
        custo_unitario=produto.custo_medio,
        observacao=observacao,
    )
    session.add(mov)
    session.flush()
    return mov


def precisa_alerta(session: Session, produto_id: int) -> bool:
    """R6 com o banco. Peça sem nenhuma entrada não alerta (decisão S14)."""
    _buscar_produto(session, produto_id)  # só para dar erro claro se não existir

    # "A última entrada": filtra por peça e tipo, ordena do id MAIOR para o
    # menor (desc) e pega só 1. Usamos id e não data porque duas movimentações
    # podem ter o mesmo horário; o id sempre cresce.
    # EF: .Where(...).OrderByDescending(m => m.Id).Select(m => m.Quantidade).FirstOrDefault()
    #
    # Repare na sintaxe: os parênteses em volta permitem quebrar a expressão
    # em várias linhas, cada método numa linha (encadeamento fluente).
    ultima_entrada = session.scalar(
        select(Movimentacao.quantidade)
        .where(
            Movimentacao.produto_id == produto_id,
            Movimentacao.tipo == TipoMovimentacao.ENTRADA,
        )
        .order_by(Movimentacao.id.desc())
        .limit(1)
    )
    if ultima_entrada is None:
        return False
    # A conta do alerta continua num lugar só: o domínio.
    return dominio.precisa_alerta(saldo(session, produto_id), ultima_entrada)
