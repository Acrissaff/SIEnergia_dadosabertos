# Resíduos de indústria de abate — nova base de cálculo

**O que mudou:** os três coprodutos de abate deixaram de ser *sebo* (fração da carcaça) e passaram a ser *resíduos de indústria de abate* (efluente do frigorífico), com fator por cabeça abatida e rota de biodigestão
**Onde:** `dim_energetico.csv`, `fatores_produto_energetico.csv`, `fatores_energetico_combustivel.csv` em `csv_exportado`; `fatos.py` e `dados_abertos.py` neste pacote
**Efeito:** +4.422,6 ktep no potencial de biodigestão acumulado (1997–2024), ~176 ktep/ano no nível de 2021; densificação inalterada
**Data:** 31/08/2026
**Status no Power BI:** aplicado em 01/09/2026 — a query `fato_energetico` passou a priorizar `abate`, depois `rebanho` e, por fim, `producao_t`

---

## 1. Por que mudou

Os coprodutos 127, 128 e 129 eram *Sebo de bovino / suíno / ave*, com `fcoprod` em t/t
sobre o peso de carcaça (0,2, 0,3 e 0,1) e `fcoleta = 0`. Duas consequências:

1. **Nada era aproveitado.** Com `fcoleta = 0`, `q_energetico` era zero nas 422.435
   linhas — o sebo entrava no arquivo apenas como quantidade de coproduto.
2. **Não havia rota.** `cd_rota = 14` (Nenhuma) e ausência na tabela
   `fatores_energetico_combustivel` faziam o join com combustível cair fora, de modo que
   os três nunca apareciam em `fato_combustivel`.

O sebo é, além disso, a fração *nobre* da carcaça — matéria-prima de biodiesel e de
saboaria, com destino de mercado já estabelecido —, e não o que sobra para digestão
anaeróbia. O que um frigorífico envia ao biodigestor é o **efluente**: sangue, conteúdo
ruminal, lavagem, restos de graxaria. É essa a corrente que o modelo passa a representar.

## 2. O que mudou nos arquivos de origem

### `fatores_produto_energetico.csv`

| cd_produto | produto | fcoprod | unidade | fcoleta | cd_energetico |
|---|---|---|---|---|---|
| 1168 | Carcaça de bovino - Total | 0,2 → **1,1** | t/t → **m³/cabeça abatida** | 0 → **1** | 127 |
| 1174 | Carcaça de suíno | 0,3 → **0,75** | t/t → **m³/cabeça abatida** | 0 → **1** | 128 |
| 1175 | Carcaça de ave | 0,1 → **0,018** | t/t → **m³/cabeça abatida** | 0 → **1** | 129 |

`fcoleta = 1` porque a fonte é industrial: o efluente já está concentrado num ponto
único e não há a dispersão em campo que justifica um fator de coleta menor que 1 na
lavoura e na pecuária.

Os volumes por cabeça — 1.100 L por bovino, 750 L por suíno, 18 L por ave — guardam entre
si a proporção esperada dos portes.

**Os seis produtos bovinos 1168–1173 continuam com fator em apenas um deles (1168,
"Total").** Os outros cinco são recortes do mesmo abate; dar-lhes fator duplicaria a
contagem. Foi assim que o modelo sempre tratou o caso, e a mudança preserva isso.

### `dim_energetico.csv`

| cd | energetico | classe | tipo | materia_seca | unidade | cd_rota |
|---|---|---|---|---|---|---|
| 127 | Sebo de bovino → **Resíduos de indústria de abate - Bovinos** | Coproduto → **Resíduo** | Sebo → **Resíduos de abate** | 0.5 → **1** | tonelada → **metro cubico** | 14 → **12** |
| 128 | Sebo de suíno → **Resíduos de indústria de abate - Suínos** | idem | idem | 0.5 → **1** | idem | 14 → **12** |
| 129 | Sebo de ave → **Resíduos de indústria de abate - Aves** | idem | idem | 0.5 → **1** | idem | 14 → **12** |

`cd_rota` 14 (Nenhuma) → 12 (Biodigestão) é a mudança que faz os três passarem pela
regra de supressão por `rotas_possiveis`. `unidade` acompanha `fcoprod`, que agora
entrega metros cúbicos de efluente e não toneladas de sebo.

