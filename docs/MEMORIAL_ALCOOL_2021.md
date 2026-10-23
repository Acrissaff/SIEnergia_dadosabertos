# Memorial de cálculo — Álcool etílico, 2021

Extração dirigida: um produto (`cd_produto` 1209, Álcool etílico hidratado), dois
coprodutos energéticos (Torta de Filtro e Vinhaça) e um ano. Duas tabelas, no leiaute
pedido pelo destinatário:

| Arquivo | Linhas | Tamanho |
|---|---|---|
| `saida/alcool_2021/fato_energetico.csv` | 524 | 41.059 bytes |
| `saida/alcool_2021/fato_combustivel.csv` | 524 | 32.292 bytes |

262 municípios × 2 coprodutos = 524 linhas em cada tabela.

Gerado por `extracao_alcool_2021.py`, que reaproveita `para_energetico` e
`para_combustivel` de `fatos.py` — as mesmas funções do ETL completo. Estes números são,
por construção, o recorte exato do que o modelo produz.

> Os arquivos saem numa subpasta própria. Os `fato_energetico.csv` e
> `fato_combustivel.csv` que estão diretamente em `saida/` são as tabelas nacionais do
> ETL principal, validadas contra o `.pbix`, e não foram tocadas.

---

## 1. Onde o leiaute pedido e o modelo não coincidem

Quatro pontos. Nenhum impede a geração, mas todos mudam como o resultado deve ser lido.
Cada um está isolado numa constante no topo de `extracao_alcool_2021.py`, de modo que
revisar qualquer decisão destas é trocar uma linha e reexecutar.

### 1.1 `cd_combustivel = 167` não é biometano neste modelo

O leiaute pede o código 167. Em `dim_combustivel`, o 167 é **"Solar térmica"** (grupo
"Outras fontes primárias", unidade "GWh eq", sem PCI). O combustível que o modelo associa
aos dois coprodutos é o **109, "Biometano"** (unidade "mil tep", PCI 0,880) — que é o que
a coluna `volume_combustivel` de fato mede.

Gravamos **167**, como pedido, presumindo que o código venha do codificador do sistema de
destino e não deste modelo. Se a intenção era o código do modelo, a constante
`CD_COMBUSTIVEL` em `extracao_alcool_2021.py` é a única linha a mudar.

### 1.2 `qtd_combustivel` sai vazia — e esse é o resultado correto

O leiaute manda preenchê-la com `combustivel_densificacao` em toneladas. **Nenhum dos
dois coprodutos tem rota de densificação:**

- em `fatores_energetico_combustivel`, ambos têm uma **única** linha, de biodigestão,
  com `fdens` nulo — logo `qct`, a quantidade de combustível sólido, é nula;
- em `dim_energetico`, ambos têm `rotas_possiveis = "Biodigestão"`.

A coluna existe na tabela e vem **em branco nas 524 linhas**. Vazio e zero diriam coisas
diferentes: zero afirmaria que a densificação foi avaliada e não rendeu nada; vazio
afirma que ela não se aplica, que é o caso. Todo o aproveitamento energético destes dois
coprodutos está em `volume_combustivel`.

### 1.3 A vinhaça é medida em m³, não em tonelada

O leiaute pede as quantidades em tonelada. A torta de filtro já sai assim
(`fcoprod_unid = "t/m"`, `dim_energetico.unidade = "tonelada"`). A vinhaça, não:
`fcoprod_unid = "m³/m³"`, `unidade = "metro cubico"`, `estado = "Líquido"`.

O modelo **não carrega densidade de coproduto**, então a conversão não sai de
`csv_exportado`. Adotamos **1,00 t/m³**, densidade usual da vinhaça, que é 93–96% água.
É uma premissa externa ao modelo, declarada na constante `DENSIDADE_VINHACA_T_M3`.

Com ρ = 1,00 o número não muda — muda o rótulo da unidade. Alterar a constante reajusta
as duas colunas de quantidade da tabela 1, e só elas: a tabela 2 é calculada da cadeia do
modelo, na unidade dele.

### 1.4 `cd_origem` — a fonte não traz, e um código novo foi atribuído

`cd_origem` identifica **a base de onde veio o dado de produção**. `dim_origem` tem 23
linhas, códigos 101 a 123, com três níveis de detalhe:

| `cd_origem` | `origem` | `origem_2` | `origem_3` |
|---|---|---|---|
| 101 | `conab_cafe_hist` | `conab_cafe` | `conab` |
| 111 | `ibge_pam_lperm` | `ibge_pam` | `ibge` |
| 118 | `ibge_ppm_rebanho` | `ibge_ppm` | `ibge` |
| 123 | `sinisa_rs_recebido` | `sinisa_rs` | `sinisa` |

