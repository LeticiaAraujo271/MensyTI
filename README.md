# Central de TI: atendimento multicanal (Django)

Chatbot corporativo de TI. O colaborador conversa pelo **portal web** (canal principal) ou,
opcionalmente, pelo **WhatsApp**. O assistente passa os **procedimentos padrão de primeiro
atendimento** e, se o problema não for resolvido, **abre um chamado com protocolo** que a equipe
atende pelo **painel de TI**. Conversas e chamados ficam no mesmo banco, qualquer que seja o canal.

- Processo de referência: [docs/Central_TI_Multicanal_Bizagi.bpmn](docs/Central_TI_Multicanal_Bizagi.bpmn)
- Especificação: [docs/especificacao.md](docs/especificacao.md)

| Endereço | Para quem |
|---|---|
| `/` | Colaborador: chat da Central de TI (celular e desktop) |
| `/painel/` | Analistas: fila, atendimento, resposta, solução |
| `/admin/` | Administradores: base de conhecimento, usuários, perfis, conversas, métricas |
| `/webhooks/digisac/?token=...` | Provedor de WhatsApp (só com `WHATSAPP_ATIVO=true`) |

## Fluxo (BPMN)

```
identificação (nome, setor, e-mail)  ──▶ menu de categorias  ou  texto livre ("erro de acesso")
        ──▶ orientação passo a passo ──▶ "Seu problema foi resolvido?"
              ├─ Sim ──▶ avaliação 1 a 5 ──▶ encerra (resolvido no autoatendimento)
              └─ Não ──▶ descrição ──▶ CHAMADO TI-AAAA-NNNNNN ──▶ dentro do horário? fila + analista
                                                                     fora? fila + janela configurada
incidente crítico/segurança ──▶ avisos seguros ──▶ chamado com prioridade CRÍTICA na hora
```

- `menu`, `sair` e `analista` funcionam em qualquer etapa; `0` abre chamado.
- 3 respostas inválidas seguidas: o assistente oferece abrir chamado.
- Com o chamado aberto, as mensagens do colaborador vão para o chamado; a TI responde pelo painel
  e a resposta aparece no chat. Ao resolver, o colaborador recebe a solução.
- O assistente nunca pede senha nem código MFA. Senhas, códigos de verificação e CPF digitados são
  removidos antes de gravar.
- 30 minutos sem resposta: o atendimento recomeça (a identificação é mantida).

## Arquitetura

```
apps/bot/engine.py            Motor da conversa: Python puro, sem Django e sem canal (testável)
apps/bot/orquestrador.py      ConversationOrchestrator: motor + banco + chamados + canais
apps/bot/horario.py           WorkingHoursService: janela de atendimento configurada
apps/orientacoes/servicos.py  KnowledgeService: só conteúdo ativo e aprovado da base
apps/chamados/servicos.py     TicketService: protocolo, prioridade, status, eventos (auditoria)
apps/canais/                  ChannelAdapter, WebChannel e WhatsAppChannel (atrás de WHATSAPP_ATIVO)
apps/portal/                  Chat web (HTML/CSS/JS sem build) + API JSON
apps/painel/                  Painel dos analistas (login + permissão)
apps/digisac/                 Cliente da API e webhook do provedor de WhatsApp
```

Modelos: `Colaborador`, `Conversa` (um atendimento por canal), `Mensagem` (colaborador, bot,
analista, sistema), `Chamado` + `EventoChamado`, `Categoria` + `Orientacao`, `OrientacaoVista`,
`Avaliacao`.

Status do chamado: `aberto → em_fila → em_atendimento ⇄ aguardando_usuario → resolvido → fechado`
(resolvido ou fechado pode ser **reaberto** no painel).

## Instalação (Windows / PowerShell)

**Jeito rápido:** na pasta do projeto, rode
`powershell -ExecutionPolicy Bypass -File .\iniciar.ps1`. Na primeira vez, o script cria o
ambiente, instala as dependências, prepara o banco, pede o usuário administrador e liga o servidor.
Nas próximas vezes, ele só liga o servidor.

Passo a passo manual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env            # ajuste se quiser; os padrões já funcionam localmente

