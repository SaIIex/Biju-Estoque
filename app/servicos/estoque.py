"""Serviço de estoque: aplica as regras do domínio sobre o banco.

Não faz commit: quem chama (a rota) decide quando salvar. Assim, uma operação
que falha no meio não deixa nada gravado pela metade.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
    produto = session.get(Produto, produto_id)
    if produto is None:
        raise ProdutoNaoEncontradoError(f"Produto {produto_id} não encontrado.")
    return produto


def cadastrar_produto(
    session: Session,
    codigo: str,
    nome: str,
    preco_venda: Decimal,
    tamanho: str | None = None,
    descricao: str | None = None,
    foto_url: str | None = None,
) -> Produto:
    if session.scalar(select(Produto.id).where(Produto.codigo == codigo)) is not None:
        raise CodigoDuplicadoError(f"Já existe uma peça com o código {codigo}.")

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
    session.add(produto)
    session.flush()  # gera o id sem fazer commit
    return produto


def saldo(session: Session, produto_id: int) -> int:
    """R1: soma das quantidades das movimentações da peça."""
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

    produto.custo_medio = dominio.novo_custo_medio(
        saldo(session, produto_id), produto.custo_medio, quantidade, custo_unitario
    )
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

    if tipo not in TIPOS_SAIDA:
        raise ValueError(f"{tipo.value} não é uma saída.")
    if quantidade <= 0:
        raise SinalInvalidoError("Informe quantas peças saíram (número positivo).")

    # R5
    if tipo == TipoMovimentacao.VENDA:
        if preco_venda is None or preco_venda < 0:
            raise PrecoVendaInvalidoError("Venda precisa do preço real cobrado.")
    elif preco_venda is not None:
        raise PrecoVendaInvalidoError(f"{tipo.value} não tem preço de venda.")

    # R1: valida antes de gravar qualquer coisa
    dominio.validar_saida(saldo(session, produto_id), quantidade)

    mov = Movimentacao(
        produto_id=produto_id,
        tipo=tipo,
        quantidade=-quantidade,
        custo_unitario=produto.custo_medio,  # R4: custo do momento
        preco_venda=preco_venda,
    )
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
    _buscar_produto(session, produto_id)
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
    return dominio.precisa_alerta(saldo(session, produto_id), ultima_entrada)
