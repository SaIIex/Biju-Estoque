"""Templates compartilhados e filtros de exibição."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.formatos import brl

# Brasília não tem horário de verão desde 2019.
_BRASILIA = timezone(timedelta(hours=-3))

_ROTULOS_TIPO = {
    "entrada": "Entrada",
    "venda": "Venda",
    "presente": "Presente",
    "uso_proprio": "Uso próprio",
    "defeito": "Defeito",
    "ajuste": "Ajuste",
}


def data_hora(valor: datetime) -> str:
    if valor.tzinfo is None:  # SQLite devolve sem fuso; gravamos em UTC
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(_BRASILIA).strftime("%d/%m/%Y %H:%M")


def rotulo_tipo(tipo) -> str:
    valor = getattr(tipo, "value", tipo)
    return _ROTULOS_TIPO.get(valor, valor)


templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")
templates.env.filters["brl"] = brl
templates.env.filters["data_hora"] = data_hora
templates.env.filters["rotulo_tipo"] = rotulo_tipo
