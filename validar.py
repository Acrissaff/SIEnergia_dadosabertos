"""Conferência das saídas contra o modelo materializado no .pbix.

O próprio `SIEnergia-hml.pbix` carrega `fato_energetico` e `fato_combustivel` já
calculados pelo Power Query, e o `pbixray` consegue decodificar essas tabelas. Elas
servem de gabarito: se as fórmulas foram portadas corretamente, as contagens e as
somas de controle têm de bater.

A comparação é recortada por ano. O .pbix reflete a última atualização feita no
Desktop, que pode ser anterior à data dos CSVs em `csv_exportado`. Anos antigos devem
bater exatamente; divergência concentrada nos anos recentes indica defasagem de carga,
não erro de fórmula.

Uso:
    python validar.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from config import PBIX, SAIDA

# Somas de controle por tabela. `q_coproduto` cobre os dois ramos da conversão
# (rebanho e produção); `qct` e `vct` cobrem as duas rotas tecnológicas.
CONTROLES = {
    "fato_energetico": ["q_coproduto", "q_energetico"],
    "fato_combustivel": ["qct", "vct"],
}

# Colunas em que divergir do .pbix é o comportamento correto, porque o defeito está no
# modelo e não no porte. Não entram no veredito, mas são relatadas com a justificativa.
DESVIOS_CONHECIDOS = {
    ("fato_combustivel", "qct"): (
        "dim_energetico.csv gravava materia_seca com ponto decimal (0.9), e era o único\n"
        "    arquivo do conjunto que o fazia. O Table.TransformColumnTypes do Power Query\n"
        "    interpreta com locale pt-BR, onde o ponto é separador de milhar: 0.9 virava 9\n"
        "    e 0.976 virava 976. Como matéria seca é uma fração, 38 das 51 linhas ficavam\n"
        "    fisicamente impossíveis no modelo, inflando qct em até 1000x.\n"
        "    O arquivo foi regravado com vírgula em 01/09/2026. O desvio permanece até que\n"
        "    o .pbix seja atualizado, porque a comparação é contra os dados nele gravados;\n"
        "    depois da atualização a razão observada deve cair de ~22,25x para 1,00x."
    ),
}

TOLERANCIA = 1e-9


def _agregar_csv(caminho: Path, colunas: list[str]) -> pd.DataFrame:
    """Contagem e somas por ano, lendo o CSV em blocos."""
    partes = []
    blocos = pd.read_csv(caminho, sep=";", decimal=",", encoding="utf-8-sig",
                         usecols=["ano"] + colunas, chunksize=2_000_000)
    for bloco in blocos:
        g = bloco.groupby("ano", dropna=False)
        partes.append(pd.concat([g.size().rename("linhas"), g[colunas].sum()], axis=1))
    return pd.concat(partes).groupby(level=0).sum()


def _agregar_pbix(modelo, tabela: str, colunas: list[str]) -> pd.DataFrame:
    """Mesma agregação, sobre a tabela materializada no .pbix."""
    partes = []
    for bloco in modelo.iter_table(tabela, columns=["ano"] + colunas):
        bloco = bloco.rename(columns=str.lower)
        g = bloco.groupby("ano", dropna=False)
        partes.append(pd.concat([g.size().rename("linhas"), g[colunas].sum()], axis=1))
    return pd.concat(partes).groupby(level=0).sum()


def _comparar(nosso: pd.DataFrame, pbi: pd.DataFrame) -> pd.DataFrame:
    """Divergência relativa por ano e métrica."""
    anos = nosso.index.union(pbi.index)
    n = nosso.reindex(anos).fillna(0)
    p = pbi.reindex(anos).fillna(0)
    denominador = p.abs().where(p.abs() > 0, 1.0)
    return ((n - p).abs() / denominador).rename_axis("ano")


def validar(saida: Path, pbix: Path) -> str:
    from pbixray import PBIXRay

    linhas = ["RELATÓRIO DE VALIDAÇÃO — ETL pandas x modelo do .pbix", "=" * 70, ""]
    modelo = PBIXRay(str(pbix), on_disk=True)
    tabelas_pbix = {t.lower(): t for t in modelo.tables}
    falhas = 0

    for tabela, colunas in CONTROLES.items():
        linhas.append(f"\n{tabela}")
        linhas.append("-" * 70)

        caminho = saida / f"{tabela}.csv"
        if not caminho.exists():
            linhas.append(f"  AUSENTE: {caminho}")
            falhas += 1
            continue
        if tabela.lower() not in tabelas_pbix:
            linhas.append("  Tabela não encontrada no .pbix — comparação impossível")
            falhas += 1
            continue

        nosso = _agregar_csv(caminho, colunas)
        pbi = _agregar_pbix(modelo, tabelas_pbix[tabela.lower()], colunas)

        n_nosso, n_pbi = int(nosso["linhas"].sum()), int(pbi["linhas"].sum())
        marca = "OK" if n_nosso == n_pbi else "DIVERGE"
        linhas.append(f"  linhas: pandas {n_nosso:,} | pbix {n_pbi:,}  [{marca}]")
        if n_nosso != n_pbi:
            falhas += 1

        div = _comparar(nosso, pbi)
        esperados = [c for c in colunas if (tabela, c) in DESVIOS_CONHECIDOS]
        exigidos = [c for c in colunas if c not in esperados]

        for col in colunas:
            rotulo = " (desvio conhecido)" if col in esperados else ""
            linhas.append(f"  {col}: pandas {nosso[col].sum():,.3f} | "
                          f"pbix {pbi[col].sum():,.3f}{rotulo}")

        # Veredito só sobre as colunas que têm de bater.
        piores = div[["linhas"] + exigidos].max(axis=1)
        divergentes = piores[piores > TOLERANCIA].sort_index()
        if divergentes.empty:
            linhas.append(f"  OK — {len(exigidos) + 1} métricas batem em todos os "
                          f"{len(div)} anos, dentro de {TOLERANCIA:g}")
        else:
            falhas += 1
            linhas.append(f"  FALHA — {len(divergentes)} de {len(div)} anos divergem:")
            for ano, desvio in divergentes.items():
                metrica = div.loc[ano, ["linhas"] + exigidos].idxmax()
                linhas.append(f"    {ano}: {desvio:.2%} (maior em {metrica})")

        for col in esperados:
            razao = pbi[col].sum() / nosso[col].sum() if nosso[col].sum() else float("nan")
            linhas.append(f"\n  DESVIO CONHECIDO em {col} — pbix/pandas = {razao:.2f}x")
            linhas.append(f"    {DESVIOS_CONHECIDOS[(tabela, col)]}")

    linhas.append("\n" + "=" * 70)
    linhas.append("VEREDITO: porte fiel" if falhas == 0
                  else f"VEREDITO: {falhas} verificação(ões) falharam")
    return "\n".join(linhas)


def main() -> None:
    p = argparse.ArgumentParser(description="Valida as saídas do ETL contra o .pbix")
    p.add_argument("--saida", type=Path, default=SAIDA)
    p.add_argument("--pbix", type=Path, default=PBIX)
    args = p.parse_args()

    relatorio = validar(args.saida, args.pbix)
    print(relatorio)

    destino = args.saida / "relatorio_validacao.txt"
    destino.write_text(relatorio, encoding="utf-8")
    print(f"\nRelatório salvo em {destino}")


if __name__ == "__main__":
    main()
