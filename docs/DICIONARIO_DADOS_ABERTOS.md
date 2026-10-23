# `sienergia_potencial_energetico_mu.csv` — dicionário de dados

Potencial energético da produção agropecuária brasileira, desagregado por município,
ano, produto e coproduto energético, sob dois cenários de rota tecnológica.

Derivado do modelo SIEnergia (`SIEnergia-hml.pbix`), reimplementado em Python. Ver
`MAPEAMENTO_MODELO.md` para a tradução completa das fórmulas.

| | |
|---|---|
| **Linhas** | 6.455.437 |
| **Cobertura** | 5.570 municípios, 1974–2024, 40 produtos, 48 coprodutos energéticos |
| **Grão** | município × ano × produto × coproduto energético |
| **Formato** | CSV, separador `;`, decimal `,`, codificação UTF-8 com BOM |
| **Tamanho** | ~1,19 GB (1.188.249.153 bytes) |

---

## Colunas

### Identificação

| Coluna | Tipo | Descrição |
|---|---|---|
| `cd_mu` | inteiro | Código IBGE do município (7 dígitos) |
| `municipio` | texto | Nome do município |
| `uf` | texto | Sigla da unidade federativa |
| `ano` | inteiro | Ano de referência da produção |
| `cd_produto` | inteiro | Código do produto agropecuário no modelo |
| `produto` | texto | Nome do produto (Soja, Milho, Bovino…) |
| `cd_energetico` | inteiro | Código do coproduto energético |
| `energetico` | texto | Nome do coproduto (Palha de Soja, Esterco de Frango…) |
| `rotas_possiveis` | texto | Rota tecnológica declarada — ver ressalva abaixo |
| `cd_origem` | inteiro | Origem do dado de produção (IBGE, CONAB…) |

### Cadeia de cálculo

Na ordem em que entram na conta. Fórmulas, unidades e exemplos conferidos em
**`MEMORIAL_DE_CALCULO.md`**.

| Coluna | Unidade | Descrição |
|---|---|---|
| `producao_t` | t | Produção agrícola. Vazia nos produtos pecuários |
| `rebanho` | cabeças | Efetivo pecuário. Vazia nos produtos agrícolas |
| `abate` | cabeças | Cabeças abatidas. Preenchida só nos resíduos de indústria de abate |
| `fcoprod` | ver `fcoprod_unid` | Fator de coproduto |
| `fcoprod_unid` | texto | Unidade de `fcoprod`: `t/t` (lavoura), `t/animal` (pecuária) ou `m³/cabeça abatida` (abate) |
| `q_coproduto_t` | t, ou m³ nos resíduos de abate | Coproduto gerado — `base × fcoprod` |
| `fcoleta` | adimensional | Fração coletável, entre 0 e 1 |
| `q_energetico_t` | t, ou m³ nos resíduos de abate | Parcela coletável — `q_coproduto_t × fcoleta` |
| `fdens` | ver `fdens_unid` | Fator de densificação |
| `fdens_unid` | texto | Unidade de `fdens`, tipicamente `tbs/tbs` (base seca) |
| `materia_seca` | adimensional | Teor de matéria seca, entre 0 e 1 |
| `combustivel_densificacao` | texto | Briquete, Carvão vegetal ou Lenha comercial |
| `pci_densificacao` | tep/t | PCI do combustível sólido |
| `potencial_rota_densificacao_ktep` | ktep | Potencial se 100% for densificado |
| `fmetanizacao` | m³/t, ou Nm³/m³ nos resíduos de abate | Potencial de metanização |
| `combustivel_biodigestao` | texto | Sempre Biometano |
| `pci_biodigestao` | tep por mil m³ | PCI do biometano |
| `potencial_rota_biodigestao_ktep` | ktep | Potencial se 100% for biodigerido |

### Regra de preenchimento

> **Uma coluna de fator está preenchida se, e somente se, ela entrou no cálculo daquela
> linha.**

As cinco colunas de densificação (`fdens` a `pci_densificacao`) acompanham exatamente
`potencial_rota_densificacao_ktep`; as três de biodigestão acompanham
`potencial_rota_biodigestao_ktep`. `fcoprod` e `fcoleta` estão sempre preenchidas.

Das três colunas de base, vem preenchida **apenas a que o modelo usou**: `abate` quando
essa coluna existe na origem, `rebanho` quando existe, `producao_t` caso contrário. São
4.460.833 linhas com `producao_t`, 1.560.472 com `rebanho` e 422.435 com `abate`.

A exclusividade importa: os produtos de abate trazem também `producao_t` na origem — o
peso de carcaça —, que não entra na conta e por isso sai em branco. Somar as três
colunas nunca é correto.

Nas 11.697 restantes as três estão vazias: 2.649 linhas de **Esgoto coletado** e 9.048
linhas dos seis coprodutos de **RDO e RPU coletado**, todas em 2023 e 2024. Correspondem
a municípios cuja célula de produção está em branco na base SINISA de origem. A cadeia
resolve em zero nas rotas aplicáveis, então o zero significa *não reportado*, e não *não
gera*. Essas linhas não alteram nenhum total.

