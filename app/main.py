from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Biju Estoque")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/saude")
def saude():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    return templates.TemplateResponse(request, "index.html")
