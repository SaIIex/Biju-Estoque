from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import senha_confere
from app.web import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def tela_login(request: Request):
    return templates.TemplateResponse(request, "login.html", {"erro": None})


@router.post("/login")
def fazer_login(request: Request, senha: str = Form("")):
    if not senha_confere(senha):
        return templates.TemplateResponse(
            request, "login.html", {"erro": "Senha incorreta."}, status_code=401
        )
    request.session.clear()
    request.session["logado"] = True
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def sair(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
