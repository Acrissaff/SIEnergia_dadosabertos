"""Tabela sintética de dados abertos.

Grão: município x ano x produto x coproduto energético. Reúne, numa linha só, a
produção convertida em coproduto, o energético resultante e o potencial de combustível
de cada rota tecnológica.

As duas colunas de potencial são **rota-puras**: cada uma responde "quanta energia este
coproduto renderia se 100% dele fosse por esta rota", e fica vazia quando a rota não se
aplica. Um coproduto que só biodigere tem apenas a coluna de biometano preenchida; um
que só densifique, apenas a de densificação; um que aceite as duas tem ambas.

Por isso a tabela não usa `fator_rota`: aquele fator existe para repartir os coprodutos
de dupla rota entre cenários, e aqui cada rota é avaliada isoladamente. `qct` e `vct` já
são os potenciais puros de cada rota.

> As duas colunas **não devem ser somadas**. Para um coproduto de dupla rota elas são
> hipóteses mutuamente exclusivas, não parcelas de um total.

Junto de cada quantidade vão os fatores técnicos que a produziram — da produção bruta
até o PCI do combustível —, na ordem em que entram na conta. A linha é assim auditável
sozinha, sem abrir o `.pbix`, e uma divergência contra o BI pode ser localizada na etapa
exata em que aparece. Vale o invariante: **uma coluna de fator está preenchida se, e
somente se, ela entrou no cálculo daquela linha**. As fórmulas estão em
`docs/MEMORIAL_DE_CALCULO.md`; `main` confere as quatro identidades a cada execução.

`cd_produto` não sobrevive à cadeia do modelo — o Power Query o descarta em
`fato_energetico` —, então esta tabela refaz a cadeia preservando-o, reutilizando as
mesmas funções de `fatos.py` para que as fórmulas não divirjam.

Uso:
    python dados_abertos.py
    python dados_abertos.py --blocos 1     # amostra
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    BIOD_E_DENSIF,
    BIODIGESTAO,
    CSV_SAIDA,
    DENSIFICACAO,
    SAIDA,
    TAMANHO_BLOCO,
)
from dimensoes import dim_combustivel, dim_energetico, dim_mu, dim_produto
from fatores import fator_energetico_combustivel, fator_produto_energetico
from fatos import (
    ARQUIVO_FONTE,
    COLUNAS_PRODUTO,
    MARCA_POR_CABECA,
    base_por_cabeca,
    para_combustivel,
    para_energetico,
    tipar,
)
from leitura import ler_csv_em_blocos

ARQUIVO_SAIDA = "sienergia_potencial_energetico_mu.csv"

GRAO = ["cd_mu", "ano", "cd_produto", "cd_energetico"]

COL_DENSIF = "potencial_rota_densificacao_ktep"
COL_BIODIG = "potencial_rota_biodigestao_ktep"
COLUNAS_KTEP = [COL_DENSIF, COL_BIODIG]

# As três bases possíveis da cadeia. Exatamente uma está preenchida por linha — a que
# o modelo consumiu; ver `_base_declarada`.
COLUNAS_BASE = ["producao_t", "rebanho", "abate"]

# Fatores técnicos trazidos pelo desdobramento por combustível. São constantes dentro
# do grão, então entram na agregação por `first`: somá-los multiplicaria o fator pelo
# número de linhas de origem.
COLUNAS_FATOR = [
    "fdens", "fdens_unid", "materia_seca",
    "combustivel_densificacao", "pci_densificacao",
    "fmetanizacao",
    "combustivel_biodigestao", "pci_biodigestao",
]

# Cada fator imediatamente antes do valor que produz: lida da esquerda para a direita,
# a linha é o próprio memorial de cálculo. Ver `docs/MEMORIAL_DE_CALCULO.md`.
ORDEM_COLUNAS = [
    "cd_mu", "municipio", "uf", "ano",
    "cd_produto", "produto",
    "cd_energetico", "energetico", "rotas_possiveis",
    "cd_origem",
    "producao_t", "rebanho", "abate", "fcoprod", "fcoprod_unid",
    "q_coproduto_t",
    "fcoleta",
    "q_energetico_t",
    "fdens", "fdens_unid", "materia_seca",
    "combustivel_densificacao", "pci_densificacao",
    COL_DENSIF,
    "fmetanizacao",
    "combustivel_biodigestao", "pci_biodigestao",
    COL_BIODIG,
]


def _potenciais(fc: pd.DataFrame, comb: pd.DataFrame) -> pd.DataFrame:
    """Converte `qct`/`vct` em ktep e expõe os fatores de cada rota.

    Cada linha de `fato_combustivel` já pertence a uma única rota: `fdens` e
    `fmetanizacao` são mutuamente exclusivos, e `rota_modelo` registra qual delas.
    Basta então converter a quantidade em energia e direcioná-la à coluna certa.

    O `pci` — já dividido por 10.000 na leitura de `dim_combustivel` — converte para
    tep. `qct` está em toneladas e `vct` em mil m3; dividir por 1000 leva o resultado
    de tep para ktep.

    A rota também tem de ser permitida por `rotas_possiveis`. A tabela de fatores traz
    linhas além da rota declarada — os cinco estercos, por exemplo, têm uma linha de
    densificação com `fdens = 0`, e papéis e plástico têm linha de biodigestão. O
    modelo neutraliza essas combinações em `fator_rota` (regras "rota=Biodigestão e
    combustível=Briquete -> 0" e sua simétrica); aqui a mesma supressão é feita
    diretamente. Sem ela, o esterco apareceria com potencial de densificação igual a
    zero, quando o correto é a coluna ficar vazia: a rota não existe para ele.

    As mesmas máscaras valem para os fatores publicados, o que sustenta o invariante
    do arquivo: **uma coluna de fator está preenchida se, e somente se, ela entrou no
    cálculo daquela linha**. Sem isso o leitor veria `fdens = 0` sob um potencial
    vazio e concluiria que a densificação foi tentada e rendeu nada.
    """
    fc = fc.merge(comb, on="cd_combustivel", how="left")

    ktep = (fc["qct"].fillna(0) + fc["vct"].fillna(0)) / 1000 * fc["pci"]

    rotas = fc["rotas_possiveis"]
    densif = (fc["rota_modelo"] == DENSIFICACAO) & rotas.isin([DENSIFICACAO, BIOD_E_DENSIF])
    biodig = (fc["rota_modelo"] == BIODIGESTAO) & rotas.isin([BIODIGESTAO, BIOD_E_DENSIF])

    # `where` deixa NaN fora da rota, e não zero: a distinção entre "esta rota não se
    # aplica a este coproduto" e "aplica-se, mas rende zero" precisa sobreviver.
    fc[COL_DENSIF] = ktep.where(densif)
    fc[COL_BIODIG] = ktep.where(biodig)

    # `materia_seca` é propriedade física do coproduto, não da rota, mas só entra na
    # fórmula do `qct` — mascará-la mantém o invariante acima.
    for coluna in ("fdens", "fdens_unid", "materia_seca"):
        fc[coluna] = fc[coluna].where(densif)
    fc["combustivel_densificacao"] = fc["combustivel"].where(densif)
    fc["pci_densificacao"] = fc["pci"].where(densif)

    fc["fmetanizacao"] = fc["fmetanizacao"].where(biodig)
    fc["combustivel_biodigestao"] = fc["combustivel"].where(biodig)
    fc["pci_biodigestao"] = fc["pci"].where(biodig)
    return fc


def _base_declarada(fe: pd.DataFrame) -> pd.DataFrame:
    """Deixa visível qual das três quantidades alimentou a cadeia.

    `para_energetico` escolhe a base nesta ordem: `abate`, quando essa coluna vem
    preenchida; `rebanho`, quando existe; `producao_t` caso contrário — os testes são
    `notna`, não `<> 0`. Publicar as três colunas cruas faria o leitor somar ou escolher
    errado num produto que trouxesse mais de uma: os produtos de abate, por exemplo,
    trazem também `producao_t`, que é o peso de carcaça e não entra na conta. Publicar
    só a que o modelo consumiu mantém a linha auditável, com as outras vazias.
    """
    fe = fe.copy()
    cabeca = base_por_cabeca(fe)
    rebanho = ~cabeca & fe["rebanho"].notna()

    fe["abate"] = fe["abate"].where(cabeca)
    fe["rebanho"] = fe["rebanho"].where(rebanho)
    fe["producao_t"] = fe["producao_t"].where(~cabeca & ~rebanho)
    return fe


def executar(saida: Path, tamanho_bloco: int = TAMANHO_BLOCO,
             limite_blocos: int | None = None) -> pd.DataFrame:
    saida.mkdir(parents=True, exist_ok=True)

    fpe = fator_produto_energetico()
    fec = fator_energetico_combustivel()
    de = dim_energetico()
    comb = dim_combustivel()[["cd_combustivel", "combustivel", "pci"]]

    parciais_e, parciais_c = [], []

    blocos = ler_csv_em_blocos(ARQUIVO_FONTE, tamanho_bloco, dtype=str)
    for i, bloco in enumerate(blocos):
        if limite_blocos is not None and i >= limite_blocos:
            break

        fp = tipar(bloco[COLUNAS_PRODUTO])
        fe = para_energetico(fp, fpe, de,
                             manter=("cd_produto",) + tuple(COLUNAS_BASE))
        fe = _base_declarada(fe)

        # Agregado no nível do energético: somar depois do desdobramento por
        # combustível contaria `q_coproduto` duas vezes (briquete e biometano).
        # Três agregações porque as regras diferem: quantidades já publicadas somam
        # como sempre somaram (todo-nulo -> 0, comportamento preservado); as colunas
        # novas de base usam `min_count=1` para distinguir "sem dado de produção" de
        # "produziu zero"; fatores não somam, repetem-se dentro do grão.
        g = fe.groupby(GRAO, dropna=False)
        parciais_e.append(
            g[["q_coproduto", "q_energetico"]].sum()
            .join(g[COLUNAS_BASE].sum(min_count=1))
            .join(g[["cd_origem", "fcoprod_u", "fcoprod_unid", "fcoleta"]].first())
        )

        fc = para_combustivel(fe, fec, manter=("cd_produto", "materia_seca"))
        fc = _potenciais(fc, comb)
        # `min_count=1` preserva o vazio: uma chave sem nenhuma linha de determinada
        # rota deve ficar em branco, não somar zero.
        gc = fc.groupby(GRAO, dropna=False)
        parciais_c.append(
            gc[COLUNAS_KTEP].sum(min_count=1).join(gc[COLUNAS_FATOR].first())
        )

        print(f"  bloco {i + 1}: {len(fp):>9,} fonte -> {len(fe):>9,} energetico "
              f"-> {len(fc):>9,} combustivel", flush=True)

    ce = pd.concat(parciais_e).groupby(level=GRAO)
    energ = (
        ce[["q_coproduto", "q_energetico"]].sum()
        .join(ce[COLUNAS_BASE].sum(min_count=1))
        .join(ce[["cd_origem", "fcoprod_u", "fcoprod_unid", "fcoleta"]].first())
        .rename(columns={"q_coproduto": "q_coproduto_t",
                         "q_energetico": "q_energetico_t",
                         "fcoprod_u": "fcoprod"})
    )

    cc = pd.concat(parciais_c).groupby(level=GRAO)
    comb_agg = cc[COLUNAS_KTEP].sum(min_count=1).join(cc[COLUNAS_FATOR].first())

    df = energ.join(comb_agg, how="left").reset_index()

    # Nomes por extenso: o arquivo precisa ser legível sem consultar as dimensões.
    # `rotas_possiveis` entra para que o potencial vazio se explique sozinho — um
    # energético com rota "Nenhuma" não tem fator de conversão em combustível, e sem
    # essa coluna o campo em branco pareceria dado faltante.
    df = df.merge(dim_mu()[["cd_mu", "Municipio", "UF"]], on="cd_mu", how="left")
    df = df.merge(dim_produto()[["cd_produto", "produto"]], on="cd_produto", how="left")
    df = df.merge(dim_energetico()[["cd_energetico", "energetico", "rotas_possiveis"]],
                  on="cd_energetico", how="left")
    df = df.rename(columns={"Municipio": "municipio", "UF": "uf"})

    df = df.sort_values(GRAO, kind="stable")[ORDEM_COLUNAS]
    df.to_csv(saida / ARQUIVO_SAIDA, **CSV_SAIDA)
    return df


def _conferir_cadeia(df: pd.DataFrame) -> list[str]:
    """Verifica que a cadeia publicada fecha com os fatores publicados.

    É o primeiro teste que um leitor tentará: pegar uma linha, multiplicar as colunas
    na ordem e ver se chega ao potencial. Se não fechar, o arquivo é internamente
    incoerente e não deve ser publicado — daí a conferência rodar aqui, e não num
    script à parte que alguém pode esquecer de executar.

    A base é `producao_t`, `rebanho` ou `abate`, nunca mais de uma (ver
    `_base_declarada`), então somá-las com `fillna(0)` recompõe a quantidade que o
    modelo usou. Quando todas estão vazias — município-ano sem dado de produção — a base
    é zero, que é como o `q_coproduto` já resolve o nulo hoje.

    Comparação relativa: `q_coproduto_t` chega a 1e9 e o erro de ponto flutuante
    escala junto, então uma tolerância absoluta reprovaria linhas corretas.
    """
    falhas = []

    base = sum(df[c].fillna(0) for c in COLUNAS_BASE)
    etapas = {
        "q_coproduto_t = base × fcoprod":
            (base * df["fcoprod"], df["q_coproduto_t"]),
        "q_energetico_t = q_coproduto_t × fcoleta":
            (df["q_coproduto_t"] * df["fcoleta"], df["q_energetico_t"]),
        f"{COL_DENSIF} = q_energetico_t × fdens × materia_seca ÷ 1000 × pci":
            (df["q_energetico_t"] * df["fdens"] * df["materia_seca"] / 1000
             * df["pci_densificacao"], df[COL_DENSIF]),
        f"{COL_BIODIG} = q_energetico_t × fmetanizacao ÷ 1000 ÷ 1000 × pci":
            (df["q_energetico_t"] * df["fmetanizacao"] / 1000 / 1000
             * df["pci_biodigestao"], df[COL_BIODIG]),
    }

    for descricao, (recalculado, publicado) in etapas.items():
        # Nulo dos dois lados é acerto: significa que a etapa não se aplica à linha.
        divergente = pd.Series(
            ~np.isclose(recalculado, publicado, rtol=1e-9, atol=1e-12, equal_nan=True),
            index=df.index,
        )
        if divergente.any():
            i = divergente.idxmax()
            falhas.append(f"{descricao}: {divergente.sum():,} linhas divergem "
                          f"(ex.: recalculado {recalculado[i]!r}, "
                          f"publicado {publicado[i]!r})")
    return falhas


def _conferir_invariante(df: pd.DataFrame) -> list[str]:
    """Um fator está preenchido se, e somente se, entrou no cálculo daquela linha.

    É a regra que permite ler o arquivo sem consultar o dicionário. Basta uma coluna
    fora de sincronia — `fdens` preenchido sob potencial vazio, por exemplo — para que
    o leitor conclua que a rota foi avaliada e rendeu nada.
    """
    grupos = {
        COL_DENSIF: ["fdens", "fdens_unid", "materia_seca",
                     "combustivel_densificacao", "pci_densificacao"],
        COL_BIODIG: ["fmetanizacao", "combustivel_biodigestao", "pci_biodigestao"],
    }
    falhas = []
    for potencial, fatores in grupos.items():
        esperado = df[potencial].notna()
        for fator in fatores:
            fora = (df[fator].notna() != esperado).sum()
            if fora:
                falhas.append(f"{fator} diverge de {potencial} em {fora:,} linhas")

    # As três bases são exclusivas entre si: no máximo uma preenchida por linha. Zero
    # é legítimo (município-ano sem dado de produção); duas não seriam, e o leitor que
    # somasse as colunas chegaria a uma base que o modelo nunca usou.
    bases = df[COLUNAS_BASE].notna().sum(axis=1)
    if (bases > 1).any():
        falhas.append(f"mais de uma base preenchida em {(bases > 1).sum():,} linhas")

    # A base `abate` é escolhida pela presença do dado (`fatos.base_por_cabeca`), e não
    # pela unidade do fator — é a opção A do ajuste de M, que espelha o idioma do teste
    # de `rebanho` já existente no Power Query. O preço é que os dois critérios podem
    # divergir se alguém cadastrar um produto de carcaça com fator em t/t, ou um fator
    # por cabeça abatida num produto sem `abate` na fonte. Nos dois casos a conta sai
    # silenciosamente errada — não há divisão por zero nem nulo que denuncie.
    #
    # Conferir aqui é barato e fecha a brecha: se as contagens divergirem, ou o cadastro
    # de fatores ou a base de origem mudou de forma que o critério não acompanha.
    unidade_diz = df["fcoprod_unid"].fillna("").str.contains(MARCA_POR_CABECA,
                                                             regex=False)
    usou_abate = df["abate"].notna()
    if (usou_abate & ~unidade_diz).any():
        n = (usou_abate & ~unidade_diz).sum()
        falhas.append(f"{n:,} linhas usaram `abate` com fator que não é por cabeça "
                      f"abatida — conferir fatores_produto_energetico.csv")
    if (unidade_diz & ~usou_abate).any():
        n = (unidade_diz & ~usou_abate).sum()
        falhas.append(f"{n:,} linhas têm fator por cabeça abatida mas `abate` vazia — "
                      f"a conta saiu por producao_t ou rebanho")
    return falhas


def main() -> None:
    p = argparse.ArgumentParser(description="Gera a tabela sintética de dados abertos")
    p.add_argument("--saida", type=Path, default=SAIDA)
    p.add_argument("--tamanho-bloco", type=int, default=TAMANHO_BLOCO)
    p.add_argument("--blocos", type=int, default=None)
    args = p.parse_args()

    inicio = time.time()
    print(f"Gerando {ARQUIVO_SAIDA} em {args.saida}\n")
    df = executar(args.saida, args.tamanho_bloco, args.blocos)

    print(f"\nLinhas: {len(df):,}")
    print(f"Municípios: {df.cd_mu.nunique():,} | Anos: {df.ano.min()}-{df.ano.max()} | "
          f"Produtos: {df.cd_produto.nunique()} | Energéticos: {df.cd_energetico.nunique()}")
    print("\nTotais:")
    for col in ["q_coproduto_t", "q_energetico_t", COL_DENSIF, COL_BIODIG]:
        print(f"  {col:<34} {df[col].sum():>20,.1f}")

    print("\nPreenchimento por rota declarada:")
    resumo = df.groupby("rotas_possiveis", dropna=False).agg(
        linhas=("cd_mu", "size"),
        densif=(COL_DENSIF, "count"),
        biodig=(COL_BIODIG, "count"),
    )
    print(resumo.to_string())

    print("\nBase de cálculo:")
    for coluna in COLUNAS_BASE:
        print(f"  linhas com {coluna:<12} {df[coluna].count():>12,}")
    sem_base = df[COLUNAS_BASE].isna().all(axis=1).sum()
    print(f"  linhas sem nenhuma       {sem_base:>12,}")

    print("\nAutoconferência da cadeia:")
    falhas = _conferir_cadeia(df) + _conferir_invariante(df)
    if falhas:
        for f in falhas:
            print(f"  FALHA: {f}")
    else:
        print("  as quatro identidades fecham e o invariante de preenchimento vale.")

    if args.blocos is not None:
        print(f"\nAVISO: amostra de {args.blocos} bloco(s) — não é a carga completa.")
    print(f"\nConcluído em {time.time() - inicio:.0f}s")


if __name__ == "__main__":
    main()