### Os resíduos de indústria de abate

Três coprodutos — bovinos, suínos e aves — fogem à unidade das demais linhas: a base é o
número de **cabeças abatidas**, `fcoprod` está em **m³ de efluente por cabeça** e
`fmetanizacao` em **Nm³ de metano por m³ de efluente**. Logo `q_coproduto_t` e
`q_energetico_t` carregam ali metros cúbicos, e não toneladas, apesar do sufixo do nome.
A coluna `fcoprod_unid` é o que distingue o caso, e a cadeia fecha nas mesmas quatro
identidades.

Cobrem 1997–2024, que é a extensão da pesquisa de abate do IBGE. Detalhes e a origem dos
fatores em **`RESIDUOS_ABATE.md`**.

### Os resíduos domiciliares e públicos — RDO e RPU

O produto **RDO e RPU coletado** (`cd_produto = 1208`) é desdobrado em seis frações:
metais, papéis, plástico, vidro, outros e matéria orgânica. Os dados de 2002–2022 vêm do
indicador SINISA `CO119 — Quantidade total de RDO e RPU coletada por todos os agentes`;
os anos de 2023 e 2024 usam os arquivos anuais por município de origem.

Papéis e plástico seguem a rota de densificação. A matéria orgânica admite densificação
e biodigestão. Metais, vidro e outros têm `fcoleta = 0` e rota `Nenhuma`, permanecendo no
arquivo para que a composição gravimétrica feche sem atribuir potencial energético a
frações não aproveitadas pelo modelo.

## Como os números são obtidos

```
q_coproduto_t  = (producao_t, rebanho ou abate) × fcoprod
q_energetico_t = q_coproduto_t × fcoleta
densificação   = q_energetico_t × fdens × materia_seca ÷ 1000 × pci_densificacao
biodigestão    = q_energetico_t × fmetanizacao ÷ 1000 ÷ 1000 × pci_biodigestao
```

Todos os termos estão no próprio arquivo, então cada linha pode ser conferida sozinha,
sem abrir o `.pbix`. As quatro identidades são verificadas sobre as 6,5 milhões de linhas
a cada geração.

O memorial completo — unidades, origem de cada divisão por 1000, exemplos numéricos e os
pontos onde o arquivo diverge do Power BI — está em **`MEMORIAL_DE_CALCULO.md`**.

`cd_origem` é preservada por rastreabilidade. Nenhuma combinação de município, ano e
produto tem mais de uma origem, então agregar sobre ela não soma fontes distintas.

---

## As duas colunas de potencial são rota-puras

Cada coluna responde a uma pergunta isolada: **quanta energia este coproduto renderia se
100% dele seguisse por esta rota?** O preenchimento segue a rota tecnológica declarada em
`rotas_possiveis`:

| `rotas_possiveis` | Linhas | `..._densificacao_ktep` | `..._biodigestao_ktep` |
|---|---|---|---|
| `Biod. e Densif.` | 4.051.861 | 2.082.607 preenchidas | 2.082.607 preenchidas |
| `Biodigestão` | 1.783.304 | **nenhuma** | 1.783.304 preenchidas |
| `Densificação` | 484.093 | 362.147 preenchidas | **nenhuma** |
| `Nenhuma` | 136.179 | **nenhuma** | **nenhuma** |

Totais: **3.400.954 ktep** na densificação e **2.513.820 ktep** na biodigestão.
4.228.058 das 6.455.437 linhas (65,5%) têm potencial em ao menos uma rota.

A rota `Nenhuma` permanece apenas nas frações não energéticas de RDO/RPU: metais, vidro
e outros. Os três resíduos de indústria de abate, que antes também carregavam essa rota,
passaram a ter fator de biodigestão.

> **As duas colunas não devem ser somadas.** Para um coproduto de dupla rota, elas são
> hipóteses mutuamente exclusivas — a mesma palha, destinada a um lugar ou a outro —,
> não parcelas de um total. Somá-las contaria a mesma biomassa duas vezes.

Para estimar um cenário misto, escolha uma coluna por coproduto conforme a rota que se
quer atribuir a ele, e só então some.

**Por que ktep?** Densificação produz massa (mil t de briquete) e biodigestão produz
volume (M m³ de biometano). As duas grandezas não são comparáveis em unidade física; o
ktep é o que permite pô-las lado a lado. Quem precisar das quantidades físicas deve usar
`fato_combustivel.csv`, que mantém `qct` (massa) e `vct` (volume) por combustível.

### Vazio e zero são coisas diferentes

**Vazio** significa que a rota não se aplica àquele coproduto. **Zero** significa que a
rota se aplica, mas a produção registrada naquele município e ano resultou em potencial
nulo. Filtros e agregações devem tratar os dois casos distintamente.

## Diferença para o cenário de rota do Power BI

O relatório SIEnergia trabalha com **cenários** (`dim_rota_cenario`): 100% densificação,
meio-a-meio e 100% biodigestão. Naquele desenho, o cenário reparte apenas os coprodutos
de dupla rota, e os demais seguem sua única rota viável — de modo que o total de
"100% densificação" inclui o biometano do esterco.

