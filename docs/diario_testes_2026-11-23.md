# Diário de testes: Central de TI (chatbot_ti)

**Data:** 23/11/2026
**Ambiente:** Windows 11 Pro · Python 3.14.8 · Django 5.2.19 · SQLite (banco de teste criado e destruído a cada execução)
**Comando:** `.venv\Scripts\python.exe manage.py test apps`
**Resultado final:** ✅ **55 de 55 testes aprovados** (13,4 s)
**Log completo da execução final:** [diario_testes_2026-11-23_log.txt](diario_testes_2026-11-23_log.txt)

---

## 1. Histórico das execuções

| # | Horário | O que foi testado | Resultado |
|---|---|---|---|
| 1 | ~15:25 | Versão original do projeto (só WhatsApp/Digisac), logo após a instalação | ✅ 25/25 aprovados |
| 2 | 16:02 | Primeira execução após a Fase 1 (portal web, chamados, painel) | ⚠️ 54 aprovados, **1 erro** |
| 3 | 16:03 | Depois da correção do erro | ✅ 55/55 aprovados |
| 4 | 16:04 | Teste de ponta a ponta no servidor real (chat pelo HTTP) | ✅ chamado `TI-2026-000001` aberto |
| 5 | 16:04 | Teste do painel no servidor real (login, fila, detalhe, arquivos estáticos) | ✅ tudo respondendo |
| 6 | 16:05 | Execução final, detalhada (`-v 2`), que gerou este diário | ✅ 55/55 aprovados |

### Execução 2: o erro e a correção

- **Teste:** `test_resposta_do_analista_aparece_no_chat` (portal).
- **Erro:** `Chamado.DoesNotExist`. O teste esperava um chamado aberto, mas nenhum foi criado.
- **Causa:** o próprio teste estava errado, não o sistema. Ele enviou a primeira mensagem sem antes
  abrir o chat. Sem a saudação inicial, o nome digitado foi tratado como "oi", e as respostas
  seguintes ficaram desalinhadas, uma etapa atrás. No uso real o navegador sempre abre o chat
  antes de enviar algo.
- **Correção:** o teste passou a abrir o chat antes, como o navegador faz. Nenhum código do
  sistema foi alterado.
- **Ajuste junto:** o comando `popular_orientacoes` deixou de imprimir mensagens quando chamado em
  modo silencioso, o que limpou a saída dos testes.

### Execução 4: teste de ponta a ponta no servidor real

Conversa simulada pelo HTTP, como um navegador faria, em `http://127.0.0.1:8000/`:

| Colaborador digitou | Assistente respondeu |
|---|---|
| (abriu a página) | "Olá! 👋 Eu sou o assistente virtual da Central de TI…" + pede o nome completo |
| Teste Automatico | "Prazer, Teste! Em qual setor/departamento você trabalha?" |
| TI | "Qual é o seu e-mail corporativo?" |
| teste@mensori.com.br | Menu "Como posso te ajudar?" |
| **erro de acesso** (texto livre) | "Encontrei estas orientações. Qual descreve melhor a sua situação?" |
| 1 | Passo a passo + "Seu problema foi resolvido?" |
| 2 (não resolveu) | "Vou abrir um chamado para a equipe de TI. 📝 Descreva…" |
| pular | "✅ Abri o chamado **TI-2026-000001** para a equipe de TI." |

Faixa no topo do chat: `TI-2026-000001 · Em fila · prioridade média`.
`/painel/` sem login redirecionou para a tela de login (302).

### Execução 5: painel no servidor real

| Verificação | Resultado |
|---|---|
| `chat.css`, `chat.js`, `painel.css` | 200 (carregando) |
| Login com o usuário `colaborador` | 200, e a fila mostra `TI-2026-000001` |
| Detalhe do chamado | 200, mostra o colaborador e o relato "erro de acesso" |

> O chamado `TI-2026-000001` ("Teste Automatico") ficou no banco local como exemplo. Pode ser
> apagado em Admin > Chamados.

---

## 2. O que cada teste verifica (execução final)

### Motor da conversa: 25 testes (`apps/bot/tests/test_engine.py`)

