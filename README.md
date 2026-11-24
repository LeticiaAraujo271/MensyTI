# Central de TI: atendimento multicanal (Django)

Chatbot corporativo de TI. O colaborador conversa pelo **portal web** (canal principal) ou,
opcionalmente, pelo **WhatsApp**. O assistente passa os **procedimentos padrão de primeiro
atendimento** e, se o problema não for resolvido, **abre um chamado com protocolo** que a equipe
atende pelo **painel de TI**. Conversas e chamados ficam no mesmo banco, qualquer que seja o canal.

- Processo de referência: [docs/Central_TI_Multicanal_Bizagi.bpmn](docs/Central_TI_Multicanal_Bizagi.bpmn)
- Especificação: [docs/especificacao.md](docs/especificacao.md)

O chat e o painel têm um fundo em marca d'água (roçadeira e trator de roçada) em
[apps/portal/static/marca/](apps/portal/static/marca/). Para incluir o **logo oficial da Mensori**,
coloque o arquivo como `logo.svg` ou `logo.png` nessa pasta e religue a Central
(`instalar_servico.ps1 -Reiniciar`): ele aparece no topo do chat, na barra do painel e clarinho no fundo.

| Endereço | Para quem |
|---|---|
| `/` | Colaborador: chat da Central de TI (celular e desktop) |
| `/painel/` | Analistas: fila, atendimento, resposta, solução |
| `/admin/` | Administradores: base de conhecimento, usuários, perfis, conversas, métricas |
| `/webhooks/digisac/?token=...` | Provedor de WhatsApp (só com `WHATSAPP_ATIVO=true`) |

Os endereços acima são relativos ao computador onde a Central roda (ex.: `http://127.0.0.1:8000/`
nele mesmo). Para os colegas acessarem pela rede, veja o passo
[8. Acesso dos colegas pela rede](#8-acesso-dos-colegas-pela-rede).

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
apps/portal/static/marca/     Marca d'água do chat e do painel (roçadeira, trator) e lugar do logo oficial
servir.py                     Servidor Waitress (Windows) usado pela tarefa em segundo plano
instalar_servico.ps1          Instala/controla a tarefa "Central de TI" (-Status, -Reiniciar, -Rede, -Remover)
```

Modelos: `Colaborador`, `Conversa` (um atendimento por canal), `Mensagem` (colaborador, bot,
analista, sistema), `Chamado` + `EventoChamado`, `Categoria` + `Orientacao`, `OrientacaoVista`,
`Avaliacao`.

Status do chamado: `aberto → em_fila → em_atendimento ⇄ aguardando_usuario → resolvido → fechado`
(resolvido ou fechado pode ser **reaberto** no painel).

## Abrir pelo GitHub (sem instalar nada)

[![Abrir no GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/gz5n88ks84-glitch/MensyTI?quickstart=1)

O **GitHub Codespaces** liga a Central num computador do próprio GitHub e abre a tela no navegador,
de qualquer lugar (inclusive fora da rede da empresa).

1. Entre no GitHub com a conta que tem acesso ao repositório e clique no botão acima
   (ou, no repositório: **Code → Codespaces → Create codespace on main**).
2. Na primeira vez, espere de 2 a 4 minutos: ele instala tudo, cria o banco e o administrador.
3. A Central abre sozinha numa aba nova. Se não abrir: aba **PORTS** (embaixo) → linha
   **Central de TI (8000)** → ícone do globo 🌐.
4. O usuário e a senha do painel/admin ficam no arquivo **ACESSO_CODESPACE.txt**, que abre sozinho
   no editor (usuário `admin`). Troque a senha em `/admin/` → Usuários.

| Endereço | Para quem |
|---|---|
| `https://<seu-codespace>-8000.app.github.dev/` | Chat |
| `https://<seu-codespace>-8000.app.github.dev/painel/` | Painel de TI |
| `https://<seu-codespace>-8000.app.github.dev/admin/` | Administração |

**Mostrar para outras pessoas:** por padrão o link só abre para você (logado no GitHub). Para
outra pessoa abrir, na aba **PORTS**, clique com o botão direito na porta 8000 →
**Port Visibility → Public** e envie o link. Qualquer pessoa com o link abre a tela; volte para
**Private** quando terminar.

**Limites do Codespaces** (bom para testar e demonstrar, não para uso diário da empresa):

- ele **desliga sozinho depois de 30 minutos sem uso**; para voltar, abra
  <https://github.com/codespaces> e clique no codespace (os dados ficam guardados enquanto o
  codespace existir; apagar o codespace apaga o banco dele);
- a conta gratuita do GitHub tem uma cota mensal de horas de uso;
- o link muda se você criar outro codespace.

