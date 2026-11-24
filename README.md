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
| `/painel/whatsapp/` | Analistas: simulador do WhatsApp (prévia da conversa no celular, sem enviar nada) |
| `/admin/` | Administradores: base de conhecimento, usuários, perfis, conversas, métricas |
| `/webhooks/digisac/?token=...` | Provedor de WhatsApp (só com `WHATSAPP_ATIVO=true`) |

Os endereços acima são relativos ao computador onde a Central roda (ex.: `http://127.0.0.1:8000/`
nele mesmo). Para os colegas acessarem pela rede, veja o passo
[8. Acesso dos colegas pela rede](#8-acesso-dos-colegas-pela-rede).

## Fluxo (BPMN)

```
identificação (nome, setor, centro de custo, e-mail) ──▶ menu de categorias  ou  texto livre ("erro de acesso")
        ──▶ orientação passo a passo ──▶ "Seu problema foi resolvido?"
              ├─ Sim ──▶ avaliação 1 a 5 ──▶ encerra (resolvido no autoatendimento)
              └─ Não ──▶ descrição ──▶ CHAMADO TI-AAAA-NNNNNN ──▶ dentro do horário? fila + analista
                                                                     fora? fila + janela configurada
incidente crítico/segurança ──▶ avisos seguros ──▶ chamado com prioridade CRÍTICA na hora
```

- Identificação: nome, setor, **centro de custo** e e-mail, cada um num campo separado. Eles vão
  para o chamado, o painel (coluna "Centro de custo", busca e detalhe), o Admin (com filtro) e o
  Excel. Quem já tinha se identificado antes responde só o centro de custo. Os campos e a ordem
  ficam em `CENTRAL_IDENTIFICACAO` no `.env` (opções: `nome`, `setor`, `centro_custo`, `email`,
  `matricula`).
- `menu`, `sair` e `analista` funcionam em qualquer etapa; `0` abre chamado.
- 3 respostas inválidas seguidas: o assistente oferece abrir chamado.
- Com o chamado aberto, as mensagens do colaborador vão para o chamado; a TI responde pelo painel
  e a resposta aparece no chat. Ao resolver, o colaborador recebe a solução e a
  **pesquisa de satisfação** (veja [SLA e pesquisa de satisfação](#sla-e-pesquisa-de-satisfação)).
- O assistente nunca pede senha nem código MFA. Senhas, códigos de verificação e CPF digitados são
  removidos antes de gravar.
- 30 minutos sem resposta: o atendimento recomeça (a identificação é mantida). A pesquisa de
  satisfação espera mais: 72 horas (`BOT_PESQUISA_HORAS`).

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

## SLA e pesquisa de satisfação

### SLA dos chamados

Todo chamado recebe, na abertura, o SLA da sua categoria, em **horas úteis**: só conta o horário de
atendimento (`BOT_HORARIO_*`, padrão segunda a sexta, das 8h às 18h) e **não contam os feriados**.
Um chamado aberto às 20h começa a contar às 8h do próximo dia útil.

| Opção | Categoria | SLA (horas úteis) | Por quê |
|---|---|---|---|
| 1 | 🔐 Acesso e login | 8h | Sem login o colaborador não trabalha |
| 8 | 🚨 Segurança e incidentes | 8h | Risco para a empresa, precisa de ação rápida |
| 3 | 📶 Internet, rede e VPN | 8h | Normalmente impede todo o trabalho |
| 4 | 📧 E-mail e Microsoft 365 | 16h | Afeta a rotina, mas costuma haver alternativa (webmail, celular) |
| 6 | 🧩 Sistemas internos | 16h | Pode depender de terceiros ou do fornecedor do sistema |
| 2 | 💻 Computador lento ou travando | 24h | Atrapalha, mas o trabalho geralmente continua |
| 5 | 🖨️ Impressora | 24h | Quase sempre há outra impressora disponível |
| 7 | 🔑 Solicitação de acesso | 40h | Depende da aprovação do gestor: é uma requisição, não um incidente |
| 9 | ✍️ Outros assuntos | 72h | Precisa de triagem; a TI pode reclassificar e o SLA muda |
| 0 | 🙋 Falar com a equipe de TI | da categoria escolhida | Sem categoria, vale o de "Outros" (72h, `SLA_PADRAO_HORAS`) |

**Cores no painel** (fila, detalhe do chamado e Admin):

| Cor | Quando |
|---|---|
| 🟢 Verde, "No prazo" | menos da metade do SLA consumida |
| 🟡 Amarelo, "Atenção" | metade do SLA (50%) ou mais já consumida |
| 🔴 Vermelho, "Vencido" | o prazo do SLA passou |

- A fila mostra a cor e o percentual de cada chamado, tem o filtro **SLA** e um aviso com quantos
  chamados abertos estão com o SLA vencido.
- No detalhe do chamado ficam o prazo, o percentual consumido, as horas que faltam e uma barra de
  progresso.
- **Reclassificar:** no detalhe do chamado (ou no Admin), troque a categoria. O SLA passa a ser o
  da nova categoria, contado desde a abertura, e a troca fica no histórico.
- Quando o chamado é resolvido, o SLA congela: **Cumprido** (resolvido no prazo) ou **Vencido**.
- Para mudar os prazos: Admin → **Categorias** → coluna "SLA (horas úteis)". Vale para os chamados
  abertos depois da mudança, ou para os que forem reclassificados.
- O tempo em "Aguardando colaborador" continua contando no SLA.

**Feriados:** os feriados nacionais de 2025 a 2030 já vêm cadastrados (Confraternização Universal,
Sexta-feira Santa, Tiradentes, Dia do Trabalho, Independência, Nossa Senhora Aparecida, Finados,
Proclamação da República, Consciência Negra e Natal). No Admin, em **Chamados → Feriados**, dá para:

- incluir os **estaduais, municipais e pontos facultativos** em que a empresa não trabalha
  (ex.: Carnaval, Corpus Christi, aniversário da cidade);
- apagar um feriado em que a empresa trabalha.

A mudança vale na hora para o cálculo das cores e do percentual. Para cadastrar os nacionais de mais
anos: `python manage.py carregar_feriados --ano 2031` (sem `--ano`, carrega o ano atual e os 4 seguintes).

### Pesquisa de satisfação

Quando a TI resolve o chamado no painel, o colaborador recebe no chat (portal ou WhatsApp) a solução
e, em seguida, a pesquisa:

```
📋 Pesquisa de satisfação do chamado TI-2026-000123
Como você avalia o atendimento da TI?

1 - 🤩 Muito satisfeito
2 - 🙂 Satisfeito
3 - 🙁 Insatisfeito
4 - 😞 Muito insatisfeito
```

- Depois da resposta, o assistente pede uma **observação**:
  - **Insatisfeito** e **Muito insatisfeito**: a observação é **obrigatória**. O assistente não
    aceita resposta vazia nem "pular" e pede de novo.
  - **Satisfeito** e **Muito satisfeito**: a observação é opcional (responda *pular*).
- O colaborador também pode responder *pular* na primeira pergunta para não participar.
- A pesquisa espera a resposta por 72 horas (`BOT_PESQUISA_HORAS`). Depois disso, a próxima
  mensagem abre um novo atendimento.
- Onde ver as respostas: no detalhe do chamado no painel (com destaque nas negativas), na coluna
  "Responsável" da fila, no histórico do chamado e no Admin, em **Pesquisas de satisfação** (com
  filtro por resposta e data).

### Exportar os chamados para Excel

Na fila do painel, o botão **⬇ Exportar Excel** baixa uma planilha (`.xlsx`) com os chamados do
**filtro que está na tela**: aba de status (Abertos, Em atendimento, Fechado... ou **Todos**),
prioridade, SLA (no prazo, atenção, vencido), busca e "só os meus". A planilha não tem o limite de
300 linhas da tela.

| Coluna | Conteúdo |
|---|---|
| Número do chamado | Protocolo (ex.: TI-2026-000123) |
| Colaborador | Nome de quem abriu |
| Centro de custo | Centro de custo informado pelo colaborador |
| Assunto | Categoria (ou "Sem categoria") |
| Status | Em fila, Em atendimento, Aguardando colaborador, Resolvido, Fechado... |
| SLA | No prazo, Atenção, Vencido ou Cumprido, com a cor verde, amarela ou vermelha |
| SLA (horas úteis), SLA consumido (%), Prazo do SLA | Detalhes do SLA |
| Responsável | Analista que assumiu |
| Canal | Portal web ou WhatsApp |
| Aberto em | Data e hora de abertura |
| Data do fechamento | Quando foi resolvido (vazio se ainda está aberto) |
| Pesquisa de satisfação | Muito satisfeito, Satisfeito, Insatisfeito ou Muito insatisfeito |
| Observação da pesquisa | O que o colaborador escreveu |

A planilha tem duas abas:

- **Dashboard** (abre primeiro), nas cores Mensori:
  - **filtros** no topo (campos verdes): **Qualidade do atendimento** (Muito satisfeito, Satisfeito,
    Insatisfeito, Muito insatisfeito, Sem resposta), **Situação do SLA** e **Status**. Ao trocar um
    filtro, todos os números e gráficos se recalculam na hora;
  - **indicadores**: chamados, em aberto, SLA vencido, pesquisas respondidas e % de satisfação;
  - **Chamados por centro de custo** (tabela + gráfico de barras);
  - **Qualidade do atendimento** e **Situação do SLA** (tabelas + gráficos de rosca);
  - **Chamados por assunto** (tabela + gráfico de barras);
  - **Qualidade do atendimento por centro de custo**: quantas avaliações de cada tipo cada centro
    de custo deu, com verde nos satisfeitos e vermelho nos insatisfeitos.
- **Chamados**: uma linha por chamado, com filtro em cada coluna e a primeira linha congelada.

Os números do Dashboard são fórmulas do próprio Excel sobre a aba Chamados (sem macros). As datas
estão no horário de Brasília. Pronto para imprimir em paisagem, uma seção inteira por página.

A avaliação de 1 a 5 continua existindo só para os casos **resolvidos no autoatendimento**, sem
chamado.

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
portal funciona normalmente.

### Simulador do WhatsApp (sem Digisac)

No painel, menu **Simulador do WhatsApp** (`/painel/whatsapp/`): um celular na tela mostra a conversa
exatamente como o colaborador vai ver no WhatsApp, com negrito, itálico, opções numeradas (sem botões)
e a resposta do analista com o nome na frente. Nada é enviado a nenhum celular.

- Cada mensagem digitada vira um evento do Digisac (`message.created`) e passa pelo mesmo motor e
  pelo mesmo canal WhatsApp da produção.
- Os chamados abertos ali aparecem na fila com o canal `whatsapp` e a marca **🧪 simulador**. Responda
  e resolva pelo painel: a resposta, a solução e a pesquisa de satisfação chegam no "celular".
- **Novo contato** simula outro número. **Apagar testes** remove as conversas e os chamados do
  simulador (os reais não são afetados).
- Funciona com o WhatsApp ligado ou desligado.

### Ligar o WhatsApp de verdade (Digisac)

O que é preciso:

| Item | Onde conseguir |
|---|---|
| Conta no Digisac com uma conexão de WhatsApp ativa | Administrador do Digisac da empresa |
| `DIGISAC_URL` | Endereço da conta, ex.: `https://suaempresa.digisac.app` |
| `DIGISAC_TOKEN` | Digisac → Conta → API → **Tokens de acesso pessoal** |
| `DIGISAC_SERVICE_ID` (opcional) | ID da conexão de WhatsApp que o bot vai usar |
| Endereço público com **HTTPS** | Para o Digisac entregar as mensagens: servidor da empresa, Codespaces (porta pública) ou ngrok (só para teste) |

Passo a passo:

1. No `.env`, preencha `DIGISAC_URL`, `DIGISAC_TOKEN`, `DIGISAC_SERVICE_ID` e gere o
   `DIGISAC_WEBHOOK_TOKEN` (`python -c "import secrets; print(secrets.token_urlsafe(32))"`).
   Deixe `WHATSAPP_ATIVO=true` e, no começo, `DIGISAC_ENVIAR_MENSAGENS=false` (só registra no log).
2. Confira: `python manage.py testar_digisac`. Ele mostra o que falta (`[FALTA]`) e a URL do webhook.
3. No Digisac, cadastre o webhook `https://SEU_ENDERECO/webhooks/digisac/?token=SEU_TOKEN` com o
   evento `message.created`, e **desative o robô nativo** do Digisac nessa conexão.
4. Reinicie a Central (`instalar_servico.ps1 -Reiniciar`) e mande um "oi" para o número da conexão.
   A conversa aparece no Admin, em **Conversas**, e o que o bot responderia aparece em
   `logs\servidor.log` (`[simulação] POST /api/v1/messages`).
5. Teste real de envio para um contato: `python manage.py testar_digisac --enviar-para ID_DO_CONTATO`
   (o ID aparece no log do webhook, campo `contactId`).
6. Tudo certo? Mude `DIGISAC_ENVIAR_MENSAGENS=true` e reinicie. A partir daí o bot responde no WhatsApp.

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
| 2. Painel TI | SLA por categoria (verde/amarelo/vermelho, sem feriados), pesquisa de satisfação e exportação para Excel ✅; atribuição a outro analista, notificações (e-mail/Teams), respostas prontas | em andamento |
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
