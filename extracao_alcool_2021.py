"""Extração dirigida: Álcool etílico (`cd_produto` 1209), ano 2021.

Duas tabelas no leiaute pedido pelo destinatário — `fato_energetico` e
`fato_combustivel` —, restritas a um produto, dois coprodutos (Torta de Filtro e
Vinhaça) e um ano. Não substituem as tabelas homônimas do ETL principal: saem em
`saida/alcool_2021/` justamente para não colidir com elas.

A cadeia não é reimplementada. `para_energetico` e `para_combustivel` são as mesmas
funções de `fatos.py` que geram o modelo completo, de modo que estes números são, por
construção, o recorte exato do que o modelo produz — não uma segunda versão que possa
divergir dele.

O que **não** vem do modelo está isolado em constantes no topo do arquivo, cada uma com
a razão de existir. São quatro pontos em que o leiaute pedido e o modelo não coincidem;
`docs/MEMORIAL_ALCOOL_2021.md` documenta os quatro e o efeito de cada um.

Uso:
    python extracao_alcool_2021.py
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from config import CSV_SAIDA, SAIDA, TAMANHO_BLOCO
from dimensoes import dim_energetico
from fatores import fator_energetico_combustivel, fator_produto_energetico
from fatos import ARQUIVO_FONTE, COLUNAS_PRODUTO, para_combustivel, para_energetico, tipar
from leitura import ler_csv_em_blocos

CD_PRODUTO = 1209
ANO = 2021

PASTA = "alcool_2021"

TORTA, VINHACA = 150, 151

# --- Constantes do leiaute pedido -------------------------------------------------
# Valores fixos por especificação do destinatário. Os três primeiros coincidem com o
# modelo (`dim_energetico` traz `cd_subclasse` 1931400 e `cd_rota` 12 para os dois
# coprodutos); são repetidos aqui porque o leiaute os pede como constantes.
CD_DATA = "20210101"
USO_MODELO = "sim"
CD_SUBCLASSE = 1931400
CD_ROTA = 12

# Divergência 1. O leiaute pede 167. Em `dim_combustivel`, 167 é "Solar térmica"; o
# combustível que o modelo associa a estes dois coprodutos é o 109, "Biometano" — que é
# o que a coluna de volume de fato mede. Gravamos o valor pedido, presumindo que ele
# venha do codificador do sistema de destino, e não deste modelo.
CD_COMBUSTIVEL = 167

# Divergência 3. A vinhaça é medida em metro cúbico (`dim_energetico.unidade`, e
# `fcoprod_unid` = "m³/m³"), e o leiaute pede tonelada. O modelo não carrega densidade
# de coproduto, então a conversão não sai de `csv_exportado`: 1,00 t/m³ é a densidade
# usual da vinhaça, que é 93-96% água. Alterar aqui reajusta as duas colunas de
# quantidade da tabela 1 — e só elas: a tabela 2 é calculada da cadeia do modelo.
DENSIDADE_VINHACA_T_M3 = 1.00

# Divergência 4. `cd_origem` identifica a base de onde veio o dado de produção
# (`dim_origem`: 101-123, de `conab_cafe_hist` a `sinisa_rs_recebido`). O álcool etílico
# é o **único** produto da fonte sem essa marcação: as 2.106 linhas do 1209 têm
# `cd_origem` nula, contra 6.362.772 linhas preenchidas em todos os demais produtos.
#
# Não há origem da ANP registrada, então este é um código novo. O sucessor de 123 seria
# 124, mas 124 já está ocupado nos fatos — 62.104 linhas do produto 1199, "RDO e RPU
# recebido", usam esse código, embora ele não conste de `dim_origem`. Para não colidir,
# o novo código é o primeiro livre de fato: 125. Ver o memorial, §1.4.
CD_ORIGEM = 125

# A torta de filtro já sai em tonelada (`fcoprod_unid` = "t/m"), então a conversão é a
# identidade. Explicitar as duas entradas evita que a ausência de uma seja lida como
# esquecimento.
PARA_TONELADA = {TORTA: 1.00, VINHACA: DENSIDADE_VINHACA_T_M3}

# `vct` sai da cadeia em mil m³; o leiaute pede m³.
MIL_M3_PARA_M3 = 1000

COLUNAS_ENERGETICO = [
    "cd_municipio", "cd_origem", "cd_data", "uso_modelo", "cd_energetico",
    "qtd_energetico", "qtd_energetico_disp", "cd_subclasse", "materia_seca", "cd_rota",
]

COLUNAS_COMBUSTIVEL = [
    "cd_municipio", "cd_combustivel", "cd_origem", "uso_modelo", "cd_energetico",
    "cd_data", "cd_rota", "cd_subclasse", "qtd_combustivel", "volume_combustivel",
]


def _ler_recorte(tamanho_bloco: int) -> pd.DataFrame:
    """Lê a fonte em blocos e devolve só as linhas do produto e ano pedidos.

    O filtro vem depois de `tipar` e não antes: os códigos são gravados na fonte ora
    como "1209", ora como "1209,0", e comparar texto perderia parte das linhas.
    """
    partes = []
    for i, bloco in enumerate(ler_csv_em_blocos(ARQUIVO_FONTE, tamanho_bloco, dtype=str)):
        fp = tipar(bloco[COLUNAS_PRODUTO])
        parte = fp[(fp["cd_produto"] == CD_PRODUTO) & (fp["ano"] == ANO)]
        if len(parte):
            partes.append(parte)
        print(f"  bloco {i + 1:>2}: {len(fp):>9,} linhas -> {len(parte):>4} do recorte",
              flush=True)

    if not partes:
        raise SystemExit(f"nenhuma linha com cd_produto {CD_PRODUTO} e ano {ANO}")
    return pd.concat(partes, ignore_index=True)


def _energetico(fe: pd.DataFrame, de: pd.DataFrame) -> pd.DataFrame:
    """Tabela 1 — quantidade de coproduto gerada e disponível, em tonelada.

    `qtd_energetico` é o coproduto gerado (`q_coproduto` = produção × `fcoprod`) e
    `qtd_energetico_disp`, a parcela coletável (`× fcoleta`). Para estes dois
    coprodutos `fcoleta` é 1,0, então as duas colunas saem iguais — o que é resultado,
    não simplificação: a coluna existe e a razão entre elas é justamente 1.
    """
    # `materia_seca` já vem da cadeia (`para_energetico` a traz de `dim_energetico`);
    # daqui só falta `cd_rota`, que o leiaute pede como variável do modelo.
    df = fe.merge(de[["cd_energetico", "cd_rota"]], on="cd_energetico", how="left")

    conversao = df["cd_energetico"].map(PARA_TONELADA)
    if conversao.isna().any():
        faltando = sorted(df.loc[conversao.isna(), "cd_energetico"].unique())
        raise SystemExit(f"sem fator de conversão para tonelada: {faltando}")

    df["cd_municipio"] = df["cd_mu"]
    df["cd_origem"] = CD_ORIGEM
    df["cd_data"] = CD_DATA
    df["uso_modelo"] = USO_MODELO
    df["cd_subclasse"] = CD_SUBCLASSE
    df["qtd_energetico"] = df["q_coproduto"] * conversao
    df["qtd_energetico_disp"] = df["q_energetico"] * conversao

    return df[COLUNAS_ENERGETICO]


def _combustivel(fc: pd.DataFrame) -> pd.DataFrame:
    """Tabela 2 — biometano gerado.

    `qtd_combustivel` sai vazia, e isso é o resultado correto: ela pede a quantidade da
    rota de densificação, e nenhum dos dois coprodutos tem essa rota. Em
    `fatores_energetico_combustivel` ambos têm uma única linha, de biodigestão, com
    `fdens` nulo — logo `qct` é nulo —, e `dim_energetico` os declara com
    `rotas_possiveis` = "Biodigestão". Preencher zero afirmaria que a densificação foi
    avaliada e não rendeu nada; vazio afirma que ela não se aplica, que é o caso.
    """
    df = fc.copy()
    df["cd_municipio"] = df["cd_mu"]
    df["cd_combustivel"] = CD_COMBUSTIVEL
    df["cd_origem"] = CD_ORIGEM
    df["uso_modelo"] = USO_MODELO
    df["cd_data"] = CD_DATA
    df["cd_rota"] = CD_ROTA
    df["cd_subclasse"] = CD_SUBCLASSE
    df["qtd_combustivel"] = df["qct"]
    df["volume_combustivel"] = df["vct"] * MIL_M3_PARA_M3

    return df[COLUNAS_COMBUSTIVEL]


def executar(saida: Path, tamanho_bloco: int = TAMANHO_BLOCO
             ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    destino = saida / PASTA
    destino.mkdir(parents=True, exist_ok=True)

    fpe = fator_produto_energetico()
    fec = fator_energetico_combustivel()
    de = dim_energetico()

    fp = _ler_recorte(tamanho_bloco)
    fe = para_energetico(fp, fpe, de, manter=("cd_produto", "producao_t", "rebanho"))
    fc = para_combustivel(fe, fec)

    energ = _energetico(fe, de).sort_values(["cd_municipio", "cd_energetico"],
                                            kind="stable")
    comb = _combustivel(fc).sort_values(["cd_municipio", "cd_energetico"],
                                        kind="stable")

    energ.to_csv(destino / "fato_energetico.csv", **CSV_SAIDA)
    comb.to_csv(destino / "fato_combustivel.csv", **CSV_SAIDA)
    return energ, comb, fe


def _conferir(energ: pd.DataFrame, comb: pd.DataFrame, fe: pd.DataFrame,
              municipios: set) -> list[str]:
    """Confere que as duas tabelas fecham entre si e com a fonte.

    Três verificações, na ordem em que um leitor desconfiado as faria: o recorte não
    perdeu nem inventou município; a cadeia da tabela 1 reconstitui a produção da fonte;
    e o volume da tabela 2 sai da quantidade da tabela 1 pelos fatores do modelo.
    """
    falhas = []

    for nome, df in (("fato_energetico", energ), ("fato_combustivel", comb)):
        vistos = set(df["cd_municipio"].dropna())
        if vistos != municipios:
            falhas.append(f"{nome}: {len(vistos)} municípios contra "
                          f"{len(municipios)} da fonte")
        esperado = len(municipios) * 2
        if len(df) != esperado:
            falhas.append(f"{nome}: {len(df):,} linhas, esperado {esperado:,} "
                          f"(2 coprodutos por município)")

    # Tabela 1 desfeita até a produção da fonte.
    aux = energ.merge(
        fe[["cd_mu", "cd_energetico", "producao_t", "fcoprod_u", "fcoleta"]],
        left_on=["cd_municipio", "cd_energetico"],
        right_on=["cd_mu", "cd_energetico"], how="left",
    )
    conversao = aux["cd_energetico"].map(PARA_TONELADA)

    # Tabela 2 a partir da tabela 1, desfazendo a conversão para tonelada: o modelo
    # aplica `fmetanizacao` sobre a quantidade na unidade dele, não na pedida.
    # `fmetanizacao` só existe na linha de biodigestão. Um energético de dupla rota tem
    # duas linhas na tabela de fatores, então indexar por `cd_energetico` sem descartar
    # a linha de densificação produziria um índice repetido.
    fmet = (fator_energetico_combustivel()
            .dropna(subset=["fmetanizacao"])
            .drop_duplicates("cd_energetico")
            .set_index("cd_energetico")["fmetanizacao"])
    aux2 = comb.merge(energ[["cd_municipio", "cd_energetico", "qtd_energetico_disp"]],
                      on=["cd_municipio", "cd_energetico"], how="left")

    identidades = {
        "qtd_energetico = producao × fcoprod × conversão":
            (aux["producao_t"] * aux["fcoprod_u"] * conversao, aux["qtd_energetico"]),
        "qtd_energetico_disp = qtd_energetico × fcoleta":
            (aux["qtd_energetico"] * aux["fcoleta"], aux["qtd_energetico_disp"]),
        "volume_combustivel = qtd_disp ÷ conversão × fmetanizacao":
            (aux2["qtd_energetico_disp"] / aux2["cd_energetico"].map(PARA_TONELADA)
             * aux2["cd_energetico"].map(fmet), aux2["volume_combustivel"]),
    }

    for descricao, (recalculado, publicado) in identidades.items():
        divergente = ~np.isclose(recalculado, publicado, rtol=1e-9, atol=1e-12,
                                 equal_nan=True)
        if divergente.any():
            i = int(np.argmax(divergente))
            falhas.append(f"{descricao}: {divergente.sum():,} linhas divergem "
                          f"(ex.: {recalculado.iloc[i]!r} vs {publicado.iloc[i]!r})")

    if comb["qtd_combustivel"].notna().any():
        falhas.append("qtd_combustivel veio preenchida — os coprodutos não densificam")

    # `cd_origem` é atribuído aqui, não lido da fonte (que o traz nulo para o 1209).
    # Se a constante for trocada por engano por um código já usado, a rastreabilidade
    # se perde silenciosamente — daí conferir que é o valor esperado, e só ele.
    for nome, df in (("fato_energetico", energ), ("fato_combustivel", comb)):
        distintos = set(df["cd_origem"].dropna())
        if distintos != {CD_ORIGEM} or df["cd_origem"].isna().any():
            falhas.append(f"{nome}: cd_origem deveria ser só {CD_ORIGEM}, veio "
                          f"{sorted(distintos)} com {df['cd_origem'].isna().sum()} nulos")

    return falhas


def main() -> None:
    p = argparse.ArgumentParser(description="Extração Álcool etílico 2021")
    p.add_argument("--saida", type=Path, default=SAIDA)
    p.add_argument("--tamanho-bloco", type=int, default=TAMANHO_BLOCO)
    args = p.parse_args()

    inicio = time.time()
    destino = args.saida / PASTA
    print(f"Extraindo cd_produto {CD_PRODUTO}, ano {ANO} em {destino}\n")

    energ, comb, fe = executar(args.saida, args.tamanho_bloco)

    print(f"\nMunicípios: {energ.cd_municipio.nunique():,}")
    print(f"fato_energetico:  {len(energ):>6,} linhas")
    print(f"fato_combustivel: {len(comb):>6,} linhas")

    de = dim_energetico().set_index("cd_energetico")["energetico"]
    print("\nPor coproduto:")
    for cd, g in energ.groupby("cd_energetico"):
        v = comb.loc[comb.cd_energetico == cd, "volume_combustivel"].sum()
        print(f"  {cd} {de.get(cd, ''):<16} "
              f"qtd {g.qtd_energetico.sum():>18,.2f} t   "
              f"biometano {v:>16,.2f} m³")

    total = comb["volume_combustivel"].sum()
    print(f"\nBiometano total: {total:,.2f} m³  ({total / 1e6:,.2f} milhões de m³)")

    print("\nConferência:")
    falhas = _conferir(energ, comb, fe, set(fe["cd_mu"].dropna()))
    for f in falhas:
        print(f"  FALHA: {f}")
    if not falhas:
        print("  as três identidades fecham; qtd_combustivel vazia como esperado.")

    print(f"\nConcluído em {time.time() - inicio:.0f}s")


if __name__ == "__main__":
    main()
