# =============================================================================
# rotas/pecas.py: as telas que a dona usa no dia a dia
# =============================================================================
# Papel deste arquivo: TRADUZIR. Pega o formulário (texto), converte para os
# tipos certos, chama o serviço, decide o que mostrar. Ele NÃO tem regra de
# negócio: saldo, custo médio e alerta estão no serviço/domínio.
# Rota magra, serviço gordo. Em ASP.NET: o Controller que só chama o Service.
#
# Fluxo de toda ação (venda, entrada...):
#   formulário -> converte -> serviço -> commit -> redireciona (PRG)
#                                  \-> erro de negócio -> rollback -> mostra erro (400)
# =============================================================================

"""Telas de peças: lista, cadastro, detalhe e movimentações."""

# Callable[[], None] = "uma função sem parâmetros que não devolve nada".
# Em C#: Action.
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

# dependencies=[Depends(exigir_login)] vale para TODAS as rotas deste router.
# É o [Authorize] em cima do Controller inteiro: impossível esquecer em uma
# rota nova. (Teste L6 garante: vender sem login é bloqueado.)
router = APIRouter(dependencies=[Depends(exigir_login)])

# Tupla de classes de erro. "except (A, B, C) as erro" pega qualquer uma.
# Estes erros são "esperados" (a dona digitou algo errado) e viram mensagem
# amigável. Qualquer OUTRO erro é bug nosso e deve aparecer como erro 500.
ERROS_DE_NEGOCIO = (
    EstoqueInsuficienteError,
    SinalInvalidoError,
    servico.PrecoVendaInvalidoError,
    servico.CodigoDuplicadoError,
    ValorInvalidoError,
)

# Lista BRANCA: só estes tipos podem entrar pela rota de "outras saídas".
# Sem isso, alguém mandaria tipo=venda e registraria venda SEM preço,
# furando a regra R5. (Teste M5.) Lista branca > lista negra: você diz o
# que pode, e todo o resto (inclusive o que ainda não existe) é proibido.
OUTRAS_SAIDAS = {
    TipoMovimentacao.PRESENTE,
    TipoMovimentacao.USO_PROPRIO,
    TipoMovimentacao.DEFEITO,
}


def _ler_inteiro(texto: str, campo: str = "Quantidade") -> int:
    try:
        return int((texto or "").strip())  # int("abc") lança ValueError
    except ValueError:
        # "from None" esconde o erro original do traceback: a mensagem nova
        # já explica tudo. Convertemos um erro técnico num erro de negócio.
        raise ValorInvalidoError(f"{campo} inválida: {texto!r}. Use um número inteiro.") from None


def _flash(request: Request, mensagem: str) -> None:
    # "Flash message": recado guardado na sessão que aparece UMA vez na
    # próxima página (que dá pop e apaga). É o TempData do ASP.NET MVC.
    request.session["flash"] = mensagem


