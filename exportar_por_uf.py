"""Recorta a tabela de dados abertos em um arquivo por UF.

O arquivo nacional tem 1,09 GB e 6,2 milhões de linhas — mais do que o Excel abre e mais
do que a maioria dos destinatários precisa. Quem trabalha com um estado quer o recorte
daquele estado.

O recorte é feito sobre o arquivo já publicado, não sobre a fonte: os valores são
idênticos aos nacionais por construção, sem risco de as duas versões divergirem. O
formato de saída é o mesmo em tudo (colunas, separador, decimal, codificação, fim de
linha), então um leitor que abra qualquer um dos arquivos vê a mesma coisa.

Uma passada só sobre o arquivo grande, com um descritor aberto por UF: ler 27 vezes
levaria 27 vezes mais tempo, e carregá-lo inteiro na memória não é opção.

Uso:
    python exportar_por_uf.py
    python exportar_por_uf.py --uf MT SP GO
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd

from config import CSV_SAIDA, SAIDA
from dados_abertos import ARQUIVO_SAIDA

PASTA_UF = "uf"
TAMANHO_BLOCO = 500_000

# Espelha o que `to_csv` produz ao escrever direto num caminho no Windows. Aqui a
# escrita é feita por descritor aberto pelo script, que não faz essa tradução — sem o
# `lineterminator` explícito os recortes sairiam com LF e o nacional com CRLF.
FIM_DE_LINHA = "\r\n"

LEITURA = {"sep": CSV_SAIDA["sep"], "decimal": CSV_SAIDA["decimal"],
           "encoding": "utf-8-sig"}
ESCRITA = {k: v for k, v in CSV_SAIDA.items() if k != "encoding"}


def exportar(saida: Path, ufs: list[str] | None = None) -> pd.DataFrame:
    origem = saida / ARQUIVO_SAIDA
    if not origem.exists():
        raise SystemExit(f"{origem} não existe — rode `python dados_abertos.py` antes.")

    destino = saida / PASTA_UF
    destino.mkdir(parents=True, exist_ok=True)

    nome = Path(ARQUIVO_SAIDA).stem
    descritores: dict[str, object] = {}
    linhas: dict[str, int] = {}

    try:
        for bloco in pd.read_csv(origem, chunksize=TAMANHO_BLOCO, **LEITURA):
            if ufs:
                bloco = bloco[bloco["uf"].isin(ufs)]
            for uf, parte in bloco.groupby("uf", sort=False):
                if uf not in descritores:
                    # `utf-8-sig` grava o BOM na primeira escrita do descritor. Se cada
                    # bloco reabrisse o arquivo em modo de anexação, o BOM voltaria no
                    # meio do arquivo; manter o descritor aberto resolve.
                    descritores[uf] = open(
                        destino / f"{nome}_{uf}.csv", "w",
                        encoding="utf-8-sig", newline="",
                    )
                    linhas[uf] = 0
                parte.to_csv(descritores[uf], header=linhas[uf] == 0,
                             lineterminator=FIM_DE_LINHA, **ESCRITA)
                linhas[uf] += len(parte)
    finally:
        for d in descritores.values():
            d.close()

    resumo = pd.DataFrame(
        [{"uf": uf,
          "linhas": n,
          "bytes": (destino / f"{nome}_{uf}.csv").stat().st_size}
         for uf, n in sorted(linhas.items())]
    )
    return resumo


def main() -> None:
    p = argparse.ArgumentParser(description="Gera um recorte da tabela por UF")
    p.add_argument("--saida", type=Path, default=SAIDA)
    p.add_argument("--uf", nargs="*", default=None,
                   help="siglas a exportar; sem isto, exporta todas")
    args = p.parse_args()

    inicio = time.time()
    print(f"Recortando {ARQUIVO_SAIDA} por UF em {args.saida / PASTA_UF}\n")
    resumo = exportar(args.saida, [u.upper() for u in args.uf] if args.uf else None)

    for _, r in resumo.iterrows():
        print(f"  {r.uf}  {r.linhas:>9,} linhas  {r.bytes / 1e6:>8,.1f} MB")

    print(f"\n{len(resumo)} arquivos | {resumo.linhas.sum():,} linhas | "
          f"{resumo.bytes.sum() / 1e9:.2f} GB")
    print(f"Concluído em {time.time() - inicio:.0f}s")


if __name__ == "__main__":
    main()
