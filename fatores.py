"""Tabelas de fatores de conversão.

`fator_produto_energetico` e `fator_energetico_combustivel` são queries auxiliares do
modelo: existem no Power Query mas não são carregadas, então não aparecem na lista de
tabelas do PBI. `fator_rota` é carregada e pondera as rotas por cenário.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import (
    BIOD_E_DENSIF,
    BIODIGESTAO,
    BIOMETANO,
    BRIQUETE,
    DENSIFICACAO,
    DIM_ROTA_CENARIO,
    MEIO_A_MEIO,
)
from dimensoes import dim_combustivel, dim_energetico
from leitura import ler_csv


def fator_produto_energetico() -> pd.DataFrame:
    """Rendimento de coproduto e taxa de coleta por par produto/energético.

    68 linhas cobrindo 45 dos 209 produtos — o join com o fato é `inner`, então os
    164 produtos sem fator são descartados da cadeia energética.
    """
    df = ler_csv("fatores_produto_energetico.csv")
    df = df.astype({
        "fcoprod": "float64",
        "fcoleta": "float64",
        "cd_produto": "Int64",
        "cd_energetico": "Int64",
    })
    return df.sort_values("cd_energetico", kind="stable")


def fator_energetico_combustivel() -> pd.DataFrame:
    """Densificação e metanização por par energético/combustível, com a rota derivada.

    `fdens` e `fmetanizacao` são mutuamente exclusivos nos dados (verificado: 0 casos
    de coexistência em 47 linhas), então a rota é sempre determinística e o ramo
    `else None` nunca é alcançado na base atual. Ele é mantido porque é o que o M faz
    e porque um fator futuro preenchido nas duas colunas deve produzir rota nula em
    vez de ser classificado errado.
    """
    df = ler_csv("fatores_energetico_combustivel.csv")
    df = df.astype({
        "fdens": "float64",
        "fmetanizacao": "float64",
        "cd_energetico": "Int64",
        "cd_combustivel": "Int64",
    })
    df["rota_modelo"] = np.select(
        [df["fmetanizacao"].isna(), df["fdens"].isna()],
        [DENSIFICACAO, BIODIGESTAO],
        default=None,
    )
    return df


def fator_rota(rotas_possiveis: pd.DataFrame) -> pd.DataFrame:
    """Peso de cada combinação combustível x rota possível x cenário de rota.

    Constrói o produto cartesiano das combinações reais de (combustível, rota
    possível) com os três cenários e zera as combinações incoerentes — não faz
    sentido produzir briquete numa rota de biodigestão, nem biometano numa rota de
    densificação.
    """
    fec = fator_energetico_combustivel()

    pares = (
        fec.merge(dim_energetico()[["cd_energetico", "rotas_possiveis"]],
                  on="cd_energetico", how="left")
        [["cd_combustivel", "rotas_possiveis"]]
        .drop_duplicates()
    )

    pares = pares.merge(rotas_possiveis, on="rotas_possiveis", how="left")
    pares = pares.merge(dim_combustivel()[["cd_combustivel", "combustivel"]],
                        on="cd_combustivel", how="left")

    cenarios = pd.DataFrame(DIM_ROTA_CENARIO)[["cd_rota_cenario", "rota_cenario"]]
    df = pares.merge(cenarios, how="cross")

    df = df.sort_values(["rota_cenario", "rotas_possiveis", "combustivel"], kind="stable")
    df = df[["cd_rota_cenario", "rota_cenario", "cd_combustivel",
             "rotas_possiveis", "cd_rotas_possiveis", "combustivel"]]

    cenario, rota, comb = df["rota_cenario"], df["rotas_possiveis"], df["combustivel"]
    df["fator_rota"] = np.select(
        [
            (cenario == BIODIGESTAO) & (rota == BIOD_E_DENSIF) & (comb == BRIQUETE),
            (rota == BIODIGESTAO) & (comb == BRIQUETE),
            (rota == DENSIFICACAO) & (comb == BIOMETANO),
            (cenario == DENSIFICACAO) & (rota == BIOD_E_DENSIF) & (comb == BIOMETANO),
            (cenario == MEIO_A_MEIO) & (rota == BIOD_E_DENSIF),
        ],
        [0.0, 0.0, 0.0, 0.0, 0.5],
        default=1.0,
    )

    # O M troca 0 por nulo para que o DAX devolva BLANK() em vez de zero. Para somas
    # dá no mesmo, mas é o que faz [RCald_]/[RTurb_] distinguirem sólido de gás — um
    # combustível zerado não deve contar como presente.
    df["fator_rota"] = df["fator_rota"].replace(0.0, np.nan)
    return df.reset_index(drop=True)