# --- lista ----------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def lista(request: Request, session: Session = Depends(get_session)):
    # "session: Session = Depends(get_session)": injeção de dependência.
    # O FastAPI chama get_session() e passa a sessão. Nos testes, trocamos
    # get_session por um banco em memória (dependency_overrides), sem mudar
    # nada aqui. É exatamente o motivo de existir DI.
    produtos = session.scalars(
        select(Produto).where(Produto.ativo.is_(True)).order_by(Produto.nome)
    ).all()

    # List comprehension montando uma lista de dicts. Em C# com LINQ:
    #   produtos.Select(p => new { produto = p, saldo = ..., alerta = ... }).ToList()
    # Detalhe de desempenho: isso faz 2 consultas POR peça (saldo e alerta).
    # Com 50 peças são ~100 consultas pequenas: irrelevante aqui. Com 50 mil
    # peças seria o famoso problema "N+1" e faríamos uma consulta só agrupada.
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
    # Recebemos TUDO como texto (str) e convertemos nós mesmos. Se
    # declarássemos "quantidade: int", o FastAPI devolveria um erro 422 em
    # JSON, feio para a dona. Convertendo à mão, mostramos a mensagem na tela.
    codigo: str = Form(""),
    nome: str = Form(""),
    preco_venda: str = Form(""),
    tamanho: str = Form(""),
    quantidade: str = Form(""),
    custo_unitario: str = Form(""),
):
    # Guardamos o que ela digitou para devolver no formulário em caso de erro.
    # Ninguém merece redigitar tudo porque errou uma vírgula.
    valores = {
        "codigo": codigo, "nome": nome, "preco_venda": preco_venda,
        "tamanho": tamanho, "quantidade": quantidade, "custo_unitario": custo_unitario,
    }
    try:
        # Atribuição múltipla: a, b = x, y. Em C#: (a, b) = (x, y);
        codigo, nome = codigo.strip(), nome.strip()
        if not codigo or not nome:  # string vazia é "falsa" em Python
            raise ValorInvalidoError("Código e nome são obrigatórios.")
        preco = ler_dinheiro(preco_venda)

        # Ternário: inteiro se preencheu, senão 0.
        qtd = _ler_inteiro(quantidade) if quantidade.strip() else 0
        if qtd and not custo_unitario.strip():
            raise ValorInvalidoError("Informe o custo unitário da compra.")

        produto = servico.cadastrar_produto(
            session, codigo=codigo, nome=nome, preco_venda=preco,
            tamanho=tamanho.strip() or None,  # "" vira None (campo opcional vazio)
        )
        if qtd:
            servico.registrar_entrada(session, produto.id, qtd, ler_dinheiro(custo_unitario))

        # SÓ AQUI grava de verdade. Peça + primeira entrada são salvas JUNTAS
        # (uma transação). Se a entrada falhar, a peça também não é criada.
        session.commit()
    except ERROS_DE_NEGOCIO as erro:
        # Desfaz tudo o que foi preparado na sessão (o flush da peça).
        session.rollback()
        # 400 = "requisição inválida": o problema é o dado enviado.
        return templates.TemplateResponse(
            request, "peca_form.html", {"erro": str(erro), "valores": valores}, status_code=400
        )

    _flash(request, f"Peça {produto.nome} cadastrada.")
    return RedirectResponse(f"/pecas/{produto.id}", status_code=303)


# --- detalhe --------------------------------------------------------------------

def _contexto_detalhe(session: Session, produto_id: int) -> dict:
    produto = session.get(Produto, produto_id)
    if produto is None:
        # HTTPException vira a resposta HTTP direto. Em C#: return NotFound();
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    historico = session.scalars(
        select(Movimentacao)
        .where(Movimentacao.produto_id == produto_id)
        .order_by(Movimentacao.id.desc())  # mais recente primeiro
    ).all()
    return {
        "produto": produto,
        "saldo": servico.saldo(session, produto_id),
        "alerta": servico.precisa_alerta(session, produto_id),
        "historico": historico,
        # sorted com key=lambda: ordena pela propriedade .value.
        # Em C#: .OrderBy(t => t.Value). Conjunto não tem ordem; o select
        # do HTML precisa de uma ordem fixa.
        "outras_saidas": sorted(OUTRAS_SAIDAS, key=lambda t: t.value),
    }


# {produto_id} na URL vira o parâmetro produto_id: int. O FastAPI converte e
# valida: /pecas/abc devolve 422 sozinho. Em ASP.NET: [HttpGet("pecas/{id:int}")].
@router.get("/pecas/{produto_id}", response_class=HTMLResponse)
def detalhe(request: Request, produto_id: int, session: Session = Depends(get_session)):
    contexto = _contexto_detalhe(session, produto_id)
    contexto.update(erro=None, flash=request.session.pop("flash", None))
    return templates.TemplateResponse(request, "peca_detalhe.html", contexto)


def _movimentar(
    request: Request, session: Session, produto_id: int, acao: Callable[[], None], sucesso: str
):
    """Executa uma movimentação: grava e redireciona, ou mostra o erro sem gravar nada."""
    # Esta função recebe OUTRA função (acao) como parâmetro. As 4 rotas
    # abaixo (entrada, venda, saída, ajuste) têm o mesmo "esqueleto":
    # tenta, commit, redireciona / ou rollback e mostra erro. Só muda o
    # miolo. Em vez de copiar o try/except 4 vezes, passamos o miolo como
    # função. Em C#: um método que recebe Action. É o padrão "Template Method"
    # em versão funcional.
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
    # Função DENTRO de função (closure). Ela "enxerga" as variáveis de fora
    # (session, produto_id, quantidade...). Em C#: uma lambda () => { ... }
    # que captura variáveis locais.
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
            # TipoMovimentacao("presente") converte texto em Enum.
            # Texto desconhecido lança ValueError. Em C#: Enum.Parse.
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
