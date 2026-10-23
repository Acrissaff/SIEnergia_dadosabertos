"""Gera versões `.txt` dos documentos em `docs/`.

O Markdown é legível cru, mas exige do leitor a tradução mental da marcação: `**` some,
`|` vira coluna, `` ` `` desaparece. Para quem recebe o documento por e-mail e o abre no
Bloco de Notas, isso atrapalha justamente as tabelas — que é onde está a informação.

A conversão faz o que um leitor de Markdown faria: alinha as tabelas em colunas de
largura fixa, sublinha os títulos, indenta blocos de código e citações, e remove a
marcação de ênfase. Não é um conversor de Markdown de uso geral — cobre a marcação que
estes quatro documentos usam, e nada mais.

É um derivado: os `.md` continuam sendo a fonte. Reexecute depois de editá-los.

Uso:
    python docs_para_txt.py
    python docs_para_txt.py --docs outra/pasta
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

# CRLF e BOM: o Bloco de Notas do Windows é o destino provável, e é o que ele espera
# para exibir acentuação e quebras de linha corretamente.
CODIFICACAO = "utf-8-sig"
QUEBRA = "\r\n"

SUBLINHADO = {1: "=", 2: "-", 3: "."}

# Ênfase e código inline não têm equivalente em texto puro: o que importa é a palavra.
# Links viram "texto (destino)" — o destino é um arquivo vizinho, útil de ver.
MARCACAO = [
    (re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), r"\1 (\2)"),
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),
    (re.compile(r"(?<!\w)_(.+?)_(?!\w)"), r"\1"),
    (re.compile(r"`([^`]+)`"), r"\1"),
    # A conversão é linha a linha, então uma marcação que atravessa a quebra deixaria
    # as duas metades do delimitador para trás. Como `**` e `` ` `` nunca são literais
    # nestes textos, o que sobrou do par é resíduo e sai. O `_` não recebe o mesmo
    # tratamento: ele aparece dentro de nomes de coluna (`producao_t`).
    (re.compile(r"\*\*|`"), ""),
]

LINHA_TABELA = re.compile(r"^\s*\|.*\|\s*$")
# O traço é obrigatório: sem ele, uma linha de cabeçalho vazia (`| | |`) — que estes
# documentos usam nas tabelas de duas colunas sem título — seria lida como separador.
SEPARADOR_TABELA = re.compile(r"^\s*\|[\s:|-]*-[\s:|-]*\|\s*$")
REGUA = re.compile(r"^\s*(---+|\*\*\*+|___+)\s*$")
TITULO = re.compile(r"^(#{1,6})\s+(.*)$")


def _limpar(texto: str, irmaos: re.Pattern | None = None) -> str:
    for padrao, troca in MARCACAO:
        texto = padrao.sub(troca, texto)
    # Quem recebe só o pacote .txt não tem os .md para abrir: a remissão tem de apontar
    # para o arquivo que existe ao lado.
    if irmaos is not None:
        texto = irmaos.sub(lambda m: m.group(1) + ".txt", texto)
    return texto.rstrip()


def _celulas(linha: str, irmaos: re.Pattern | None = None) -> list[str]:
    return [_limpar(c.strip(), irmaos) for c in linha.strip().strip("|").split("|")]


def _tabela(linhas: list[str], irmaos: re.Pattern | None = None) -> list[str]:
    """Alinha uma tabela de canos em colunas de largura fixa.

    A primeira linha é o cabeçalho e a segunda, o separador de alinhamento do Markdown,
    que não carrega informação e é descartada — no lugar dela entra uma régua da largura
    real da tabela.
    """
    grade = [_celulas(l, irmaos) for l in linhas if not SEPARADOR_TABELA.match(l)]
    if not grade:
        return []

    # Tabelas com células a menos numa linha existem; a largura é a do maior.
    colunas = max(len(l) for l in grade)
    grade = [l + [""] * (colunas - len(l)) for l in grade]
    larguras = [max(len(l[i]) for l in grade) for i in range(colunas)]

    def formatar(celulas: list[str]) -> str:
        # A última coluna não é preenchida à direita: evita espaços no fim da linha.
        partes = [c.ljust(larguras[i]) for i, c in enumerate(celulas[:-1])]
        return "  ".join(partes + [celulas[-1]]).rstrip()

    cabecalho = formatar(grade[0])
    regua = "  ".join("-" * l for l in larguras).rstrip()
    corpo = ["  " + formatar(l) for l in grade[1:]]

    # Tabela de duas colunas usada como ficha (rótulo/valor): o cabeçalho é vazio de
    # propósito. Imprimir a régua ali separaria a primeira ficha das demais, sugerindo
    # que ela é o título da tabela.
    if not cabecalho:
        return corpo
    return ["  " + cabecalho, "  " + regua] + corpo


def converter(markdown: str, irmaos: re.Pattern | None = None) -> str:
    linhas = markdown.splitlines()
    saida: list[str] = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]

        # Blocos de código saem literais: contêm diagramas e fórmulas em que cada
        # caractere posicionado importa. Só a cerca some, trocada por indentação.
        if linha.lstrip().startswith("```"):
            i += 1
            while i < len(linhas) and not linhas[i].lstrip().startswith("```"):
                saida.append(("    " + linhas[i]).rstrip())
                i += 1
            i += 1
            continue

        if LINHA_TABELA.match(linha):
            bloco = []
            while i < len(linhas) and LINHA_TABELA.match(linhas[i]):
                bloco.append(linhas[i])
                i += 1
            saida.extend(_tabela(bloco, irmaos))
            continue

        if m := TITULO.match(linha):
            nivel, texto = len(m.group(1)), _limpar(m.group(2), irmaos)
            if saida and saida[-1]:
                saida.append("")
            if nivel == 1:
                texto = texto.upper()
            saida.append(texto)
            if nivel in SUBLINHADO:
                saida.append(SUBLINHADO[nivel] * len(texto))
            i += 1
            continue

        if REGUA.match(linha):
            saida.append("-" * 78)
            i += 1
            continue

        if linha.lstrip().startswith(">"):
            saida.append("    " + _limpar(re.sub(r"^\s*>\s?", "", linha), irmaos))
            i += 1
            continue

        saida.append(_limpar(linha, irmaos))
        i += 1

    # Colapsa as linhas em branco que a inserção de títulos pode ter duplicado.
    enxuto: list[str] = []
    for linha in saida:
        if linha or (enxuto and enxuto[-1]):
            enxuto.append(linha)
    return QUEBRA.join(enxuto).strip() + QUEBRA


def main() -> None:
    p = argparse.ArgumentParser(description="Gera versões .txt dos documentos")
    p.add_argument("--docs", type=Path, default=Path(__file__).parent / "docs")
    args = p.parse_args()

    arquivos = sorted(args.docs.glob("*.md"))
    if not arquivos:
        print(f"Nenhum .md em {args.docs}")
        return

    # Só os documentos que de fato serão convertidos: uma remissão a um `.md` que
    # continua só em Markdown deve permanecer apontando para ele.
    irmaos = re.compile(r"\b(" + "|".join(re.escape(md.stem) for md in arquivos)
                        + r")\.md\b")

    for md in arquivos:
        txt = md.with_suffix(".txt")
        texto = converter(md.read_text(encoding="utf-8"), irmaos)
        # `newline=""` desliga a tradução de fim de linha do Windows: o texto já vem
        # com CRLF, e sem isso o `\n` seria expandido de novo, gerando `\r\r\n`.
        txt.write_text(texto, encoding=CODIFICACAO, newline="")
        print(f"  {md.name:<32} -> {txt.name:<32} {txt.stat().st_size:>8,} bytes")

    print(f"\n{len(arquivos)} arquivo(s) em {args.docs}")


if __name__ == "__main__":
    main()
