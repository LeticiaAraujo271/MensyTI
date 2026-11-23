# Especificação para Claude Code — Central de Atendimento TI Multicanal

## Objetivo
Construir um chatbot corporativo de TI acessível por **link web** como canal principal e por **WhatsApp oficial** como canal opcional. A indisponibilidade do WhatsApp não pode impedir a operação do portal. As mensagens, atendimentos e chamados devem ser armazenados de forma centralizada, independentemente do canal.

## Contexto
O processo de referência possui identificação do colaborador, escolha do assunto, orientação passo a passo, verificação de resolução, avaliação de 1 a 5 e transferência para atendimento humano pelo Digisac. Adaptar para a experiência multicanal. O arquivo BPMN anexo é o fluxo-alvo inicial.

## Requisitos funcionais (MVP)
1. Portal público por URL amigável, responsivo e acessível em celular e desktop, com interface de conversa.
2. Identificar colaborador (nome, setor, e-mail corporativo ou matrícula, conforme configuração). Não confiar em identidade fornecida apenas por número de WhatsApp; proteger informações pessoais e sensíveis.
3. Menu inicial: acesso/login; computador lento ou travando; internet/rede/VPN; e-mail e Microsoft 365; impressora; sistemas internos; solicitação de acesso; outros.
4. Perguntas guiadas e base de conhecimento versionada, editável por administradores, para instruções aprovadas. Não inventar procedimentos nem solicitar senhas, códigos MFA ou dados sensíveis.
5. Ao finalizar uma orientação, perguntar: “Seu problema foi resolvido?” Se sim, permitir avaliação de 1 a 5, registrar atendimento e encerrar.
6. Se não resolver, abrir chamado com protocolo, descrição, categoria, prioridade e resumo da conversa, sem exigir que o colaborador repita os dados.
7. Incidentes críticos/de segurança (por exemplo, suspeita de phishing, vazamento, indisponibilidade coletiva) devem pular instruções arriscadas e gerar escalonamento prioritário.
8. Se houver analista disponível, oferecer atendimento humano via painel web; fora do expediente, registrar na fila, exibir protocolo e informar a janela de suporte **configurada**, sem inventar previsão.
9. Painel de analistas para filas, status, prioridades, atribuição, histórico, respostas, registro da solução e encerramento.
10. Painel administrativo para gerenciar categorias, artigos, horários de atendimento, usuários e permissões, integrações e métricas.
11. Integração WhatsApp desacoplada: webhooks de entrada, envio de respostas via API oficial/provedor autorizado, idempotência, tentativas com backoff, fila e indicador de saúde. Quando indisponível, informar o link de acesso no que for tecnicamente possível; não depender de conseguir enviar mensagem pelo canal caído.
12. Acompanhamento do chamado por protocolo no portal após autenticação/validação adequada.

## Requisitos não funcionais
- Autenticação de analistas e administradores com controle de acesso por perfil (RBAC).
- Tratamento de dados conforme LGPD: finalidade, minimização, retenção configurável, trilha de auditoria e remoção/exportação conforme regras internas.
- Criptografia em trânsito, segredos apenas em variáveis de ambiente, validação de entrada, proteção contra abuso, logs sem senhas e observabilidade.
- Não expor conversas de um colaborador a outro. Separar identificação de canal, usuário, conversa e chamado.
- Testes automatizados para ramos resolvido/não resolvido, segurança, fora do expediente, falha de WhatsApp e criação duplicada.

## Arquitetura sugerida (adaptável ao repositório)
- Frontend: Next.js + TypeScript, UI de chat para colaboradores e dashboard de analistas.
- Backend: API tipada com módulo de orquestração de conversas, regras de atendimento e adaptadores de canal.
- Banco: PostgreSQL (Prisma ou equivalente), com migrações.
- Filas/tarefas: Redis + worker, se necessário para integrações e retentativas.
- Canal web: REST e/ou streaming/SSE/WebSocket, com estado de sessão persistido.
- Canal WhatsApp: adaptador isolado; não acoplar ao motor de conversa.
- IA: opcional, com recuperação apenas de conteúdo interno aprovado; respostas determinísticas como fallback quando IA/API estiver indisponível.
- Digisac: integração futura condicionada à documentação e às credenciais, sem inventar endpoints. O MVP deve ter fila e painel próprios.

## Modelo de dados mínimo
users, departments, channels, conversations, messages, categories, knowledge_articles, troubleshooting_flows, tickets, ticket_events, satisfaction_ratings, integrations, working_hours, audit_logs.

## Estados essenciais
Conversa: nova -> identificacao -> triagem -> orientacao -> resolvida OU escalada -> encerrada.
Chamado: aberto -> em_fila -> em_atendimento -> aguardando_usuario -> resolvido -> fechado. Permitir reabertura autorizada.

## Critérios de aceite
- Abrir URL e conseguir registrar um problema completo **sem WhatsApp configurado**.
- Usuário resolve via orientações e registra nota 1–5.
- Usuário não resolve, recebe protocolo e analista visualiza o chamado com histórico.
- Fora do horário o chamado fica pendente, sem perda de mensagens.
- Canal WhatsApp desligado não degrada o portal.
- Reenvio duplicado de webhook não duplica chamados ou mensagens.
- Analista e colaborador não conseguem acessar dados de outras pessoas indevidamente.
- Há instruções de instalação local, `.env.example`, seed, testes e README.

## Tarefa para execução pelo Claude Code
1. Inspecione o repositório e descreva o que já existe; não sobrescreva código sem necessidade.
2. Escreva um plano por fases (MVP portal, painel TI, base de conhecimento, WhatsApp, observabilidade).
3. Implemente primeiro **portal web + backend + banco + painel básico + testes**.
4. Crie interfaces de `ChannelAdapter`, `ConversationOrchestrator`, `TicketService`, `KnowledgeService` e `WorkingHoursService`.
5. Adicione um adaptador `WebChannel`; deixe `WhatsAppChannel` atrás de feature flag, com mock para testes e sem exigir credenciais para executar localmente.
6. Apresente migrações, arquitetura, comandos de execução e testes; rode e corrija os testes disponíveis.
7. Não prometa integrações reais não configuradas. Pergunte por credenciais e documentação apenas quando chegar à fase de ativá-las.

## Decisões de produto
- Canal primário: URL da central de TI.
- Canal secundário: WhatsApp, quando a conexão estiver operacional.
- Gestão central: mesma plataforma e mesmo histórico de tickets.
- Atendimento automatizado não significa que a IA tenha permissão para executar comandos administrativos ou acessar sistemas internos: essas ações exigem integrações aprovadas, autorização e trilha de auditoria.
