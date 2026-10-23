"""Dimensões do modelo.

Cada função reproduz uma query do Power Query. Quando o M faz uma transformação que
não é óbvia — divisão do `pci`, join para trazer `rotas_possiveis` — o motivo está
comentado no ponto em que ocorre.
"""

from __future__ import annotations

import pandas as pd

from leitura import ler_csv


def dim_rota() -> pd.DataFrame:
    """Rotas tecnológicas possíveis por energético (4 linhas)."""
    df = ler_csv("dim_rota.csv")
    return df.astype({"cd_rota": "Int64"})


def dim_energetico() -> pd.DataFrame:
    """Energéticos, com a rota possível trazida de `dim_rota`.

    Este arquivo é o único do conjunto que usa ponto como separador decimal — o
    leitor já trata isso. `materia_seca` entra na fórmula do `qct`.
    """
    df = ler_csv("dim_energetico.csv")
    df = df.astype({
        "cd_energetico": "Int64",
        "teor_mo": "float64",
        "materia_seca": "float64",
        "cd_subclasse": "Int64",
        "cd_rota": "Int64",
    })
    return df.merge(dim_rota()[["cd_rota", "rotas_possiveis"]], on="cd_rota", how="left")


def dim_combustivel() -> pd.DataFrame:
    """Combustíveis e seus poderes caloríficos.

    O `pci` é dividido por 10.000, convertendo kcal/kg em fator tep (8550 -> 0,855).
    Toda a cadeia de ktep depende disso, e aplicar a divisão duas vezes é um erro
    silencioso — por isso ela está isolada aqui e coberta por `_conferir_pci`.
    """
    df = ler_csv("dim_combustivel.csv")
    df = df.astype({"cd_combustivel": "Int64"})

    # O M usa Table.ReplaceErrorValues: valores não numéricos viram nulo em vez de
    # abortar a carga. `errors="coerce"` é o equivalente em pandas.
    for col in ("densidade", "pcs", "pci"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["pci"] = df["pci"] / 10_000
    _conferir_pci(df)
    return df


def _conferir_pci(df: pd.DataFrame) -> None:
    """Sanidade: após a divisão, o pci é um fator tep e deve ficar abaixo de 1,5."""
    excedentes = df.loc[df["pci"] > 1.5, ["cd_combustivel", "combustivel", "pci"]]
    if not excedentes.empty:
        raise ValueError(
            "pci fora da faixa esperada de fator tep — a divisão por 10.000 pode ter "
            f"sido aplicada duas vezes ou nenhuma:\n{excedentes}"
        )


def dim_produto() -> pd.DataFrame:
    """Produtos agropecuários (209 linhas)."""
    df = ler_csv("dim_produto.csv")
    return df.astype({"cd_subclasse": "Int64", "cd_produto": "Int64"})


def dim_mu() -> pd.DataFrame:
    """Municípios. Os renomes reproduzem os do M, usados nas medidas de exibição."""
    df = ler_csv("dim_mu.csv")
    df = df.astype({"cd_mu": "Int64", "cd_micro": "Int64", "cd_meso": "Int64", "cd_uf": "Int64"})
    return df.rename(columns={"uf_sigla": "UF", "municipio": "Municipio", "uf": "uf_nome"})


def dim_ano() -> pd.DataFrame:
    df = ler_csv("dim_ano.csv")
    return df.astype({"ano": "Int64", "ano_i": "Int64", "ano_f": "Int64", "ano_base": "Int64"})


def dim_subclasse() -> pd.DataFrame:
    """Classificação CNAE dos produtos. `s4_divisao` e `s5_secao` filtram medidas."""
    df = ler_csv("dim_subclasse.csv")
    return df.astype({"cd_subclasse": "Int64"})


def dim_rotas_possiveis(rotas_observadas: list[str]) -> pd.DataFrame:
    """Índice das rotas possíveis observadas em `fato_energetico`.

    Recebe os valores distintos já na ordem de primeira aparição no fato, que é como
    o `Table.Distinct` do M os produz.

    Duas fidelidades deliberadas ao M, ambas questionáveis mas mantidas:

    - O filtro `<> "N"` não casa com nenhum valor real (os valores são "Densificação",
      "Biodigestão", "Biod. e Densif." e "Nenhuma"). É provável resíduo de uma versão
      anterior da query. Replicado como está, então "Nenhuma" permanece na dimensão.
    - `cd_rotas_possiveis` vem de um índice sequencial sobre a ordem das linhas, logo
      não é estável entre cargas: se a ordem do arquivo-fonte mudar, os códigos mudam.
    """
    rotas = [r for r in rotas_observadas if r != "N"]
    return pd.DataFrame({
        "rotas_possiveis": rotas,
        "cd_rotas_possiveis": range(1, len(rotas) + 1),
    })