| Grupo | Teste | Verifica que… | Resultado |
|---|---|---|---|
| Identificação | `test_pede_nome_setor_email_e_mostra_menu` | pede nome, setor e e-mail, nessa ordem, e mostra o menu | ✅ |
| | `test_email_de_outro_dominio_e_recusado` | recusa e-mail fora do domínio configurado (ex.: @gmail) | ✅ |
| | `test_identificacao_configuravel_com_matricula` | aceita matrícula no lugar do e-mail, se configurado | ✅ |
| | `test_nome_invalido` | recusa nome inválido (ex.: "12") | ✅ |
| | `test_colaborador_conhecido_vai_direto_ao_menu` | quem já se identificou não precisa repetir os dados | ✅ |
| Resolvido | `test_resolve_avalia_e_encerra` | resolveu → avaliação de 1 a 5 → encerra como "resolvida" | ✅ |
| | `test_sim_por_texto` | entende "sim" escrito, além do número | ✅ |
| Não resolvido | `test_pede_descricao_e_abre_chamado_com_resumo` | não resolveu → pede descrição → abre chamado com categoria, prioridade e resumo | ✅ |
| | `test_nao_por_texto` | entende "não" escrito | ✅ |
| | `test_com_chamado_aberto_bot_fica_em_silencio` | com chamado aberto, o assistente não interfere (a TI responde) | ✅ |
| | `test_fora_do_horario_informa_janela_configurada` | fora do horário, informa a janela **configurada** (sem inventar prazo) | ✅ |
| | `test_categoria_sem_orientacao_vai_direto_para_chamado` | "Outros assuntos" leva direto ao chamado | ✅ |
| | `test_solicitacao_de_acesso_sempre_abre_chamado` | pedido de acesso explica o processo e abre chamado | ✅ |
| Crítico | `test_seguranca_escala_na_hora_com_prioridade_critica` | phishing: só avisos seguros + chamado **crítico** na hora, sem perguntar se resolveu | ✅ |
| | `test_texto_livre_de_phishing_escala` | "recebi um email de phishing" (texto livre) também escala | ✅ |
| Texto livre | `test_erro_de_acesso_sugere_orientacoes` | "erro de acesso" → sugere as orientações de senha/conta/MFA | ✅ |
| | `test_descricao_clara_vai_direto_para_a_orientacao` | "a impressora não imprime" → vai direto ao procedimento certo | ✅ |
| | `test_relato_vira_descricao_sem_repetir` | o que o colaborador já escreveu vira a descrição do chamado | ✅ |
| | `test_sem_resultado_conta_como_tentativa` | texto sem correspondência mostra o menu de novo | ✅ |
| Navegação | `test_comandos_globais` | `menu`, `sair` e `analista` funcionam em qualquer etapa | ✅ |
| | `test_ver_outra_orientacao` | opção "ver outra orientação deste assunto" | ✅ |
| | `test_tres_opcoes_invalidas_oferece_chamado` | 3 respostas inválidas seguidas → oferece abrir chamado | ✅ |
| | `test_nao_muta_estado_de_entrada` | o motor não altera o estado recebido (segurança interna) | ✅ |
| Dados sensíveis | `test_remove_senha_codigo_e_cpf` | remove senha, código de verificação e CPF digitados | ✅ |
| | `test_mantem_frases_normais` | **não** apaga frases inocentes ("minha senha de rede", código de erro `0x80070005`) | ✅ |

### Orquestrador (banco + chamados + canais): 11 testes (`apps/bot/tests/test_orquestrador.py`)

| Teste | Verifica que… | Resultado |
|---|---|---|
| `test_resolvido_registra_avaliacao_e_encerra` | grava a nota, a métrica "resolveu" e encerra; nenhum chamado criado | ✅ |
| `test_nao_resolvido_abre_chamado_com_protocolo` | chamado `TI-AAAA-NNNNNN` com descrição, categoria, prioridade, resumo e dados do colaborador | ✅ |
| `test_incidente_critico_tem_prioridade_critica` | incidente de segurança grava prioridade crítica | ✅ |
| `test_fora_do_horario_fica_na_fila_sem_perder_mensagens` | fora do horário: chamado na fila, e mensagens posteriores ficam no chamado | ✅ |
| `test_mensagem_repetida_nao_duplica` | a mesma mensagem enviada duas vezes é gravada uma vez só | ✅ |
| `test_chamado_nao_duplica_na_mesma_conversa` | não abre dois chamados para o mesmo atendimento | ✅ |
| `test_falha_do_whatsapp_nao_perde_mensagens` | provedor fora do ar: nada é perdido e o sistema não trava ¹ | ✅ |
| `test_canal_whatsapp_desligado_nao_afeta_o_portal` | WhatsApp desligado: o portal funciona normalmente | ✅ |
| `test_analista_responde_e_resolve` | analista responde e resolve, o colaborador recebe a solução e o novo atendimento reaproveita a identificação | ✅ |
| `test_senha_nao_e_gravada` | senha digitada não vai para o banco nem para o chamado, e o colaborador é avisado | ✅ |
| `test_conversa_inativa_expira` | após 30 min sem resposta, o atendimento recomeça | ✅ |

¹ A linha `ERROR apps.canais.whatsapp: Falha ao enviar mensagem pelo WhatsApp` no log é
**esperada**: o teste simula de propósito o provedor fora do ar e confirma que o erro é
registrado sem derrubar o atendimento.

