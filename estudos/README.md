# Estudos

Cópias comentadas do código do projeto, para estudo. **Não são usadas pelo app**: o código que roda está em `app/` e `tests/`.

Quando o código original mudar, a cópia aqui pode ficar desatualizada. Na dúvida, o que vale é o original.

## Ordem de leitura sugerida

1. [app/config.py](app/config.py): como o app lê configuração (senha, chave de API).
2. [app/main.py](app/main.py): como nasce uma aplicação FastAPI e como funcionam rotas.
3. [tests/test_saude.py](tests/test_saude.py): como testar uma rota com pytest.

## Mapa rápido C# para Python

| C# / .NET | Python / FastAPI |
|---|---|
| `Program.cs` com `WebApplication.CreateBuilder` | `app = FastAPI()` em `main.py` |
| `app.MapGet("/rota", ...)` | `@app.get("/rota")` |
| `appsettings.json` + `IOptions<T>` | `pydantic-settings` (`BaseSettings`) |
| Razor (`.cshtml`) | Jinja2 (`.html`) |
| NuGet + `.csproj` | pip + `requirements.txt` |
| `using` | `import` / `from ... import` |
| xUnit + `WebApplicationFactory` | pytest + `TestClient` |
| `namespace` / pasta | pacote (pasta com `__init__.py`) |