.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py popular_orientacoes   # base de conhecimento inicial
.venv\Scripts\python.exe manage.py configurar_perfis     # grupos Analista / Administrador de TI
.venv\Scripts\python.exe manage.py createsuperuser
.venv\Scripts\python.exe manage.py runserver
```

Abra <http://127.0.0.1:8000/> (chat) e <http://127.0.0.1:8000/painel/> (equipe).
No Linux/macOS, use `.venv/bin/python` e `cp`.

### Equipe de TI

No Admin, em **Usuários**, crie o usuário de cada analista e coloque no grupo **Analista de TI**
(painel) ou **Administrador de TI** (painel + base de conhecimento). Para entrar no `/admin/`,
marque também "Membro da equipe".

### Testes

```powershell
.venv\Scripts\python.exe manage.py test apps
```

Cobrem os ramos resolvido e não resolvido, incidente crítico, fora do horário (sem perder
mensagens), texto livre, falha e desligamento do WhatsApp, webhook e clique duplicados, isolamento
entre colaboradores, permissões do painel e remoção de senhas.

Para conversar pelo terminal: `.venv\Scripts\python.exe manage.py simular_conversa --novo`

## Base de conhecimento

Fica no Admin, em **Orientações**. Um passo por linha. Alguns campos mudam o comportamento:

- **Palavras-chave**: ajudam a achar a orientação quando o colaborador escreve com as próprias palavras.
- **Prioridade crítica**: mostra os avisos e abre o chamado na hora (phishing, vírus, indisponibilidade geral).
- **Sempre abre chamado**: para pedidos que a TI precisa executar (ex.: solicitação de acesso).
- Uma categoria sem orientações (ex.: "Outros assuntos") leva direto ao chamado.

> ⚠️ Substitua os textos entre `[colchetes]` (links, nomes de sistemas, e-mail da segurança) pelos
> dados reais. O assistente só mostra o que estiver cadastrado; ele não inventa procedimentos.

## WhatsApp (opcional)

Fica desligado por padrão (`WHATSAPP_ATIVO=false`). Nesse caso o webhook ignora as mensagens e o
portal funciona normalmente. Para ativar, quando houver as credenciais:

1. No `.env`: `WHATSAPP_ATIVO=true`, `DIGISAC_URL`, `DIGISAC_TOKEN`, `DIGISAC_SERVICE_ID`,
   `DIGISAC_WEBHOOK_TOKEN`. Comece com `DIGISAC_ENVIAR_MENSAGENS=false`, que só registra no log.
2. Cadastre o webhook `https://SEU_DOMINIO/webhooks/digisac/?token=...` com o evento `message.created`.
3. Desative o robô nativo do Digisac nessa conexão.

Confirme as rotas da API na documentação da sua conta antes de ativar
([apps/digisac/client.py](apps/digisac/client.py)). O atendimento humano acontece no painel da Central.

## Fases

| Fase | Escopo | Situação |
|---|---|---|
| 1. MVP portal | Chat web, identificação, base, texto livre, chamado com protocolo/prioridade, painel básico, perfis, testes | ✅ feito |
| 2. Painel TI | Atribuição a outro analista, SLA, notificações (e-mail/Teams), respostas prontas | a fazer |
| 3. Base de conhecimento | Versões e aprovação de artigos, horários e feriados editáveis no Admin, dashboard de métricas | a fazer |
| 4. WhatsApp | Fila de envio com retentativas e backoff, indicador de saúde, link do portal quando o canal cair | a fazer |
| 5. Segurança e LGPD | Retenção configurável, exportação e remoção de dados, auditoria de acessos, acompanhamento do chamado por protocolo com validação por e-mail, limites contra abuso por IP | a fazer |

## Produção

- `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY` forte, `DJANGO_ALLOWED_HOSTS` e
  `DJANGO_CSRF_TRUSTED_ORIGINS` com o domínio, e HTTPS obrigatório.
- PostgreSQL: preencha `DB_NAME` etc.
- Arquivos estáticos: rode `manage.py collectstatic` e sirva `staticfiles/` pelo servidor web
  (ou adicione o WhiteNoise).
- Linux: `gunicorn config.wsgi`.