`materia_seca` vai a **1** por três razões convergentes: é o valor que a vinhaça já usa —
o análogo mais próximo, resíduo líquido medido em m³ e só biodigerido —; só entra na
fórmula da densificação, que não se aplica aqui; e `1` é o único valor imune ao defeito
de conversão decimal descrito em [`ERRO_MATERIA_SECA.md`](ERRO_MATERIA_SECA.md), por não
ter ponto.

### `fatores_energetico_combustivel.csv` — três linhas novas

| cd_energetico | fdens | fmetanizacao | cd_combustivel |
|---|---|---|---|
| 127 Resíduos de indústria de abate - Bovinos | *(vazio)* | 4,76026 | 109 Biometano |
| 128 Resíduos de indústria de abate - Suínos | *(vazio)* | 1,21333 | 109 Biometano |
| 129 Resíduos de indústria de abate - Aves | *(vazio)* | 0,06467 | 109 Biometano |

`fmetanizacao` está em **Nm³ de metano por m³ de resíduo**, a mesma convenção da vinhaça
(8,35) e da torta de filtro (55,68) — e **não** a convenção dos estercos, cujo fator é
por tonelada. `fdens` vazio é o que declara a rota única: sem ele, a linha não é
elegível à densificação.

### `dim_produto.csv` — sem alteração

Os produtos 1168, 1174 e 1175 continuam sendo carcaças: é o que a fonte do IBGE mede.
O que mudou foi o coproduto que deles se extrai, e isso vive em `dim_energetico`.
Alterar `dim_produto` renomearia o dado bruto para descrever o derivado.

O arquivo entrou no backup mesmo assim, por precaução.

## 3. A cadeia, ponta a ponta

```
abate [cabeças]  × fcoprod [m³/cabeça]     = q_coproduto  [m³ de resíduo]
q_coproduto      × fcoleta = 1             = q_energetico [m³ de resíduo]
q_energetico     × fmetanizacao [Nm³/m³]   = CH₄ [Nm³]  → ÷1000 = vct [mil m³]
vct ÷ 1000 × 0,88 [ktep/MM m³]             = potencial de biodigestão [ktep]
```

Conferido no arquivo publicado, ano de 2021:

| Coproduto | Cabeças abatidas | m³ de resíduo | Nm³ de CH₄ | ktep |
|---|---|---|---|---|
| Bovinos | 27.615.107 | 30.376.618 | 144.600.598 | 127,2 |
| Suínos | 53.027.651 | 39.770.738 | 48.255.030 | 42,5 |
| Aves | 5.990.134.808 | 107.822.427 | 6.972.876 | 6,1 |
| **Total** | | | **199.828.504** | **175,8** |

Os totais de cabeças correspondem ao abate brasileiro de 2021 e servem de aferição
independente da base.

## 4. Efeito no arquivo de dados abertos

| Métrica | Antes | Depois | Variação |
|---|---|---|---|
| Linhas | 6.233.284 | 6.233.284 | — |
| `q_coproduto_t` | 195.743.535.399 | 199.520.636.426 | +3.777.101.027 |
| `q_energetico_t` | 154.800.007.274 | 158.664.285.931 | +3.864.278.657 |
| `potencial_rota_densificacao_ktep` | 2.811.975,0 | 2.811.975,0 | — |
| `potencial_rota_biodigestao_ktep` | 2.192.715 | 2.197.137,7 | **+4.422,6** |

A contagem de linhas não muda porque as 422.435 linhas dos três coprodutos já existiam —
o que mudou foi o valor delas. E os +4.422,6 ktep de biodigestão são **exatamente** o
somatório dos três coprodutos novos, o que demonstra que nenhum outro produto foi
afetado. A densificação fica idêntica ao dígito, como tem de ficar: nada nesta mudança
toca aquela rota.

`q_energetico_t` cresce mais que `q_coproduto_t` porque `fcoleta` saiu de 0 para 1: antes,
todo o coproduto se perdia na coleta.

### Coluna nova: `abate`

O arquivo passa a publicar `abate`, ao lado de `producao_t` e `rebanho`. Vale para as
três o mesmo invariante de sempre: **exatamente uma está preenchida por linha** — a que
o modelo consumiu. Os produtos de abate trazem também `producao_t` (o peso de carcaça),
que não entra na conta e por isso sai em branco. `main()` confere essa exclusividade a
cada execução.

