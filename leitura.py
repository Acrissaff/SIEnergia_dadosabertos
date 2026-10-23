"""Leitores no padrão do Power Query.

Cada `Csv.Document` do modelo declara seu próprio `Encoding`, então cada leitor carrega
os parâmetros da sua fonte em vez de assumir um padrão único. Reproduzir isso
exatamente é pré-requisito de fidelidade.

O separador decimal, esse sim, é uniforme: vírgula em todo o `csv_exportado`.
`dim_energetico.csv` era a exceção — gravava `0.9` —, e o ponto era lido pelo Power
Query como separador de milhar, inflando `materia_seca` em até 1000×. O arquivo foi
regravado com vírgula em 01/09/2026; ver `docs/ERRO_MATERIA_SECA.md`.
"""

from __future__ import annotations

import pandas as pd

from config import BIS_OUTPUTS

# Encoding declarado no M por arquivo. 65001 = UTF-8, 1252 = Windows-1252.
#
# `fatos_hist_mu_mod.csv` é a exceção: o M declara 1252, mas o arquivo tem BOM UTF-8.
# Ler como 1252 transformaria o primeiro cabeçalho em "ï»¿cd_mu" e quebraria o acesso
# à coluna `cd_mu`. Usamos utf-8-sig, que consome o BOM.
ENCODINGS = {
    "fatos_hist_mu_mod.csv": "utf-8-sig",
    "fatores_produto_energetico.csv": "utf-8",
    "fatores_energetico_combustivel.csv": "utf-8",
    "dim_energetico.csv": "utf-8",
    "dim_rota.csv": "utf-8",
    "dim_combustivel.csv": "utf-8",
    "dim_produto.csv": "utf-8",
    "dim_mu.csv": "utf-8",
    "dim_subclasse.csv": "utf-8",
    "dim_ano.csv": "cp1252",
}

def ler_csv(nome: str, **kwargs) -> pd.DataFrame:
    """Lê um CSV de `csv_exportado` com os parâmetros declarados no Power Query."""
    return pd.read_csv(
        BIS_OUTPUTS / nome,
        sep=";",
        decimal=",",
        encoding=ENCODINGS[nome],
        **kwargs,
    )


def ler_csv_em_blocos(nome: str, tamanho: int, **kwargs):
    """Itera um CSV em blocos, mantendo os mesmos parâmetros de `ler_csv`."""
    return pd.read_csv(
        BIS_OUTPUTS / nome,
        sep=";",
        decimal=",",
        encoding=ENCODINGS[nome],
        chunksize=tamanho,
        **kwargs,
    )
