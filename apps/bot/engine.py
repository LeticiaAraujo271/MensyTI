"""
Motor de conversa da Central de TI (fluxo do BPMN docs/Central_TI_Multicanal_Bizagi.bpmn).

Python puro: não importa Django nem sabe qual é o canal (web ou WhatsApp).
Recebe o estado da conversa + o texto do colaborador e devolve:
  - o novo estado,
  - as respostas do bot,
  - as ações que o orquestrador executa (abrir chamado, registrar avaliação...).

Etapas (BPMN):
  identificacao -> menu/categoria/sugestoes (triagem) -> orientacao (resolveu?)
  -> avaliacao -> encerrado            (resolvido no autoatendimento)
  -> descrever -> humano               (chamado aberto; a TI continua pelo painel)
  -> pesquisa -> pesquisa_obs -> encerrado   (TI resolveu o chamado: pesquisa de satisfação)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------
# Etapas
# --------------------------------------------------------------------------
INICIO = "inicio"
IDENTIFICACAO = "identificacao"
MENU = "menu"
CATEGORIA = "categoria"
SUGESTOES = "sugestoes"
RESOLVEU = "resolveu"
DESCREVER = "descrever"
AVALIACAO = "avaliacao"
HUMANO = "humano"          # chamado aberto: mensagens vão para a TI, o bot não responde
PESQUISA = "pesquisa"      # chamado resolvido: "como você avalia o atendimento?"
PESQUISA_OBS = "pesquisa_obs"  # observação (obrigatória se insatisfeito)
ENCERRADO = "encerrado"

# --------------------------------------------------------------------------
# Ações executadas pelo orquestrador
# --------------------------------------------------------------------------
ACAO_IDENTIFICADO = "identificado"
ACAO_REGISTRAR_ORIENTACAO = "registrar_orientacao"
ACAO_ABRIR_CHAMADO = "abrir_chamado"
ACAO_REGISTRAR_AVALIACAO = "registrar_avaliacao"
ACAO_REGISTRAR_PESQUISA = "registrar_pesquisa"
ACAO_ENCERRAR = "encerrar"

# O orquestrador troca este marcador pelo protocolo real do chamado.
PROTOCOLO = "{protocolo}"

PRIORIDADES = ("baixa", "media", "alta", "critica")
MAX_TENTATIVAS_INVALIDAS = 3

CMD_MENU = {"menu", "inicio", "voltar", "voltar ao menu"}
CMD_SAIR = {"sair", "encerrar", "tchau", "finalizar"}
CMD_ANALISTA = {"atendente", "analista", "humano", "pessoa", "falar com analista",
                "chamado", "abrir chamado"}

# Chaves temporárias de cada atendimento (as de identificação ficam).
_TEMPORARIOS = ("campo", "categoria", "orientacao", "sugestoes", "tentativas",
                "motivo", "relato", "descricao", "pesquisa", "pesquisa_resposta")

# Pesquisa de satisfação do chamado: (valor gravado, rótulo, emoji, exige observação)
OPCOES_PESQUISA = (
    ("muito_satisfeito", "Muito satisfeito", "🤩", False),
    ("satisfeito", "Satisfeito", "🙂", False),
    ("insatisfeito", "Insatisfeito", "🙁", True),
    ("muito_insatisfeito", "Muito insatisfeito", "😞", True),
)
CMD_PULAR = {"pular", "nao", "n", "sem observacao", "nada"}


@dataclass
class Estado:
    etapa: str = INICIO
    dados: dict[str, Any] = field(default_factory=dict)


@dataclass
class Acao:
    tipo: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Resultado:
    estado: Estado
    respostas: list[str] = field(default_factory=list)
    acoes: list[Acao] = field(default_factory=list)


@dataclass
class Contexto:
    """Informações externas que o motor precisa, mas não calcula."""
    catalogo: list[dict]                       # categorias -> orientações (KnowledgeService)
    dentro_do_horario: bool = True             # WorkingHoursService
    texto_horario: str = "segunda a sexta, das 8h às 18h"
    campos_identificacao: tuple[str, ...] = ("nome", "setor", "email")
    dominios_email: tuple[str, ...] = ()       # vazio = aceita qualquer domínio
    nome_central: str = "Central de TI"


# --------------------------------------------------------------------------
# Utilitários
# --------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def _numero(texto: str) -> int | None:
    t = normalizar(texto).rstrip(".)- ")
    return int(t) if t.isdigit() else None


def _primeiro_nome(dados: dict) -> str:
    nome = dados.get("nome") or ""
    return nome.split()[0] if nome else ""


def _limpar(texto: str) -> str:
    return " ".join((texto or "").split())


# --------------------------------------------------------------------------
# Dados sensíveis: o bot nunca pede e não guarda senhas, códigos MFA ou CPF.
# --------------------------------------------------------------------------
_SENSIVEIS = [
    # "minha senha é X", "senha: X", "password=X" (não pega "minha senha de rede")
    (re.compile(r"\b(senha|password|pwd)(\s*(?:é|eh|:|=)\s*)\S+", re.I), r"\1\2[removido]"),
    # "código de verificação 123456", "token 1234" (não pega códigos de erro como 0x80070005)
    (re.compile(r"\b(c[oó]digo\s+(?:de\s+)?(?:verifica[cç][aã]o|seguran[cç]a|acesso|sms)|token|mfa|otp)"
                r"(\D{0,10})\b\d{4,8}\b", re.I), r"\1\2[removido]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[cpf removido]"),
]

AVISO_SENSIVEL = ("🔒 Removi da mensagem o que parecia ser uma senha, código ou documento. "
                  "A TI *nunca* pede esses dados.")


def mascarar_sensivel(texto: str) -> tuple[str, bool]:
    """Devolve o texto sem senhas/códigos/CPF e se algo foi removido."""
    original = texto or ""
    for padrao, troca in _SENSIVEIS:
        texto = padrao.sub(troca, texto or "")
    return texto, texto != original


# --------------------------------------------------------------------------
# Busca por texto livre (ex.: "erro de acesso", "impressora não imprime")
# --------------------------------------------------------------------------
_STOPWORDS = {
    "de", "da", "do", "das", "dos", "a", "o", "as", "os", "e", "em", "no", "na", "nos",
    "nas", "um", "uma", "para", "pra", "por", "com", "sem", "meu", "minha", "meus",
    "minhas", "que", "nao", "esta", "estou", "ta", "consigo", "conseguir", "quando",
    "como", "ao", "se", "eu", "me", "mim", "isso", "esse", "essa", "ele", "ela", "tem",
    "ter", "muito", "mais", "problema", "ajuda", "preciso", "favor", "ola", "oi", "bom",
    "dia", "tarde", "noite", "aqui", "fica", "ficou", "deu", "dando", "esta", "estao",
}


def _tokens(texto: str) -> list[str]:
    saida = []
    for t in re.findall(r"[a-z0-9]+", normalizar(texto)):
        if len(t) < 3 or t in _STOPWORDS:
            continue
        if len(t) > 4 and t.endswith("s"):
            t = t[:-1]
        saida.append(t)
    return saida


def _pontuar(consulta: list[str], vocabulario: set[str]) -> int:
    pontos = 0
    for q in consulta:
        if q in vocabulario:
            pontos += 2
        elif len(q) >= 4 and any(len(v) >= 4 and v[:5] == q[:5] for v in vocabulario):
            pontos += 1
    return pontos


def buscar_orientacoes(catalogo: list[dict], texto: str, limite: int = 3) -> list[tuple[int, int, int]]:
    """Devolve [(pontos, i_categoria, i_orientacao)] das orientações mais parecidas."""
    consulta = _tokens(texto)
    if not consulta:
        return []
    achados = []
    for ci, cat in enumerate(catalogo):
        base_cat = set(_tokens(cat["nome"]))
        for oi, ori in enumerate(cat["orientacoes"]):
            vocab = base_cat | set(_tokens(ori["titulo"])) | set(_tokens(" ".join(ori.get("palavras_chave", []))))
            pontos = _pontuar(consulta, vocab)
            if pontos:
                achados.append((pontos, ci, oi))
    achados.sort(key=lambda a: (-a[0], a[1], a[2]))
    return achados[:limite]


# --------------------------------------------------------------------------
# Identificação
# --------------------------------------------------------------------------
PERGUNTAS = {
    "nome": "Para começar, qual é o seu *nome completo*?",
    "setor": "Em qual *setor/departamento* você trabalha?",
    "email": "Qual é o seu *e-mail corporativo*?",
    "matricula": "Qual é a sua *matrícula*?",
}

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_campo(campo: str, texto: str, ctx: Contexto) -> tuple[str | None, str]:
    valor = _limpar(texto)
    if campo == "nome":
        if len(valor) < 3 or not any(c.isalpha() for c in valor):
            return None, "Não entendi 🤔 Por favor, digite o seu *nome completo*."
        return valor.title(), ""
    if campo == "setor":
        if len(valor) < 2:
            return None, "Por favor, digite o nome do seu *setor*."
        return valor, ""
    if campo == "email":
        valor = valor.lower()
        if not _RE_EMAIL.match(valor):
            return None, "Esse e-mail não parece válido. Digite o seu *e-mail corporativo* (ex.: nome@empresa.com.br)."
        dominio = valor.rsplit("@", 1)[1]
        if ctx.dominios_email and not any(dominio == d or dominio.endswith("." + d) for d in ctx.dominios_email):
            aceitos = ", ".join("@" + d for d in ctx.dominios_email)
            return None, f"Use o seu e-mail *corporativo* ({aceitos})."
        return valor, ""
    if campo == "matricula":
        valor = valor.upper()
        if not (3 <= len(valor) <= 20 and valor.replace("-", "").isalnum()):
            return None, "Matrícula inválida. Digite apenas letras e números."
        return valor, ""
    return valor or None, "Valor inválido."


def _campo_faltante(estado: Estado, ctx: Contexto) -> str | None:
    for campo in ctx.campos_identificacao:
        if not estado.dados.get(campo):
            return campo
    return None


def identificado(estado: Estado, ctx: Contexto) -> bool:
    return _campo_faltante(estado, ctx) is None


# --------------------------------------------------------------------------
# Textos
# --------------------------------------------------------------------------
def texto_menu(ctx: Contexto) -> str:
    linhas = ["*Como posso te ajudar?* Responda com o número ou *descreva o problema* com as suas palavras:", ""]
    for i, cat in enumerate(ctx.catalogo, start=1):
        emoji = cat.get("emoji", "")
        linhas.append(f"*{i}* - {emoji} {cat['nome']}".replace("  ", " "))
    linhas.append("*0* - 🙋 Falar com a equipe de TI (abrir chamado)")
    linhas.append("")
    linhas.append("_Digite *menu* a qualquer momento para voltar aqui ou *sair* para encerrar._")
    return "\n".join(linhas)


def texto_categoria(cat: dict) -> str:
    linhas = [f"*{cat['nome']}* - qual é a sua situação?", ""]
    for i, ori in enumerate(cat["orientacoes"], start=1):
        linhas.append(f"*{i}* - {ori['titulo']}")
    linhas.append("*0* - ✍️ Não está na lista: falar com a TI")
    linhas.append("")
    linhas.append("_Digite *menu* para voltar._")
    return "\n".join(linhas)


def texto_orientacao(ori: dict) -> str:
    icone = "🚨" if ori.get("prioridade") == "critica" else "📋"
    linhas = [f"{icone} *{ori['titulo']}*", ""]
    for i, passo in enumerate(ori["passos"], start=1):
        linhas.append(f"{i}. {passo}")
    if ori.get("observacao"):
        linhas += ["", f"⚠️ {ori['observacao']}"]
    return "\n".join(linhas)


TEXTO_RESOLVEU = (
    "*Seu problema foi resolvido?*\n\n"
    "*1* - ✅ Sim, resolvido\n"
    "*2* - ❌ Não, abrir um chamado para a TI\n"
    "*3* - ↩ Ver outra orientação deste assunto"
)

TEXTO_AVALIACAO = (
    "Que bom! 🎉 Para melhorarmos o atendimento, avalie de *1* a *5*:\n\n"
    "*1* - 😞 Ruim\n*2* - 🙁\n*3* - 😐\n*4* - 🙂\n*5* - 🤩 Excelente"
)


def texto_pesquisa(protocolo: str) -> str:
    opcoes = "\n".join(f"*{i}* - {emoji} {rotulo}" for i, (_, rotulo, emoji, _) in enumerate(OPCOES_PESQUISA, 1))
    return (f"📋 *Pesquisa de satisfação* do chamado *{protocolo}*\n"
            f"Como você avalia o atendimento da TI?\n\n{opcoes}")


# --------------------------------------------------------------------------
# Motor
# --------------------------------------------------------------------------
def processar(estado: Estado, texto: str, ctx: Contexto) -> Resultado:
    estado = Estado(estado.etapa, dict(estado.dados))  # não muta a entrada
    cmd = normalizar(texto)

    # Chamado aberto: quem responde é a TI (o orquestrador anexa a mensagem ao chamado).
    if estado.etapa == HUMANO:
        return Resultado(estado)

    if identificado(estado, ctx) and estado.etapa not in (INICIO, ENCERRADO, IDENTIFICACAO):
        if cmd in CMD_SAIR:
            return _encerrar(estado, "Atendimento encerrado. Quando precisar, é só chamar! 👋", "cancelada")
        if cmd in CMD_MENU:
            return _ir_menu(estado, ctx)
        if cmd in CMD_ANALISTA and estado.etapa not in (DESCREVER, PESQUISA_OBS):
            return _pedir_descricao(estado, ctx, motivo="colaborador pediu atendimento da TI")

    etapa = estado.etapa
    if etapa in (INICIO, ENCERRADO):
        return _saudacao(estado, ctx)
    if etapa == IDENTIFICACAO:
        return _receber_identificacao(estado, texto, ctx)
    if etapa == MENU:
        return _menu(estado, texto, ctx)
    if etapa == CATEGORIA:
        return _categoria(estado, texto, ctx)
    if etapa == SUGESTOES:
        return _sugestoes(estado, texto, ctx)
    if etapa == RESOLVEU:
        return _resolveu(estado, texto, ctx)
    if etapa == DESCREVER:
        return _receber_descricao(estado, texto, ctx)
    if etapa == AVALIACAO:
        return _avaliacao(estado, texto)
    if etapa == PESQUISA:
        return _pesquisa(estado, texto)
    if etapa == PESQUISA_OBS:
        return _pesquisa_obs(estado, texto)

    # Etapa desconhecida (ex.: mudança de versão): recomeça com segurança.
    estado.etapa = INICIO
    return _saudacao(estado, ctx)


# --- identificação --------------------------------------------------------
def _saudacao(estado: Estado, ctx: Contexto) -> Resultado:
    for k in _TEMPORARIOS:
        estado.dados.pop(k, None)
    if identificado(estado, ctx):
        r = _ir_menu(estado, ctx)
        r.respostas.insert(0, f"Olá, {_primeiro_nome(estado.dados)}! 👋 Aqui é o assistente da *{ctx.nome_central}*.")
        return r
    campo = _campo_faltante(estado, ctx)
    estado.etapa = IDENTIFICACAO
    estado.dados["campo"] = campo
    return Resultado(estado, [
        f"Olá! 👋 Eu sou o assistente virtual da *{ctx.nome_central}*.\n"
        "Vou te passar as orientações padrão para os problemas mais comuns e, se não resolver, "
        "abro um chamado para a equipe de TI.\n\n"
        "🔒 _Nunca envie senhas ou códigos de verificação por aqui._",
        PERGUNTAS[campo],
    ])


def _receber_identificacao(estado: Estado, texto: str, ctx: Contexto) -> Resultado:
    campo = estado.dados.get("campo") or _campo_faltante(estado, ctx)
    if campo is None:
        return _ir_menu(estado, ctx)
    valor, erro = validar_campo(campo, texto, ctx)
    if valor is None:
        return Resultado(estado, [erro])
    estado.dados[campo] = valor
    proximo = _campo_faltante(estado, ctx)
    if proximo:
        estado.dados["campo"] = proximo
        pergunta = PERGUNTAS[proximo]
        if campo == "nome":
            pergunta = f"Prazer, {_primeiro_nome(estado.dados)}! " + pergunta
        return Resultado(estado, [pergunta])
    estado.dados.pop("campo", None)
    r = _ir_menu(estado, ctx)
    r.acoes.insert(0, Acao(ACAO_IDENTIFICADO, {c: estado.dados[c] for c in ctx.campos_identificacao}))
    return r


# --- triagem --------------------------------------------------------------
def _ir_menu(estado: Estado, ctx: Contexto) -> Resultado:
    estado.etapa = MENU
    for k in _TEMPORARIOS:
        estado.dados.pop(k, None)
    return Resultado(estado, [texto_menu(ctx)])


def _menu(estado: Estado, texto: str, ctx: Contexto) -> Resultado:
    n = _numero(texto)
    if n == 0:
        return _pedir_descricao(estado, ctx, motivo="colaborador pediu atendimento da TI no menu")
    if n is not None and 1 <= n <= len(ctx.catalogo):
        return _abrir_categoria(estado, ctx, n - 1)
    if n is None and _tokens(texto):
        return _buscar(estado, texto, ctx, reapresentar=texto_menu(ctx))
    return _opcao_invalida(estado, ctx, texto_menu(ctx))


def _abrir_categoria(estado: Estado, ctx: Contexto, i: int) -> Resultado:
    cat = ctx.catalogo[i]
    estado.dados["categoria"] = i
    estado.dados["tentativas"] = 0
    if not cat["orientacoes"]:
        # Ex.: "Outros": não há procedimento padrão, vai direto para o chamado.
        return _pedir_descricao(estado, ctx, motivo=f"assunto '{cat['nome']}'",
                                prefixo=f"Certo: *{cat['nome']}*.")
    estado.etapa = CATEGORIA
    return Resultado(estado, [texto_categoria(cat)])


def _categoria(estado: Estado, texto: str, ctx: Contexto) -> Resultado:
    cat = _categoria_atual(estado, ctx)
    if cat is None:
        return _ir_menu(estado, ctx)
    n = _numero(texto)
    if n == 0:
        return _pedir_descricao(estado, ctx, motivo=f"situação não listada em '{cat['nome']}'")
    if n is not None and 1 <= n <= len(cat["orientacoes"]):
        return _mostrar_orientacao(estado, ctx, estado.dados["categoria"], n - 1)
    if n is None and _tokens(texto):
        return _buscar(estado, texto, ctx, reapresentar=texto_categoria(cat))
    return _opcao_invalida(estado, ctx, texto_categoria(cat))


def _buscar(estado: Estado, texto: str, ctx: Contexto, reapresentar: str) -> Resultado:
    estado.dados["relato"] = _limpar(texto)[:500]
    achados = buscar_orientacoes(ctx.catalogo, texto)
    if not achados:
        return _opcao_invalida(
            estado, ctx, reapresentar,
            aviso="Não encontrei uma orientação para isso. 😕 Escolha uma opção pelo *número* "
                  "ou digite *0* para abrir um chamado.",
        )
    melhor = achados[0]
    ori_melhor = ctx.catalogo[melhor[1]]["orientacoes"][melhor[2]]
    unico = len(achados) == 1 or melhor[0] >= 2 * achados[1][0]
    if unico or ori_melhor.get("prioridade") == "critica":
        return _mostrar_orientacao(estado, ctx, melhor[1], melhor[2],
                                   prefixo="Encontrei esta orientação para você:")
    estado.etapa = SUGESTOES
    estado.dados["sugestoes"] = [[ci, oi] for _, ci, oi in achados]
    estado.dados["tentativas"] = 0
    return Resultado(estado, [_texto_sugestoes(estado, ctx)])


def _texto_sugestoes(estado: Estado, ctx: Contexto) -> str:
    linhas = ["Encontrei estas orientações. Qual descreve melhor a sua situação?", ""]
    for i, (ci, oi) in enumerate(estado.dados["sugestoes"], start=1):
        linhas.append(f"*{i}* - {ctx.catalogo[ci]['orientacoes'][oi]['titulo']}")
    linhas.append("*0* - ✍️ Nenhuma dessas: falar com a TI")
    return "\n".join(linhas)


def _sugestoes(estado: Estado, texto: str, ctx: Contexto) -> Resultado:
    sugestoes = [s for s in estado.dados.get("sugestoes") or []
                 if 0 <= s[0] < len(ctx.catalogo) and 0 <= s[1] < len(ctx.catalogo[s[0]]["orientacoes"])]
    if not sugestoes:
        return _ir_menu(estado, ctx)
    estado.dados["sugestoes"] = sugestoes
    n = _numero(texto)
    if n == 0:
        return _pedir_descricao(estado, ctx, motivo="nenhuma orientação sugerida serviu")
    if n is not None and 1 <= n <= len(sugestoes):
        ci, oi = sugestoes[n - 1]
        return _mostrar_orientacao(estado, ctx, ci, oi)
    if n is None and _tokens(texto):
        return _buscar(estado, texto, ctx, reapresentar=_texto_sugestoes(estado, ctx))
    return _opcao_invalida(estado, ctx, _texto_sugestoes(estado, ctx))


# --- orientação -----------------------------------------------------------
def _mostrar_orientacao(estado: Estado, ctx: Contexto, ci: int, oi: int, prefixo: str | None = None) -> Resultado:
    cat = ctx.catalogo[ci]
    ori = cat["orientacoes"][oi]
    estado.dados.update(categoria=ci, orientacao=oi, tentativas=0)
    estado.dados.pop("sugestoes", None)
    acoes = [Acao(ACAO_REGISTRAR_ORIENTACAO, {"categoria": cat["nome"], "orientacao": ori["titulo"]})]
    respostas = ([prefixo] if prefixo else []) + [texto_orientacao(ori)]

    if ori.get("prioridade") == "critica":
        # Incidente crítico/segurança: sem passos arriscados, escalonamento imediato.
        r = _abrir_chamado(estado, ctx, motivo=f"incidente crítico: {ori['titulo']}", prioridade="critica")
    elif ori.get("abre_chamado"):
        # Ex.: solicitação de acesso: a orientação explica, mas a TI precisa executar.
        r = _pedir_descricao(estado, ctx, motivo=f"{ori['titulo']} (requer ação da TI)")
    else:
        estado.etapa = RESOLVEU
        return Resultado(estado, respostas + [TEXTO_RESOLVEU], acoes)
    r.respostas = respostas + r.respostas
    r.acoes = acoes + r.acoes
    return r


def _resolveu(estado: Estado, texto: str, ctx: Contexto) -> Resultado:
    n = _numero(texto)
    if n is None:
        c = normalizar(texto)
        n = 1 if c in {"sim", "s", "resolveu", "resolvido"} else 2 if c in {"nao", "n"} else None
    if n == 1:
        estado.etapa = AVALIACAO
        estado.dados["tentativas"] = 0
        return Resultado(estado, [TEXTO_AVALIACAO])
    if n == 2:
        return _pedir_descricao(estado, ctx, motivo="orientação não resolveu")
    if n == 3:
        cat = _categoria_atual(estado, ctx)
        if cat is None:
            return _ir_menu(estado, ctx)
        estado.etapa = CATEGORIA
        return Resultado(estado, [texto_categoria(cat)])
    return _opcao_invalida(estado, ctx, TEXTO_RESOLVEU)


def _avaliacao(estado: Estado, texto: str) -> Resultado:
    n = _numero(texto)
    if n is not None and 1 <= n <= 5:
        r = _encerrar(estado, "Obrigado pela avaliação! Atendimento encerrado. 👋", "resolvida")
        r.acoes.insert(0, Acao(ACAO_REGISTRAR_AVALIACAO, {"nota": n}))
        return r
    estado.dados["tentativas"] = estado.dados.get("tentativas", 0) + 1
    if estado.dados["tentativas"] >= 2:
        return _encerrar(estado, "Tudo bem! Atendimento encerrado. Quando precisar, é só chamar. 👋", "resolvida")
    return Resultado(estado, ["Por favor, responda com um número de *1* a *5*."])


# --- pesquisa de satisfação do chamado --------------------------------------
def _opcao_pesquisa(texto: str) -> int | None:
    n = _numero(texto)
    if n is not None:
        return n - 1 if 1 <= n <= len(OPCOES_PESQUISA) else None
    c = normalizar(texto)
    for i, (_, rotulo, _, _) in enumerate(OPCOES_PESQUISA):
        if c == normalizar(rotulo):
            return i
    return None


def _pesquisa(estado: Estado, texto: str) -> Resultado:
    if normalizar(texto) in CMD_PULAR:
        return _encerrar(estado, "Tudo bem! Atendimento encerrado. Quando precisar, é só chamar. 👋", "escalada")
    i = _opcao_pesquisa(texto)
    if i is None:
        estado.dados["tentativas"] = estado.dados.get("tentativas", 0) + 1
        if estado.dados["tentativas"] >= 3:
            return _encerrar(estado, "Tudo bem, vou encerrar a pesquisa. Se precisar de algo, é só escrever "
                                     "de novo para abrir um novo atendimento. 👋", "escalada")
        protocolo = (estado.dados.get("pesquisa") or {}).get("protocolo", "")
        return Resultado(estado, ["Responda com o *número* de 1 a 4 (ou *pular* para não responder).",
                                  texto_pesquisa(protocolo)])
    valor, rotulo, _, exige = OPCOES_PESQUISA[i]
    estado.etapa = PESQUISA_OBS
    estado.dados["pesquisa_resposta"] = valor
    estado.dados["tentativas"] = 0
    if exige:
        return Resultado(estado, [f"Sentimos muito. 😕 Você marcou *{rotulo}*.\n"
                                  "Conte o que não foi bom para a TI melhorar o atendimento "
                                  "(*obrigatório*):"])
    return Resultado(estado, [f"Obrigado! Você marcou *{rotulo}*. 😊\n"
                              "Quer deixar uma observação? Escreva aqui ou responda *pular*."])


def _pesquisa_obs(estado: Estado, texto: str) -> Resultado:
    valor = estado.dados.get("pesquisa_resposta")
    exige = next((o[3] for o in OPCOES_PESQUISA if o[0] == valor), False)
    observacao = _limpar(texto)
    if not exige and normalizar(observacao) in CMD_PULAR:
        observacao = ""
    elif exige and (len(observacao) < 3 or normalizar(observacao) in CMD_PULAR):
        return Resultado(estado, ["A observação é *obrigatória* quando você está insatisfeito. "
                                  "Conte em poucas palavras o que aconteceu:"])
    pesquisa = estado.dados.get("pesquisa") or {}
    acao = Acao(ACAO_REGISTRAR_PESQUISA, {"chamado": pesquisa.get("chamado"), "resposta": valor,
                                          "observacao": observacao[:1000]})
    r = _encerrar(estado, "Obrigado pela sua avaliação! Ela ajuda a TI a melhorar. Atendimento encerrado. 👋",
                  "escalada")
    r.acoes.insert(0, acao)
    return r


# --- chamado --------------------------------------------------------------
def _pedir_descricao(estado: Estado, ctx: Contexto, motivo: str, prefixo: str | None = None) -> Resultado:
    estado.etapa = DESCREVER
    estado.dados["motivo"] = motivo
    estado.dados["tentativas"] = 0
    texto = ("Vou abrir um chamado para a equipe de TI. 📝\n"
             "Descreva em poucas palavras o que está acontecendo: mensagem de erro, desde quando, "
             "se afeta outras pessoas...\n"
             "_Não informe senhas nem códigos de verificação._")
    if estado.dados.get("relato"):
        texto += "\n\nSe não tiver nada a acrescentar, responda *pular*."
    return Resultado(estado, ([prefixo] if prefixo else []) + [texto])


def _receber_descricao(estado: Estado, texto: str, ctx: Contexto) -> Resultado:
    descricao = _limpar(texto)
    if normalizar(descricao) == "pular" and estado.dados.get("relato"):
        descricao = estado.dados["relato"]
    elif len(descricao) < 5:
        return Resultado(estado, ["Pode descrever um pouco melhor? (ou digite *menu* para voltar)"])
    estado.dados["descricao"] = descricao[:1000]
    ori = _orientacao_atual(estado, ctx)
    prioridade = ori.get("prioridade", "media") if ori else "media"
    return _abrir_chamado(estado, ctx, motivo=estado.dados.get("motivo") or "colaborador pediu atendimento",
                          prioridade=prioridade if prioridade in PRIORIDADES else "media")


def _abrir_chamado(estado: Estado, ctx: Contexto, motivo: str, prioridade: str) -> Resultado:
    cat = _categoria_atual(estado, ctx)
    ori = _orientacao_atual(estado, ctx)
    d = estado.dados
    params = {
        "categoria": cat["nome"] if cat else "",
        "orientacao": ori["titulo"] if ori else "",
        "prioridade": prioridade,
        "motivo": motivo,
        "descricao": d.get("descricao") or d.get("relato") or "",
        "resumo": _resumo(estado, ctx, motivo, prioridade),
    }
    estado.etapa = HUMANO
    for k in ("tentativas", "motivo", "sugestoes", "campo"):
        d.pop(k, None)

    if prioridade == "critica":
        texto = (f"🚨 Abri um chamado *prioritário* para a TI: *{PROTOCOLO}*.\n"
                 "Se puder, conte aqui mais detalhes (o que aconteceu, quando, quem mais foi afetado). "
                 "Tudo vai direto para a equipe.")
    else:
        texto = (f"✅ Abri o chamado *{PROTOCOLO}* para a equipe de TI. "
                 "Você não precisa repetir as informações.")
    if ctx.dentro_do_horario:
        texto += "\n\nUm analista vai continuar o atendimento por aqui. ⏳"
    else:
        texto += (f"\n\n🕒 No momento estamos fora do horário de atendimento ({ctx.texto_horario}). "
                  "O seu chamado ficou na fila e será atendido no próximo horário de suporte. "
                  "As mensagens que você enviar aqui ficam registradas no chamado.")
    return Resultado(estado, [texto], [Acao(ACAO_ABRIR_CHAMADO, params)])


# --- desfechos ------------------------------------------------------------
def _encerrar(estado: Estado, mensagem: str, resultado: str) -> Resultado:
    estado.etapa = ENCERRADO
    for k in _TEMPORARIOS:
        estado.dados.pop(k, None)
    return Resultado(estado, [mensagem], [Acao(ACAO_ENCERRAR, {"resultado": resultado})])


def _opcao_invalida(estado: Estado, ctx: Contexto, reapresentar: str,
                    aviso: str = "Opção inválida. Responda com o *número* da opção ou descreva o problema.") -> Resultado:
    estado.dados["tentativas"] = estado.dados.get("tentativas", 0) + 1
    if estado.dados["tentativas"] >= MAX_TENTATIVAS_INVALIDAS:
        return _pedir_descricao(estado, ctx, motivo="não encontrou a opção após várias tentativas",
                                prefixo="Parece que não encontrei a opção certa para você. 😕")
    return Resultado(estado, [aviso, reapresentar])


def _categoria_atual(estado: Estado, ctx: Contexto) -> dict | None:
    i = estado.dados.get("categoria")
    if isinstance(i, int) and 0 <= i < len(ctx.catalogo):
        return ctx.catalogo[i]
    return None


def _orientacao_atual(estado: Estado, ctx: Contexto) -> dict | None:
    cat = _categoria_atual(estado, ctx)
    j = estado.dados.get("orientacao")
    if cat is not None and isinstance(j, int) and 0 <= j < len(cat["orientacoes"]):
        return cat["orientacoes"][j]
    return None


def _resumo(estado: Estado, ctx: Contexto, motivo: str, prioridade: str) -> str:
    d = estado.dados
    cat = _categoria_atual(estado, ctx)
    ori = _orientacao_atual(estado, ctx)
    linhas = [
        "Resumo do assistente da Central de TI",
        f"Colaborador: {d.get('nome', '-')}",
        f"Setor: {d.get('setor', '-')}",
    ]
    if d.get("email"):
        linhas.append(f"E-mail: {d['email']}")
    if d.get("matricula"):
        linhas.append(f"Matrícula: {d['matricula']}")
    linhas += [
        f"Assunto: {cat['nome'] if cat else '-'}",
        f"Orientação vista: {ori['titulo'] if ori else '-'}",
        f"Relato inicial: {d.get('relato') or '-'}",
        f"Descrição: {d.get('descricao') or '-'}",
        f"Prioridade: {prioridade}",
        f"Motivo: {motivo}",
    ]
    return "\n".join(linhas)
