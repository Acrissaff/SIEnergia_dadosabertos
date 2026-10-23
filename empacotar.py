"""Monta a pasta de distribuição e o .zip a partir do que já está em `saida/`.

Não recria a pasta do zero: o OneDrive mantém descritor aberto no diretório e um
`shutil.rmtree` falha com WinError 5 no `rmdir`, depois de já ter apagado o conteúdo.
Sobrescrever arquivo a arquivo e apagar só o que sobrou de gerações anteriores evita
mexer nos nós de diretório.

Uso:
    python empacotar.py
"""

from __future__ import annotations

import shutil
import time
import zipfile
from pathlib import Path

SAIDA = Path("saida")
PACOTE = SAIDA / "dados_abertos_SIEnergia"
ZIP = SAIDA / "dados_abertos_SIEnergia.zip"
CSV = "sienergia_potencial_energetico_mu.csv"

# O dicionário e tudo o que ele referencia — o pacote anterior levava só três dos
# cinco, deixando remissões sem destino.
DOCS = ["DICIONARIO_DADOS_ABERTOS", "MEMORIAL_DE_CALCULO", "MAPEAMENTO_MODELO",
        "ERRO_MATERIA_SECA", "RESIDUOS_ABATE"]


def copiar(origem: Path, destino: Path) -> None:
    shutil.copy2(origem, destino)
    if destino.stat().st_size != origem.stat().st_size:
        raise SystemExit(f"cópia truncada: {destino}")


def main() -> None:
    inicio = time.time()
    (PACOTE / "uf").mkdir(parents=True, exist_ok=True)

    esperados = {CSV} | {d + ext for d in DOCS for ext in (".md", ".txt")}

    print(f"Montando {PACOTE}")
    copiar(SAIDA / CSV, PACOTE / CSV)
    for d in DOCS:
        for ext in (".md", ".txt"):
            copiar(Path("docs") / (d + ext), PACOTE / (d + ext))

    ufs = sorted((SAIDA / "uf").glob("*.csv"))
    if not ufs:
        raise SystemExit("saida/uf está vazia — rode `python exportar_por_uf.py` antes.")
    for f in ufs:
        copiar(f, PACOTE / "uf" / f.name)

    # Sobras de gerações anteriores: nomes que não estão no conjunto atual.
    nomes_uf = {f.name for f in ufs}
    for p in PACOTE.iterdir():
        if p.is_file() and p.name not in esperados:
            print(f"  removendo obsoleto {p.name}")
            p.unlink()
    for p in (PACOTE / "uf").iterdir():
        if p.is_file() and p.name not in nomes_uf:
            print(f"  removendo obsoleto uf/{p.name}")
            p.unlink()

    itens = sorted(p for p in PACOTE.rglob("*") if p.is_file())
    bruto = sum(p.stat().st_size for p in itens)
    print(f"{len(itens)} arquivos | {bruto / 1e9:.2f} GB | {time.time() - inicio:.0f}s")

    print(f"\nCompactando {ZIP}")
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in itens:
            z.write(p, p.relative_to(PACOTE).as_posix())

    with zipfile.ZipFile(ZIP) as z:
        ruim = z.testzip()
        n = len(z.namelist())
    if ruim is not None:
        raise SystemExit(f"CRC inválido em {ruim}")

    tam = ZIP.stat().st_size
    print(f"{n} entradas | {tam / 1e6:,.0f} MB | {tam / bruto:.1%} do bruto | "
          f"CRC conferido")
    print(f"Concluído em {time.time() - inicio:.0f}s")


if __name__ == "__main__":
    main()
