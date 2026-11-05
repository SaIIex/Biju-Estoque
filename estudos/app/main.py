# =============================================================================
# main.py: o ponto de entrada da aplicação web
# =============================================================================
# Comparação com C#: este arquivo é o Program.cs de um projeto ASP.NET Core
# com Minimal APIs. Ele cria o app e define quais URLs existem.
#
# Quem roda este arquivo? O uvicorn, que é o SERVIDOR web (o papel do
# Kestrel no .NET). O comando é:
#   uvicorn app.main:app --reload
# Leia "app.main:app" como: "no módulo app/main.py, use a variável app".
# --reload = reinicia sozinho quando você salva um arquivo (como o hot reload).
# =============================================================================

# Path é a forma moderna de lidar com caminhos de arquivo em Python.
# Equivale ao System.IO.Path, mas orientado a objetos: dá para fazer
# pasta / "arquivo.txt" para juntar caminhos.
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# __file__ é uma variável especial: o caminho DESTE arquivo (main.py).
# .resolve() transforma em caminho absoluto; .parent pega a pasta (app/).
# Por que isso? Para achar a pasta templates/ independentemente de onde você
# rodou o comando. Sem isso, rodar o app de outra pasta quebraria tudo.
BASE_DIR = Path(__file__).resolve().parent

# Cria a aplicação. Equivale a:
#   var app = WebApplication.CreateBuilder(args).Build();
# O title aparece na documentação automática em http://localhost:8000/docs
# (o FastAPI gera um Swagger de graça, igual ao Swashbuckle no .NET).
app = FastAPI(title="Biju Estoque")

# Configura o motor de templates (Jinja2). É o "Razor" do Python:
# HTML com marcações {{ variavel }} e {% bloco %} preenchidas no servidor.
# O "/" aqui não é divisão: o Path sobrecarrega o operador para juntar
# caminhos. BASE_DIR / "templates" = ".../app/templates".
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# @app.get("/saude") é um DECORATOR. Ele "pendura" a função abaixo na URL
# GET /saude. Em C# Minimal API seria:
#   app.MapGet("/saude", () => new { status = "ok" });
# Ou num controller: [HttpGet("saude")] em cima do método. Mesma ideia
# dos atributos do C#: metadado que muda como o framework trata o método.
@app.get("/saude")
def saude():
    # Retornar um dict faz o FastAPI responder JSON automaticamente:
    # {"status": "ok"}. dict do Python = Dictionary<string, object> /
    # objeto anônimo do C#.
    #
    # Para que serve esta rota? O Render chama /saude de tempos em tempos.
    # Se responder 200, ele sabe que o app está vivo. Isso se chama
    # HEALTH CHECK, e é padrão em qualquer deploy profissional.
    return {"status": "ok"}


# response_class=HTMLResponse avisa ao FastAPI (e à documentação) que esta
# rota devolve HTML, não JSON.
@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    # "request: Request": o FastAPI vê o tipo Request na assinatura e injeta
    # a requisição atual sozinho. É INJEÇÃO DE DEPENDÊNCIA pelo tipo, igual
    # ao ASP.NET injetando HttpContext ou serviços pelo construtor/parâmetro.
    #
    # TemplateResponse renderiza templates/index.html e devolve o HTML.
    # Equivale ao "return View()" de um controller MVC.
    # O request é obrigatório porque o Jinja2 do FastAPI usa ele para montar
    # URLs dentro do template.
    return templates.TemplateResponse(request, "index.html")


# Detalhe de Python: repare que não existe "public", "static", chaves {} nem
# ponto e vírgula. O que define o que está DENTRO da função é a INDENTAÇÃO
# (4 espaços). Errar indentação em Python não é feio: é erro de sintaxe ou,
# pior, muda o comportamento sem dar erro.