Cinco instituições no nível mais agregado: `conab`, `epe`, `ibge`, `mapa`, `sinisa`.
**Não há nenhuma origem da ANP.**

O álcool etílico é o **único produto da fonte inteira sem essa marcação**: as 2.106
linhas de `cd_produto = 1209` têm `cd_origem` nula, contra 6.362.772 linhas preenchidas
em todos os demais produtos. Não é dado faltante disperso — é um produto inteiro que
entrou na base sem registro de procedência.

**Código atribuído: 125.** O sucessor natural de 123 seria 124, mas 124 **já está
ocupado nos fatos**: 62.104 linhas do produto 1199, "RDO e RPU recebido" (2002–2024),
usam esse código, embora ele não conste de `dim_origem` — é um código órfão, presente
nos fatos e ausente da dimensão. Usar 124 para a ANP faria duas fontes distintas
compartilharem o mesmo código. O primeiro valor livre de fato é **125**.

Linha a acrescentar em `dim_origem` para que o código resolva:

| `cd_origem` | `origem` | `origem_2` | `origem_3` |
|---|---|---|---|
| 125 | `anp_producao_etanol` | `anp_producao` | `anp` |

Duas ressalvas. A primeira: **o modelo não afirma que este dado vem da ANP** — a célula
de origem está simplesmente vazia, e a atribuição é conhecimento de domínio de quem
pediu a extração, não algo que `csv_exportado` ateste. A segunda: o código órfão 124
merece correção à parte, já que hoje `dim_origem` não explica a procedência de 62.104
linhas de resíduo sólido urbano.

`CD_ORIGEM` em `extracao_alcool_2021.py` é a única linha a mudar se o valor ou o nome
tiverem de ser outros. A conferência automática garante que as 524 linhas das duas
tabelas saiam com esse código e nenhum outro.

---

## 2. Cadeia de cálculo

```
                producao          [m³ de álcool]
                    │
                    │  × fcoprod
                    ▼
             q_coproduto          [t] torta  |  [m³] vinhaça
                    │
                    │  × fcoleta
                    ▼
             q_energetico         [t] torta  |  [m³] vinhaça
                    │
        ┌───────────┴───────────┐
        │  × conversão p/ t     │  × fmetanizacao
        ▼                       ▼
  qtd_energetico [t]      volume_combustivel [m³ de biometano]
   (tabela 1)                    (tabela 2)
```

Um detalhe de nomenclatura que engana: na fonte, a produção de álcool está numa coluna
chamada `producao_t`, mas o **denominador dos dois fatores de coproduto é m³** (`t/m` e
`m³/m³`). A produção de álcool etílico é medida em metro cúbico; o `_t` é do nome da
coluna, não da grandeza.

### Fatores aplicados

| | Torta de Filtro (150) | Vinhaça (151) |
|---|---|---|
| `fcoprod` | 0,375 | 10,000 |
| `fcoprod_unid` | t/m³ | m³/m³ |
| `fcoleta` | 1,0 | 1,0 |
| conversão para tonelada | 1,00 (já é t) | 1,00 t/m³ (premissa §1.3) |
| `fmetanizacao` | 55,68 m³/t | 8,35 m³/m³ |
| `materia_seca` | 1,0 | 1,0 |
| `fdens` | — (sem densificação) | — (sem densificação) |
| `cd_rota` | 12 (Biodigestão) | 12 (Biodigestão) |
| `cd_subclasse` | 1931400 | 1931400 |

`materia_seca = 1,0` para os dois. Isso tem uma consequência boa: o **defeito de
`materia_seca` do Power BI** (`ERRO_MATERIA_SECA.md`), em que o valor é lido com o ponto
decimal tomado por separador de milhar, **não afeta esta extração** — 1,0 não tem casa
decimal para corromper. E, de todo modo, `materia_seca` só entraria na rota de
densificação, que aqui não existe.

---

## 3. Coluna a coluna

### Tabela 1 — `fato_energetico.csv`

| Coluna | Como é obtida |
|---|---|
| `cd_municipio` | `cd_mu` da fonte, que já é o código IBGE de 7 dígitos |
| `cd_origem` | constante `125` — código novo, ver §1.4 |
| `cd_data` | constante `20210101` |
| `uso_modelo` | constante `sim` |
| `cd_energetico` | `fator_produto_energetico`: 1209 gera 150 e 151 |
| `qtd_energetico` | `producao × fcoprod × conversão` — coproduto **gerado**, em t |
| `qtd_energetico_disp` | `qtd_energetico × fcoleta` — parcela **coletável**, em t |
| `cd_subclasse` | constante `1931400`, que confere com `dim_energetico` |
| `materia_seca` | `dim_energetico` — 1,0 nos dois |
| `cd_rota` | `dim_energetico.cd_rota` — 12 nos dois |

