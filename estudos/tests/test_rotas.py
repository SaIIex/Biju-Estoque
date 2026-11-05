# =============================================================================
# test_rotas.py: testes das TELAS (de ponta a ponta, sem navegador)
# =============================================================================
# O TestClient faz requisições HTTP de mentira direto no app, em memória.
# Em C#: WebApplicationFactory<Program> + HttpClient.
#
# Conceitos novos aqui (as fixtures client e logado estão no conftest.py):
#
# - follow_redirects=False: por padrão o TestClient SEGUE redirecionamentos
#   (como o navegador). Desligamos quando queremos conferir o PRÓPRIO
#   redirecionamento: status 303 e para onde ele aponta (headers["location"]).
#
# - data={...}: envia como formulário HTML (application/x-www-form-urlencoded),
#   igual ao <form method="post"> da tela. Os valores vão como TEXTO
#   ("45,00"), exatamente como a dona digitaria.
#
# - Os testes conferem o EFEITO no banco (saldo, preço gravado), não só o
#   HTML. Uma tela pode mostrar "Venda registrada" e ter gravado errado.
#   Foi assim que a quebra proposital achou o bug R9: a venda gravava sempre
#   R$ 50 e nenhum teste olhava o preço gravado.
#
# - r.text.split("Anel Acabando")[1].split("</article>")[0]: corta o HTML
#   para pegar só o "cartão" do anel e conferir que o alerta está NELE, e
#   não no cartão de outra peça.
# =============================================================================

"""Testes das telas: login, lista, cadastro e movimentações via formulário."""

from decimal import Decimal

from sqlalchemy import func, select

from app.dominio.estoque import TipoMovimentacao as T
from app.modelos import Produto
from app.servicos.estoque import cadastrar_produto, registrar_entrada, registrar_saida, saldo
from tests.conftest import SENHA_TESTE


def _peca(session, codigo="01521", nome="Colar Cravejado", qtd=3, custo="15"):
    p = cadastrar_produto(session, codigo=codigo, nome=nome, preco_venda=Decimal("50"))
    if qtd:
        registrar_entrada(session, p.id, quantidade=qtd, custo_unitario=Decimal(custo))
    session.commit()
    return p


# --- login ----------------------------------------------------------------------

