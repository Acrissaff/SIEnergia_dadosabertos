# Mapeamento do Modelo de Dados — SIEnergia-hml.pbix

Extraído de `SIEnergia-hml.pbix` (141 MB; `DataModel` de 109 MB, formato ABF/xpress9).
20 tabelas carregadas + 12 queries auxiliares/parâmetros não carregados, 49 medidas DAX, 20 relacionamentos.

---

## 1. Parâmetros e caminhos

| Parâmetro | Valor |
|---|---|
| `bis_outputs` | `X:\SIEnergia\bd\csv_exportado\` |
| `bis_data` | `C:/Users/daniel.coelho/OneDrive - epe.gov.br/bis/data/` (legado, não usado nas queries ativas) |

Fontes fora de `bis_outputs`:
- `X:\Biocombustiveis - Diretorio\Técnico\Produtos\SIEnergia\bd\dim_pbi\` → `dim_rota_modelo.csv`, `dim_rota_cenario.csv`
- `X:\SIEnergia\BASE DE DADOS\ANP\` → vendas de diesel e gasolina C por município
- `X:\Biocombustiveis - Diretorio\...\CAMINHOS DA SAFRA\caminhos_safra.xlsx` (aba `trechos`)

---

## 2. Linhagem da cadeia principal

```
fatos_hist_mu_mod.csv ──> fato_produto
                              │
                              ├── join fator_produto_energetico (cd_produto)  [INNER]
                              └──> fato_energetico
                                       │
                                       ├── join fator_energetico_combustivel (cd_energetico) [LEFT]
                                       └──> fato_combustivel
```

Derivadas: `dim_rotas_possiveis` ← `fato_energetico`; `fator_rota` ← `fator_energetico_combustivel`.

---

## 3. `fato_produto` — tratamento do `fatos_hist_mu`

**Fonte:** `bis_outputs & "fatos_hist_mu_mod.csv"` — 268 MB, `Delimiter=";"`, `Columns=9`, `Encoding=1252`, `QuoteStyle=None`.

Passos M:
1. `Csv.Document` + `PromoteHeaders`
2. Renomeia `valor` → `valor_bruto`
3. `TransformColumnTypes`:
   - `Int64`: `cd_mu`, `cd_produto`, `ano`, `cd_origem`
   - `number`: `area_ha`, `producao_t`, `valor_bruto`, `rebanho`, `abate`
4. Renomeia `valor_bruto` → `valor` (volta ao nome original)

> O par rename→rename é um no-op efetivo: existe apenas para forçar a coerção de tipo sobre `valor`. O tratamento pesado do `fatos_hist_mu` acontece **fora do PBI** (pipeline que gera `fatos_hist_mu_mod.csv` a partir de `fatos_hist_mu.csv`).

**Schema de saída:** `cd_mu, cd_produto, cd_origem, ano, area_ha, producao_t, valor, rebanho, abate`

**Armadilhas de leitura:**
- Separador decimal é **vírgula** (`76,0`)
- Arquivo tem **BOM UTF-8** apesar de `Encoding=1252` declarado no M → usar `utf-8-sig`
- `rebanho` e `abate` são majoritariamente nulos (só pecuária)

---

## 4. `fato_energetico` — conversão produto → energético

**Fonte:** `fato_produto` ⋈ `fator_produto_energetico`

`fator_produto_energetico` (query auxiliar, não carregada) lê `fatores_produto_energetico.csv`
(`Columns=7`, `Encoding=65001`, quoted, decimal vírgula), tipa `fcoprod`/`fcoleta` como number,
`cd_produto`/`cd_energetico` como Int64, ordena por `cd_energetico`.

Passos:
1. **`JoinKind.Inner`** em `cd_produto` → expande `fcoprod`, `fcoprod_unid`, `fcoleta`, `cd_energetico`
   > Inner: produtos sem fator energético são **descartados**; produtos com N energéticos **multiplicam** as linhas.
2. `q_coproduto` = `if [rebanho] <> null then [rebanho]*[fcoprod] else [producao_t]*[fcoprod]`
3. `q_energetico` = `q_coproduto * fcoleta`
4. Remove `area_ha`, `producao_t`, `valor`, `rebanho`, `cd_produto`, `abate`
5. `JoinKind.LeftOuter` em `cd_energetico` com `dim_energetico` → expande `materia_seca`, `rotas_possiveis`
6. Renomeia `fcoprod` → `fcoprod_u`

**Schema de saída:** `cd_mu, cd_origem, ano, fcoprod_u, fcoprod_unid, fcoleta, cd_energetico, q_coproduto, q_energetico, materia_seca, rotas_possiveis`

---

## 5. `fato_combustivel` — conversão energético → combustível

**Fonte:** `fato_energetico` ⋈ `fator_energetico_combustivel`

`fator_energetico_combustivel` (auxiliar) lê `fatores_energetico_combustivel.csv` (`Columns=7`, `Encoding=65001`)
e **deriva a rota**:
```
rota_modelo = if fmetanizacao = null then "Densificação"
              else if fdens = null   then "Biodigestão"
              else null
