# ADR 0001: IA do MVP é o cadastro e anúncio a partir da foto

**Data:** 03/11/2026
**Status:** Aceito

## Contexto
A vaga exige uma funcionalidade de IA generativa justificada pelo negócio. A dona já fotografa cada peça e escreve manualmente o anúncio para o grupo do WhatsApp. O cadastro no sistema precisa ser tão fácil quanto anotar no caderno, senão ela abandona o sistema.

## Decisão
A partir da foto da peça, um LLM multimodal sugere nome, descrição, tags e o texto do anúncio do WhatsApp com o preço de venda. A dona revisa e confirma antes de salvar ou copiar.

## Alternativas consideradas
- **Consulta em linguagem natural (tool calling):** forte para a vaga, mas com uma usuária e catálogo pequeno um painel responde o mesmo. Fica como Could.
- **Assistente de reposição:** não há histórico de vendas ainda. Backlog.
- **Servidor MCP:** sem valor para a dona. Backlog como bônus.

## Consequências
- Exige upload e armazenamento de imagem.
- Saída do modelo em structured output, validada antes de usar.
- **Regra de segurança:** o preço de custo nunca é enviado ao modelo, e a saída é verificada para não conter valores além do preço de venda.
- Humano no circuito: nada é salvo sem a confirmação da dona.
