"""
Testes do motor de conversa (Python puro, sem banco):
    python -m unittest apps.bot.tests.test_engine
"""
import unittest

from apps.bot import engine as e
from apps.orientacoes.conteudo_inicial import CATALOGO_INICIAL

# Menu: 1 Acesso | 2 Computador | 3 Internet | 4 E-mail | 5 Impressora | 6 Sistemas
#       7 Solicitação de acesso | 8 Segurança | 9 Requisição de material | 10 Outros
CTX = e.Contexto(catalogo=CATALOGO_INICIAL)
IDENT = ("oi", "Maria Silva", "Financeiro", "maria@empresa.com.br")


def conversa(*mensagens, estado=None, ctx=CTX):
    estado = estado or e.Estado()
    resultados = []
    for m in mensagens:
        r = e.processar(estado, m, ctx)
        resultados.append(r)
        estado = r.estado
    return estado, resultados


def tipos(r):
    return [a.tipo for a in r.acoes]


def acao(r, tipo):
    return next(a for a in r.acoes if a.tipo == tipo)


class Identificacao(unittest.TestCase):
    def test_pede_nome_setor_email_e_mostra_menu(self):
        estado, rs = conversa(*IDENT)
        self.assertIn("nome completo", rs[0].respostas[-1])
        self.assertIn("setor", rs[1].respostas[0])
        self.assertIn("e-mail corporativo", rs[2].respostas[0])
        self.assertEqual(estado.etapa, e.MENU)
        self.assertEqual(acao(rs[3], e.ACAO_IDENTIFICADO).params["email"], "maria@empresa.com.br")
        self.assertIn("Acesso e login", rs[3].respostas[0])

    def test_email_de_outro_dominio_e_recusado(self):
        ctx = e.Contexto(catalogo=CATALOGO_INICIAL, dominios_email=("empresa.com.br",))
        estado, rs = conversa("oi", "Maria Silva", "Financeiro", "maria@gmail.com", ctx=ctx)
        self.assertEqual(estado.etapa, e.IDENTIFICACAO)
        self.assertIn("@empresa.com.br", rs[-1].respostas[0])
        estado, _ = conversa("maria@empresa.com.br", estado=estado, ctx=ctx)
        self.assertEqual(estado.etapa, e.MENU)

    def test_identificacao_configuravel_com_matricula(self):
        ctx = e.Contexto(catalogo=CATALOGO_INICIAL, campos_identificacao=("nome", "matricula"))
        estado, rs = conversa("oi", "Maria Silva", "ab-1234", ctx=ctx)
        self.assertEqual(estado.etapa, e.MENU)
        self.assertEqual(estado.dados["matricula"], "AB-1234")

    def test_nome_invalido(self):
        estado, _ = conversa("oi", "12")
        self.assertEqual(estado.etapa, e.IDENTIFICACAO)

    def test_colaborador_conhecido_vai_direto_ao_menu(self):
        estado = e.Estado(e.ENCERRADO, {"nome": "Ana Lima", "setor": "RH", "email": "ana@x.com"})
        r = e.processar(estado, "bom dia", CTX)
        self.assertEqual(r.estado.etapa, e.MENU)
        self.assertIn("Ana", r.respostas[0])


class Base(unittest.TestCase):
    def setUp(self):
        self.base, _ = conversa(*IDENT)

    def falar(self, *mensagens, ctx=CTX):
        return conversa(*mensagens, estado=self.base, ctx=ctx)


class Resolvido(Base):
    def test_resolve_avalia_e_encerra(self):
        estado, rs = self.falar("3", "1", "1", "5")
        self.assertIn(e.ACAO_REGISTRAR_ORIENTACAO, tipos(rs[1]))
        self.assertEqual(rs[1].estado.etapa, e.RESOLVEU)
        self.assertIn("Seu problema foi resolvido?", rs[1].respostas[-1])
        self.assertEqual(rs[2].estado.etapa, e.AVALIACAO)
        self.assertEqual(tipos(rs[3]), [e.ACAO_REGISTRAR_AVALIACAO, e.ACAO_ENCERRAR])
        self.assertEqual(acao(rs[3], e.ACAO_REGISTRAR_AVALIACAO).params["nota"], 5)
        self.assertEqual(acao(rs[3], e.ACAO_ENCERRAR).params["resultado"], "resolvida")
        self.assertEqual(estado.etapa, e.ENCERRADO)

    def test_sim_por_texto(self):
        estado, _ = self.falar("1", "2", "sim")
        self.assertEqual(estado.etapa, e.AVALIACAO)


