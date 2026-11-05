"""Telas de peças: lista, cadastro, detalhe e movimentações."""

from collections.abc import Callable

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import exigir_login
from app.db import get_session
from app.dominio.estoque import (
    EstoqueInsuficienteError,
    SinalInvalidoError,
    TipoMovimentacao,
)
from app.formatos import ValorInvalidoError, ler_dinheiro
from app.modelos import Movimentacao, Produto
from app.servicos import estoque as servico
from app.web import templates

router = APIRouter(dependencies=[Depends(exigir_login)])

# Erros que viram mensagem para a dona (e não tela de erro do servidor).
ERROS_DE_NEGOCIO = (
    EstoqueInsuficienteError,
    SinalInvalidoError,
    servico.PrecoVendaInvalidoError,
    servico.CodigoDuplicadoError,
    ValorInvalidoError,
)

OUTRAS_SAIDAS = {
    TipoMovimentacao.PRESENTE,
    TipoMovimentacao.USO_PROPRIO,
    TipoMovimentacao.DEFEITO,
}


def _ler_inteiro(texto: str, campo: str = "Quantidade") -> int:
    try:
        return int((texto or "").strip())
    except ValueError:
        raise ValorInvalidoError(f"{campo} inválida: {texto!r}. Use um número inteiro.") from None


def _flash(request: Request, mensagem: str) -> None:
    request.session["flash"] = mensagem


# --- lista ----------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def lista(request: Request, session: Session = Depends(get_session)):
    produtos = session.scalars(
        select(Produto).where(Produto.ativo.is_(True)).order_by(Produto.nome)
    ).all()
    itens = [
        {
            "produto": p,
            "saldo": servico.saldo(session, p.id),
            "alerta": servico.precisa_alerta(session, p.id),
        }
        for p in produtos
    ]
    return templates.TemplateResponse(
        request, "lista.html", {"itens": itens, "flash": request.session.pop("flash", None)}
    )


# --- cadastro -------------------------------------------------------------------

@router.get("/pecas/nova", response_class=HTMLResponse)
def tela_nova(request: Request):
    return templates.TemplateResponse(request, "peca_form.html", {"erro": None, "valores": {}})


@router.post("/pecas")
def cadastrar(
    request: Request,
    session: Session = Depends(get_session),
    codigo: str = Form(""),
    nome: str = Form(""),
    preco_venda: str = Form(""),
    tamanho: str = Form(""),
    quantidade: str = Form(""),
    custo_unitario: str = Form(""),
):
    valores = {
        "codigo": codigo, "nome": nome, "preco_venda": preco_venda,
        "tamanho": tamanho, "quantidade": quantidade, "custo_unitario": custo_unitario,
    }
    try:
        codigo, nome = codigo.strip(), nome.strip()
        if not codigo or not nome:
            raise ValorInvalidoError("Código e nome são obrigatórios.")
        preco = ler_dinheiro(preco_venda)

        qtd = _ler_inteiro(quantidade) if quantidade.strip() else 0
        if qtd and not custo_unitario.strip():
            raise ValorInvalidoError("Informe o custo unitário da compra.")

        produto = servico.cadastrar_produto(
            session, codigo=codigo, nome=nome, preco_venda=preco,
            tamanho=tamanho.strip() or None,
        )
        if qtd:
            servico.registrar_entrada(session, produto.id, qtd, ler_dinheiro(custo_unitario))
        session.commit()
    except ERROS_DE_NEGOCIO as erro:
        session.rollback()
        return templates.TemplateResponse(
            request, "peca_form.html", {"erro": str(erro), "valores": valores}, status_code=400
        )

    _flash(request, f"Peça {produto.nome} cadastrada.")
    return RedirectResponse(f"/pecas/{produto.id}", status_code=303)


# --- detalhe --------------------------------------------------------------------

def _contexto_detalhe(session: Session, produto_id: int) -> dict:
    produto = session.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    historico = session.scalars(
        select(Movimentacao)
        .where(Movimentacao.produto_id == produto_id)
        .order_by(Movimentacao.id.desc())
    ).all()
    return {
        "produto": produto,
        "saldo": servico.saldo(session, produto_id),
        "alerta": servico.precisa_alerta(session, produto_id),
        "historico": historico,
        "outras_saidas": sorted(OUTRAS_SAIDAS, key=lambda t: t.value),
    }


@router.get("/pecas/{produto_id}", response_class=HTMLResponse)
def detalhe(request: Request, produto_id: int, session: Session = Depends(get_session)):
    contexto = _contexto_detalhe(session, produto_id)
    contexto.update(erro=None, flash=request.session.pop("flash", None))
    return templates.TemplateResponse(request, "peca_detalhe.html", contexto)


def _movimentar(
    request: Request, session: Session, produto_id: int, acao: Callable[[], None], sucesso: str
):
    """Executa uma movimentação: grava e redireciona, ou mostra o erro sem gravar nada."""
    try:
        acao()
        session.commit()
    except servico.ProdutoNaoEncontradoError:
        session.rollback()
        raise HTTPException(status_code=404, detail="Peça não encontrada") from None
    except ERROS_DE_NEGOCIO as erro:
        session.rollback()
        contexto = _contexto_detalhe(session, produto_id)
        contexto.update(erro=str(erro), flash=None)
        return templates.TemplateResponse(
            request, "peca_detalhe.html", contexto, status_code=400
        )
    _flash(request, sucesso)
    return RedirectResponse(f"/pecas/{produto_id}", status_code=303)


@router.post("/pecas/{produto_id}/entrada")
def entrada(
    request: Request, produto_id: int, session: Session = Depends(get_session),
    quantidade: str = Form(""), custo_unitario: str = Form(""),
):
    def acao():
        servico.registrar_entrada(
            session, produto_id, _ler_inteiro(quantidade), ler_dinheiro(custo_unitario)
        )
    return _movimentar(request, session, produto_id, acao, "Entrada registrada.")


@router.post("/pecas/{produto_id}/venda")
def venda(
    request: Request, produto_id: int, session: Session = Depends(get_session),
    quantidade: str = Form(""), preco_venda: str = Form(""),
):
    def acao():
        servico.registrar_saida(
            session, produto_id, TipoMovimentacao.VENDA,
            _ler_inteiro(quantidade), preco_venda=ler_dinheiro(preco_venda),
        )
    return _movimentar(request, session, produto_id, acao, "Venda registrada.")


@router.post("/pecas/{produto_id}/saida")
def outra_saida(
    request: Request, produto_id: int, session: Session = Depends(get_session),
    tipo: str = Form(""), quantidade: str = Form(""),
):
    def acao():
        try:
            tipo_mov = TipoMovimentacao(tipo)
        except ValueError:
            raise ValorInvalidoError(f"Tipo de saída inválido: {tipo!r}.") from None
        if tipo_mov not in OUTRAS_SAIDAS:
            raise ValorInvalidoError(f"Use a tela própria para {tipo_mov.value}.")
        servico.registrar_saida(session, produto_id, tipo_mov, _ler_inteiro(quantidade))
    return _movimentar(request, session, produto_id, acao, "Saída registrada.")


@router.post("/pecas/{produto_id}/ajuste")
def ajuste(
    request: Request, produto_id: int, session: Session = Depends(get_session),
    quantidade: str = Form(""), observacao: str = Form(""),
):
    def acao():
        servico.registrar_ajuste(
            session, produto_id, _ler_inteiro(quantidade), observacao.strip() or None
        )
    return _movimentar(request, session, produto_id, acao, "Ajuste registrado.")
