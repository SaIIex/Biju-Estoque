# ADR 0002: Stack do MVP

**Data:** 03/11/2026
**Status:** Aceito

## Contexto
MVP em 14 dias, uma usuária usando no celular, IA multimodal (ADR 0001). O Salles domina C#/.NET, mas a vaga é de AI Engineer, onde Python predomina.

## Decisão
| Camada | Escolha |
|---|---|
| Linguagem e back-end | Python + FastAPI |
| Front-end | HTML no servidor (Jinja2) + HTMX + Pico.css, mobile first |
| Banco | SQLAlchemy; SQLite no desenvolvimento, PostgreSQL em produção |
| LLM | Claude API, começando pelo modelo menor (Haiku) e subindo só se a qualidade não bastar |
| Testes | pytest |
| Login | Uma usuária, senha em variável de ambiente, sessão por cookie |
| Deploy | Render ou Railway (decidido na Fase 7) |

## Alternativas consideradas
- **ASP.NET Core:** entrega mais rápida para o Salles, mas menos alinhada à vaga e ao ecossistema de IA.
- **React/SPA:** mais uma curva de aprendizado; HTMX resolve a interatividade necessária.

## Consequências
- Horas de adaptação ao Python. Se o prazo apertar, corta-se escopo, não a linguagem.
- FastAPI espelha conceitos do ASP.NET Core (tipos, DTOs com validação via Pydantic, injeção de dependência).

## Regra de testes (proposta pelo Salles)
LLMs tendem a gerar testes que passam por construção. Para evitar:
1. **Valor esperado escrito à mão, a partir da spec**, nunca calculado com a mesma lógica do código testado.
2. **Teste antes do código** nas regras de negócio (alerta, lucro): o teste nasce da tabela da spec e precisa falhar primeiro.
3. **Prova da falha:** quebrar o código de propósito e confirmar que o teste fica vermelho.
4. Todo teste gerado por IA é revisado no diff antes de ser aceito.