class NaoResolvido(Base):
    def test_pede_descricao_e_abre_chamado_com_resumo(self):
        estado, rs = self.falar("3", "1", "2", "O cabo está ligado e continua sem rede")
        self.assertEqual(rs[2].estado.etapa, e.DESCREVER)
        self.assertEqual(estado.etapa, e.HUMANO)
        p = acao(rs[-1], e.ACAO_ABRIR_CHAMADO).params
        self.assertEqual(p["categoria"], "Internet, rede e VPN")
        self.assertEqual(p["orientacao"], "Estou sem internet no computador")
        self.assertEqual(p["prioridade"], "media")
        self.assertEqual(p["descricao"], "O cabo está ligado e continua sem rede")
        self.assertIn("Maria Silva", p["resumo"])
        self.assertIn("maria@empresa.com.br", p["resumo"])
        self.assertIn(e.PROTOCOLO, rs[-1].respostas[0])

    def test_nao_por_texto(self):
        estado, _ = self.falar("1", "2", "não")
        self.assertEqual(estado.etapa, e.DESCREVER)

    def test_com_chamado_aberto_bot_fica_em_silencio(self):
        estado, _ = self.falar("0", "Preciso de ajuda com o ERP")
        self.assertEqual(estado.etapa, e.HUMANO)
        r = e.processar(estado, "alô?", CTX)
        self.assertEqual((r.respostas, r.acoes), ([], []))

    def test_fora_do_horario_informa_janela_configurada(self):
        ctx = e.Contexto(catalogo=CATALOGO_INICIAL, dentro_do_horario=False, texto_horario="seg a sex, 9h-17h")
        estado, rs = self.falar("0", "Monitor piscando desde ontem", ctx=ctx)
        self.assertEqual(estado.etapa, e.HUMANO)
        self.assertIn(e.ACAO_ABRIR_CHAMADO, tipos(rs[-1]))
        self.assertIn("fora do horário", rs[-1].respostas[0])
        self.assertIn("seg a sex, 9h-17h", rs[-1].respostas[0])

    def test_categoria_sem_orientacao_vai_direto_para_chamado(self):
        estado, rs = self.falar("10")  # Outros assuntos
        self.assertEqual(estado.etapa, e.DESCREVER)

    def test_solicitacao_de_acesso_sempre_abre_chamado(self):
        estado, rs = self.falar("7", "1")
        self.assertEqual(estado.etapa, e.DESCREVER)
        self.assertIn("coordenador", rs[-1].respostas[0])


class Critico(Base):
    def test_seguranca_escala_na_hora_com_prioridade_critica(self):
        estado, rs = self.falar("8", "1")
        self.assertEqual(estado.etapa, e.HUMANO)
        self.assertIn("Não clique em links", rs[-1].respostas[0])
        self.assertNotIn(e.TEXTO_RESOLVEU, rs[-1].respostas)
        self.assertEqual(acao(rs[-1], e.ACAO_ABRIR_CHAMADO).params["prioridade"], "critica")
        self.assertIn("prioritário", rs[-1].respostas[-1])

    def test_texto_livre_de_phishing_escala(self):
        estado, rs = self.falar("recebi um email de phishing")
        self.assertEqual(estado.etapa, e.HUMANO)
        self.assertEqual(acao(rs[-1], e.ACAO_ABRIR_CHAMADO).params["prioridade"], "critica")


class TextoLivre(Base):
    def test_erro_de_acesso_sugere_orientacoes(self):
        estado, rs = self.falar("erro de acesso")
        self.assertEqual(estado.etapa, e.SUGESTOES)
        self.assertIn("Esqueci minha senha", rs[-1].respostas[0])
        estado, rs = conversa("1", estado=estado)
        self.assertEqual(estado.etapa, e.RESOLVEU)

    def test_descricao_clara_vai_direto_para_a_orientacao(self):
        estado, rs = self.falar("a impressora não imprime")
        self.assertEqual(estado.etapa, e.RESOLVEU)
        self.assertIn("Não consigo imprimir", rs[-1].respostas[1])

    def test_relato_vira_descricao_sem_repetir(self):
        estado, rs = self.falar("erro de acesso", "0", "pular")
        self.assertEqual(estado.etapa, e.HUMANO)
        self.assertEqual(acao(rs[-1], e.ACAO_ABRIR_CHAMADO).params["descricao"], "erro de acesso")

    def test_sem_resultado_conta_como_tentativa(self):
        estado, rs = self.falar("xyzwq")
        self.assertEqual(estado.etapa, e.MENU)
        self.assertIn("Não encontrei", rs[-1].respostas[0])


