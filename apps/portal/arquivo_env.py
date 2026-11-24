"""
Lê e grava valores no .env (Python puro: funciona antes do Django carregar, ex.: no preparar.py).

Mantém comentários e a ordem das linhas; um valor novo vai para o fim do arquivo.
"""
from __future__ import annotations

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
ARQUIVO = BASE_DIR / ".env"
EXEMPLO = BASE_DIR / ".env.example"
# Textos de exemplo do .env.example: contam como "não preenchido".
EXEMPLOS = ("suaempresa", "cole-aqui", "gere-um", "troque")


def _linha_da_chave(chave: str):
    return re.compile(rf"^\s*{re.escape(chave)}\s*=")


def ler(chave: str, arquivo: Path = ARQUIVO) -> str:
    """Valor da chave no .env ("" se não existe ou ainda é o texto de exemplo)."""
    if not arquivo.exists():
        return ""
    padrao = _linha_da_chave(chave)
    for linha in arquivo.read_text(encoding="utf-8-sig").splitlines():
        if padrao.match(linha):
            valor = linha.split("=", 1)[1].strip()
            return "" if any(e in valor.lower() for e in EXEMPLOS) else valor
    return ""


def gravar(chave: str, valor: str, arquivo: Path = ARQUIVO, comentario: str = "") -> None:
    """Troca o valor da chave (ou acrescenta no fim, com um comentário opcional)."""
    valor = str(valor).replace("\n", " ").strip()
    linhas = arquivo.read_text(encoding="utf-8-sig").splitlines() if arquivo.exists() else []
    padrao = _linha_da_chave(chave)
    for i, linha in enumerate(linhas):
        if padrao.match(linha):
            linhas[i] = f"{chave}={valor}"
            break
    else:
        if comentario:
            linhas += ["", f"# {comentario}"]
        linhas.append(f"{chave}={valor}")
    arquivo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
