"""Relatório de lucro do mês: filtro por mês (fuso de Brasília), ranking por peça e tela."""

from datetime import datetime, timezone
from decimal import Decimal

from app.dominio.estoque import TipoMovimentacao as T
from app.servicos.estoque import cadastrar_produto, registrar_entrada, registrar_saida
from app.servicos.relatorio import relatorio_do_mes

D = Decimal


def _utc(ano, mes, dia, hora, minuto=0):
    return datetime(ano, mes, dia, hora, minuto, tzinfo=timezone.utc)


def _peca(session, codigo, nome, qtd=10, custo="10"):
    p = cadastrar_produto(session, codigo=codigo, nome=nome, preco_venda=D("50"))
    registrar_entrada(session, p.id, quantidade=qtd, custo_unitario=D(custo))
    return p


def _venda_em(session, produto, quando_utc, qtd=1, preco="50"):
    mov = registrar_saida(session, produto.id, T.VENDA, quantidade=qtd, preco_venda=D(preco))
    mov.criado_em = quando_utc
    session.flush()
    return mov


# --- filtro por mês -------------------------------------------------------------

def test_r1_so_conta_o_mes_pedido(session):
    colar = _peca(session, "C1", "Colar")
    _venda_em(session, colar, _utc(2026, 10, 15, 15))  # outubro
    _venda_em(session, colar, _utc(2026, 11, 10, 15))  # novembro
    _venda_em(session, colar, _utc(2026, 11, 20, 15))  # novembro

    rel = relatorio_do_mes(session, 2026, 11)
    assert rel.total.unidades_vendidas == 2
    assert rel.total.resultado == D("80")  # 2 x (50 - 10)


def test_r2_virada_do_mes_usa_horario_de_brasilia(session):
    colar = _peca(session, "C1", "Colar")
    # 30/11 23:30 em Brasília = 01/12 02:30 UTC -> é venda de NOVEMBRO
    _venda_em(session, colar, _utc(2026, 12, 1, 2, 30))
    # 01/11 00:30 em Brasília = 01/11 03:30 UTC -> é NOVEMBRO
    _venda_em(session, colar, _utc(2026, 11, 1, 3, 30))
    # 31/10 23:59 em Brasília = 01/11 02:59 UTC -> é OUTUBRO
    _venda_em(session, colar, _utc(2026, 11, 1, 2, 59))

    assert relatorio_do_mes(session, 2026, 11).total.unidades_vendidas == 2
    assert relatorio_do_mes(session, 2026, 10).total.unidades_vendidas == 1
    assert relatorio_do_mes(session, 2026, 12).total.unidades_vendidas == 0


def test_r3_dezembro_vira_o_ano(session):
    colar = _peca(session, "C1", "Colar")
    _venda_em(session, colar, _utc(2026, 12, 31, 20))   # dezembro de 2026
    _venda_em(session, colar, _utc(2027, 1, 1, 12))     # janeiro de 2027
    assert relatorio_do_mes(session, 2026, 12).total.unidades_vendidas == 1


# --- por peça -------------------------------------------------------------------

def test_r4_ranking_por_peca_ordenado_pelo_lucro(session):
    colar = _peca(session, "C1", "Colar", custo="15")    # lucro 35 por unidade
    brinco = _peca(session, "B1", "Brinco", custo="5")   # lucro 45 por unidade
    quando = _utc(2026, 11, 10, 15)
    _venda_em(session, colar, quando, qtd=2)    # 70
    _venda_em(session, brinco, quando, qtd=1)   # 45

    pecas = relatorio_do_mes(session, 2026, 11).por_peca
    assert [p.nome for p in pecas] == ["Colar", "Brinco"]
    assert [p.unidades_vendidas for p in pecas] == [2, 1]
    assert [p.resultado for p in pecas] == [D("70"), D("45")]


def test_r5_peca_sem_venda_no_mes_nao_aparece_no_ranking(session):
    _peca(session, "C1", "Colar")  # só compra
    assert relatorio_do_mes(session, 2026, 11).por_peca == []


# --- tela -----------------------------------------------------------------------

def test_r6_tela_exige_login(client):
    r = client.get("/relatorio", follow_redirects=False)
    assert r.status_code == 303


def test_r7_tela_mostra_resultado_e_pecas(logado, session):
    colar = _peca(session, "C1", "Colar Cravejado", custo="15")
    _venda_em(session, colar, _utc(2026, 11, 10, 15), qtd=2, preco="45")
    session.commit()

    r = logado.get("/relatorio?mes=2026-11")
    assert r.status_code == 200
    assert "R$ 60,00" in r.text   # 2 x (45 - 15)
    assert "Colar Cravejado" in r.text
    assert "novembro de 2026" in r.text.lower()


def test_r8_mes_invalido_da_400(logado):
    for mes in ["2026-13", "abc", "2026-1-1"]:
        assert logado.get(f"/relatorio?mes={mes}").status_code == 400


def test_r9_venda_a_meia_noite_do_dia_1_conta_so_no_mes_novo(session):
    # Pega o bug de fim de mês inclusivo (<= em vez de <): a venda contaria nos dois meses.
    colar = _peca(session, "C1", "Colar")
    _venda_em(session, colar, _utc(2026, 12, 1, 3, 0))  # 01/12 00:00 em Brasília
    assert relatorio_do_mes(session, 2026, 11).total.unidades_vendidas == 0
    assert relatorio_do_mes(session, 2026, 12).total.unidades_vendidas == 1