class Navegacao(Base):
    def test_comandos_globais(self):
        estado, _ = self.falar("2", "menu")
        self.assertEqual(estado.etapa, e.MENU)
        estado, rs = self.falar("2", "Sair")
        self.assertEqual(estado.etapa, e.ENCERRADO)
        self.assertEqual(acao(rs[-1], e.ACAO_ENCERRAR).params["resultado"], "cancelada")
        estado, _ = self.falar("Analista")
        self.assertEqual(estado.etapa, e.DESCREVER)

    def test_ver_outra_orientacao(self):
        estado, _ = self.falar("1", "1", "3")
        self.assertEqual(estado.etapa, e.CATEGORIA)

    def test_tres_opcoes_invalidas_oferece_chamado(self):
        estado, rs = self.falar("99", "98", "97")
        self.assertEqual(rs[0].estado.etapa, e.MENU)
        self.assertEqual(estado.etapa, e.DESCREVER)

    def test_nao_muta_estado_de_entrada(self):
        original = e.Estado()
        e.processar(original, "oi", CTX)
        self.assertEqual(original.etapa, e.INICIO)


class DadosSensiveis(unittest.TestCase):
    def test_remove_senha_codigo_e_cpf(self):
        for texto in ("minha senha é Abc@123", "senha: Abc@123", "código de verificação 123456",
                      "meu cpf 123.456.789-09"):
            limpo, removeu = e.mascarar_sensivel(texto)
            self.assertTrue(removeu, texto)
            self.assertNotIn("123", limpo.replace("[removido]", ""), texto)

    def test_mantem_frases_normais(self):
        for texto in ("esqueci minha senha de rede", "erro 0x80070005 ao abrir", "sala 1234"):
            self.assertEqual(e.mascarar_sensivel(texto), (texto, False))


if __name__ == "__main__":
    unittest.main()


class CentroDeCusto(unittest.TestCase):
    CTX_CC = e.Contexto(catalogo=CATALOGO_INICIAL, campos_identificacao=("nome", "setor", "centro_custo", "email"))

    def test_pergunta_o_centro_de_custo_depois_do_setor(self):
        estado, rs = conversa("oi", "Maria Silva", "Financeiro", "1105 - Financeiro", "maria@empresa.com.br",
                              ctx=self.CTX_CC)
        self.assertIn("centro de custo", rs[2].respostas[0])
        self.assertEqual(estado.dados["centro_custo"], "1105 - Financeiro")
        self.assertEqual(estado.dados["nome"], "Maria Silva")  # campos separados
        self.assertEqual(estado.etapa, e.MENU)
        ident = acao(rs[-1], e.ACAO_IDENTIFICADO).params
        self.assertEqual(ident["centro_custo"], "1105 - Financeiro")

    def test_centro_de_custo_invalido(self):
        estado, rs = conversa("oi", "Maria Silva", "Financeiro", "?", ctx=self.CTX_CC)
        self.assertIn("centro de custo", rs[-1].respostas[0])
        self.assertEqual(estado.dados["campo"], "centro_custo")

    def test_quem_ja_tinha_cadastro_so_informa_o_centro_de_custo(self):
        antigo = e.Estado(e.INICIO, {"nome": "Maria Silva", "setor": "Financeiro", "email": "maria@empresa.com.br"})
        estado, rs = conversa("oi", "2030", estado=antigo, ctx=self.CTX_CC)
        self.assertIn("Olá, Maria", rs[0].respostas[0])
        self.assertIn("centro de custo", rs[0].respostas[1])
        self.assertEqual((estado.etapa, estado.dados["centro_custo"]), (e.MENU, "2030"))


