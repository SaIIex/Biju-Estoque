# =============================================================================
# test_saude.py: testes das rotas básicas
# =============================================================================
# Comparação com C#: pytest é o xUnit do Python, e o TestClient é o
# WebApplicationFactory + HttpClient. Ele "liga" o app em memória, sem abrir
# porta de rede, e deixa você fazer requisições de mentira.
#
# Como o pytest acha os testes (convenção, sem atributos):
# - arquivos que começam com test_  (test_saude.py)
# - funções que começam com test_   (test_saude_responde_ok)
# Em xUnit você marca com [Fact]. No pytest, o NOME já é a marcação.
#
# Para rodar: python -m pytest   (ou só "pytest" com o venv ativado)
# =============================================================================

from fastapi.testclient import TestClient

# Importa o objeto app do arquivo app/main.py. Isso só funciona porque o
# pyproject.toml diz ao pytest: pythonpath = ["."], ou seja, "a raiz do
# projeto é o ponto de partida dos imports".
from app.main import app

# Um cliente para o arquivo inteiro. Criado uma vez, reaproveitado nos testes.
client = TestClient(app)


def test_saude_responde_ok():
    # Os 3 passos clássicos de um teste (Arrange, Act, Assert), o mesmo
    # padrão AAA que você já viu em C#. Aqui o Arrange é o client acima.

    # Act: faz um GET /saude.
    resposta = client.get("/saude")

    # Assert: em Python o assert é uma palavra da LINGUAGEM, não um método.
    # "assert condição" falha se a condição for falsa. O pytest ainda mostra
    # os dois lados da comparação quando falha, por exemplo: assert 404 == 200.
    # Em xUnit seria: Assert.Equal(200, resposta.StatusCode);
    assert resposta.status_code == 200

    # .json() converte o corpo da resposta em dict. Comparar dicts com ==
    # compara chave por chave, valor por valor.
    assert resposta.json() == {"status": "ok"}

    # Lembrete das nossas regras de teste: este teste foi rodado ANTES da rota
    # existir e falhou com "assert 404 == 200" (rota não encontrada). Depois
    # quebramos o código de propósito ("quebrado" no lugar de "ok") e ele
    # falhou de novo. Só assim sabemos que o teste realmente vigia algo.


def test_pagina_inicial_abre():
    resposta = client.get("/")
    assert resposta.status_code == 200

    # "x in y" para strings = "y contém x?". Em C#: resposta.Text.Contains(...)
    # Teste propositalmente simples: só garante que a página renderiza.
    # Testar HTML palavra por palavra deixa o teste frágil (quebra a cada
    # mudança visual sem ter bug nenhum).
    assert "Biju Estoque" in resposta.text
