# Estudos

Cópias comentadas do código do projeto, para estudo. **Não são usadas pelo app**: o código que roda está em `app/` e `tests/`.

Quando o código original mudar, a cópia aqui pode ficar desatualizada. Na dúvida, o que vale é o original.

## Ordem de leitura sugerida

1. [app/config.py](app/config.py): como o app lê configuração (senha, chave de API).
2. [app/main.py](app/main.py): como nasce uma aplicação FastAPI e como funcionam rotas.
3. [tests/test_saude.py](tests/test_saude.py): como testar uma rota com pytest.
4. [app/dominio/estoque.py](app/dominio/estoque.py): regras de negócio puras (custo médio, saldo, sinal, alerta). Decimal para dinheiro, Enum, dataclass, exceções próprias.
5. [tests/test_dominio_estoque.py](tests/test_dominio_estoque.py): parametrize, casos de fronteira e teste de mutação.
6. [app/db.py](app/db.py): engine, sessão e criação das tabelas (o "DbContext" do Python).
7. [app/modelos.py](app/modelos.py): tabelas como classes (Code First com SQLAlchemy).
8. [app/servicos/estoque.py](app/servicos/estoque.py): serviço que junta domínio e banco; unit of work.
9. [tests/conftest.py](tests/conftest.py): fixtures do pytest e banco em memória para testes.
10. [tests/test_servico_estoque.py](tests/test_servico_estoque.py): testes de integração com banco e como a quebra proposital revelou testes fracos.
11. [app/formatos.py](app/formatos.py): validar entrada do usuário com regex; "R$ 1.234,50".
12. [app/auth.py](app/auth.py): login com senha em variável de ambiente, padrão seguro, ataque de tempo.
13. [app/web.py](app/web.py): filtros do Jinja2, fuso horário, autoescape contra XSS.
14. [app/main.py](app/main.py): lifespan, middleware de sessão, exception handler.
15. [app/rotas/auth.py](app/rotas/auth.py): login/logout e o padrão PRG.
16. [app/rotas/pecas.py](app/rotas/pecas.py): rotas magras, transação, lista branca, closures.
17. [tests/test_formatos.py](tests/test_formatos.py) e [tests/test_rotas.py](tests/test_rotas.py): TestClient, monkeypatch, dependency_overrides.
18. [tests/test_db.py](tests/test_db.py): URL do banco, driver e por que um teste "passando" pode não proteger nada.

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
| `record` | `@dataclass(frozen=True)` |
| `decimal` | `Decimal("...")` (sempre a partir de texto) |
| `decimal?` | `Decimal \| None` |
| `$"texto {x}"` | `f"texto {x}"` |
| `list.Sum(x => x.Qtd)` | `sum(x.qtd for x in lista)` |
| `[Theory]` + `[InlineData]` | `@pytest.mark.parametrize` |
| `Assert.Throws<T>(...)` | `with pytest.raises(T):` |
| Entity Framework | SQLAlchemy |
| `DbContext` | `Session` |
| `SaveChanges()` | `session.commit()` (e `flush()` para enviar sem confirmar) |
| `context.Produtos.Find(id)` | `session.get(Produto, id)` |
| LINQ `.Where(...).Select(...)` | `select(...).where(...)` |
| `using (var x = ...)` | `with ... as x:` |
| construtor/Dispose da classe de teste | `@pytest.fixture` com `yield` |