class Aprovacao(Base):
    """Criação de usuário e liberação de acesso: pede coordenador e gerente da área."""

    APROVADORES = ("Carlos Souza", "carlos@empresa.com.br", "Gina Prado", "gina@empresa.com.br")

    def test_liberar_acesso_pede_coordenador_e_gerente(self):
        estado, rs = self.falar("7", "1", "Acesso de leitura na pasta Financeiro")
        self.assertEqual(estado.etapa, e.APROVADORES)
        self.assertIn("duas aprovações", rs[-1].respostas[0])
        self.assertIn("coordenador", rs[-1].respostas[1])
        estado, rs = conversa(*self.APROVADORES, estado=estado)
        self.assertIn("gerente da área", rs[1].respostas[0])
        self.assertEqual(estado.etapa, e.HUMANO)
        params = acao(rs[-1], e.ACAO_ABRIR_CHAMADO).params
        self.assertEqual(params["aprovadores"], [
            {"nivel": 1, "nome": "Carlos Souza", "email": "carlos@empresa.com.br"},
            {"nivel": 2, "nome": "Gina Prado", "email": "gina@empresa.com.br"},
        ])
        self.assertIn("Aprovador 2 (gerente da área): Gina Prado", params["resumo"])
        self.assertIn("seguiu para aprovação", rs[-1].respostas[0])
        self.assertNotIn("aprovadores", estado.dados)

    def test_criacao_de_usuario_tambem_exige_aprovacao(self):
        estado, _ = self.falar("7", "2", "Usuário para o João, que entra dia 01/12 no Comercial")
        self.assertEqual(estado.etapa, e.APROVADORES)

    def test_nao_pode_aprovar_a_propria_solicitacao(self):
        estado, rs = self.falar("7", "1", "Acesso ao ERP", "Maria Silva", "maria@empresa.com.br")
        self.assertEqual(estado.etapa, e.APROVADORES)
        self.assertIn("própria solicitação", rs[-1].respostas[0])

    def test_coordenador_e_gerente_precisam_ser_pessoas_diferentes(self):
        estado, rs = self.falar("7", "1", "Acesso ao ERP", "Carlos Souza", "carlos@empresa.com.br",
                                "Carlos Souza", "carlos@empresa.com.br")
        self.assertEqual(estado.etapa, e.APROVADORES)
        self.assertIn("pessoas diferentes", rs[-1].respostas[0])

    def test_email_do_aprovador_invalido(self):
        estado, rs = self.falar("7", "1", "Acesso ao ERP", "Carlos Souza", "carlos")
        self.assertEqual(estado.etapa, e.APROVADORES)
        self.assertIn("e-mail corporativo* do seu coordenador", rs[-1].respostas[0])

    def test_outras_orientacoes_nao_pedem_aprovacao(self):
        estado, rs = self.falar("3", "1", "2", "Cabo conectado e continua sem rede")
        self.assertEqual(estado.etapa, e.HUMANO)
        self.assertNotIn("aprovadores", acao(rs[-1], e.ACAO_ABRIR_CHAMADO).params)


class RequisicaoDeMaterial(Base):
    """9 - Requisição de material: 1 Notebook | 2 Monitor | 3 Mouse/teclado | 4 Cabo HDMI | 5 Outro."""

    def test_aparece_no_menu_antes_de_outros(self):
        menu = e.texto_menu(CTX)
        self.assertIn("*9* - 📦 Requisição de material", menu)
        self.assertIn("*10* - ✍️ Outros assuntos", menu)
        _, rs = self.falar("9")
        for item in ("Notebook", "Monitor (tela)", "Mouse ou teclado", "Cabo HDMI ou adaptador"):
            self.assertIn(item, rs[-1].respostas[0])

    def test_notebook_e_monitor_exigem_aprovacao(self):
        for opcao in ("1", "2"):
            estado, rs = self.falar("9", opcao, "Colaborador novo no Comercial, começa dia 01/12")
            self.assertEqual(estado.etapa, e.APROVADORES, opcao)

    def test_mouse_e_cabo_hdmi_abrem_chamado_direto(self):
        for opcao in ("3", "4", "5"):
            estado, rs = self.falar("9", opcao, "Preciso de 2 unidades para a sala de reunião")
            self.assertEqual(estado.etapa, e.HUMANO, opcao)
            params = acao(rs[-1], e.ACAO_ABRIR_CHAMADO).params
            self.assertEqual(params["categoria"], "Requisição de material")
            self.assertNotIn("aprovadores", params)

    def test_texto_livre_acha_o_cabo_hdmi(self):
        estado, rs = self.falar("preciso de um cabo hdmi")
        self.assertIn("Cabo HDMI ou adaptador", " ".join(rs[-1].respostas))
