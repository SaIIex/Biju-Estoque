from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_saude_responde_ok():
    # Usado pelo Render para saber se o app subiu.
    resposta = client.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_pagina_inicial_abre():
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "Biju Estoque" in resposta.text