`fcoleta = 1,0` nos dois coprodutos, então `qtd_energetico` e `qtd_energetico_disp` saem
**iguais em todas as 524 linhas**. Isso é resultado, não simplificação: o modelo não
prevê perda de coleta para torta nem para vinhaça — as duas saem prontas da usina.

### Tabela 2 — `fato_combustivel.csv`

| Coluna | Como é obtida |
|---|---|
| `cd_municipio` | `cd_mu` da fonte |
| `cd_combustivel` | constante `167`, conforme pedido — ver §1.1 |
| `cd_origem` | constante `125` — código novo, ver §1.4 |
| `uso_modelo` | constante `sim` |
| `cd_energetico` | 150 / 151 |
| `cd_data` | constante `20210101` |
| `cd_rota` | constante `12`, que confere com `dim_energetico` |
| `cd_subclasse` | constante `1931400` |
| `qtd_combustivel` | `qct` do modelo — **vazia**, ver §1.2 |
| `volume_combustivel` | `vct × 1000` — biometano em m³ |

`vct` sai da cadeia do modelo em **mil m³** (`q_energetico × fmetanizacao ÷ 1000`); o
leiaute pede m³, daí a multiplicação por 1000. Combinando as duas operações, o efeito
líquido é `volume_combustivel = q_energetico × fmetanizacao`.

---

## 4. Exemplo conferido

**Catanduva/SP** (`cd_municipio` 3511102), o maior valor da extração.

Produção de álcool etílico hidratado em 2021: **543.874,5379162189 m³**.

```
TORTA DE FILTRO (150)
  543.874,5379162189  m³ de álcool
    × fcoprod   0,375  →     203.952,95171858207 t   = qtd_energetico
    × fcoleta     1,0  →     203.952,95171858207 t   = qtd_energetico_disp
    × fmetan.   55,68  →  11.356.100,35169065   m³   = volume_combustivel

VINHAÇA (151)
  543.874,5379162189  m³ de álcool
    × fcoprod  10,000  →   5.438.745,379162189  m³
    × ρ         1,00   →   5.438.745,379162189  t    = qtd_energetico
    × fcoleta     1,0  →   5.438.745,379162189  t    = qtd_energetico_disp
    × fmetan.    8,35  →  45.413.523,91600427   m³   = volume_combustivel

qtd_combustivel: vazia nas duas linhas — não há rota de densificação
```

A mesma reconstituição roda sobre as 524 linhas a cada execução
(`extracao_alcool_2021._conferir`), em três identidades:

```
qtd_energetico      ≡ producao × fcoprod × conversão
qtd_energetico_disp ≡ qtd_energetico × fcoleta
volume_combustivel  ≡ qtd_energetico_disp ÷ conversão × fmetanizacao
```

Mais a verificação de que `qtd_combustivel` está vazia, de que `cd_origem` é 125 em todas
as linhas, e de que as duas tabelas cobrem exatamente os mesmos 262 municípios da fonte.

---

## 5. Totais

| Coproduto | Quantidade | Biometano |
|---|---|---|
| 150 Torta de Filtro | 10.300.470,55 t | 573.530.200,19 m³ |
| 151 Vinhaça | 274.679.214,65 t | 2.293.571.442,31 m³ |
| **Total** | | **2.867.101.642,50 m³** |

Diferente das duas colunas de potencial da tabela de dados abertos, **estes dois valores
podem ser somados**: são coprodutos distintos do mesmo produto, pela mesma rota, e não
hipóteses alternativas para o mesmo material.

A vinhaça responde por 80% do biometano com 96% da massa — é muito mais volumosa, mas
metaniza a 8,35 m³/t contra 55,68 da torta.

Aferição de ordem de grandeza: a quantidade de vinhaça implica uma produção nacional de
**27.467.921 m³ de álcool etílico hidratado** em 2021 (`274.679.214,65 ÷ 10`), ou ~27,5
bilhões de litros — compatível com a produção brasileira de etanol daquele ano.

---

## 6. Reprodução

```bash
cd etl_sienergia
python extracao_alcool_2021.py
```

Lê `X:\SIEnergia\bd\csv_exportado\` (somente leitura) e grava os dois arquivos em
`saida/alcool_2021/`. Cerca de 4 minutos — o filtro por produto e ano vem depois da
tipagem, então a fonte inteira é percorrida. Ao final imprime os totais e a conferência.

Documentos relacionados: `MEMORIAL_DE_CALCULO.md` (a cadeia completa do modelo),
`DICIONARIO_DADOS_ABERTOS.md` (a tabela nacional), `ERRO_MATERIA_SECA.md` (o defeito que
não afeta esta extração).
