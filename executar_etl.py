"""Orquestrador do ETL.

Gera `fato_energetico` e `fato_combustivel` a partir de `fatos_hist_mu_mod.csv`,
mais as duas tabelas de apoio que a camada de medidas consome.

Uso:
    python executar_etl.py                 # carga completa
    python executar_etl.py --blocos 1      # amostra, para conferência rápida
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import fatos
from config import CSV_SAIDA, SAIDA, TAMANHO_BLOCO
from dimensoes import dim_rotas_possiveis
from fatores import fator_rota

# Apagados antes de começar. Sem isso, uma execução que falhe cedo deixa para trás os
# arquivos da execução anterior, que passam a ser lidos como se fossem válidos.
GERADOS = ["fato_energetico.csv", "fato_combustivel.csv",
           "fator_rota.csv", "dim_rotas_possiveis.csv"]


def _limpar(saida: Path) -> None:
    saida.mkdir(parents=True, exist_ok=True)
    for nome in GERADOS:
        (saida / nome).unlink(missing_ok=True)


def _relatar_conversao(diagnostico: dict) -> None:
    """Equivalente à query `Erros em fato_produto` do modelo.

    Separa o que é só formatação — código gravado como "1100015,0" — do que seria
    corrupção de base, isto é, um código com parte decimal real.
    """
    problemas = {c: d for c, d in diagnostico.items()
                 if d["ilegiveis"] or d["fracionarios"]}
    if not problemas:
        print("\nConversão de tipos: nenhum valor ilegível.")
        return

    print("\nConversão de tipos:")
    for coluna, d in problemas.items():
        if d["ilegiveis"]:
            print(f"  {coluna:<14} {d['ilegiveis']:>10,} valores ilegíveis -> nulo")
        if d["fracionarios"]:
            print(f"  AVISO: {coluna} tem {d['fracionarios']:,} códigos fracionários "
                  "— arredondados, mas isso indica defeito na base")


def main() -> None:
    p = argparse.ArgumentParser(
        description="ETL SIEnergia — fato_energetico e fato_combustivel")
    p.add_argument("--saida", type=Path, default=SAIDA)
    p.add_argument("--tamanho-bloco", type=int, default=TAMANHO_BLOCO)
    p.add_argument("--blocos", type=int, default=None,
                   help="processa apenas os N primeiros blocos (amostra)")
    args = p.parse_args()

    inicio = time.time()
    print(f"Gravando em {args.saida}\n")
    _limpar(args.saida)

    print("Cadeia de fatos:")
    resultado = fatos.executar(args.saida, args.tamanho_bloco, args.blocos)

    # `dim_rotas_possiveis` e `fator_rota` dependem das rotas efetivamente observadas
    # no fato, então só podem ser fechadas depois da varredura.
    drp = dim_rotas_possiveis(resultado["rotas_possiveis"])
    drp.to_csv(args.saida / "dim_rotas_possiveis.csv", **CSV_SAIDA)

    fr = fator_rota(drp)
    fr.to_csv(args.saida / "fator_rota.csv", **CSV_SAIDA)

    print(f"\nLinhas lidas da fonte: {resultado['linhas_fonte']:,}")
    print("\nLinhas gravadas:")
    for nome, n in resultado["linhas"].items():
        print(f"  {nome:<20} {n:>12,}")
    print(f"  {'dim_rotas_possiveis':<20} {len(drp):>12,}")
    print(f"  {'fator_rota':<20} {len(fr):>12,}")

    _relatar_conversao(resultado["diagnostico"])

    print(f"\nRotas possíveis observadas: {resultado['rotas_possiveis']}")

    if args.blocos is not None:
        print(f"\nAVISO: amostra de {args.blocos} bloco(s) — não é a carga completa.")

    print(f"\nConcluído em {time.time() - inicio:.0f}s")


if __name__ == "__main__":
    main()
