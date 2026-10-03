# Cabana Gestão — Teste de Reabertura da Competência

## Objetivo
Validar o fluxo DP → solicitação → Gerência → autorização/recusa → novo fechamento.

## Teste 1 — Solicitação pelo DP
1. Entrar como Usuário DP.
2. Abrir DP / Fechamento.
3. Competência deve estar fechada.
4. Clicar em Solicitar Reabertura.
5. Informar o motivo.
6. Enviar para Gerência.

Resultado esperado:
- competência permanece fechada;
- solicitação fica como `requested`;
- motivo e solicitante aparecem;
- auditoria registra a solicitação.

## Teste 2 — Autorização pela Gerência
1. Clicar em Trocar usuário.
2. Selecionar Gerência.
3. Abrir DP / Fechamento.
4. Deve aparecer a solicitação pendente.
5. Clicar em Analisar Reabertura.
6. Selecionar pelo menos um item.
7. Clicar em Autorizar reabertura.

Resultado esperado:
- competência muda para Em andamento;
- somente os itens selecionados voltam a pendente;
- demais itens permanecem concluídos;
- versão do fechamento aumenta;
- auditoria registra a autorização;
- DP poderá continuar o fechamento.

## Teste 3 — Recusa pela Gerência
1. Fazer nova solicitação pelo DP.
2. Entrar como Gerência.
3. Analisar a solicitação.
4. Clicar em Recusar.
5. Informar obrigatoriamente o motivo.

Resultado esperado:
- competência continua fechada;
- solicitação fica `denied`;
- motivo da recusa fica registrado;
- auditoria registra a recusa.

## Teste 4 — Novo fechamento após autorização
1. Gerência autoriza a reabertura.
2. Trocar para Usuário DP.
3. Corrigir os itens pendentes.
4. Concluir novamente o fechamento.

Resultado esperado:
- 24/24;
- competência fechada novamente;
- histórico preservado;
- auditoria preservada.

## Observação
Esta versão é de HOMOLOGAÇÃO. Não publicar como produção nem migrar para V3/servidor até que todos os fluxos sejam testados e aprovados.
