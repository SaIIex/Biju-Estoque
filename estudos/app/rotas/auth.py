# =============================================================================
# rotas/auth.py: telas de entrar e sair
# =============================================================================
# APIRouter = um "pedaço" de rotas que depois é plugado no app (main.py).
# Em ASP.NET: é um Controller (AuthController), ou um MapGroup.
# =============================================================================

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import senha_confere
from app.web import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def tela_login(request: Request):
    # O 3º argumento é o "contexto": as variáveis que o HTML pode usar.
    # É o ViewBag / Model do MVC.
    return templates.TemplateResponse(request, "login.html", {"erro": None})


@router.post("/login")
def fazer_login(request: Request, senha: str = Form("")):
    # "senha: str = Form("")": o FastAPI lê o campo "senha" do formulário
    # HTML (<input name="senha">). Em ASP.NET: [FromForm] string senha.
    # O "" é o padrão se o campo não vier.
    if not senha_confere(senha):
        # 401 = "não autorizado". Mostramos a mesma tela com a mensagem.
        # Mensagem genérica de propósito: não dizemos o que errou.
        return templates.TemplateResponse(
            request, "login.html", {"erro": "Senha incorreta."}, status_code=401
        )
    # clear() antes de marcar como logado: começa uma sessão limpa. Evita
    # carregar lixo de uma sessão anterior (boa prática contra "fixação de
    # sessão").
    request.session.clear()
    request.session["logado"] = True

    # 303 "See Other": depois de um POST, mandamos o navegador fazer um GET
    # em outra página. Isso é o padrão PRG (Post/Redirect/Get). Sem ele, se a
    # dona apertar F5, o navegador pergunta "reenviar formulário?" e pode
    # repetir a ação (imagina isso numa VENDA: venderia duas vezes).
    return RedirectResponse("/", status_code=303)


# Sair é POST, não GET, de propósito. Um GET pode ser disparado por um link
# ou imagem em outro site; ações que mudam estado devem ser POST.
@router.post("/logout")
def sair(request: Request):
    request.session.clear()  # rasga a pulseira
    return RedirectResponse("/login", status_code=303)
