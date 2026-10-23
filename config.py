"""Constantes e caminhos do ETL SIEnergia.

Reproduz em Python os parâmetros do modelo `SIEnergia-hml.pbix`. Todos os valores
aqui foram extraídos do Power Query / DAX do próprio arquivo — ver
`docs/MAPEAMENTO_MODELO.md`.

Os textos acentuados são significativos: entram em comparações e joins contra
valores lidos dos CSVs, então precisam bater caractere a caractere.
"""

from pathlib import Path

# ---------------------------------------------------------------- caminhos

# Parâmetro `bis_outputs` do Power Query. Somente leitura.
BIS_OUTPUTS = Path(r"X:\SIEnergia\bd\csv_exportado")

BASE = Path(__file__).resolve().parent
SAIDA = BASE / "saida"

PBIX = BASE.parent / "SIEnergia-hml.pbix"

# ------------------------------------------------- dimensões fora do csv_exportado

# `dim_rota_modelo` e `dim_rota_cenario` vivem em `bd\dim_pbi`, fora da pasta que o
# ETL pode ler. São 2 e 3 linhas, com conteúdo integralmente conhecido, então entram
# como literal em vez de dependência externa.

DENSIFICACAO = "Densificação"
BIODIGESTAO = "Biodigestão"
BIOD_E_DENSIF = "Biod. e Densif."
MEIO_A_MEIO = "Meio-a-meio"

BRIQUETE = "Briquete"
BIOMETANO = "Biometano"

DIM_ROTA_MODELO = {DENSIFICACAO: 1, BIODIGESTAO: 2}

DIM_ROTA_CENARIO = [
    {"cd_rota_cenario": 1, "rota_cenario": DENSIFICACAO, "rota_cenario_sigla": "A(100-0)",
     DENSIFICACAO: 100, BIODIGESTAO: 0},
    {"cd_rota_cenario": 3, "rota_cenario": MEIO_A_MEIO, "rota_cenario_sigla": "C(50-50)",
     DENSIFICACAO: 50, BIODIGESTAO: 50},
    {"cd_rota_cenario": 5, "rota_cenario": BIODIGESTAO, "rota_cenario_sigla": "E(0-100)",
     DENSIFICACAO: 0, BIODIGESTAO: 100},
]

# ------------------------------------------------------------- conversões

# Constantes das medidas DAX de `fato_combustivel`.
KTEP_PARA_TJ = 41.87
KTEP_PARA_GWH = 11.63
GWH_PARA_TJ = 3.6
HORAS_ANO = 8760
FATOR_CAPACIDADE = 0.8          # medida [FCap_]
BIOMETANO_KTEP_POR_MM3 = 0.88   # medida [Biometano (ktep)]

# Rendimentos por estado físico do combustível — medidas [RCald_] e [RTurb_].
RENDIMENTO_CALDEIRA = {"solido": 0.80, "gas": 1.00}
RENDIMENTO_ELETRICO = {"solido": 0.25, "gas": 0.30}

# ------------------------------------------------------------------ escrita

# Padrão do Power Query, para que as saídas possam ser reingeridas pelo modelo.
CSV_SAIDA = {"sep": ";", "decimal": ",", "encoding": "utf-8-sig", "index": False}

# Linhas por bloco no processamento em streaming do fato de 268 MB. Menor que o
# natural porque a fonte é lida como texto — ver `fatos.tipar`.
TAMANHO_BLOCO = 500_000