```

Passos:
1. `JoinKind.LeftOuter` em `cd_energetico` → expande `cd_combustivel`, `fdens`, `fdens_unid`, `fmetanizacao`, `rota_modelo`
   > Um energético gera até 2 linhas (Briquete e Biometano).
2. Filtra `cd_combustivel <> null` (equivale a inner join)
3. Remove `fcoprod_u`, `fcoprod_unid`, `fcoleta`, `q_coproduto`
4. `LeftOuter` em `rota_modelo` com `dim_rota_modelo` → expande `cd_rota_modelo`
5. **`qct`** = `q_energetico * fdens * materia_seca`   ← massa do combustível sólido (t)
6. **`vct`** = `q_energetico * fmetanizacao / 1000`    ← volume de biometano (mil m³)
7. Remove `q_energetico`, `materia_seca`

**Schema de saída:** `cd_mu, cd_origem, ano, cd_energetico, rotas_possiveis, cd_combustivel, fdens, fdens_unid, fmetanizacao, rota_modelo, cd_rota_modelo, qct, vct`

> `qct` fica nulo na rota Biodigestão (`fdens` nulo) e `vct` fica nulo na Densificação (`fmetanizacao` nulo).

---

## 6. `fator_rota` — matriz de escolha de rota

Constrói o produto cartesiano `combustível × rotas_possiveis × cenário de rota` e atribui um peso:

```
fator_rota =
  0    se cenário=Biodigestão   e rotas_possiveis="Biod. e Densif." e combustível=Briquete
  0    se rotas_possiveis=Biodigestão   e combustível=Briquete
  0    se rotas_possiveis=Densificação  e combustível=Biometano
  0    se cenário=Densificação  e rotas_possiveis="Biod. e Densif." e combustível=Biometano
  0.5  se cenário=Meio-a-meio   e rotas_possiveis="Biod. e Densif."
  1    caso contrário
```
Ao final, `0` é substituído por `null` (para gerar BLANK no DAX em vez de zero).

---

## 7. `derivados_petroleo_mu` — benchmark de combustível fóssil

`Table.Combine({diesel_mu, galosina_mu})` (ambos da ANP, com coluna `combustivel` fixa)
⋈ `dim_combustivel` por nome do combustível →
```
venda_ktep = venda_litro * densidade * pci / 1e6 / 1000
```
⋈ `trechos` (caminhos_safra.xlsx) por `cd_mu` → `caminho = if CD_MUN <> null then "Caminho da Safra" else "Fora do Caminho"`

> Atenção: em `dim_combustivel`, `pci` é dividido por 10.000 no M (`8550 → 0,855`), virando fator tep.

---

## 8. Relacionamentos (todos M:1, ativos, filtro simples)

| De | Coluna | Para |
|---|---|---|
| fato_produto | ano / cd_mu / cd_produto | dim_ano / dim_mu / dim_produto |
| fato_energetico | ano / cd_mu / cd_energetico | dim_ano / dim_mu / dim_energetico |
| fato_combustivel | ano / cd_mu / cd_combustivel / cd_energetico | dim_ano / dim_mu / dim_combustivel / dim_energetico |
| fato_populacao_mu | ano / cd_mu | dim_ano / dim_mu |
| derivados_petroleo_mu | ano / cd_mu / cd_combustivel / caminho | dim_ano / dim_mu / dim_combustiveis_venda / dim_caminho |
| dim_produto | cd_subclasse | dim_subclasse |
| dim_energetico | cd_subclasse / rotas_possiveis | dim_subclasse / dim_rotas_possiveis |
| fator_rota | rotas_possiveis | dim_rotas_possiveis |

---

## 9. Medidas DAX — cadeia de cálculo energético

Núcleo (em `fato_combustivel`):

```
qct_calc  = SUM(fato_combustivel[qct])
vct_calc  = SUM(fato_combustivel[vct])

