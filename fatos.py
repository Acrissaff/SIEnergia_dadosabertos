"""Geração de `fato_energetico` e `fato_combustivel`.

`fato_produto` não é gerado: ele é o próprio `fatos_hist_mu_mod.csv` com os tipos
aplicados, e reescrevê-lo seria uma cópia de 274 MB sem informação nova. Ele existe
aqui apenas como etapa intermediária da cadeia.

Todos os joins são contra tabelas de dezenas de linhas (68, 47 e 51), então nenhuma
etapa precisa enxergar o fato inteiro de uma vez. O processamento é feito em blocos,
o que mantém a memória constante.

A ordem das colunas de cada saída reproduz a do Power Query: `Table.ExpandTableColumn`
e `Table.AddColumn` anexam ao final, e `Table.RemoveColumns` preserva o que sobra.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config import CSV_SAIDA, DIM_ROTA_MODELO, TAMANHO_BLOCO
from dimensoes import dim_energetico
from fatores import fator_energetico_combustivel, fator_produto_energetico
from leitura import ler_csv, ler_csv_em_blocos

ARQUIVO_FONTE = "fatos_hist_mu_mod.csv"

# Tipos do `Table.TransformColumnTypes` de `fato_produto`. Larguras reduzidas onde os
# domínios permitem: são ~6,4 milhões de linhas e cada byte por coluna conta.
COLUNAS_INTEIRAS = {"cd_mu": "Int32", "cd_produto": "Int32",
                    "cd_origem": "Int32", "ano": "Int16"}
COLUNAS_REAIS = ["area_ha", "producao_t", "valor", "rebanho", "abate"]

COLUNAS_PRODUTO = list(COLUNAS_INTEIRAS) + COLUNAS_REAIS

COLUNAS_ENERGETICO = [
    "cd_mu", "cd_origem", "ano", "fcoprod_u", "fcoprod_unid", "fcoleta",
    "cd_energetico", "q_coproduto", "q_energetico", "materia_seca", "rotas_possiveis",
]

COLUNAS_COMBUSTIVEL = [
    "cd_mu", "cd_origem", "ano", "cd_energetico", "rotas_possiveis", "cd_combustivel",
    "fdens", "fdens_unid", "fmetanizacao", "rota_modelo", "cd_rota_modelo", "qct", "vct",
]

# A base da cadeia é o número de cabeças abatidas quando `abate` vem preenchida. É o
# mesmo idioma do teste de `rebanho` que já existia — presença do dado, não código de
# produto —, e reproduz a opção A do ajuste de M descrito em `docs/RESIDUOS_ABATE.md`.
#
# O critério é seguro porque `abate` só existe nos oito produtos de carcaça (1168–1175),
# nunca coexiste com `rebanho` na mesma linha, e cinco desses oito não têm fator e caem
# no join interno antes de chegar aqui. Sobram exatamente 1168, 1174 e 1175.
#
# O que ele não vê é a unidade do fator: um produto de carcaça cadastrado com fator em
# t/t seguiria por este ramo indevidamente. `dados_abertos._conferir_invariante` fecha
# essa brecha conferindo, a cada geração, que os dois critérios continuam coincidindo.
MARCA_POR_CABECA = "cabeça abatida"


def base_por_cabeca(df: pd.DataFrame) -> pd.Series:
    """Linhas cuja base de cálculo é o número de cabeças abatidas."""
    return df["abate"].notna()


def tipar(bloco: pd.DataFrame, diagnostico: dict | None = None) -> pd.DataFrame:
    """Converte um bloco lido como texto, reproduzindo `Table.TransformColumnTypes`.

    O arquivo-fonte grava parte dos códigos inteiros em notação decimal ("1100015,0"
    em vez de "1100015"). O `decimal=","` do pandas só vale para colunas float — o
    parser de inteiro recebe a string bruta e falha. O Power Query não tropeça nisso
    porque `Csv.Document` produz texto e a conversão vem depois, respeitando o locale;
    é exatamente isso que fazemos aqui.

    Que o defeito é conhecido de quem construiu o modelo, o próprio PBI atesta: há uma
    query `Erros em fato_produto` com `Table.SelectRowsWithErrors` sobre estas colunas.

    Valores irrecuperáveis viram nulo em vez de abortar a carga. `diagnostico`, se
    fornecido, acumula as contagens por coluna.
    """
    saida = {}

    # Só as colunas presentes: `ler_fato_produto` aceita um subconjunto.
    for coluna in [c for c in COLUNAS_PRODUTO if c in bloco.columns]:
        valores = pd.to_numeric(
            bloco[coluna].str.replace(",", ".", regex=False), errors="coerce"
        )

        if diagnostico is not None:
            d = diagnostico.setdefault(coluna, {"ilegiveis": 0, "fracionarios": 0})
            d["ilegiveis"] += int((valores.isna() & bloco[coluna].notna()).sum())

        if coluna in COLUNAS_INTEIRAS:
            if diagnostico is not None:
                # Um código com parte decimal real é corrupção de base, não
                # formatação: o arredondamento altera o dado em vez de só reescrevê-lo.
                # O `notna` é necessário porque `NaN % 1` é `NaN`, que não é igual a
                # zero — sem ele, todo valor ilegível seria contado duas vezes.
                fracionario = (valores % 1 != 0) & valores.notna()
                diagnostico[coluna]["fracionarios"] += int(fracionario.sum())
            valores = valores.round().astype(COLUNAS_INTEIRAS[coluna])

        saida[coluna] = valores

    return pd.DataFrame(saida, index=bloco.index)


def para_energetico(fp: pd.DataFrame, fpe: pd.DataFrame, de: pd.DataFrame,
                    manter: tuple[str, ...] = ()) -> pd.DataFrame:
    """Converte produção em quantidade de energético.

    O join é `inner` de propósito: a tabela de fatores define quais produtos têm
    potencial energético, então ela é o filtro da cadeia. Produtos com mais de um
    energético multiplicam a linha (16 dos 45 produtos cobertos).

    `manter` preserva colunas que o modelo descarta — `cd_produto`, por exemplo, que
    o M remove aqui mas que a tabela de dados abertos precisa.
    """
    df = fp.merge(
        fpe[["cd_produto", "fcoprod", "fcoprod_unid", "fcoleta", "cd_energetico"]],
        on="cd_produto",
        how="inner",
    )

    # O M testa `[rebanho] <> null`, não `<> 0`: pecuária usa o rebanho, lavoura usa a
    # produção. Um rebanho igual a zero ainda é pecuária e segue por aquele ramo.
    #
    # O primeiro ramo — `abate` — ainda não existe no Power Query publicado: o M remove
    # a coluna logo após a tipagem, e por isso o modelo não calcula os resíduos de
    # indústria de abate. O ajuste está pronto em `docs/m/fato_energetico_CORRIGIDO.m`
    # e documentado em `docs/RESIDUOS_ABATE.md`.
    #
    # Ele vem primeiro porque os produtos de abate trazem também `producao_t` — o peso
    # de carcaça —, que capturaria a linha pelo ramo errado no `default`. Ante `rebanho`
    # a ordem é indiferente: as duas colunas nunca estão preenchidas na mesma linha.
    por_cabeca = base_por_cabeca(df)
    df["q_coproduto"] = np.select(
        [por_cabeca, df["rebanho"].notna()],
        [df["abate"] * df["fcoprod"], df["rebanho"] * df["fcoprod"]],
        default=df["producao_t"] * df["fcoprod"],
    )
    df["q_energetico"] = df["q_coproduto"] * df["fcoleta"]

    df = df.merge(
        de[["cd_energetico", "materia_seca", "rotas_possiveis"]],
        on="cd_energetico",
        how="left",
    )
    df = df.rename(columns={"fcoprod": "fcoprod_u"})
    return df[COLUNAS_ENERGETICO + list(manter)]


def para_combustivel(fe: pd.DataFrame, fec: pd.DataFrame,
                     manter: tuple[str, ...] = ()) -> pd.DataFrame:
    """Converte energético em combustível sólido (`qct`) ou biometano (`vct`).

    O M faz left join e em seguida filtra `cd_combustivel <> null`, o que equivale a um
    inner join. Mantemos os dois passos separados para espelhar a query.
    """
    df = fe.merge(
        fec[["cd_energetico", "cd_combustivel", "fdens", "fdens_unid",
             "fmetanizacao", "rota_modelo"]],
        on="cd_energetico",
        how="left",
    )
    df = df[df["cd_combustivel"].notna()]

    df["cd_rota_modelo"] = df["rota_modelo"].map(DIM_ROTA_MODELO).astype("Int64")

    # Como `fdens` e `fmetanizacao` são mutuamente exclusivos, cada linha alimenta
    # exatamente uma das duas colunas e a outra fica nula — o NaN do pandas propaga
    # pela multiplicação exatamente como o null do M.
    df["qct"] = df["q_energetico"] * df["fdens"] * df["materia_seca"]
    df["vct"] = df["q_energetico"] * df["fmetanizacao"] / 1000

    return df[COLUNAS_COMBUSTIVEL + list(manter)]


def ler_fato_produto(colunas: list[str] | None = None) -> pd.DataFrame:
    """Lê a fonte inteira já tipada. Usado pela camada de medidas."""
    return tipar(ler_csv(ARQUIVO_FONTE, dtype=str, usecols=colunas))


class _EscritorCSV:
    """Grava um DataFrame em blocos, escrevendo o cabeçalho só na primeira vez."""

    def __init__(self, caminho: Path):
        self.caminho = caminho
        self.primeiro = True
        self.linhas = 0

    def escrever(self, df: pd.DataFrame) -> None:
        df.to_csv(
            self.caminho,
            mode="w" if self.primeiro else "a",
            header=self.primeiro,
            **CSV_SAIDA,
        )
        self.primeiro = False
        self.linhas += len(df)


def executar(saida: Path, tamanho_bloco: int = TAMANHO_BLOCO,
             limite_blocos: int | None = None) -> dict:
    """Gera `fato_energetico` e `fato_combustivel` a partir da fonte.

    Devolve a contagem de linhas por tabela, as rotas possíveis observadas na ordem de
    primeira aparição — é essa ordem que `dim_rotas_possiveis` indexa — e o
    diagnóstico de conversão.
    """
    saida.mkdir(parents=True, exist_ok=True)

    fpe = fator_produto_energetico()
    fec = fator_energetico_combustivel()
    de = dim_energetico()

    escritores = {
        "fato_energetico": _EscritorCSV(saida / "fato_energetico.csv"),
        "fato_combustivel": _EscritorCSV(saida / "fato_combustivel.csv"),
    }
    rotas_vistas: dict[str, None] = {}
    diagnostico: dict[str, dict[str, int]] = {}
    linhas_fonte = 0

    blocos = ler_csv_em_blocos(ARQUIVO_FONTE, tamanho_bloco, dtype=str)
    for i, bloco in enumerate(blocos):
        if limite_blocos is not None and i >= limite_blocos:
            break

        fp = tipar(bloco[COLUNAS_PRODUTO], diagnostico)
        fe = para_energetico(fp, fpe, de)
        fc = para_combustivel(fe, fec)

        escritores["fato_energetico"].escrever(fe)
        escritores["fato_combustivel"].escrever(fc)

        linhas_fonte += len(fp)
        rotas_vistas.update(dict.fromkeys(fe["rotas_possiveis"].dropna()))
        print(f"  bloco {i + 1}: {len(fp):>9,} fonte -> {len(fe):>9,} energetico "
              f"-> {len(fc):>9,} combustivel", flush=True)

    return {
        "linhas_fonte": linhas_fonte,
        "linhas": {nome: e.linhas for nome, e in escritores.items()},
        "rotas_possiveis": list(rotas_vistas),
        "diagnostico": diagnostico,
    }
