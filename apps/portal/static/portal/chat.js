(function () {
  "use strict";
  // Nome do cookie CSRF vem da página (configurável no .env); padrão do Django: csrftoken.
  const NOME_COOKIE_CSRF = (document.querySelector('meta[name="csrf-cookie"]') || {}).content || "csrftoken";

  const lista = document.getElementById("mensagens");
  const opcoes = document.getElementById("opcoes");
  const form = document.getElementById("form");
  const campo = document.getElementById("texto");
  const botao = document.getElementById("enviar");
  const faixa = document.getElementById("faixa-chamado");

  let ultimoId = 0;
  let enviando = false;
  let digitando = null;

  const NOMES = { bot: "Assistente", analista: "Analista de TI", sistema: "Central de TI" };

  function cookie(nome) {
    const m = document.cookie.match(new RegExp("(?:^|; )" + nome + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }

  function novoId() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 12);
  }

  // Formatação no estilo WhatsApp: *negrito*, _itálico_, quebras de linha. Sempre escapa HTML.
  function formatar(texto) {
    const seguro = texto
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    return seguro
      .replace(/\*([^*\n]+)\*/g, "<strong>$1</strong>")
      .replace(/(^|[\s(])_([^_\n]+)_(?=[\s).,!?:;]|$)/g, "$1<em>$2</em>")
      .replace(/\n/g, "<br>");
  }

  function rolar() { lista.scrollTop = lista.scrollHeight; }

  function adicionar(m) {
    const div = document.createElement("div");
    div.className = "msg " + m.autor;
    let html = "";
    if (m.autor === "analista") html += '<span class="quem">' + formatar(m.analista || NOMES.analista) + " · TI</span>";
    html += formatar(m.texto) + '<span class="hora">' + m.hora + "</span>";
    div.innerHTML = html;
    lista.appendChild(div);
  }

  // Botões de resposta rápida a partir das linhas "*N* - texto" da última mensagem do assistente.
  function atualizarOpcoes(ultima) {
    opcoes.innerHTML = "";
    if (!ultima || ultima.autor !== "bot") return;
    const re = /^\*(\d+)\* - (.+)$/gm;
    let m;
    while ((m = re.exec(ultima.texto)) !== null) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = m[1] + " · " + m[2].replace(/\*/g, "");
      b.dataset.valor = m[1];
      b.addEventListener("click", () => enviar(b.dataset.valor));
      opcoes.appendChild(b);
    }
  }

  function atualizarEstado(estado) {
    const c = estado && estado.chamado;
    if (c) {
      faixa.hidden = false;
      faixa.textContent = "📄 Chamado " + c.protocolo + " · " + c.status + " · prioridade " + c.prioridade.toLowerCase();
    } else {
      faixa.hidden = true;
    }
  }

  function aplicar(dados) {
    let ultima = null;
    (dados.mensagens || []).forEach((m) => {
      if (m.id <= ultimoId) return;
      adicionar(m);
      ultimoId = m.id;
      ultima = m;
    });
    if (ultima) { atualizarOpcoes(ultima); rolar(); }
    atualizarEstado(dados.estado);
  }

  function mostrarDigitando(sim) {
    if (sim && !digitando) {
      digitando = document.createElement("div");
      digitando.className = "digitando";
      digitando.textContent = "Assistente digitando…";
      lista.appendChild(digitando);
      rolar();
    } else if (!sim && digitando) {
      digitando.remove();
      digitando = null;
    }
  }

  function erro(texto) {
    const p = document.createElement("p");
    p.className = "erro";
    p.textContent = texto;
    lista.appendChild(p);
    rolar();
  }

  async function buscar() {
    try {
      const r = await fetch("api/mensagens/?depois=" + ultimoId, { credentials: "same-origin" });
      if (r.ok) aplicar(await r.json());
    } catch (e) { /* sem rede: tenta de novo no próximo ciclo */ }
  }

  async function enviar(texto) {
    texto = (texto || "").trim();
    if (!texto || enviando) return;
    enviando = true;
    botao.disabled = true;
    opcoes.innerHTML = "";
    mostrarDigitando(true);
    try {
      const r = await fetch("api/enviar/", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": cookie(NOME_COOKIE_CSRF) },
        body: JSON.stringify({ texto: texto, id: novoId(), depois: ultimoId }),
      });
      const dados = await r.json().catch(() => ({}));
      mostrarDigitando(false);
      if (!r.ok) { erro(dados.erro || "Não foi possível enviar. Tente novamente."); return; }
      campo.value = "";
      ajustarAltura();
      aplicar(dados);
    } catch (e) {
      mostrarDigitando(false);
      erro("Sem conexão. Verifique a internet e tente novamente.");
    } finally {
      enviando = false;
      botao.disabled = false;
      campo.focus();
    }
  }

  function ajustarAltura() {
    campo.style.height = "auto";
    campo.style.height = Math.min(campo.scrollHeight, 140) + "px";
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); enviar(campo.value); });
  campo.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(campo.value); }
  });
  campo.addEventListener("input", ajustarAltura);

  buscar();
  // Busca respostas da equipe de TI periodicamente (só com a aba visível).
  setInterval(() => { if (!document.hidden && !enviando) buscar(); }, 4000);
})();
