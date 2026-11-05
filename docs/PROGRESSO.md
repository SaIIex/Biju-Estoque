# Progresso

**Última atualização:** 03/11/2026
**Prazo do MVP:** 17/11/2026 (14 dias restantes)
**Orçamento de tempo:** 1h30 a 3h/dia, ou seja, entre ~21h e ~42h até o prazo.

## Fase atual
Fase 1: Descoberta. **Fase 1 concluída em 03/11.** MoSCoW ([requisitos](mapas/requisitos.md)) e roadmap ([roadmap](mapas/roadmap.md)) aprovados.
**Fase 2 (modelagem ER) iniciada em 03/11**, um dia antes do roadmap. Salles propõe as tabelas; eu reviso.
- 04/11: v1 em texto revisada (respostas às 5 perguntas). Pendente: decidir pedido x venda direta, saldo calculado x coluna, tipo como texto; exercício de custo médio; v2 em erDiagram.
- 04/11: v2 do ER enviada como imagem (PRODUTO 1:N MOVIMENTACAO, tipo em texto, quantidade com sinal, saldo calculado, transacao_id opcional). Faltam no PRODUTO: código, custo médio, foto, tamanho. Coluna `preco` da movimentação tem dois significados. Tipos divergem dos requisitos ("devolucao" novo; faltam uso_proprio e defeito).
- 04/11: v3 escrita por mim em [modelo-dados.md](mapas/modelo-dados.md) com regras R1 a R8 e exemplos para testes.
**Fase 2 concluída em 04/11:** modelo v3 aprovado. Padrões assumidos: devolução fora do MVP; código da peça é texto livre digitado pela dona; uma foto por peça.
**Fase 3 em andamento (04/11):** estrutura de pastas, venv, dependências fixadas, página inicial, rota /saude com teste (falhou primeiro, quebra proposital detectada), render.yaml e [arquitetura](mapas/arquitetura.md). Rodando local.
**Fase 3 concluída em 04/11 (dois dias antes do roadmap):** repositório https://github.com/SaIIex/Biju-Estoque e app publicado em https://biju-estoque.onrender.com (/saude respondendo 200). Plano gratuito do Render: o app dorme sem uso; abrir 1 minuto antes de demos.
- Aviso pendente: Starlette sugere trocar `httpx` por `httpx2` no TestClient. Avaliar antes de trocar.
**Ritmo acelerado (aprovado em 03/11):** descoberta fecha em no máximo 2 sessões. Usuários já decidido; restam Vendas, IA e Técnico, depois MoSCoW. Meta: começar a codar até 06/11.

## Requisitos levantados
### Negócio
- Usuária única: a dona da loja (pessoa real, conhecida do Salles).
- Canais: loja física (principal) e WhatsApp.
- Catálogo: menor do que o estimado (40 a 50 citado antes; a confirmar com o caderno). Máximo encontrado: 4 unidades por peça.
- Controle atual: caderno.

### Produto
- Registro real no caderno: nome ("Colar Cravejado"), preço pago (15), preço de venda (50), código (01521), quantidade.
- O código parece esconder o preço de custo dentro dele (15 dentro de 01521). Hipótese: serve para a cliente não ver o custo na etiqueta. A confirmar com a dona.
- **Custo é dado sensível:** nunca pode aparecer em nada que a cliente veja (etiqueta, anúncio de WhatsApp, saída da IA).
- Variações: praticamente não há tamanhos diferentes; várias unidades da mesma peça. Modelo: 1 produto = 1 peça com quantidade; tamanho opcional.
- Kits: backlog.
- Foto: ela fotografa e posta no grupo do WhatsApp com o valor. Gancho para a IA.

### Estoque
- Modelo: **histórico de movimentações** (entrada, venda, presente, uso próprio, defeito, ajuste). Saldo = soma das movimentações.
- Saldo nunca negativo: saída maior que o saldo é bloqueada (requisito surgido no exemplo das regras de testes).
- Entradas: compras Shopee/Shein por unidade, custo conhecido por peça. Custo registrado a cada entrada.
- Alerta de estoque baixo: **30% da quantidade da última entrada, arredondado para cima**. Ajuste de conferência não muda a base.
- Conferência física: semanal; diferença vira movimentação de ajuste.
- Em aberto: mesma peça recomprada com custo diferente (custo médio).