| Base | Linhas |
|---|---|
| `producao_t` | 4.247.728 |
| `rebanho` | 1.560.472 |
| `abate` | 422.435 |
| nenhuma | 2.649 |

Cobertura temporal dos três coprodutos: **1997–2024**. É onde a pesquisa de abate do
IBGE tem série; antes disso não há dado, e as linhas não existem.

### Efeito nas tabelas de fatos

| Tabela | Antes | Depois |
|---|---|---|
| `fato_energetico` | 6.233.284 | 6.233.284 |
| `fato_combustivel` | 6.693.485 | **7.115.920** |
| `dim_rotas_possiveis` | 4 linhas | **3 linhas** |

`fato_combustivel` cresce exatamente 422.435 linhas: os três coprodutos passam a ter
combustível e deixam de ser eliminados pelo filtro `cd_combustivel <> null`. Antes,
nenhuma linha de sebo chegava a esta tabela.

`dim_rotas_possiveis` perde a entrada **Nenhuma**. Ela existia só por causa do sebo, que
era o único energético com `cd_rota = 14` a ter linhas no fato. Os três códigos restantes
não se moveram — *Nenhuma* era o último na ordem de primeira aparição, que é como essa
dimensão se indexa —, então nada que dependa de `cd_rotas_possiveis` 1, 2 ou 3 muda.
`fator_rota` fica idêntica, com as mesmas 27 linhas.

## 5. Ajuste aplicado no Power BI

**A edição dos CSVs isoladamente não bastava.** A versão anterior da query
`fato_energetico` escolhia a base entre apenas duas colunas e removia `abate` logo em
seguida:

```m
#"PAdicionada - coproduto" = Table.AddColumn(#"fator_produto_energetico Expandido",
    "q_coproduto", each if [rebanho] <> null then [rebanho]*[fcoprod]
                        else [producao_t]*[fcoprod]),
```

Com os CSVs novos e o M antigo, o modelo multiplicaria `producao_t` — o peso de carcaça
em toneladas — por um fator que é metros cúbicos por cabeça. `rebanho` é nulo nas 422.435
linhas destes produtos (conferido), então a linha cairia sempre no `else` final.

O PBIX atualizado em 01/09/2026 já contém a forma compacta equivalente:
`([abate] ?? [rebanho] ?? [producao_t]) * [fcoprod]`.

O resultado não teria significado físico, e seria **menor** que o correto na razão do peso
médio de carcaça: `producao_t = abate × peso_kg ÷ 1000`, de modo que o modelo entregaria
`peso_kg/1000` do valor devido — 3,7× a menos em bovinos, 10,8× em suínos e **486× a
menos** em aves, cujo peso de carcaça é ~2 kg. Não é um erro que salte aos olhos pela
ordem de grandeza do total; salta pela proporção entre as três espécies, que se inverte.

### O que já está pronto no modelo

Três coisas não precisam de trabalho nenhum, e vale saber disso antes de escolher a
opção:

- **`abate` já chega tipada.** A query `fato_produto` a converte em `type number` junto
  com as demais (`{"abate", type number}`), desde sempre. Não é preciso tocar nela.
- **`abate` já está disponível na etapa certa.** Ela sobrevive até
  `#"Colunas Removidas"`, que vem *depois* de `#"PAdicionada - coproduto"` — é por isso
  que aquela etapa precisa removê-la explicitamente hoje.
- **`fato_combustivel` não muda.** Ela só consome `q_energetico`, `fdens`,
  `materia_seca` e `fmetanizacao`; a aritmética independe da unidade. Os três coprodutos
  passam a atravessá-la sozinhos, porque deixam de cair no filtro
  `[cd_combustivel] <> null`.

A alteração é, portanto, **uma etapa de uma query**. As duas opções abaixo diferem só no
critério do teste.

### Opção A — testar `abate` por nulo (recomendada)

```m
#"PAdicionada - coproduto" = Table.AddColumn(#"fator_produto_energetico Expandido",
    "q_coproduto", each if [abate] <> null then [abate]*[fcoprod]
                        else if [rebanho] <> null then [rebanho]*[fcoprod]
                        else [producao_t]*[fcoprod]),
```