def test_l1_sem_login_redireciona_para_login(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_l2_senha_errada_nao_entra(client):
    r = client.post("/login", data={"senha": "chute"}, follow_redirects=False)
    assert r.status_code == 401
    assert "Senha incorreta" in r.text
    assert client.get("/", follow_redirects=False).status_code == 303


def test_l3_senha_certa_entra(client):
    r = client.post("/login", data={"senha": SENHA_TESTE}, follow_redirects=False)
    assert r.status_code == 303
    assert client.get("/", follow_redirects=False).status_code == 200


def test_l4_senha_nao_configurada_bloqueia_todo_login(client, monkeypatch):
    # Padrão seguro: sem APP_SENHA no servidor, ninguém entra (nem com senha vazia).
    from app.config import settings

    monkeypatch.setattr(settings, "app_senha", "")
    r = client.post("/login", data={"senha": ""}, follow_redirects=False)
    assert r.status_code == 401


def test_l5_logout_encerra_a_sessao(logado):
    logado.post("/logout")
    assert logado.get("/", follow_redirects=False).status_code == 303


def test_l6_paginas_internas_tambem_exigem_login(client, session):
    p = _peca(session)
    assert client.get(f"/pecas/{p.id}", follow_redirects=False).status_code == 303
    r = client.post(f"/pecas/{p.id}/venda", data={"quantidade": "1", "preco_venda": "50"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert saldo(session, p.id) == 3  # nada foi vendido


# --- lista ----------------------------------------------------------------------

def test_p1_lista_mostra_pecas_saldo_e_preco(logado, session):
    _peca(session)
    r = logado.get("/")
    assert "Colar Cravejado" in r.text
    assert "01521" in r.text
    assert "R$ 50,00" in r.text


def test_p2_lista_marca_estoque_baixo_so_na_peca_certa(logado, session):
    acabando = _peca(session, codigo="A1", nome="Anel Acabando", qtd=4)
    _peca(session, codigo="B1", nome="Brinco Tranquilo", qtd=4)
    registrar_saida(session, acabando.id, T.VENDA, quantidade=2, preco_venda=Decimal("50"))
    session.commit()  # Anel: saldo 2, limite 2 -> alerta. Brinco: saldo 4 -> não.

    r = logado.get("/")
    assert r.text.count("Estoque baixo") == 1
    trecho_anel = r.text.split("Anel Acabando")[1].split("</article>")[0]
    assert "Estoque baixo" in trecho_anel


def test_p3_lista_nao_mostra_custo(logado, session):
    # Decisão: a tela é usada no balcão; a cliente pode ver. Custo só no detalhe.
    _peca(session, custo="15")
    r = logado.get("/")
    assert "15,00" not in r.text


# --- cadastro -------------------------------------------------------------------

def test_c1_cadastro_com_quantidade_inicial(logado, session):
    r = logado.post(
        "/pecas",
        data={"codigo": "01521", "nome": "Colar Cravejado", "preco_venda": "50,00",
              "quantidade": "3", "custo_unitario": "15,00"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    p = session.scalar(select(Produto).where(Produto.codigo == "01521"))
    assert r.headers["location"] == f"/pecas/{p.id}"
    assert saldo(session, p.id) == 3
    assert p.custo_medio == Decimal("15.0000")


def test_c2_cadastro_sem_quantidade_so_cria_a_peca(logado, session):
    logado.post("/pecas", data={"codigo": "X9", "nome": "Pulseira", "preco_venda": "20"})
    p = session.scalar(select(Produto).where(Produto.codigo == "X9"))
    assert p is not None
    assert saldo(session, p.id) == 0


def test_c3_codigo_duplicado_mostra_erro_e_nao_duplica(logado, session):
    _peca(session, codigo="01521")
    r = logado.post("/pecas", data={"codigo": "01521", "nome": "Outro", "preco_venda": "10"})
    assert r.status_code == 400
    assert "Já existe uma peça com o código 01521" in r.text
    assert session.scalar(select(func.count()).select_from(Produto)) == 1


def test_c4_preco_invalido_mostra_erro(logado, session):
    r = logado.post("/pecas", data={"codigo": "Z1", "nome": "Anel", "preco_venda": "abc"})
    assert r.status_code == 400
    assert "valor inválido" in r.text.lower()
    assert session.scalar(select(func.count()).select_from(Produto)) == 0


def test_c5_quantidade_sem_custo_e_recusada(logado, session):
    # Entrada sem custo quebraria o custo médio e o lucro.
    r = logado.post("/pecas", data={"codigo": "Z2", "nome": "Anel", "preco_venda": "30",
                                    "quantidade": "2"})
    assert r.status_code == 400
    assert session.scalar(select(func.count()).select_from(Produto)) == 0


# --- detalhe e movimentações ----------------------------------------------------

def test_d1_detalhe_mostra_saldo_custo_e_historico(logado, session):
    p = _peca(session, qtd=3, custo="15")
    r = logado.get(f"/pecas/{p.id}")
    assert r.status_code == 200
    assert "Colar Cravejado" in r.text
    assert "R$ 15,00" in r.text  # custo médio aparece aqui
    assert "entrada" in r.text.lower()


def test_d2_peca_inexistente_da_404(logado):
    assert logado.get("/pecas/999").status_code == 404


def test_m1_venda_pelo_formulario(logado, session):
    p = _peca(session, qtd=3, custo="15")
    r = logado.post(f"/pecas/{p.id}/venda", data={"quantidade": "1", "preco_venda": "45,00"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert saldo(session, p.id) == 2


def test_m2_venda_acima_do_saldo_mostra_erro(logado, session):
    p = _peca(session, qtd=3)
    r = logado.post(f"/pecas/{p.id}/venda", data={"quantidade": "5", "preco_venda": "50"})
    assert r.status_code == 400
    assert "Estoque insuficiente" in r.text
    assert saldo(session, p.id) == 3


def test_m3_entrada_pelo_formulario_atualiza_custo(logado, session):
    p = _peca(session, qtd=2, custo="15")
    logado.post(f"/pecas/{p.id}/entrada", data={"quantidade": "2", "custo_unitario": "18,00"})
    session.refresh(p)
    assert saldo(session, p.id) == 4
    assert p.custo_medio == Decimal("16.5000")


def test_m4_outras_saidas_pelo_formulario(logado, session):
    p = _peca(session, qtd=3)
    logado.post(f"/pecas/{p.id}/saida", data={"tipo": "presente", "quantidade": "1"})
    logado.post(f"/pecas/{p.id}/saida", data={"tipo": "defeito", "quantidade": "1"})
    assert saldo(session, p.id) == 1


def test_m5_saida_nao_aceita_tipo_venda_nem_entrada(logado, session):
    # A rota de "outras saídas" não pode virar porta dos fundos para venda sem preço.
    p = _peca(session, qtd=3)
    for tipo in ["venda", "entrada", "qualquer"]:
        r = logado.post(f"/pecas/{p.id}/saida", data={"tipo": tipo, "quantidade": "1"})
        assert r.status_code == 400
    assert saldo(session, p.id) == 3


def test_m6_ajuste_pelo_formulario(logado, session):
    p = _peca(session, qtd=3)
    logado.post(f"/pecas/{p.id}/ajuste", data={"quantidade": "-1", "observacao": "conferência"})
    assert saldo(session, p.id) == 2