### Vendas e financeiro
- Lucro calculado por CMV: receita das vendas menos custo das peças vendidas, menos perdas (presente, defeito, ajuste) pelo custo.
- Relatórios: lucro mensal (gráfico), lucro por peça, unidades vendidas por peça.
- Venda: sugere o preço do cadastro, ela pode alterar; lucro usa o preço real da venda.
- Uso: no celular, no balcão. Web responsiva (mobile first).
- Peças paradas: Could (fora do MVP se apertar).

### Usuários e acesso
- Uma usuária só. Login simples. Perfis e permissões: backlog.

## Decisões tomadas
- Estoque por movimentações.
- Alerta: ceil(30% × última entrada).
- Lucro por CMV, perdas valoradas pelo custo.
- Custo de recompras: custo médio ponderado, gravado em cada saída no momento em que ocorre.
- MoSCoW e roadmap aprovados em 03/11. Walking skeleton: deploy já na Fase 3.
- IA do MVP: cadastro e anúncio a partir da foto ([ADR 0001](adr/0001-ia-anuncio-por-foto.md)). Consulta em linguagem natural: Could.
- Stack: Python + FastAPI + Jinja2/HTMX/Pico.css + SQLAlchemy (SQLite/PostgreSQL) + Claude API + pytest ([ADR 0002](adr/0002-stack.md)).
- Regra de testes: valor esperado à mão a partir da spec, teste antes do código nas regras de negócio, provar que o teste falha, revisar todo teste gerado por IA.

## Riscos
- Prazo curto + linguagem nova. 14 dias restantes e ainda na Fase 1.

## Conceitos que já domino
- Requisito implícito: lucro exige custo, registrado na entrada da peça.
- Estoque como movimentações (com ressalva: esqueceu o ajuste no exercício).
- Lucro (CMV) vs caixa: entendido, mas a conta do 2º mês não foi feita. Revalidar quando implementar o relatório de lucro, via teste unitário.
- Teste tautológico: identificou sozinho o risco de testes gerados por IA que passam por construção.
- `pytest.raises`: código depois da exceção, dentro do `with`, nunca executa; asserts de estado vão fora do bloco.
- ADR, MoSCoW, walking skeleton (apresentados).

## Dúvidas pendentes
- Confirmar com a dona a lógica do código da peça.

## Próximo passo
1. Fase 4, próxima entrega: banco (SQLAlchemy, tabelas PRODUTO e MOVIMENTACAO) e serviço que usa as regras do domínio ao registrar entrada e saída.

## Fase 4: entregas
- 04/11: **regras de domínio** em `app/dominio/estoque.py` (R1, R2, R3, R6). 33 testes aprovados pelo Salles, escritos antes do código; falharam no assert com stubs; 9 mutações manuais detectadas. Decisão: custo médio guardado com 4 casas (ROUND_HALF_UP), exibição com 2. Limite do alerta em aritmética inteira.
2. Confirmar com a dona a lógica do código da peça e se ela faz trocas.

## Preferência de trabalho
- Salles prefere que eu proponha respostas padrão para ele confirmar ou corrigir.
- **Desde 04/11: modo rápido.** Foco em entregar o projeto: perguntas objetivas, eu proponho e escrevo, ele confirma. Exercícios e verificações ficam para depois do MVP (lista em "Aprendizado adiado").

- **Pasta [estudos/](../estudos/README.md):** todo arquivo Python novo ou alterado ganha uma cópia comentada lá (tom de pleno para estagiário, com comparações com C#).

## Aprendizado adiado (pós-MVP)
- Custo médio ponderado com quantidades desiguais (1 a R$ 15 + 3 a R$ 18 = R$ 17,25).
- Modelagem: coluna com dois significados, YAGNI, regra de sinal por tipo.
- Fundamentos de Python antes de aprofundar no código.
