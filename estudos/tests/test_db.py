# =============================================================================
# test_db.py: testes da conversão da URL do banco
# =============================================================================
# Uma função de 6 linhas com 6 testes. Exagero? Não: ela roda UMA vez, na
# subida do servidor, e se errar o app inteiro não liga em produção. Bug de
# configuração é o tipo que só aparece no pior momento (no deploy).
#
# Os casos B5 e B6 são os "traiçoeiros": um espaço colado por engano no
# painel do Render, e uma senha que contém o próprio prefixo.
# Lição da quebra proposital: o B6 usava "postgres://" dentro de uma URL que
# começa com "postgresql://". Um replace ingênuo NÃO mexeria nele, então o
# teste não distinguia o código certo do errado. Um teste só protege se o
# código errado o faria falhar.
# =============================================================================

"""Conversão da URL do banco para o driver certo (psycopg 3)."""

import pytest

from app.db import normalizar_url_banco


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        # B1: formato antigo que alguns provedores ainda entregam
        ("postgres://u:s@host/banco", "postgresql+psycopg://u:s@host/banco"),
        # B2: formato do Neon, com parâmetro de SSL preservado
        ("postgresql://u:s@host/banco?sslmode=require",
         "postgresql+psycopg://u:s@host/banco?sslmode=require"),
        # B3: já está no formato certo -> não mexe
        ("postgresql+psycopg://u:s@host/banco", "postgresql+psycopg://u:s@host/banco"),
        # B4: SQLite local -> não mexe
        ("sqlite:///./biju.db", "sqlite:///./biju.db"),
        # B5: espaços e quebra de linha colados por engano no painel do Render
        ("  postgresql://u:s@host/banco\n", "postgresql+psycopg://u:s@host/banco"),
    ],
    ids=["B1-postgres", "B2-neon-ssl", "B3-ja-certo", "B4-sqlite", "B5-espacos"],
)
def test_normalizar_url_banco(entrada, esperado):
    assert normalizar_url_banco(entrada) == esperado


def test_b6_senha_com_postgres_no_meio_nao_e_alterada():
    # Só o prefixo muda. Um "postgres://" dentro da senha ou do host fica intacto.
    url = "postgresql://u:postgres://x@host/banco"
    assert normalizar_url_banco(url) == "postgresql+psycopg://u:postgres://x@host/banco"
