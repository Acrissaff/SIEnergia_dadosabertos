# Erro nos multiplicadores de matéria seca — diagnóstico e correção

**Onde:** query `dim_energetico`, coluna `materia_seca`
**Efeito:** potencial de combustível sólido superestimado em até **1000×** por linha, **22×** no agregado; comparação entre rotas distorcida em **10× a 1.000×**
**Encontrado em:** validação do ETL em pandas contra `SIEnergia-hml.pbix`
**Status:** corrigido na origem em 01/09/2026 pela Opção B — `dim_energetico.csv` passou a
gravar `materia_seca` com vírgula decimal. O modelo publicado carrega os valores errados
até ser atualizado, e o processo que exporta o `csv_exportado` ainda emite ponto, de modo
que a próxima exportação reintroduz o defeito se não for corrigido junto. Ver seção 5.

---

## 1. O erro

A query `dim_energetico` lê `dim_energetico.csv` e converte tipos:

```m
Fonte = Csv.Document(File.Contents(bis_outputs & "dim_energetico.csv"),
                     [Delimiter=";", Columns=10, Encoding=65001, QuoteStyle=QuoteStyle.None]),
#"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
#"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",
    {{"cd_energetico", Int64.Type}, {"teor_mo", type number},
     {"materia_seca", type number}, ...})
```

O arquivo gravava os decimais com **ponto** — este é o conteúdo anterior a 01/09/2026:

```
cd_energetico;energetico;...;teor_mo;materia_seca;estado;...
101;Palha de Arroz;...;1;0.9;Sólido;...
125;Casca de Arroz;...;1;0.976;Sólido;...
```

**`dim_energetico.csv` era o único arquivo de `csv_exportado` que usava ponto decimal.**
Todos os demais — `fatos_hist_mu_mod.csv`, `fatores_produto_energetico.csv`,
`fatores_energetico_combustivel.csv`, `dim_combustivel.csv` — usam vírgula.

Mais que isso: era o único **sem nenhuma vírgula** em suas 51×10 células, enquanto
arquivos comparáveis têm muitas (`dim_subclasse` 154, `fatores_produto_energetico` 49,
`dim_produto` 8). E a coluna de texto `tipo_energetico` traz `Colmo. sabugo. folha e
palha`, que só se lê como *"Colmo, sabugo, folha e palha"*. O padrão sugere uma
**substituição geral de vírgula por ponto** na exportação deste arquivo, e não uma
escolha de formato decimal — o que também explica o texto corrompido.

`Table.TransformColumnTypes` sem terceiro argumento converte na cultura do arquivo, que
neste modelo é pt-BR. Em pt-BR o ponto é **separador de milhar**. O Power Query então
descarta o ponto e concatena os dígitos:

| No arquivo | Interpretado como | Resultado | Linhas |
|---|---|---|---|
| `0.9`   | 0 milhar e 9   | `9`   | 17 |
| `0.5`   | 0 milhar e 5   | `5`   | 13 |
| `0.125` | 0 milhar e 125 | `125` | 2 |
| `0.976` | 0 milhar e 976 | `976` | 1 |
| `0.15`  | 0 milhar e 15  | `15`  | 1 |
| `0.6`   | 0 milhar e 6   | `6`   | 1 |
| `0.1`   | 0 milhar e 1   | `1`   | 2 |
| `1`     | sem ponto      | `1`   | 14 |

Matéria seca é a fração seca da massa úmida: por definição, `0 < ms <= 1`.
**No modelo, 35 das 51 linhas violam esse limite.** Uma palha com 900% de matéria seca
não é um número plausível — é um erro de leitura.

A coluna `teor_mo` escapa por acaso: seus valores são `0` e `1`, sem separador decimal.
Se a exportação um dia emitir um valor fracionário ali, ele sofrerá o mesmo defeito.

## 2. Como se propaga

O valor entra direto na query `fato_combustivel`:

```m
#"PAdicionada - qct" = Table.AddColumn(#"dim_rota Expandido", "qct",
    each [q_energetico]*[fdens]*[materia_seca]),
```

Portanto `qct` — a massa de combustível sólido — sai multiplicada por 10, 100 ou 1000
conforme o número de casas decimais do valor original.

| Métrica | Cálculo correto | Modelo atual | Razão |
|---|---|---|---|
| `qct` total | 7.586.360.154 | 168.837.812.477 | **22,25×** |
| `vct` total | 2.491.721.639 | 2.491.721.639 | 1,00× |

O biometano **não é afetado**, porque `vct = q_energetico * fmetanizacao / 1000` não
usa `materia_seca`. É justamente por isso que o erro passou despercebido: metade do
modelo continua certa.

A jusante, contaminam-se todas as medidas da rota de densificação:

```
Combustivel (mil t)  →  Combustível (ktep)  →  Combustível (TJ)
                                            →  Calor (TJ)
                                            →  Eletricidade (GWh)  →  Energia (TJ)
                                                                   →  Potência (MW)
```