É o mesmo idioma do teste que já existe — `<> null`, sem função de texto e sem guarda de
nulo — e por isso a que menos destoa do resto do modelo.

**O que a torna segura** (verificado sobre as 6.364.878 linhas da fonte):

- `abate` está preenchida em **oito produtos, todos carcaças** (1168–1175) e em nenhum
  outro;
- **nenhuma linha do arquivo tem `abate` e `rebanho` preenchidas ao mesmo tempo**, de
  modo que a ordem entre os dois primeiros testes é indiferente;
- dos oito, cinco (1169–1173, os recortes bovinos) **não têm linha em
  `fatores_produto_energetico`** e são eliminados pelo `JoinKind.Inner` da etapa
  anterior — nunca chegam a este `if`. Só 1168, 1174 e 1175 passam.

**A ressalva:** o critério é a presença do dado, não a unidade do fator. Se um dia se
cadastrar um produto de carcaça com fator em `t/t` — sebo de verdade, por exemplo —, ele
cairia no ramo de `abate` indevidamente. A Opção B não tem esse risco.

Essa ressalva já está coberta no ETL Python: `dados_abertos._conferir_invariante` compara,
a cada geração, os dois critérios nas duas direções — linha que usou `abate` com fator que
não é por cabeça abatida, e fator por cabeça abatida em linha sem `abate`. Qualquer
divergência entre eles reprova a geração.

**É esta a opção implementada.** `fatos.base_por_cabeca` testa `abate.notna()`. A troca foi
verificada regerando o arquivo inteiro e comparando byte a byte com a geração anterior,
que usava o critério da Opção B: **os 1.139.795.864 bytes são idênticos**. Os dois
critérios selecionam exatamente as mesmas 422.435 linhas na base de hoje.

#### Forma compacta, com o operador `??`

Equivalente e mais curta, útil quando o M precisa caber num orçamento de bytes:

```m
#"PAdicionada - coproduto" = Table.AddColumn(#"fator_produto_energetico Expandido",
    "q_coproduto", each ([abate] ?? [rebanho] ?? [producao_t])*[fcoprod]),
```

`a ?? b` devolve `a` quando `a` não é nulo, e `b` caso contrário — a mesma precedência dos
três testes encadeados, na mesma ordem. Cabe em 53 bytes contra os 79 da expressão em
produção, o que abre folga para uma edição de comprimento fixo (ver §6).

### Opção B — testar a unidade do fator

```m
#"PAdicionada - coproduto" = Table.AddColumn(#"fator_produto_energetico Expandido",
    "q_coproduto", each if Text.Contains([fcoprod_unid] ?? "", "cabeça abatida")
                            then [abate]*[fcoprod]
                        else if [rebanho] <> null then [rebanho]*[fcoprod]
                        else [producao_t]*[fcoprod]),
```

Aqui o critério é o que dimensionalmente justifica o ramo: um fator em m³ por cabeça
abatida **tem** de multiplicar cabeças abatidas. Cadastrar um novo produto de abate na
tabela de fatores com a unidade certa passa a bastar para que ele seja calculado, sem
abrir o M outra vez.

**O `?? ""` não é precaução teórica.** A linha de fator de **Cana-de-açúcar → Ponta de
Cana** (1048 → 111) tem `fcoprod_unid` vazia, e é um dos produtos com mais linhas do
arquivo. Sem a guarda, `Text.Contains(null, ...)` devolve `null`, o `if` recebe um nulo
onde espera um lógico e a atualização falha com *"Não é possível converter o valor null
para o tipo Logical"* — em milhões de linhas, não numa borda rara.

Se o operador `??` não estiver disponível na versão instalada, o equivalente é
`Text.Contains(if [fcoprod_unid] = null then "" else [fcoprod_unid], "cabeça abatida")`.

### A ordem dos testes importa nas duas

O teste de `abate` tem de vir **antes do `else` final**, porque os produtos de carcaça
trazem `producao_t` preenchida — o peso de carcaça. Se ele viesse por último, o
`else [producao_t]*[fcoprod]` capturaria a linha primeiro e a conta sairia pelo caminho
errado, sem erro nenhum a sinalizar o problema.

Entre `abate` e `rebanho` a ordem é indiferente (nunca coexistem), mas manter `abate`
primeiro deixa a leitura alinhada com a documentação.

### O que não fazer

