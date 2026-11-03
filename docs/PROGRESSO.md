# Progresso

**Última atualização:** 03/11/2026
**Prazo do MVP:** 17/11/2026 (14 dias restantes)
**Orçamento de tempo:** 1h30 a 3h/dia, ou seja, entre ~21h e ~42h até o prazo.

## Fase atual
Fase 1: Descoberta. **Fase 1 concluída em 03/11.** MoSCoW ([requisitos](mapas/requisitos.md)) e roadmap ([roadmap](mapas/roadmap.md)) aprovados. Próxima: Fase 2, modelagem do domínio e ER (04/11).
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
- ADR, MoSCoW, walking skeleton (apresentados).

## Dúvidas pendentes
- Confirmar com a dona a lógica do código da peça.

## Próximo passo
1. Salles adiciona a seção `# Regras de testes` ao CLAUDE.md; eu reviso.
2. Fase 2: modelagem ER (produto, movimentação, custo médio ponderado gravado na venda).
3. Confirmar com a dona a lógica do código da peça.

## Preferência de trabalho
- Salles prefere que eu proponha respostas padrão para ele confirmar ou corrigir.