Combustivel (mil t) = SUMX(dim_rota_cenario, SUMX(dim_combustivel, SUMX(dim_rotas_possiveis,
    CALCULATE(SUM(fator_rota[fator_rota]), <filtros de cenário/combustível/rota>) * qct_calc / 1000 )))

Combustível (M m3) = idem, com vct_calc / 1000

Combustível (ktep) = SUMX(dim_combustivel, [Combustível (M m3)]*[PCI] + [Combustivel (mil t)]*[PCI])
Combustível (TJ)   = SUMX(dim_combustivel, [Combustível (ktep)]*41.87)
```

Rendimentos e conversões:
```
RCald_ = 0.80 se sólido (mil t) ; 1 se gás (M m3)      -- rendimento de caldeira
RTurb_ = 0.25 se sólido         ; 0.3 se gás           -- rendimento elétrico
RTE    = RCald_ * RTurb

Calor (TJ)          = SUMX(dim_combustivel, [Combustível (ktep)] * [RCald] * 41.87)
Eletricidade (GWh)  = SUMX(dim_combustivel, [Combustível (ktep)] * [RTE] * 11.63)
Energia (TJ)        = [Eletricidade (GWh)] * 3.6
Potência (MW)       = SUMX(dim_combustivel, [Eletricidade (GWh)] / (8760 * 0.8)) * 1000
Biometano (ktep)    = [Combustível (M m3)] * 0.88
Balanço O&D (ktep)  = [Biometano (ktep)] - [Combustível vendido (ktep)]
```

Constantes de conversão: `41.87` (ktep→TJ), `11.63` (ktep→GWh), `3.6` (GWh→TJ), `8760` h/ano, `FCap = 0.8`.

Em `fato_produto`:
```
Produção (mil t)     = SUM(producao_t)/1000        (BLANK se 0)
Rebanho (mil cb²)    = SUM(rebanho)/1000           (BLANK se 0)
Área (mil ha)        = SUM(area_ha)/1000           (BLANK se 0)
Rend. (kg/ha)        = SUMX(dim_produto, CALCULATE(SUM(producao_t), area_ha<>BLANK)*1000 / SUM(area_ha))
Lotação (cb²/ha)     = Rebanho/Área para produto_2="Bovino", só se Área>30 e Rebanho>30 e razão<100
Geração (kg/hab/dia) = CALCULATE(SUM(producao_t), s5_secao="Saneamento")/365/SUM(populacao)*1000
```

Em `fato_energetico`:
```
Energético (mil t)  = SUM(q_energetico)/1000       (BLANK se 0)
Coproduto (mil t)   = SUM(q_coproduto)/1000
F.Coprod. / F.Coleta / M.Seca / Rotas = médias/distincts condicionados a HASONEVALUE
```

---

## 10. Arquivos gerados nesta extração

```
extract/
├── MAPEAMENTO_MODELO.md      (este documento)
├── power_query.csv           (M das 20 tabelas carregadas)
├── m_parameters.csv          (M das 12 queries auxiliares + parâmetros)
├── dax_measures.csv          (49 medidas)
├── relationships.csv         (20 relacionamentos)
├── schema.csv                (168 colunas tipadas)
├── metadata.csv, statistics.csv
└── m/*.m                     (uma query M por arquivo)
```