- **Coluna Condicional pela interface** (*Adicionar Coluna → Coluna Condicional*) não
  resolve: ela só entrega valores ou colunas como resultado, não o produto de duas
  colunas. É preciso o Editor Avançado.
- **Acrescentar uma coluna de base a `fatores_produto_energetico.csv`** parece mais
  limpo, mas a query lê o arquivo com `Csv.Document(..., Columns=7)`. Uma oitava coluna
  exige alterar esse número junto, sob pena de ela ser silenciosamente ignorada — troca
  uma edição de M por duas, num arquivo e numa query.
- **Reescrever `producao_t` em cabeças na origem** desfaria as medidas *Produção
  (mil t)*, *Rend. (kg/ha)* e *Geração (kg/hab/dia)*, que somam a coluna sem filtrar
  produto. Ver a seção 8.

### Passo a passo

1. **Página Inicial → Transformar dados.**
2. No painel de consultas, selecionar **`fato_energetico`**.
3. **Exibição → Editor Avançado.**
4. Substituir a linha que começa em `#"PAdicionada - coproduto"` pelo bloco da opção
   escolhida. É a única linha alterada; as demais etapas ficam intactas.
5. **Concluído**, e **Fechar e Aplicar**.

Se a correção de [`ERRO_MATERIA_SECA.md`](ERRO_MATERIA_SECA.md) for aplicada na mesma
sessão, as duas são independentes e não conflitam — estão em queries diferentes. Os três
coprodutos de abate, aliás, não são afetados por aquele defeito: `materia_seca = 1` não
tem ponto decimal, e eles são de rota única em biodigestão.

### Verificação depois de aplicar

1. Em **Transformar dados**, `dim_energetico` deve mostrar os três nomes novos com
   `cd_rota = 12`, e `fatores_energetico_combustivel` deve ter 51 linhas (eram 48).
2. Ainda em `fato_energetico`, filtrar `cd_energetico = 127` e conferir uma linha à mão:
   `q_coproduto` tem de ser 1,1 × cabeças, e não 1,1 × toneladas. Um município grande de
   2021 dá na casa dos 10⁵ m³ — ver o exemplo de Corumbá/MS no
   [memorial](MEMORIAL_DE_CALCULO.md).
3. `fato_combustivel` passa a ter **+422.435 linhas** e, pela primeira vez, linhas para
   os energéticos 127, 128 e 129.
4. A medida de biometano sobe **~176 ktep no filtro de 2021** e ~4.423 ktep no
   acumulado; o total da densificação **não se move nem um dígito**.
5. `dim_rotas_possiveis` cai de 4 para 3 linhas — *Nenhuma* deixa de existir. Os códigos
   1, 2 e 3 não se deslocam, então nada que dependa deles muda.

Se o passo 4 mostrar a densificação mudando, a edição atingiu a etapa errada.

### Rollback

Desfazer é reabrir o Editor Avançado e restaurar a condição de dois ramos. Como o
`.pbix` guarda o M inteiro, convém salvar uma cópia do arquivo antes de aplicar — é o
rollback mais rápido, e o único que também reverte o cache de dados do modelo.

## 6. Backup e rollback

Cópia dos quatro arquivos como estavam antes da edição, em dois lugares:

- `X:\SIEnergia\bd\csv_exportado\backup_20260831_pre_residuos_abate\`
- `etl_sienergia\backup\20260831_pre_residuos_abate\`

| Arquivo | Bytes | sha256 (16 primeiros) |
|---|---|---|
| `fatores_produto_energetico.csv` | 4.067 | `c90217abd35168f2` |
| `fatores_energetico_combustivel.csv` | 2.407 | `42e0b2c17fd5ea3f` |
| `dim_energetico.csv` | 3.548 | `5c13673a8357a68e` |
| `dim_produto.csv` | 15.047 | `7ba444bc4e9dec7e` |

Para reverter, basta copiá-los de volta e reexecutar `dados_abertos.py`. Do lado do
código, o ramo novo em `fatos.py` fica inerte sozinho: sem nenhum fator com unidade
"cabeça abatida", `base_por_cabeca` não seleciona linha alguma e a cadeia volta ao
comportamento de duas bases.

## 7. Ressalvas

- **Os fatores são de literatura, não de medição.** Os volumes por cabeça e os
  rendimentos de metano vieram de levantamento bibliográfico. Um frigorífico real varia
  com o processo, com o grau de recirculação de água e com o pré-tratamento do efluente.
- **`materia_seca = 1` é convenção, não medida.** O efluente de abate é diluído; o valor
  1 está ali porque a coluna não participa da conta em nenhuma linha destes coprodutos.
  Se algum dia se abrir uma rota de densificação para eles, o valor precisa ser revisto
  antes.
- **A cobertura começa em 1997.** Séries anteriores de potencial não incluem estes
  coprodutos, e comparações que atravessem 1997 têm um degrau que não é econômico.
- **`abate` é estimativa rateada, não contagem.** 422.392 das 422.435 linhas trazem valor
  com parte fracionária: a pesquisa de abate do IBGE apura por unidade da federação, e o
  valor municipal vem de rateio na base de origem. A unidade continua sendo cabeças — a
  razão `producao_t × 1000 ÷ abate` dá mediana de 231 kg em bovinos, 81 kg em suínos e
  2,0 kg em aves, que são os pesos de carcaça —, mas um município isolado carrega a
  incerteza do rateio.

## 8. Por que não reescrever `producao_t` em cabeças

A pergunta aparece naturalmente: se o problema é o M escolher a coluna errada, por que
não pôr o número de cabeças na coluna que ele já lê?

### A relação entre as duas colunas é exata

`producao_t` e `abate` **não são medições independentes**. A razão
`producao_t × 1000 ÷ abate` — quilos de carcaça por cabeça — tem **coeficiente de
variação exatamente zero dentro de cada UF-ano**: 100% dos 671 grupos de bovinos, 565 de
suínos e 485 de aves. As duas colunas saem da mesma apuração estadual do IBGE, rateadas
ao município pela mesma chave.

O elo é o **peso médio de carcaça da UF no ano** — não uma constante nacional:

| kg/cabeça (Brasil) | 1997 | 2005 | 2015 | 2021 | 2024 |
|---|---|---|---|---|---|
| Bovinos | 223,9 | 226,3 | 244,6 | 269,2 | 261,0 |
| Suínos | 74,2 | 91,9 | 87,4 | 92,4 | 92,1 |
| Aves | 1,68 | 1,81 | 1,93 | 2,06 | 2,11 |

Por UF a amplitude é maior: bovinos vão de 162 a 313 kg. A conversão é exatamente
invertível — `abate = producao_t × 1000 ÷ peso(uf, ano)` —, de modo que a substituição
seria tecnicamente possível.

### Mas custa três coisas

1. **Desfaz medidas DAX em produção.** `producao_t` alimenta **Produção (mil t)**,
   **Rend. (kg/ha)** e **Geração (kg/hab/dia)** em `fato_produto`, sem filtro de produto.
   Aves passariam a reportar 5.990.135 "mil t" no lugar de 12.332 — erro de 486×.
2. **Exige regravar `fatos_hist_mu_mod.csv`** (268 MB, 6,36 M linhas), que é gerado por
   processo a montante: a próxima regeração desfaz a edição em silêncio.
3. **Destrói a tonelada de carcaça**, grandeza legítima e publicada.

### A variante sem código, e por que também não serve

Como a relação é exata, dá para reexpressar `fcoprod` em **m³ por tonelada de carcaça** e
deixar o M atual funcionando sem alteração nenhuma. Calibrando pelo peso nacional de
2021:

| | fcoprod m³/t | ktep por cabeça | ktep por massa | erro |
|---|---|---|---|---|
| Bovinos | 4,0861 | 3.532,1 | 3.180,2 | −10,0% |
| Suínos | 8,1203 | 759,0 | 733,5 | −3,4% |
| Aves | 8,7290 | 131,5 | 122,4 | −6,9% |
| **Total** | | **4.422,6** | **4.036,1** | **−8,7%** |

O erro zera no ano de calibração e cresce para trás — **−17% a −20% em 1997**, quando os
animais eram mais leves —, além de variar entre UFs dentro do mesmo ano. É a deriva do
peso médio, que um fator de valor único não acompanha.

Trocaria, além disso, o modelo físico: *efluente por cabeça*, que é o que a literatura
mediu, por *efluente por tonelada de carcaça*. Duas linhas de M custam menos.
