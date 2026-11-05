# =============================================================================
# web.py: configuração dos templates e "filtros" de exibição
# =============================================================================
# Um FILTRO do Jinja2 é uma função que você usa dentro do HTML com "|":
#     {{ produto.preco_venda | brl }}   ->   R$ 50,00
# É como um "pipe" do Angular, ou um HTML helper do Razor.
# Aqui ficam: brl (dinheiro), data_hora (fuso de Brasília) e rotulo_tipo
# ("uso_proprio" vira "Uso próprio").
# =============================================================================

"""Templates compartilhados e filtros de exibição."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.formatos import brl

# Fuso fixo de -3h. Por que não ZoneInfo("America/Sao_Paulo")?
# No Windows, o Python não traz a base de fusos horários sem instalar um
# pacote extra (tzdata). Como o Brasil não tem horário de verão desde 2019,
# um deslocamento fixo resolve sem dependência nova.
_BRASILIA = timezone(timedelta(hours=-3))

# Dicionário: chave -> valor. É o Dictionary<string, string> do C#.
_ROTULOS_TIPO = {
    "entrada": "Entrada",
    "venda": "Venda",
    "presente": "Presente",
    "uso_proprio": "Uso próprio",
    "defeito": "Defeito",
    "ajuste": "Ajuste",
}


def data_hora(valor: datetime) -> str:
    # O SQLite devolve a data SEM fuso (naive). Como gravamos sempre em UTC,
    # "carimbamos" UTC de volta antes de converter para Brasília.
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    # strftime = ToString("dd/MM/yyyy HH:mm") do C#, com outra notação.
    return valor.astimezone(_BRASILIA).strftime("%d/%m/%Y %H:%M")


def rotulo_tipo(tipo) -> str:
    # getattr(obj, "value", padrão): pega obj.value se existir, senão o padrão.
    # Assim a função aceita tanto o Enum (TipoMovimentacao.VENDA) quanto
    # o texto puro ("venda").
    valor = getattr(tipo, "value", tipo)
    # dict.get(chave, padrão): se a chave não existir, devolve o padrão.
    # Em C#: dict.GetValueOrDefault(chave, padrao).
    return _ROTULOS_TIPO.get(valor, valor)


# UMA instância de templates para o app todo, com os filtros registrados.
# Todas as rotas importam esta mesma (from app.web import templates).
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")
templates.env.filters["brl"] = brl
templates.env.filters["data_hora"] = data_hora
templates.env.filters["rotulo_tipo"] = rotulo_tipo

# Segurança que vem de graça: o Jinja2Templates faz AUTOESCAPE em arquivos
# .html. Se a dona (ou um atacante) cadastrar uma peça chamada
# "<script>alert(1)</script>", o HTML mostra o texto, não executa o script.
# Isso evita XSS. O Razor do ASP.NET faz o mesmo por padrão.