### Portal web: 7 testes (`apps/portal/tests.py`)

| Teste | Verifica que… | Resultado |
|---|---|---|
| `test_pagina_abre` | a página do chat abre e entrega o cookie de proteção (CSRF) | ✅ |
| `test_fluxo_completo_ate_o_protocolo` | **critério de aceite:** registrar um problema completo pela URL, sem WhatsApp | ✅ |
| `test_colaborador_nao_ve_conversa_de_outro` | um navegador não vê as mensagens de outro | ✅ |
| `test_clique_duplo_nao_duplica` | clique duplo no "enviar" não duplica a mensagem | ✅ |
| `test_validacao_de_entrada` | recusa mensagem vazia, longa demais (mais de 2000 caracteres) ou malformada | ✅ |
| `test_limite_de_mensagens` | bloqueia excesso de mensagens por minuto (proteção contra abuso) | ✅ |
| `test_resposta_do_analista_aparece_no_chat` | a resposta do analista aparece no chat do colaborador, com o nome dele | ✅ |

### Painel de TI: 4 testes (`apps/painel/tests.py`)

| Teste | Verifica que… | Resultado |
|---|---|---|
| `test_exige_login` | sem login, redireciona para a tela de entrada | ✅ |
| `test_usuario_sem_perfil_nao_acessa` | usuário sem perfil de TI recebe "acesso negado" (403) | ✅ |
| `test_analista_ve_fila_e_historico` | o analista vê a fila e o histórico completo da conversa | ✅ |
| `test_atender_responder_e_resolver` | assumir → responder → aguardar o colaborador → resolver (solução obrigatória) → reabrir | ✅ |

### WhatsApp / Digisac: 8 testes (`apps/digisac/tests.py`, `apps/bot/tests/test_webhook.py`)

| Teste | Verifica que… | Resultado |
|---|---|---|
| `test_exige_token` | webhook sem o token correto é recusado (403) | ✅ |
| `test_canal_desligado_ignora` | com o WhatsApp desligado, o webhook responde OK e não cria nada | ✅ |
| `test_reenvio_do_webhook_nao_duplica` | **critério de aceite:** reenvio do mesmo webhook não duplica mensagens | ✅ |
| `test_mensagem_do_colaborador` | lê corretamente a mensagem enviada pelo provedor | ✅ |
| `test_mensagem_do_atendente_ou_bot` | ignora mensagens enviadas pela própria empresa | ✅ |
| `test_fechamento_de_ticket` | reconhece mensagens de sistema do provedor | ✅ |
| `test_outros_eventos_e_lixo` | ignora eventos desconhecidos e dados inválidos | ✅ |
| `test_lista_de_mensagens` | processa várias mensagens num mesmo envio | ✅ |

---

## 3. Critérios de aceite da especificação

| Critério | Coberto por | Situação |
|---|---|---|
| Abrir a URL e registrar um problema completo sem WhatsApp | `test_fluxo_completo_ate_o_protocolo` + execução 4 | ✅ |
| Resolver pelas orientações e registrar nota de 1 a 5 | `test_resolvido_registra_avaliacao_e_encerra` | ✅ |
| Não resolver, receber protocolo, e o analista ver o chamado com histórico | `test_nao_resolvido_abre_chamado_com_protocolo`, `test_analista_ve_fila_e_historico` | ✅ |
| Fora do horário: chamado pendente sem perda de mensagens | `test_fora_do_horario_fica_na_fila_sem_perder_mensagens` | ✅ |
| WhatsApp desligado não degrada o portal | `test_canal_whatsapp_desligado_nao_afeta_o_portal`, `test_canal_desligado_ignora` | ✅ |
| Webhook reenviado não duplica | `test_reenvio_do_webhook_nao_duplica`, `test_mensagem_repetida_nao_duplica` | ✅ |
| Ninguém acessa dados de outras pessoas indevidamente | `test_colaborador_nao_ve_conversa_de_outro`, `test_usuario_sem_perfil_nao_acessa` | ✅ |
| Instruções de instalação, `.env.example`, seed, testes e README | README.md, `.env.example`, `popular_orientacoes` | ✅ |

---

## 4. O que ainda não é testado (fases seguintes)

- Visual do chat no navegador (layout no celular, botões de resposta rápida). Foi verificado só
  pelo HTTP, sem abrir um navegador de verdade.
- Envio real pelo Digisac. Só simulado, porque não há credenciais.
- Retentativas de envio do WhatsApp, versões dos artigos, retenção e remoção de dados (LGPD) e
  acompanhamento por protocolo com validação por e-mail: ainda não implementados (Fases 2 a 5 do
  README).