E, por consequência, `Balanço O&D (ktep)`, que compara o potencial com as vendas de
derivados de petróleo.

### O efeito mais crítico: a comparação entre rotas

Além de inflar o total da densificação, o erro **distorce a escolha entre densificar e
biodigerir** — que é justamente a decisão que o modelo existe para informar.

Para um coproduto que aceita as duas rotas, a razão entre os potenciais é:

```
                    fdens × materia_seca × pci_briquete × 1000
razão densif/biod = ------------------------------------------
                         fmetanizacao × pci_biometano
```

`materia_seca` aparece **só no numerador**. Inflá-la por 10 ou 1000 multiplica a razão
na mesma proporção:

| Coproduto | `materia_seca` correta | Razão correta | No modelo PBI | Razão no PBI |
|---|---|---|---|---|
| 11 resíduos lignocelulósicos | 0,9 | **1,563×** | 9 | **15,63×** |
| Casca de Arroz | 0,976 | **1,695×** | 976 | **1.695×** |

No modelo em produção, portanto, a densificação aparenta render de 15 a 1.700 vezes
mais que a biodigestão. Com os valores corretos, a vantagem é de ~1,56×.

**Se alguma recomendação de rota tecnológica foi construída sobre essa comparação, ela
precisa ser refeita.** É a consequência mais séria do defeito — mais do que o total
agregado, porque inverte a ordem de grandeza da decisão.

### Ressalva sobre a diferenciação entre rotas

Vale registrar, à parte do erro: entre os 13 coprodutos de dupla rota, apenas dois
conjuntos de parâmetros existem.

- **12 resíduos lignocelulósicos** (palhas, cascas, ramas, resíduos de fruta) têm todos
  `fdens = 1` e `fmetanizacao = 250 m³/t`. O que os diferencia entre si é somente a
  `materia_seca`, que assume 0,9 em onze deles e 0,976 na Casca de Arroz.
- **Mat. Orgânica - Res.** tem `fmetanizacao = 55` e `materia_seca = 0,5`, razão 3,946×
  — mas não tem nenhuma linha no arquivo, por falta de dado de produção.

A variabilidade real de `fmetanizacao` no modelo (8,35 na vinhaça, 17 no esterco bovino,
44 no suíno, 55,68 na torta de filtro, 90 em aves, 110 em efluentes) está **inteiramente
em coprodutos de rota única**, que nunca entram numa comparação entre rotas.

Consequência: na prática, a comparação densificação x biodigestão do modelo é um
multiplicador constante de ~1,56 aplicado a todo o arquivo, e não uma diferenciação
técnica por coproduto. `fdens = 1` (tbs/tbs) também significa que a densificação é
modelada como conservativa em base seca, sem perda de processo.

Isso não é defeito de leitura como o da matéria seca — é escolha de parametrização. Mas
convém saber que a comparação entre rotas, nesse grupo, não carrega informação sobre o
coproduto.

## 3. Por que é erro do modelo, e não do porte

Na validação, tudo o que não depende de `materia_seca` bate exatamente:

| Verificação | Resultado |
|---|---|
| `fato_energetico` — linhas | 6.233.284 = PBI |
| `fato_energetico` — `q_coproduto`, `q_energetico` | idênticos nos 51 anos, tolerância 1e-9 |
| `fato_combustivel` — linhas | 6.693.485 = PBI |
| `fato_combustivel` — `vct` | idêntico nos 51 anos |
| `fato_combustivel` — `qct` | diverge 22,25× |

E a razão observada por energético é exatamente `materia_seca_modelo /
materia_seca_arquivo`: 10× onde o valor tem uma casa decimal, 1000× onde tem três.

## 4. Como confirmar por conta própria

No Power BI Desktop, sem nenhuma alteração: abra **Transformar dados**, selecione a
query `dim_energetico` e olhe a coluna `materia_seca`. Os valores aparecem como
`9`, `5`, `125`, `976`. Deveriam ser `0,9`, `0,5`, `0,125` e `0,976`.

Por código:

```python
import pandas as pd
from pbixray import PBIXRay

m = PBIXRay("SIEnergia-hml.pbix", on_disk=True)
print(m.get_table("dim_energetico")["materia_seca"].value_counts().sort_index())

bruto = pd.read_csv("X:/SIEnergia/bd/csv_exportado/dim_energetico.csv",
                    sep=";", dtype=str)["materia_seca"]
print(pd.to_numeric(bruto).value_counts().sort_index())                  # correto
print(pd.to_numeric(bruto.str.replace(".", "", regex=False))
        .value_counts().sort_index())                                     # o do PBI
```

A terceira saída reproduz a distribuição do modelo linha a linha.

---

## 5. Correção no Power BI

### Opção A — fixar a cultura na conversão

Corrige o modelo sem depender de quem gera o CSV. No Editor do Power Query, selecione a
query `dim_energetico`, abra o **Editor Avançado** e troque a etapa `#"Tipo Alterado"`
por sua variante com cultura explícita:

```m
#"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",
    {{"cd_energetico", Int64.Type}, {"teor_mo", type number},
     {"materia_seca", type number}, {"cd_subclasse", Int64.Type},
     {"cd_rota", Int64.Type}},
    "en-US"),
```

O terceiro argumento é a cultura usada na conversão. Com `"en-US"`, o ponto volta a ser
separador decimal e `0.9` é lido como 0,9.

Pela interface, o mesmo efeito se obtém em **Tipo de Dados → Usando Localidade…**,
escolhendo *Número decimal* e localidade *Inglês (Estados Unidos)*.

> Aplique **apenas** à query `dim_energetico`. As demais leem arquivos com vírgula
> decimal e continuam corretas na cultura pt-BR — mudar a cultura delas introduziria
> o erro simétrico.

### Opção B — padronizar o arquivo na origem — **é esta a aplicada**

Regravar `dim_energetico.csv` com vírgula decimal, alinhando-o aos outros arquivos de
`csv_exportado`. Elimina a assimetria que causou o problema, mas depende de alterar o
processo que gera o arquivo, e qualquer regeração futura reintroduz o erro se o
processo não for corrigido junto.

Aplicada em 01/09/2026, editando só o campo `materia_seca`: 37 linhas, 37 bytes trocados
de `.` para `,`, os 3.677 bytes do arquivo preservados no tamanho e nos demais campos.
Os 11 pontos restantes são de texto (`Esterco Bov. corte`, `Mat. Orgânica - Efl.`).

**A correção do processo de exportação ficou pendente** — enquanto ele não mudar, cada
nova exportação do `csv_exportado` traz o defeito de volta.

Duas coisas andam junto com essa edição:

- **`leitura.py`** declarava `DECIMAIS = {"dim_energetico.csv": "."}`. Com o arquivo em
  vírgula e o pandas esperando ponto, `materia_seca` voltaria como **texto**, não como
  nulo, e a cadeia da densificação produziria lixo. A entrada foi removida e o separador
  passou a ser `","` para todo o conjunto.
- **Verificação:** regerar os dados abertos e comparar byte a byte com a geração
  anterior. Como o ETL sempre leu o valor correto, o arquivo tem de sair idêntico —
  e saiu: os 1.139.795.864 bytes conferem.

Se escolher a Opção A no lugar desta, **não** aplique as duas: com o arquivo em vírgula e
a conversão forçada para `en-US`, a vírgula passaria a ser lida como separador de milhar
e o erro voltaria, invertido.

### Opção C — deixar a query indiferente ao formato

Se o processo de exportação não puder ser corrigido, esta é preferível à Opção A, porque
não amarra o `.pbix` ao formato que a exportação escolher emitir:

```m
#"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",
    {{"cd_energetico", Int64.Type}, {"cd_subclasse", Int64.Type}, {"cd_rota", Int64.Type}}),
#"Decimais normalizados" = Table.TransformColumns(#"Tipo Alterado",
    {{"teor_mo",      each Number.FromText(Text.Replace(_, ",", "."), "en-US"), type number},
     {"materia_seca", each Number.FromText(Text.Replace(_, ",", "."), "en-US"), type number}}),
```

Lê corretamente tanto `0,9` quanto `0.9`. É seguro **aqui** porque nenhuma das duas
colunas carrega separador de milhar: `materia_seca` ∈ (0, 1] e `teor_mo` ∈ {0, 1}.
Convém guardar contra nulo (`each if _ = null then null else …`) — hoje não há vazios
nessas colunas, mas nada garante isso adiante.

### Verificação depois da correção

1. Em **Transformar dados**, `dim_energetico[materia_seca]` deve ficar entre 0 e 1 em
   todas as 51 linhas.
2. Atualize o modelo e compare o total de `qct`: deve cair de ~1,69e11 para ~7,6e9.
3. As medidas da rota de densificação caem na mesma proporção. **Números já publicados
   com base no modelo atual precisam ser revisados.**
4. Rodando `validar.py` deste pacote, o desvio conhecido em `qct` passa de 22,26× para
   1,00×.

---

## 6. O que o ETL em pandas faz

Sempre leu o valor correto, e continua lendo depois da Opção B. Até 01/09/2026 isso
exigia uma exceção declarada em `leitura.py`:

```python
DECIMAIS = {
    "dim_energetico.csv": ".",   # único do conjunto que usa ponto
}
```

Com o arquivo regravado em vírgula, a exceção deixou de existir: `ler_csv` e
`ler_csv_em_blocos` passam `decimal=","` para todo o conjunto. A prova de que a troca é
neutra está na regeração — o arquivo de dados abertos saiu **byte a byte idêntico** ao
anterior, 1.139.795.864 bytes.

`validar.py` mantém a divergência de `qct` fora do veredito de fidelidade, registrada em
`DESVIOS_CONHECIDOS`, mas exibe a razão observada a cada execução — ela permanece em
~22,25× enquanto o `.pbix` guardar os dados antigos e cai sozinha para 1,00× na primeira
execução após a atualização do modelo.
