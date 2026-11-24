"""
Conteúdo inicial da base de conhecimento (categorias do menu da especificação).

Carregue no banco com:  python manage.py popular_orientacoes
Depois disso, a equipe de TI edita tudo pelo Admin (/admin/).

IMPORTANTE: os textos entre [colchetes] precisam ser substituídos pelos dados reais
da empresa (links, nomes de sistemas, ramais). O assistente não inventa procedimentos:
ele só mostra o que estiver cadastrado e aprovado aqui.
"""

CATALOGO_INICIAL = [
    {
        "nome": "Acesso e login",
        "sla_horas": 8,
        "emoji": "🔐",
        "orientacoes": [
            {
                "titulo": "Esqueci minha senha de rede/Windows",
                "palavras_chave": ["senha", "esqueci", "login", "acesso", "logar", "entrar", "expirada", "resetar"],
                "passos": [
                    "Acesse o portal de troca de senha: [link do portal de autoatendimento].",
                    "Informe seu usuário de rede e confirme a sua identidade (SMS ou app autenticador).",
                    "Crie a nova senha seguindo a política: mínimo 12 caracteres, com letras maiúsculas, minúsculas, números e símbolos.",
                    "Bloqueie (Win + L) e desbloqueie o computador usando a senha nova.",
                ],
                "observacao": "A TI nunca pede a sua senha por mensagem, e-mail ou telefone.",
            },
            {
                "titulo": "Minha conta está bloqueada",
                "palavras_chave": ["bloqueada", "bloqueio", "bloqueou", "acesso", "negado", "login", "tentativas"],
                "passos": [
                    "Aguarde 15 minutos: o bloqueio por tentativas erradas é liberado automaticamente.",
                    "Confira se o Caps Lock está desligado e se o teclado está no idioma correto.",
                    "Se você trocou a senha recentemente, atualize-a também no celular (e-mail corporativo, Wi-Fi), que pode estar tentando a senha antiga.",
                ],
                "observacao": "",
            },
            {
                "titulo": "Troquei de celular e perdi o autenticador (MFA)",
                "palavras_chave": ["mfa", "autenticador", "authenticator", "celular", "codigo", "verificacao", "dois fatores"],
                "passos": [
                    "Se você ainda tem o celular antigo, use a opção de transferência de contas do próprio app autenticador.",
                    "Se não tem mais o aparelho antigo, a reconfiguração precisa ser feita por um analista, para garantir a segurança da conta.",
                ],
                "observacao": "Nunca informe o código do autenticador para ninguém, nem para a TI.",
                "abre_chamado": True,
                "prioridade": "alta",
            },
        ],
    },
    {
        "nome": "Computador lento ou travando",
        "sla_horas": 24,
        "emoji": "💻",
        "orientacoes": [
            {
                "titulo": "Computador lento ou travando",
                "palavras_chave": ["lento", "lentidao", "travando", "trava", "travou", "congelou", "demora", "pesado"],
                "passos": [
                    "Salve o seu trabalho e reinicie o computador (reiniciar, não apenas desligar a tela).",
                    "Feche programas e abas do navegador que não estiver usando.",
                    "Abra o Gerenciador de Tarefas (Ctrl + Shift + Esc) e veja qual programa usa mais memória ou CPU.",
                    "Verifique se há atualizações pendentes do Windows e deixe concluir.",
                ],
                "observacao": "",
            },
            {
                "titulo": "Computador não liga ou tela azul",
                "palavras_chave": ["liga", "ligar", "desligou", "tela azul", "azul", "reiniciando", "inicia"],
                "passos": [
                    "Confira se o cabo de energia está conectado na tomada e no computador (notebook: conecte o carregador).",
                    "Segure o botão de ligar por 10 segundos, solte e ligue de novo.",
                    "Se aparecer tela azul, anote ou fotografe o código de erro exibido.",
                ],
                "observacao": "Não abra o equipamento.",
            },
            {
                "titulo": "Monitor, teclado ou mouse não funciona",
                "palavras_chave": ["monitor", "teclado", "mouse", "tela preta", "periferico", "usb", "webcam", "fone"],
                "passos": [
                    "Confira os cabos nas duas pontas e, se possível, teste em outra porta USB.",
                    "Para equipamentos sem fio, troque as pilhas ou recarregue a bateria.",
                    "Monitor: verifique se ele está ligado e na entrada correta (HDMI/DisplayPort) pelo botão do próprio monitor.",
                    "Reinicie o computador com o equipamento conectado.",
                ],
                "observacao": "",
            },
        ],
    },
    {
        "nome": "Internet, rede e VPN",
        "sla_horas": 8,
        "emoji": "📡",
        "orientacoes": [
            {
                "titulo": "Estou sem internet no computador",
                "palavras_chave": ["internet", "rede", "wifi", "wi-fi", "conexao", "cabo", "offline", "navegar"],
                "passos": [
                    "Veja se os colegas próximos também estão sem internet. Se vários estiverem, use a opção de incidente coletivo no menu de Segurança e incidentes.",
                    "No cabo de rede, confira se ele está bem encaixado e se a luz da placa de rede está acesa.",
                    "No Wi-Fi, desconecte e conecte de novo na rede [nome da rede corporativa].",
                    "Reinicie o computador.",
                ],
                "observacao": "",
            },
            {
                "titulo": "Não consigo conectar na VPN (trabalho remoto)",
                "palavras_chave": ["vpn", "remoto", "home office", "casa", "conectar", "forticlient", "globalprotect"],
                "passos": [
                    "Verifique primeiro se a sua internet de casa está funcionando (abra um site qualquer).",
                    "Abra o aplicativo de VPN [nome do app de VPN].",
                    "Informe o endereço [endereço do servidor VPN], se for pedido.",
                    "Entre com o seu usuário e senha de rede e confirme no autenticador.",
                ],
                "observacao": "",
            },
        ],
    },
    {
        "nome": "E-mail e Microsoft 365",
        "sla_horas": 16,
        "emoji": "📧",
        "orientacoes": [
            {
                "titulo": "Outlook não recebe ou não envia e-mails",
                "palavras_chave": ["outlook", "email", "e-mail", "receber", "enviar", "caixa de saida", "webmail"],
                "passos": [
                    "Verifique se o Outlook mostra 'Conectado' no rodapé. Se estiver 'Trabalhando offline', clique em Enviar/Receber > Trabalhar Offline para desativar.",
                    "Feche e abra o Outlook novamente.",
                    "Teste o acesso pelo navegador em [link do webmail]. Se lá funcionar, o problema está só no aplicativo.",
                    "Confira se a caixa de correio não está cheia (Arquivo > Informações).",
                ],
                "observacao": "",
            },
            {
                "titulo": "Caixa de e-mail cheia",
                "palavras_chave": ["cheia", "espaco", "armazenamento", "limite", "caixa", "email"],
                "passos": [
                    "Esvazie as pastas 'Itens Excluídos' e 'Lixo Eletrônico'.",
                    "Pesquise e-mails grandes: na busca, use o filtro 'Tamanho > Grande'.",
                    "Apague ou salve no OneDrive os anexos que não precisam ficar no e-mail.",
                ],
                "observacao": "",
            },
            {
                "titulo": "Teams sem áudio, vídeo ou microfone",
                "palavras_chave": ["teams", "reuniao", "audio", "microfone", "camera", "video", "som", "chamada"],
                "passos": [
                    "No Teams, vá em Configurações > Dispositivos e escolha o fone/microfone e a câmera corretos.",
                    "Verifique se o fone está bem conectado e se não há botão de mudo no próprio fone.",
                    "Feche o Teams completamente (inclusive no ícone perto do relógio) e abra de novo.",
                    "Se o problema continuar, reinicie o computador.",
                ],
                "observacao": "",
            },
            {
                "titulo": "OneDrive ou SharePoint não sincroniza",
                "palavras_chave": ["onedrive", "sharepoint", "sincronizar", "sincroniza", "arquivo", "nuvem", "pasta"],
                "passos": [
                    "Clique no ícone de nuvem do OneDrive perto do relógio e veja se há alguma mensagem de erro.",
                    "Confira se você está conectado com a conta corporativa.",
                    "Pause e retome a sincronização (ícone do OneDrive > Ajuda e Configurações > Pausar sincronização).",
                ],
                "observacao": "",
            },
        ],
    },
    {
        "nome": "Impressora",
        "sla_horas": 24,
        "emoji": "🖨️",
        "orientacoes": [
            {
                "titulo": "Não consigo imprimir",
                "palavras_chave": ["imprimir", "impressora", "impressao", "imprime", "papel", "atolado", "fila"],
                "passos": [
                    "Confira se a impressora está ligada, com papel e sem mensagem de erro no painel.",
                    "No computador, abra Configurações > Impressoras e veja se a impressora correta está selecionada.",
                    "Abra a fila de impressão e cancele documentos travados.",
                    "Tente imprimir de novo. Se não funcionar, teste em outra impressora do andar.",
                ],
                "observacao": "Atolamento de papel: abra só as tampas indicadas no painel e não puxe o papel com força.",
            },
            {
                "titulo": "Adicionar uma impressora no meu computador",
                "palavras_chave": ["adicionar", "instalar", "impressora", "nova", "configurar", "scanner"],
                "passos": [
                    "Abra Configurações > Bluetooth e dispositivos > Impressoras e scanners.",
                    "Clique em 'Adicionar dispositivo' e escolha a impressora do seu andar ([padrão de nomes das impressoras]).",
                    "Se ela não aparecer, anote a etiqueta com o nome da impressora e abra um chamado.",
                ],
                "observacao": "",
            },
            {
                "titulo": "Toner ou cartucho acabando",
                "palavras_chave": ["toner", "cartucho", "tinta", "acabando", "acabou", "fraca", "falhada",
                                   "suprimento", "refil"],
                "passos": [
                    "Informe o nome da impressora (está na etiqueta do equipamento) e o andar ou a sala.",
                    "Informe se a impressão já está falhando ou se a impressora só avisou que o toner está acabando.",
                    "Não troque o toner sem a TI se a impressora for alugada: o fornecedor faz a troca.",
                ],
                "observacao": "",
                "abre_chamado": True,
                "prioridade": "baixa",
            },
        ],
    },
    {
        "nome": "Sistemas internos",
        "sla_horas": 16,
        "emoji": "🧩",
        "orientacoes": [
            {
                "titulo": "Erro em um sistema interno",
                "palavras_chave": ["erro", "sistema", "mensagem de erro", "nao abre", "falha", "tela", "erp"],
                "passos": [
                    "Tire um print da tela com a mensagem de erro (tecla Win + Shift + S).",
                    "Anote o que você estava fazendo quando o erro apareceu.",
                    "Feche o sistema, limpe o cache do navegador (Ctrl + Shift + Del) e tente de novo.",
                    "Pergunte a um colega se o erro também acontece com ele.",
                ],
                "observacao": "",
            },
            {
                "titulo": "Preciso instalar um programa",
                "palavras_chave": ["instalar", "programa", "software", "aplicativo", "licenca", "baixar"],
                "passos": [
                    "Verifique se o programa está disponível no [Portal da Empresa / Centro de Software] e instale por lá.",
                    "Se não estiver, a instalação precisa de aprovação do seu gestor e da TI.",
                    "Tenha em mãos o nome do programa e para que ele será usado.",
                ],
                "observacao": "Não instale programas baixados da internet por conta própria.",
            },
        ],
    },
    {
        "nome": "Solicitação de acesso",
        "sla_horas": 40,
        "emoji": "🔑",
        "orientacoes": [
            {
                "titulo": "Acesso a sistema, pasta de rede ou grupo de e-mail",
                "palavras_chave": ["solicitar", "liberar", "liberacao", "permissao", "acesso", "pasta", "compartilhada", "grupo"],
                "passos": [
                    "Informe qual sistema, pasta ou grupo você precisa acessar e o tipo de acesso (leitura ou edição).",
                    "O seu coordenador e o gerente da área precisam aprovar o acesso (o assistente pede os dois).",
                    "A TI só libera o acesso depois da aprovação registrada no chamado.",
                ],
                "observacao": "",
                "abre_chamado": True,
                "exige_aprovacao": True,
            },
            {
                "titulo": "Acesso para colaborador novo",
                "palavras_chave": ["novo", "admissao", "contratado", "integracao", "usuario novo", "criar usuario"],
                "passos": [
                    "A criação do usuário precisa da aprovação do coordenador e do gerente da área (o assistente pede os dois).",
                    "Informe nome completo, setor, cargo, data de início e os sistemas necessários.",
                ],
                "observacao": "",
                "abre_chamado": True,
                "exige_aprovacao": True,
                "prioridade": "baixa",
            },
        ],
    },
    {
        "nome": "Segurança e incidentes",
        "sla_horas": 8,
        "emoji": "🚨",
        "orientacoes": [
            {
                "titulo": "Recebi um e-mail ou mensagem suspeita (phishing)",
                "palavras_chave": ["phishing", "suspeito", "suspeita", "golpe", "fraude", "link estranho", "spam", "cliquei"],
                "passos": [
                    "Não clique em links, não abra anexos e não responda.",
                    "Use o botão 'Reportar phishing' do Outlook ou encaminhe o e-mail para [e-mail da segurança].",
                    "Se você já clicou ou informou a sua senha, troque a senha imediatamente pelo portal oficial.",
                ],
                "observacao": "Casos de segurança são sempre encaminhados com prioridade para a TI.",
                "prioridade": "critica",
            },
            {
                "titulo": "Vírus, vazamento de dados ou equipamento perdido/roubado",
                "palavras_chave": ["virus", "malware", "ransomware", "hacker", "invadido", "vazamento", "roubado", "perdi notebook", "sequestro"],
                "passos": [
                    "Desconecte o computador da rede (cabo e Wi-Fi), mas não desligue.",
                    "Não tente remover o problema por conta própria.",
                ],
                "observacao": "Casos de segurança são sempre encaminhados com prioridade para a TI.",
                "prioridade": "critica",
            },
            {
                "titulo": "Vários colegas sem sistema ou internet ao mesmo tempo",
                "palavras_chave": ["todos", "geral", "varios", "ninguem", "fora do ar", "caiu", "indisponivel", "setor inteiro"],
                "passos": [
                    "Não é preciso que cada pessoa abra um chamado: um chamado prioritário já basta.",
                    "Informe quais sistemas estão fora e quais setores estão afetados.",
                ],
                "observacao": "",
                "prioridade": "critica",
            },
        ],
    },
    {
        # Pedido de equipamento: a TI entrega. Os itens de maior valor ou risco precisam de coordenador e gerente.
        "nome": "Requisição de material",
        "sla_horas": 40,
        "emoji": "📦",
        "orientacoes": [
            {
                "titulo": "Notebook",
                "palavras_chave": ["notebook", "laptop", "computador novo", "maquina nova", "requisicao",
                                   "material", "equipamento", "solicitar", "pedir"],
                "passos": [
                    "Informe para quem é o notebook (você ou um colaborador novo) e o motivo: colaborador novo, troca por defeito ou equipamento antigo.",
                    "Se for troca, informe o número de patrimônio do notebook atual.",
                    "A entrega depende da aprovação do coordenador e do gerente da área (o assistente pede os dois) e do estoque.",
                ],
                "observacao": "Não compre equipamentos por conta própria: a TI entrega o notebook já configurado.",
                "abre_chamado": True,
                "exige_aprovacao": True,
            },
            {
                "titulo": "Computador de mesa (desktop)",
                "palavras_chave": ["desktop", "computador de mesa", "cpu", "gabinete", "pc", "computador novo",
                                   "requisicao", "material", "equipamento"],
                "passos": [
                    "Informe para quem é o computador e o motivo: colaborador novo, troca por defeito ou equipamento antigo.",
                    "Se for troca, informe o número de patrimônio do computador atual.",
                    "A entrega depende da aprovação do coordenador e do gerente da área (o assistente pede os dois) e do estoque.",
                ],
                "observacao": "",
                "abre_chamado": True,
                "exige_aprovacao": True,
            },
            {
                "titulo": "Monitor (tela)",
                "palavras_chave": ["monitor", "tela", "segunda tela", "monitor novo", "tela nova", "requisicao",
                                   "material", "equipamento"],
                "passos": [
                    "Informe quantos monitores você precisa e o motivo (segunda tela, troca por defeito, colaborador novo).",
                    "Informe onde o monitor vai ser usado (andar, sala ou mesa).",
                    "A entrega depende da aprovação do coordenador e do gerente da área (o assistente pede os dois) e do estoque.",
                ],
                "observacao": "",
                "abre_chamado": True,
                "exige_aprovacao": True,
            },
            {
                "titulo": "Mouse ou teclado",
                "palavras_chave": ["mouse", "teclado", "mouse novo", "teclado novo", "requisicao", "material"],
                "passos": [
                    "Informe se precisa de mouse, teclado ou os dois, e a quantidade.",
                    "Se for troca por defeito, a TI recolhe o item antigo na entrega.",
                ],
                "observacao": "",
                "abre_chamado": True,
            },
            {
                "titulo": "Headset (fone com microfone)",
                "palavras_chave": ["headset", "fone", "fone de ouvido", "microfone", "audio", "ligacao",
                                   "reuniao", "teams", "requisicao", "material"],
                "passos": [
                    "Informe a quantidade e o uso: reuniões, atendimento por telefone ou chamadas o dia todo.",
                    "Informe a conexão que você prefere, se souber (USB, P2 ou Bluetooth).",
                    "Se for troca por defeito, a TI recolhe o item antigo na entrega.",
                ],
                "observacao": "",
                "abre_chamado": True,
            },
            {
                "titulo": "Webcam",
                "palavras_chave": ["webcam", "camera", "video", "reuniao", "teams", "requisicao", "material"],
                "passos": [
                    "Informe a quantidade e onde vai ser usada (mesa ou sala de reunião).",
                    "Se o seu notebook já tem câmera e ela não funciona, use a opção de computador em vez desta.",
                ],
                "observacao": "",
                "abre_chamado": True,
            },
            {
                "titulo": "Carregador ou fonte do notebook",
                "palavras_chave": ["carregador", "fonte", "bateria", "carregar", "nao carrega", "requisicao",
                                   "material"],
                "passos": [
                    "Informe o modelo do notebook (está na etiqueta embaixo dele) ou o número de patrimônio.",
                    "Informe o motivo: perda, defeito ou um carregador extra.",
                    "Se for defeito, a TI recolhe o carregador antigo na entrega.",
                ],
                "observacao": "Use só carregadores entregues pela TI: um carregador errado pode danificar o notebook.",
                "abre_chamado": True,
            },
            {
                "titulo": "Cabo HDMI ou adaptador",
                "palavras_chave": ["hdmi", "cabo", "adaptador", "displayport", "usb-c", "conversor", "extensao",
                                   "requisicao", "material"],
                "passos": [
                    "Informe o tipo de cabo ou adaptador (HDMI, DisplayPort, USB-C para HDMI...) e a quantidade.",
                    "Se souber, informe o comprimento necessário (ex.: 1,5 m ou 3 m).",
                    "Informe onde vai ser usado (mesa, sala de reunião...).",
                ],
                "observacao": "",
                "abre_chamado": True,
            },
            {
                "titulo": "Dock station ou hub USB-C",
                "palavras_chave": ["dock", "docking", "station", "hub", "usb-c", "portas", "replicador",
                                   "requisicao", "material"],
                "passos": [
                    "Informe o modelo do notebook ou o número de patrimônio.",
                    "Informe o que você precisa ligar nele (quantos monitores, teclado, mouse, rede por cabo...).",
                ],
                "observacao": "",
                "abre_chamado": True,
            },
            {
                "titulo": "Suporte para notebook ou monitor",
                "palavras_chave": ["suporte", "ergonomia", "base", "altura", "braco articulado", "requisicao",
                                   "material"],
                "passos": [
                    "Informe se o suporte é para notebook ou para monitor, e a quantidade.",
                    "Se for recomendação médica ou ergonômica, informe no pedido.",
                ],
                "observacao": "",
                "abre_chamado": True,
            },
            {
                "titulo": "Filtro de linha ou extensão elétrica",
                "palavras_chave": ["filtro de linha", "extensao", "tomada", "regua", "benjamim", "energia",
                                   "requisicao", "material"],
                "passos": [
                    "Informe a quantidade e quantas tomadas você precisa.",
                    "Informe onde vai ser usado (mesa, sala de reunião...).",
                ],
                "observacao": "Não ligue uma extensão em outra: pode sobrecarregar a tomada.",
                "abre_chamado": True,
            },
            {
                "titulo": "Celular ou chip corporativo",
                "palavras_chave": ["celular", "chip", "smartphone", "linha", "telefone corporativo",
                                   "celular corporativo", "requisicao", "material"],
                "passos": [
                    "Informe se precisa do aparelho, do chip ou dos dois, e para quem é.",
                    "Informe o motivo: função que exige contato externo, colaborador novo, troca por defeito ou perda.",
                    "Por ter custo mensal, a entrega depende da aprovação do coordenador e do gerente da área (o assistente pede os dois).",
                ],
                "observacao": "Em caso de perda ou roubo, avise a TI na hora para bloquear a linha e os dados do aparelho.",
                "abre_chamado": True,
                "exige_aprovacao": True,
            },
            {
                "titulo": "Pendrive ou HD externo",
                "palavras_chave": ["pendrive", "pen drive", "hd externo", "ssd externo", "armazenamento",
                                   "backup", "requisicao", "material"],
                "passos": [
                    "Informe para que vai usar (ex.: levar arquivos para um cliente, backup de um equipamento) e por quanto tempo.",
                    "Informe se os arquivos têm dados pessoais ou confidenciais.",
                    "Por risco de vazamento de dados, a entrega depende da aprovação do coordenador e do gerente da área (o assistente pede os dois).",
                ],
                "observacao": "O uso segue a política de segurança da informação: a TI pode entregar o dispositivo com criptografia.",
                "abre_chamado": True,
                "exige_aprovacao": True,
            },
            {
                "titulo": "Empréstimo temporário (notebook, projetor, caixa de som...)",
                "palavras_chave": ["emprestimo", "emprestar", "temporario", "evento", "treinamento",
                                   "projetor", "caixa de som", "apresentacao", "requisicao", "material"],
                "passos": [
                    "Informe o que você precisa e a quantidade.",
                    "Informe a data e o horário de retirada e de devolução.",
                    "Informe o local e o responsável pelo equipamento durante o empréstimo.",
                ],
                "observacao": "Peça com antecedência: o empréstimo depende da disponibilidade na data.",
                "abre_chamado": True,
            },
            {
                "titulo": "Devolução de equipamento",
                "palavras_chave": ["devolucao", "devolver", "desligamento", "demissao", "recolher", "baixa",
                                   "patrimonio", "troca"],
                "passos": [
                    "Informe de quem são os equipamentos e o motivo: desligamento, troca ou fim de empréstimo.",
                    "Liste os itens (notebook, carregador, monitor, celular, chip, headset...) e, se souber, o número de patrimônio.",
                    "Informe a data e o local para a TI recolher.",
                ],
                "observacao": "No desligamento, a TI também bloqueia os acessos do colaborador na data informada.",
                "abre_chamado": True,
            },
            {
                "titulo": "Outro material",
                "palavras_chave": ["outro", "material", "equipamento", "acessorio", "requisicao"],
                "passos": [
                    "Informe qual material você precisa, a quantidade e o motivo (novo, troca por defeito...).",
                    "Se for troca, a TI recolhe o item antigo na entrega.",
                ],
                "observacao": "",
                "abre_chamado": True,
            },
        ],
    },
    {
        # Sem orientações: o colaborador descreve e o chamado é aberto direto.
        "nome": "Outros assuntos",
        "sla_horas": 72,
        "emoji": "✍️",
        "orientacoes": [],
    },
]
