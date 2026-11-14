"""Tela do lucro do mês."""

import re
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth import exigir_login
from app.db import get_session
from app.servicos.relatorio import BRASILIA, relatorio_do_mes
from app.web import templates

router = APIRouter(dependencies=[Depends(exigir_login)])

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
_FORMATO_MES = re.compile(r"(\d{4})-(\d{2})")


def _vizinho(ano: int, mes: int, passo: int) -> str:
    indice = ano * 12 + (mes - 1) + passo
    return f"{indice // 12:04d}-{indice % 12 + 1:02d}"


@router.get("/relatorio", response_class=HTMLResponse)
def relatorio(request: Request, mes: str | None = None, session: Session = Depends(get_session)):
    if mes is None:
        agora = datetime.now(BRASILIA)
        ano, numero = agora.year, agora.month
    else:
        achado = _FORMATO_MES.fullmatch(mes)
        ano, numero = (int(achado[1]), int(achado[2])) if achado else (0, 0)
        if not 1 <= numero <= 12:
            return templates.TemplateResponse(
                request, "relatorio.html",
                {"erro": f"Mês inválido: {mes!r}. Use o formato 2026-11.", "rel": None},
                status_code=400,
            )

    rel = relatorio_do_mes(session, ano, numero)
    return templates.TemplateResponse(
        request,
        "relatorio.html",
        {
            "erro": None,
            "rel": rel,
            "titulo_mes": f"{MESES[numero - 1].capitalize()} de {ano}",
            "anterior": _vizinho(ano, numero, -1),
            "proximo": _vizinho(ano, numero, +1),
        },
    )
