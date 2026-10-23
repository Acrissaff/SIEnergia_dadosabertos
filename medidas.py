"""Medidas DAX portadas para pandas.

Medidas DAX dependem do contexto de filtro do visual que as consome, o que não tem
equivalente direto fora do Power BI. O porte resolve isso com uma função-núcleo,
`base_combustivel`, que materializa o grão `grupo x cd_combustivel` e devolve todas as
grandezas derivadas de uma vez; as medidas viram agregações sobre essa base.

O recorte é explícito: `grupo` são as colunas de quebra, `filtros` o contexto e
`cd_rota_cenario` o cenário de rota. No DAX esse último vem de
`HASONEVALUE(dim_rota_cenario[rota_cenario])`, ou seja, a medida só existe com um
cenário selecionado — aqui ele é parâmetro obrigatório, sem default silencioso.

Não portadas: `UF Selecionada`, `Ano Selecionado`, `Rotas`, `F.Coprod.`, `M.Seca` e
similares só produzem texto de cabeçalho a partir de `HASONEVALUE`/`DISTINCTCOUNT`, e
`Geração (kg/hab/dia)` depende de `fato_populacao_mu`, que está fora do escopo.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    BIOMETANO_KTEP_POR_MM3,
    FATOR_CAPACIDADE,
    GWH_PARA_TJ,
    HORAS_ANO,
    KTEP_PARA_GWH,
    KTEP_PARA_TJ,
    RENDIMENTO_CALDEIRA,
    RENDIMENTO_ELETRICO,
    SAIDA,
)
from dimensoes import dim_combustivel, dim_produto, dim_subclasse

# Só o necessário para as medidas — `fato_combustivel` tem dezenas de milhões de linhas
# e carregar as colunas de fator (`fdens`, `fmetanizacao`) não agrega nada aqui.
COLUNAS_COMBUSTIVEL = ["cd_mu", "ano", "cd_energetico", "rotas_possiveis",
                       "cd_combustivel", "qct", "vct"]
COLUNAS_PRODUTO = ["cd_mu", "cd_produto", "ano", "area_ha", "producao_t", "rebanho"]
COLUNAS_ENERGETICO = ["cd_mu", "ano", "cd_energetico", "q_coproduto", "q_energetico"]


def _ler(caminho: Path, colunas: list[str] | None = None) -> pd.DataFrame:
    return pd.read_csv(caminho, sep=";", decimal=",", encoding="utf-8-sig", usecols=colunas)


def _aplicar(df: pd.DataFrame, filtros: dict | None) -> pd.DataFrame:
    """Aplica o contexto de filtro. Valor escalar ou lista de valores aceitos."""
    if not filtros:
        return df
    mascara = pd.Series(True, index=df.index)
    for coluna, valor in filtros.items():
        alvo = df[coluna]
        mascara &= alvo.isin(valor) if isinstance(valor, (list, tuple, set)) else alvo == valor
    return df[mascara]


def _branco_se_zero(s: pd.Series) -> pd.Series:
    """Replica `if(SUM(...)=0, BLANK(), ...)`: soma nula vira ausência, não zero."""
    return s.where(s != 0)


class Medidas:
    """Star schema carregado em memória, com as medidas do modelo como métodos."""

    def __init__(self, fato_produto, fato_energetico, fato_combustivel, fator_rota):
        self.fato_produto = fato_produto
        self.fato_energetico = fato_energetico
        self.fato_combustivel = fato_combustivel
        self.fator_rota = fator_rota
        self.dim_combustivel = dim_combustivel()
        self.dim_produto = dim_produto()
        self.dim_subclasse = dim_subclasse()

    @classmethod
    def carregar(cls, saida: Path = SAIDA) -> "Medidas":
        # `fato_produto` vem direto da fonte: ele é o próprio `fatos_hist_mu_mod.csv`
        # com os tipos aplicados, e o ETL não gera uma cópia dele.
        from fatos import ler_fato_produto

        return cls(
            fato_produto=ler_fato_produto(COLUNAS_PRODUTO),
            fato_energetico=_ler(saida / "fato_energetico.csv", COLUNAS_ENERGETICO),
            fato_combustivel=_ler(saida / "fato_combustivel.csv", COLUNAS_COMBUSTIVEL),
            fator_rota=_ler(saida / "fator_rota.csv"),
        )

    # ------------------------------------------------------ núcleo energético

    def base_combustivel(self, grupo: list[str], cd_rota_cenario: int,
                         filtros: dict | None = None) -> pd.DataFrame:
        """Grão `grupo x cd_combustivel` com todas as grandezas energéticas.

        É a tradução do bloco `SUMX(dim_rota_cenario, SUMX(dim_combustivel,
        SUMX(dim_rotas_possiveis, CALCULATE(SUM(fator_rota)) * qct_calc)))`: a soma
        aninhada do DAX é, na prática, um join com `fator_rota` seguido de agregação.
        """
        fc = _aplicar(self.fato_combustivel, filtros)

        pesos = self.fator_rota.loc[
            self.fator_rota["cd_rota_cenario"] == cd_rota_cenario,
            ["cd_combustivel", "rotas_possiveis", "fator_rota"],
        ]
        df = fc.merge(pesos, on=["cd_combustivel", "rotas_possiveis"], how="left")

        # `fator_rota` nulo é BLANK no DAX, que zera a contribuição da linha.
        peso = df["fator_rota"].fillna(0.0)

        df["_qct"] = peso * df["qct"].fillna(0.0)
        df["_vct"] = peso * df["vct"].fillna(0.0)

        chaves = list(grupo) + ["cd_combustivel"]
        base = (
            df.groupby(chaves, dropna=False)[["_qct", "_vct"]].sum()
            .rename(columns={"_qct": "mil_t", "_vct": "M_m3"})
            .reset_index()
        )
        base["mil_t"] /= 1000
        base["M_m3"] /= 1000
        base = base[(base["mil_t"] != 0) | (base["M_m3"] != 0)]

        base = base.merge(
            self.dim_combustivel[["cd_combustivel", "combustivel", "pci"]],
            on="cd_combustivel", how="left",
        )

        # Cada combustível é sólido ou gasoso, nunca os dois: é isso que [RCald_] e
        # [RTurb_] usam para escolher o rendimento.
        solido = base["mil_t"] > 0
        gas = base["M_m3"] > 0

        base["ktep"] = (base["mil_t"] + base["M_m3"]) * base["pci"]
        base["TJ"] = base["ktep"] * KTEP_PARA_TJ

        r_cald = np.where(solido, RENDIMENTO_CALDEIRA["solido"],
                          np.where(gas, RENDIMENTO_CALDEIRA["gas"], np.nan))
        r_turb = np.where(solido, RENDIMENTO_ELETRICO["solido"],
                          np.where(gas, RENDIMENTO_ELETRICO["gas"], np.nan))

        base["calor_TJ"] = base["ktep"] * r_cald * KTEP_PARA_TJ
        base["eletricidade_GWh"] = base["ktep"] * (r_cald * r_turb) * KTEP_PARA_GWH
        base["energia_TJ"] = base["eletricidade_GWh"] * GWH_PARA_TJ
        base["potencia_MW"] = (
            base["eletricidade_GWh"] / (HORAS_ANO * FATOR_CAPACIDADE) * 1000
        )
        base["biometano_ktep"] = base["M_m3"] * BIOMETANO_KTEP_POR_MM3
        return base

    def energia(self, grupo: list[str], cd_rota_cenario: int,
                filtros: dict | None = None) -> pd.DataFrame:
        """Agrega `base_combustivel` sobre os combustíveis, no grão pedido."""
        base = self.base_combustivel(grupo, cd_rota_cenario, filtros)
        colunas = ["mil_t", "M_m3", "ktep", "TJ", "calor_TJ",
                   "eletricidade_GWh", "energia_TJ", "potencia_MW", "biometano_ktep"]
        if not grupo:
            return base[colunas].sum().to_frame().T
        return base.groupby(list(grupo), dropna=False)[colunas].sum().reset_index()

    # ------------------------------------------------------------ fato_produto

    def producao(self, grupo: list[str], filtros: dict | None = None) -> pd.DataFrame:
        """Produção, rebanho e área — medidas diretas, todas em BLANK quando zeradas."""
        fp = _aplicar(self.fato_produto, filtros)
        g = fp.groupby(list(grupo), dropna=False) if grupo else fp

        soma = (g[["producao_t", "rebanho", "area_ha"]].sum()
                if grupo else fp[["producao_t", "rebanho", "area_ha"]].sum().to_frame().T)

        out = pd.DataFrame({
            "producao_mil_t": _branco_se_zero(soma["producao_t"] / 1000),
            "rebanho_mil_cab": _branco_se_zero(soma["rebanho"] / 1000),
            "area_mil_ha": _branco_se_zero(soma["area_ha"] / 1000),
        })
        out["producao_unid"] = out["producao_mil_t"].fillna(0) + out["rebanho_mil_cab"].fillna(0)
        return out.reset_index() if grupo else out

    def rendimento_kg_ha(self, filtros: dict | None = None) -> pd.DataFrame:
        """Rend. (kg/ha), por produto.

        O DAX calcula a razão dentro de `SUMX(dim_produto, ...)`, isto é, produto a
        produto — a razão do agregado não é a mesma coisa e não é o que a medida faz.
        O numerador ignora linhas sem área, senão produção sem lavoura inflaria o
        rendimento.
        """
        fp = _aplicar(self.fato_produto, filtros)
        com_area = fp[fp["area_ha"].notna()]
        g = com_area.groupby("cd_produto", dropna=False)
        out = (g["producao_t"].sum() * 1000 / g["area_ha"].sum()).rename("rend_kg_ha")
        return out.replace([np.inf, -np.inf], np.nan).reset_index()

    def lotacao_cab_ha(self, grupo: list[str], filtros: dict | None = None) -> pd.DataFrame:
        """Lotação (cb/ha) para bovinos, com os mesmos cortes de sanidade do DAX.

        A medida original descarta municípios pequenos (área ou rebanho abaixo de 30
        mil) e razões acima de 100 cabeças por hectare, que indicam erro de base.
        """
        bovinos = self.dim_produto.loc[self.dim_produto["produto_2"] == "Bovino", "cd_produto"]
        fp = _aplicar(self.fato_produto, filtros)
        fp = fp[fp["cd_produto"].isin(bovinos)]

        soma = fp.groupby(list(grupo), dropna=False)[["rebanho", "area_ha"]].sum()
        rebanho = soma["rebanho"] / 1000
        area = soma["area_ha"] / 1000

        razao = rebanho / area
        valida = (area > 30) & (rebanho > 30) & (razao < 100)
        return razao.where(valida).rename("lotacao_cab_ha").reset_index()

    def producao_por_divisao(self, divisao: str, grupo: list[str],
                             filtros: dict | None = None) -> pd.DataFrame:
        """Produção (mil t) restrita a uma divisão da CNAE.

        Cobre `Produção RSU (t)` (divisão "Resíduo") e `Produção Agric. (t)`
        (divisão "Agrícola"), que no DAX são CALCULATE sobre `dim_subclasse`.
        """
        subclasses = self.dim_subclasse.loc[
            self.dim_subclasse["s4_divisao"] == divisao, "cd_subclasse"]
        produtos = self.dim_produto.loc[
            self.dim_produto["cd_subclasse"].isin(subclasses), "cd_produto"]

        fp = _aplicar(self.fato_produto, filtros)
        fp = fp[fp["cd_produto"].isin(produtos)]
        soma = fp.groupby(list(grupo), dropna=False)["producao_t"].sum() / 1000
        return _branco_se_zero(soma).rename("producao_mil_t").reset_index()

    def n_municipios_producao(self, filtros: dict | None = None) -> int:
        return int(_aplicar(self.fato_produto, filtros)["cd_mu"].nunique())

    # --------------------------------------------------------- fato_energetico

    def energetico(self, grupo: list[str], filtros: dict | None = None) -> pd.DataFrame:
        """Coproduto e energético em mil t."""
        fe = _aplicar(self.fato_energetico, filtros)
        soma = fe.groupby(list(grupo), dropna=False)[["q_coproduto", "q_energetico"]].sum()
        return pd.DataFrame({
            "coproduto_mil_t": soma["q_coproduto"] / 1000,
            "energetico_mil_t": _branco_se_zero(soma["q_energetico"] / 1000),
        }).reset_index()
