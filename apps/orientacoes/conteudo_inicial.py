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
        ],
    },
    {
        "nome": "Sistemas internos",
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
        "emoji": "🔑",
        "orientacoes": [
            {
                "titulo": "Acesso a sistema, pasta de rede ou grupo de e-mail",
                "palavras_chave": ["solicitar", "liberar", "liberacao", "permissao", "acesso", "pasta", "compartilhada", "grupo"],
                "passos": [
                    "Informe qual sistema, pasta ou grupo você precisa acessar e o tipo de acesso (leitura ou edição).",
                    "Informe o nome do seu gestor, que precisa aprovar o acesso.",
                    "A TI só libera o acesso depois da aprovação registrada no chamado.",
                ],
                "observacao": "",
                "abre_chamado": True,
            },
            {
                "titulo": "Acesso para colaborador novo",
                "palavras_chave": ["novo", "admissao", "contratado", "integracao", "usuario novo", "criar usuario"],
                "passos": [
                    "A solicitação deve ser feita pelo gestor ou pelo RH.",
                    "Informe nome completo, setor, cargo, data de início e os sistemas necessários.",
                ],
                "observacao": "",
                "abre_chamado": True,
                "prioridade": "baixa",
            },
        ],
    },
    {
        "nome": "Segurança e incidentes",
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
        # Sem orientações: o colaborador descreve e o chamado é aberto direto.
        "nome": "Outros assuntos",
        "emoji": "✍️",
        "orientacoes": [],
    },
]
