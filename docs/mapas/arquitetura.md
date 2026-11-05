# Arquitetura

```mermaid
mindmap
  root((Arquitetura))
    Camadas
      Rotas FastAPI
        recebem formulário, devolvem HTML
      Domínio
        regras R1 a R8 em funções puras
        testadas sem banco
      Dados
        SQLAlchemy
        SQLite dev, PostgreSQL prod
      IA
        cliente Claude API isolado
        valida saída antes de usar
    Front-end
      Jinja2
      HTMX
      Pico.css mobile first
    Configuração
      variáveis de ambiente
      .env só local, fora do git
    Deploy
      Render via render.yaml
      health check em /saude
```

## Estrutura de pastas

```
app/
  main.py          # cria o FastAPI e registra as rotas
  config.py        # lê variáveis de ambiente
  templates/       # HTML (Jinja2)
  dominio/         # regras de negócio puras (Fase 4)
  db.py, modelos.py  # banco (Fase 4)
  ia/              # cliente do LLM (Fase 5)
tests/             # pytest
docs/              # progresso, ADRs, mapas
```

Princípio: **regras de negócio não conhecem banco nem HTTP.** Assim os testes das regras R1 a R8 rodam rápido e com valores calculados à mão.

```mermaid
flowchart LR
    Celular[Celular da dona] -->|HTTPS| Rotas[Rotas FastAPI]
    Rotas --> Dominio[Domínio: regras]
    Rotas --> Dados[(Banco)]
    Rotas --> IA[Cliente IA]
    IA -->|foto + preço, nunca custo| Claude[Claude API]
```