Este arquivo adota o recorte por coproduto, não por cenário. Um valor em
`potencial_rota_densificacao_ktep` é sempre combustível sólido; um valor em
`potencial_rota_biodigestao_ktep` é sempre biometano. Não há mistura.

## Potencial em branco

Cerca de 2,2 milhões de linhas têm as duas colunas vazias. Isso **não é dado faltante** —
significa que aquele coproduto não tem fator de conversão em combustível no modelo.

A causa é uma só: **rota declarada, mas sem fator de conversão** — 15 das 51 entradas
declaram rota em `dim_energetico` sem ter entrada correspondente em
`fatores_energetico_combustivel`:

> Madeira, Madeira - Extrat., Cacho de Banana, Grão de Café, Fruto da Laranja,
> Caroço de Algodão, Caroço de Algodão - código legado sem uso, Grão de Arroz,
> Colmo de Cana, Grão de Feijão, Raiz de Mandioca, Grão de Milho, Grão de Soja,
> Grão de Trigo, Pastagem

A entrada legada do Caroço de Algodão não recebe linhas do fato. A associação duplicada
foi removida em 02/09/2026, mantendo apenas o código canônico 140. Na mesma correção, o
Feijão passou a apontar para Grão de Feijão (144), e a Ponta de Cana recebeu os fatores
de densificação e metanização da Palha de Cana.

Quase todos são o **produto principal**, não o resíduo — não se briqueta grão nem se
biodigere fibra de algodão. A ausência de fator é correta; o valor de
`rotas_possiveis` é que está desatualizado nessas linhas, herdado de `dim_rota` por
`cd_rota` sem reflexo na tabela de fatores.

**Consequência prática:** não filtre por `rotas_possiveis` esperando isolar as linhas
com potencial. Filtre pelas colunas de potencial não nulas.

## Nota técnica: rótulo de rota x tabela de fatores

Sete coprodutos têm, em `fatores_energetico_combustivel`, linhas de uma rota que
`dim_energetico` não lhes atribui:

| Coproduto | `rotas_possiveis` | Fatores presentes |
|---|---|---|
| Esterco bovino (corte e leite), suíno, de frango, de galinha | `Biodigestão` | biodigestão **e densificação** |
| Papéis, Plástico | `Densificação` | densificação **e biodigestão** |

Nos cinco estercos, a linha de densificação traz `fdens = 0` — o arquivo codifica
explicitamente rendimento nulo, em vez de omitir a linha. O modelo Power BI neutraliza
essas combinações em `fator_rota`, pelas regras "rota = Biodigestão e combustível =
Briquete → 0" e sua simétrica.

Este arquivo adota o mesmo critério: **`rotas_possiveis` é a autoridade**. Um coproduto
rotulado `Biodigestão` tem a coluna de densificação vazia, e não zero — a rota não existe
para ele, e um zero sugeriria erroneamente que existe e não rende nada.

Papéis e Plástico não aparecem no arquivo: são resíduos urbanos sem produção registrada
em `fatos_hist_mu_mod.csv`.

## Ressalva sobre a comparação com o Power BI

Os valores deste arquivo divergem do relatório SIEnergia para a rota de densificação, por
um fator de até 1000× conforme o coproduto, **enquanto o modelo não for atualizado**.

A causa é um defeito de leitura no modelo Power BI, não neste arquivo: `dim_energetico.csv`
gravava decimais com ponto e o Power Query os interpretava como separador de milhar,
transformando uma matéria seca de 0,9 em 9. O arquivo de origem foi regravado com vírgula
em 01/09/2026, o que corrige a leitura sem alterar o `.pbix`; a divergência se encerra na
primeira atualização do modelo. Diagnóstico completo em `ERRO_MATERIA_SECA.md`.

Este arquivo sempre usou os valores fisicamente corretos — a correção da origem não mudou
um byte dele. O biometano nunca foi afetado e coincide com o modelo.

**Segunda divergência, na biodigestão:** os três resíduos de indústria de abate podem não
aparecer no relatório publicado. A query `fato_energetico` escolhia a base entre
`producao_t` e `rebanho` apenas, descartando a coluna `abate` — de modo que não conseguia
calcular coprodutos cujo fator é por cabeça abatida, mesmo depois de os arquivos de
fatores terem sido atualizados. São +4.422,6 ktep acumulados neste arquivo, ~176 ktep/ano
no nível de 2021. O ajuste de M está em `RESIDUOS_ABATE.md`, seção 5, e já foi aplicado
ao `SIEnergia-hml.pbix`.


## Reprodução

```bash
cd etl_sienergia
python dados_abertos.py
```

Lê a fonte primária diretamente — não depende de `executar_etl.py`. Ao final imprime os
totais, o preenchimento por rota e a autoconferência das quatro identidades da cadeia.

Fonte primária: `X:\SIEnergia\bd\csv_exportado\`, somente leitura.
