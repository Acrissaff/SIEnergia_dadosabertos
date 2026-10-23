"""Spot check de 400 chaves do arquivo de dados abertos contra os fatos validados.

O que este script testa, e o que não testa
------------------------------------------
`fato_energetico.csv` e `fato_combustivel.csv` já foram conferidos contra o
`SIEnergia-hml.pbix` (linhas e somas idênticas; `qct` com o desvio documentado de
matéria seca). Aqui eles servem de gabarito para o arquivo de dados abertos, que é
derivado deles. O teste cobre a agregação, o join com o PCI e a aritmética do ktep.

Ele **não** testa a regra de supressão por `rotas_possiveis` — a mesma regra é
aplicada dos dois lados, então ela passa por construção. Essa regra é uma decisão de
modelagem (espelha o `fator_rota` do PBI) e está verificada em outro lugar.

Grão
----
`dados_abertos` tem `cd_produto`; os fatos não (o Power Query o descarta). A
comparação portanto acontece em [cd_mu, ano, cd_energetico], agregando o lado dos
dados abertos primeiro.
"""

from __future__ import annotations

import pandas as pd

from config import BIOD_E_DENSIF, BIODIGESTAO, DENSIFICACAO, SAIDA
from dimensoes import dim_combustivel

GRAO = ["cd_mu", "ano", "cd_energetico"]
N_AMOSTRA = 400
TOL_TONELADA = 0.01
TOL_KTEP = 1e-6

LEITURA = dict(sep=";", decimal=",", encoding="utf-8-sig")


def _amostra() -> pd.DataFrame:
    """Agrega o arquivo de dados abertos ao grão dos fatos e sorteia N chaves.

    `min_count=1` mantém o vazio: uma chave sem nenhuma linha de uma rota fica NaN,
    e não zero. Sem isso, todo branco viraria zero e a comparação perderia justamente
    a distinção que o arquivo existe para expressar.
    """
    da = pd.read_csv(SAIDA / "sienergia_potencial_energetico_mu.csv", **LEITURA)
    agregado = da.groupby(GRAO, dropna=False).agg(
        q_coproduto_t=("q_coproduto_t", "sum"),
        q_energetico_t=("q_energetico_t", "sum"),
        densif=("potencial_rota_densificacao_ktep", lambda s: s.sum(min_count=1)),
        biodig=("potencial_rota_biodigestao_ktep", lambda s: s.sum(min_count=1)),
    ).reset_index()
    return agregado.sample(n=min(N_AMOSTRA, len(agregado)), random_state=42)


def _por_blocos(arquivo: str, chaves: pd.DataFrame, usecols: list[str],
                dtype: dict | None = None) -> pd.DataFrame:
    """Lê um fato em blocos, guardando só as linhas das chaves sorteadas.

    Um scan por arquivo, e não um por linha da amostra: o loop ingênuo varria 6,7
    milhões de linhas 400 vezes.
    """
    partes = []
    for bloco in pd.read_csv(SAIDA / arquivo, usecols=usecols, dtype=dtype,
                             chunksize=1_000_000, **LEITURA):
        partes.append(bloco.merge(chaves, on=GRAO, how="inner"))
    return pd.concat(partes, ignore_index=True)


def _gabarito_energetico(chaves: pd.DataFrame) -> pd.DataFrame:
    fe = _por_blocos("fato_energetico.csv", chaves,
                     GRAO + ["q_coproduto", "q_energetico"])
    return fe.groupby(GRAO).agg(
        ref_q_coproduto=("q_coproduto", "sum"),
        ref_q_energetico=("q_energetico", "sum"),
    ).reset_index()


def _gabarito_combustivel(chaves: pd.DataFrame) -> pd.DataFrame:
    """Recalcula o ktep de cada rota a partir de `qct`/`vct`, do zero.

    A supressão por `rotas_possiveis` repete a de `dados_abertos._potenciais`: os
    estercos têm linha de densificação com `fdens = 0`, que precisa sair como vazio
    e não como zero.
    """
    fc = _por_blocos(
        "fato_combustivel.csv", chaves,
        GRAO + ["rotas_possiveis", "cd_combustivel", "rota_modelo", "qct", "vct"],
        dtype={"rotas_possiveis": str, "rota_modelo": str},
    )
    fc = fc.merge(dim_combustivel()[["cd_combustivel", "pci"]],
                  on="cd_combustivel", how="left")

    ktep = (fc["qct"].fillna(0) + fc["vct"].fillna(0)) / 1000 * fc["pci"]
    rotas = fc["rotas_possiveis"]
    fc["d"] = ktep.where((fc["rota_modelo"] == DENSIFICACAO)
                         & rotas.isin([DENSIFICACAO, BIOD_E_DENSIF]))
    fc["b"] = ktep.where((fc["rota_modelo"] == BIODIGESTAO)
                         & rotas.isin([BIODIGESTAO, BIOD_E_DENSIF]))

    g = fc.groupby(GRAO)[["d", "b"]].sum(min_count=1).reset_index()
    return g.rename(columns={"d": "ref_densif", "b": "ref_biodig"})


def _comparar(df: pd.DataFrame, obtido: str, esperado: str, tol: float,
              rotulo: str) -> pd.DataFrame:
    """Classifica cada chave em uma categoria de erro, ou nenhuma.

    Vazio de um lado e preenchido do outro é erro de categoria própria: um desvio
    numérico é ruído de arredondamento, mas uma célula que deveria estar em branco
    e não está muda o significado do dado.
    """
    a, b = df[obtido], df[esperado]
    ambos = a.notna() & b.notna()

    return pd.DataFrame({
        "chave": df[GRAO].astype(str).agg("|".join, axis=1),
        "categoria": pd.Series(
            pd.NA, index=df.index, dtype="object"
        ).mask(ambos & ((a - b).abs() > tol), f"{rotulo}: divergência numérica")
         .mask(a.notna() & b.isna(), f"{rotulo}: preenchido, deveria ser vazio")
         .mask(a.isna() & b.notna(), f"{rotulo}: vazio, deveria estar preenchido"),
        "obtido": a,
        "esperado": b,
    }).dropna(subset=["categoria"])


def main() -> None:
    amostra = _amostra()
    chaves = amostra[GRAO]
    print(f"Amostra: {len(amostra)} chaves no grão {GRAO}\n")

    df = (amostra
          .merge(_gabarito_energetico(chaves), on=GRAO, how="left")
          .merge(_gabarito_combustivel(chaves), on=GRAO, how="left"))

    ausentes = df["ref_q_coproduto"].isna().sum()
    if ausentes:
        print(f"AVISO: {ausentes} chaves não encontradas em fato_energetico\n")

    erros = pd.concat([
        _comparar(df, "q_coproduto_t", "ref_q_coproduto", TOL_TONELADA, "q_coproduto"),
        _comparar(df, "q_energetico_t", "ref_q_energetico", TOL_TONELADA, "q_energetico"),
        _comparar(df, "densif", "ref_densif", TOL_KTEP, "densificação"),
        _comparar(df, "biodig", "ref_biodig", TOL_KTEP, "biodigestão"),
    ], ignore_index=True)

    print(f"Erros: {len(erros)}")
    if erros.empty:
        print("\nA amostra reproduz os fatos validados em todas as quatro colunas.")
        return

    print("\nPor categoria:")
    print(erros["categoria"].value_counts().to_string())
    print("\nPrimeiros casos:")
    print(erros.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