Para a Central ficar no ar o tempo todo, use o computador da empresa (passos 7 e 8 abaixo) ou um
servidor/nuvem (veja **Produção**).

## Como rodar no Windows (passo a passo)

### Pré-requisitos

- **Python 3.12 ou mais novo** (<https://www.python.org/downloads/>). Na instalação, marque
  **"Add python.exe to PATH"**. Confira no PowerShell: `python --version`.
- **Git** (<https://git-scm.com/download/win>). Confira: `git --version`.
- Para testar o webhook do WhatsApp: **ngrok** (<https://ngrok.com/download>), opcional.

Todos os comandos abaixo são para o **PowerShell**, rodados na pasta do projeto.

> **Jeito rápido:** depois de clonar (passo 1), rode
> `powershell -ExecutionPolicy Bypass -File .\iniciar.ps1`. Na primeira vez o script cria o
> ambiente, instala as dependências, cria o `.env` com uma chave secreta nova, prepara o banco, pede
> o usuário administrador e liga o servidor. Nas próximas vezes, ele só liga o servidor.
> Os passos 2 a 6 fazem a mesma coisa à mão.

### 1. Clonar o repositório

```powershell
git clone https://github.com/gz5n88ks84-glitch/MensyTI.git
cd MensyTI
```

### 2. Criar e ativar o ambiente virtual (venv)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

O começo da linha passa a mostrar `(.venv)`. Se aparecer o erro *"a execução de scripts foi
desabilitada neste sistema"*, libere só para esta janela e ative de novo:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

> Toda vez que abrir um PowerShell novo, ative o venv de novo (`.venv\Scripts\Activate.ps1`)
> antes de usar o `python manage.py`.

### 3. Instalar as dependências

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar o `.env`

As configurações e os segredos (chave do Django, tokens do Digisac) ficam no arquivo `.env`, lido
pelo [python-decouple](https://pypi.org/project/python-decouple/). Ele **não vai para o Git**; o
repositório só tem o modelo [.env.example](.env.example), sem valores reais.

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Abra o `.env` (`notepad .env`) e cole a chave gerada em `DJANGO_SECRET_KEY=`. Para rodar no seu
computador, o resto pode ficar como está. Principais variáveis:

| Variável | Para que serve |
|---|---|
| `DJANGO_SECRET_KEY` | **Obrigatória.** Chave secreta do Django; sem ela o projeto não sobe |
| `DJANGO_DEBUG` | `true` no seu computador, `false` em produção |
| `DJANGO_ALLOWED_HOSTS` | Endereços aceitos, separados por vírgula |
| `WHATSAPP_ATIVO` | `true` liga o canal WhatsApp (Digisac); com `false` o webhook ignora as mensagens |
| `DIGISAC_URL`, `DIGISAC_TOKEN` | Endereço da conta e token pessoal da API do Digisac |
| `DIGISAC_WEBHOOK_TOKEN` | Segredo que o Digisac manda na URL do webhook |
| `DIGISAC_ENVIAR_MENSAGENS` | `false` só registra as respostas no log, sem enviar ao WhatsApp |

As demais estão comentadas no próprio `.env.example`. Uma variável definida no sistema
(`$env:NOME = "valor"`) tem prioridade sobre o `.env`.

### 5. Criar o banco (migrate) e os dados iniciais

```powershell
python manage.py migrate
python manage.py popular_orientacoes   # base de conhecimento inicial
python manage.py configurar_perfis     # grupos Analista de TI / Administrador de TI
python manage.py createsuperuser       # seu usuário de administrador
```

Sem `DB_NAME` no `.env`, o banco é o SQLite (`db.sqlite3`, criado na pasta do projeto e fora do Git).

### 6. Ligar o servidor (runserver)

```powershell
python manage.py runserver
```

Abra <http://127.0.0.1:8000/> (chat), <http://127.0.0.1:8000/painel/> (equipe) e
<http://127.0.0.1:8000/admin/> (administração). `Ctrl+C` para parar.

No Linux/macOS, ative com `source .venv/bin/activate` e copie com `cp .env.example .env`.

> O `runserver` só funciona enquanto a janela dele estiver aberta. Para a Central ficar sempre no
> ar, use o passo 7.

### 7. Deixar a Central sempre ligada (segundo plano)

Para não depender de nenhuma janela, terminal ou editor aberto, instale a Central como tarefa do
Windows (não precisa ser administrador):

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar_servico.ps1
```

O script prepara o projeto (como o `iniciar.ps1`) e cria a tarefa agendada **"Central de TI"**,
que roda o [servir.py](servir.py) com o servidor **Waitress**, sem janela. A partir daí:

- a Central **liga sozinha sempre que você entra no Windows** e fica no ar até desligar o computador;
- pode fechar o PowerShell, o VS Code e tudo mais: <http://127.0.0.1:8000/> continua funcionando;
- se o servidor cair, o Windows tenta religar a cada minuto;
- os registros ficam em `logs\servidor.log` (e erros de inicialização em `logs\saida.log`).

| Comando (na pasta do projeto) | Para que serve |
|---|---|
| `powershell -ExecutionPolicy Bypass -File .\instalar_servico.ps1 -Status` | Mostra se a Central está no ar |
| `powershell -ExecutionPolicy Bypass -File .\instalar_servico.ps1 -Reiniciar` | Religa; use depois de mudar o `.env` ou atualizar o código (`git pull`) |
| `powershell -ExecutionPolicy Bypass -File .\instalar_servico.ps1 -Remover` | Desliga e tira da inicialização do Windows |

A tarefa também aparece no **Agendador de Tarefas** do Windows, com o nome "Central de TI".
Enquanto ela estiver ativa, não rode o `runserver` na mesma porta: use `-Remover` antes ou escolha
outra porta (`python manage.py runserver 8001`).

Para os colegas acessarem de outros computadores, veja o passo 8.

### 8. Acesso dos colegas pela rede

Por padrão, só o computador onde a Central está instalada abre os endereços
(`SERVIDOR_HOST=127.0.0.1`). Para os colegas usarem o chat e o painel pelo navegador deles, rode
**uma vez**, no computador da Central:

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar_servico.ps1 -Rede
```

O script:

1. descobre o IP deste computador na rede da empresa (ex.: `192.168.0.50`) e o nome dele;
2. ajusta o `.env`: `SERVIDOR_HOST=0.0.0.0`, coloca o IP e o nome em `DJANGO_ALLOWED_HOSTS`,
   `DJANGO_DEBUG=false` (ninguém vê detalhes técnicos de erro) e `DJANGO_COOKIES_SEGUROS=false`
   (o login do painel funciona em `http://` dentro da rede);
3. libera a porta 8000 no Firewall do Windows, só nas redes do domínio e privadas (nunca em Wi-Fi
   público). O Windows pede permissão de administrador uma vez; se você não tiver, o script mostra
   o comando para a equipe de TI rodar;
4. religa a Central e mostra os endereços para enviar aos colegas.

**O que os colegas fazem:** nada para instalar. Basta abrir no navegador (Chrome, Edge, celular no
Wi-Fi da empresa) o endereço que o script mostrou:

| Para quem | Endereço (exemplo) |
|---|---|
| Colaboradores (chat) | `http://192.168.0.50:8000/` ou `http://nome-do-computador:8000/` |
| Analistas de TI (painel) | `http://192.168.0.50:8000/painel/`, com o usuário criado no Admin (veja **Equipe de TI**) |
| Administradores | `http://192.168.0.50:8000/admin/` |

Para conferir se está tudo certo: `instalar_servico.ps1 -Status` neste computador e, em outro
computador da rede, `Test-NetConnection 192.168.0.50 -Port 8000` (deve mostrar
`TcpTestSucceeded : True`).

Se não abrir no computador do colega:

| Sintoma | O que fazer |
|---|---|
| "Não é possível acessar esse site" / demora e dá erro | A Central está desligada (`-Status`), o firewall não foi liberado (rode `-Rede` de novo) ou o colega não está na mesma rede/VPN |
| "Bad Request (400)" | O endereço usado não está em `DJANGO_ALLOWED_HOSTS`: rode `-Rede` de novo (ele acrescenta o IP atual) |
| Funcionava e parou depois de alguns dias | O IP deste computador mudou. Rode `-Rede` de novo e mande o endereço novo, ou use o endereço pelo nome do computador. Para não mudar mais, peça à equipe de redes um **IP fixo** (reserva no DHCP) para esta máquina |
| O login do painel volta para a tela de login | Confira `DJANGO_COOKIES_SEGUROS=false` no `.env` e rode `-Reiniciar` |

Para voltar a ser só local: no `.env`, `SERVIDOR_HOST=127.0.0.1`, e rode `-Reiniciar`.

> A Central só fica disponível enquanto este computador estiver ligado e com o usuário conectado
> no Windows. Para funcionar 24 horas, sem depender de um computador pessoal, publique em um
> servidor da empresa ou na nuvem (veja **Produção**).

### Problemas comuns

| Mensagem | O que fazer |
|---|---|
| `'python' não é reconhecido...` | Reinstale o Python marcando "Add python.exe to PATH", ou use `py` no lugar de `python` |
| `a execução de scripts foi desabilitada` | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| `No module named 'decouple'` (ou `'django'`) | O venv não está ativo: `.venv\Scripts\Activate.ps1` e `pip install -r requirements.txt` |
| `DJANGO_SECRET_KEY não definida` | Falta o `.env` ou a chave nele (passo 4) |
| `Invalid HTTP_HOST header` | Acrescente o endereço em `DJANGO_ALLOWED_HOSTS` no `.env` |
| `That port is already in use` | A tarefa "Central de TI" já está usando a 8000 (veja `-Status`), ou use outra porta: `python manage.py runserver 8001` |
| O link não abre ("não é possível acessar esse site") | O servidor está desligado: rode `instalar_servico.ps1 -Status` e, se preciso, `-Reiniciar` ou o passo 7 |

### Equipe de TI

No Admin, em **Usuários**, crie o usuário de cada analista e coloque no grupo **Analista de TI**
(painel) ou **Administrador de TI** (painel + base de conhecimento). Para entrar no `/admin/`,
marque também "Membro da equipe".

### Testes

```powershell
python manage.py test apps
```

Cobrem os ramos resolvido e não resolvido, incidente crítico, fora do horário (sem perder
mensagens), texto livre, falha e desligamento do WhatsApp, webhook e clique duplicados, isolamento
entre colaboradores, permissões do painel e remoção de senhas.

Para conversar pelo terminal: `python manage.py simular_conversa --novo`

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

### Testar o webhook no seu computador com o ngrok

O Digisac precisa de um endereço público com HTTPS para entregar as mensagens. O ngrok cria um
túnel da internet até o seu `runserver`.

1. Instale o ngrok, crie uma conta gratuita em <https://ngrok.com> e configure o seu token (uma vez só):

   ```powershell
   ngrok config add-authtoken SEU_TOKEN_DO_NGROK
   ```

2. Gere um segredo para o webhook:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   e ajuste o `.env`:

   ```ini
   WHATSAPP_ATIVO=true
   DIGISAC_WEBHOOK_TOKEN=cole-o-segredo-gerado
   DIGISAC_ENVIAR_MENSAGENS=false
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.ngrok-free.app
   ```

   Com `DIGISAC_ENVIAR_MENSAGENS=false` o bot só registra no log o que responderia: dá para testar
   sem mandar nada para o WhatsApp de ninguém.

3. Em um PowerShell (com o venv ativo), ligue o servidor: `python manage.py runserver 8000`.
   Em **outro** PowerShell, abra o túnel:

   ```powershell
   ngrok http 8000
   ```

   O ngrok mostra um endereço como `https://abcd-1234.ngrok-free.app` (no plano gratuito ele muda
   cada vez que o ngrok é aberto). Em <http://127.0.0.1:4040> dá para ver cada requisição que chegou.

4. Simule uma mensagem do Digisac (troque o endereço e o segredo):

   ```powershell
   $url = "https://abcd-1234.ngrok-free.app/webhooks/digisac/?token=SEU_SEGREDO"
   $corpo = @{
       event = "message.created"
       data  = @{ id = "teste-1"; contactId = "contato-teste"; type = "chat"; text = "oi";
                  isFromMe = $false; isFromBot = $false }
   } | ConvertTo-Json -Depth 5
   Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json; charset=utf-8" -Body $corpo
   ```

   Resposta esperada: `ok: True` e `processadas: 1`. A resposta do bot aparece no terminal do
   `runserver`, e a conversa fica no Admin, em **Conversas**. Para conferir a proteção, repita com
   um token errado: a resposta deve ser **403 (token inválido)**. Se vier
   `ignorado: canal WhatsApp desativado`, falta `WHATSAPP_ATIVO=true` (reinicie o `runserver`
   depois de mudar o `.env`).

5. Para receber mensagens reais, cadastre no Digisac o webhook
   `https://abcd-1234.ngrok-free.app/webhooks/digisac/?token=SEU_SEGREDO` com o evento
   `message.created` e mande uma mensagem para o número da conexão. Para o bot responder de
   verdade, preencha `DIGISAC_URL`, `DIGISAC_TOKEN` e `DIGISAC_SERVICE_ID` e mude
   `DIGISAC_ENVIAR_MENSAGENS=true`.

> O endereço do ngrok é público: deixe o túnel aberto só enquanto estiver testando e nunca publique
> o `DIGISAC_WEBHOOK_TOKEN`. Se ele vazar, gere outro e troque no `.env` e no Digisac.

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
- Arquivos estáticos: já são entregues pelo WhiteNoise (CSS/JS do chat, do painel e do Admin).
- Windows: `python servir.py` (Waitress) ou o `instalar_servico.ps1`; Linux: `gunicorn config.wsgi`.
- Com `DJANGO_DEBUG=false` os cookies de login passam a exigir HTTPS. Se for usar `false` em
  `http://` (ex.: só na rede interna), coloque também `DJANGO_COOKIES_SEGUROS=false`, senão o login
  do painel não funciona.
