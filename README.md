# SIEnergia — dados abertos

Scripts Python para transformar os arquivos exportados do SIEnergia em uma
tabela aberta auditável e em recortes por unidade da Federação.

Este repositório registra o estado atual do desenvolvimento. As fontes do
modelo e os resultados completos continuam sendo arquivos operacionais locais;
não são necessários para navegar pelo código, mas são necessários para executar
o ETL completo.

## O que o pipeline produz

O produto principal é uma linha no grão:

```text
município × ano × produto × coproduto energético
```

Cada linha preserva a base de atividade usada, os fatores técnicos da cadeia e
os potenciais de duas rotas puras:

- densificação;
- biodigestão.

As rotas são alternativas. Os dois potenciais não devem ser somados quando o
coproduto aceita ambas.

## Como navegar

| Arquivo ou pasta | Responsabilidade |
| --- | --- |
| [`config.py`](config.py) | Caminhos, constantes, conversões e formato CSV |
| [`leitura.py`](leitura.py) | Leitura em blocos, encoding, separador e decimal |
| [`dimensoes.py`](dimensoes.py) | Dimensões do modelo e conversões de PCI |
| [`fatores.py`](fatores.py) | Fatores produto-energético, combustível e rota |
| [`fatos.py`](fatos.py) | Tipagem e cadeia produto → energético → combustível |
| [`dados_abertos.py`](dados_abertos.py) | Agregação e autovalidação da tabela publicada |
| [`executar_etl.py`](executar_etl.py) | Orquestração dos fatos materializados |
| [`exportar_por_uf.py`](exportar_por_uf.py) | Recortes estaduais a partir do CSV nacional |
| [`docs_para_txt.py`](docs_para_txt.py) | Conversão da documentação Markdown para TXT |
| [`empacotar.py`](empacotar.py) | Montagem da distribuição e do ZIP |
| [`validar.py`](validar.py) | Comparação com tabelas materializadas no Power BI |
| [`medidas.py`](medidas.py) | Reprodução de medidas dependentes de cenário |
| [`extracao_alcool_2021.py`](extracao_alcool_2021.py) | Extração específica do recorte de álcool de 2021 |
| [`docs/`](docs/) | Dicionário, memorial de cálculo, mapeamento e diagnósticos |

## Pré-requisitos

- Python 3.10 ou superior;
- `pandas` e `numpy`;
- acesso somente leitura à pasta de exportação do modelo, normalmente
  `X:\SIEnergia\bd\csv_exportado`;
- fontes como `fatos_hist_mu_mod.csv`, `dim_produto.csv`,
  `dim_energetico.csv` e os arquivos de fatores.

As dependências não estão fixadas neste snapshot. Instale-as no ambiente
isolado de sua preferência antes de executar os scripts.

## Execução recomendada

No PowerShell, a partir da raiz:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python dados_abertos.py
python exportar_por_uf.py
python docs_para_txt.py
python empacotar.py
```

Para uma conferência rápida, os scripts que aceitam amostra podem ser chamados
com `--blocos 1`. Essa opção não substitui a geração completa.

Os resultados são gravados em `saida/`, incluindo o CSV nacional, os recortes
por UF, a pasta de distribuição, o ZIP e os relatórios de validação.

## Regras importantes

- O CSV publicado usa `;`, decimal `,` e UTF-8 com BOM.
- Quantidades de coproduto e energético são agregadas antes do desdobramento
  por combustível, evitando duplicação.
- Fatores constantes no grão são agregados com o primeiro valor, não somados.
- Nulo significa que a rota ou o dado não se aplica; zero é resultado numérico
  zero.
- A geração deve falhar ou ser considerada inválida quando os invariantes de
  quantidade, rota, cobertura de dimensões ou PCI não fecharem.
- Não execute o ETL contra uma fonte compartilhada sem confirmar o caminho e
  preservar os resultados anteriores.

As fórmulas e as decisões de domínio estão detalhadas em
[`docs/MEMORIAL_DE_CALCULO.md`](docs/MEMORIAL_DE_CALCULO.md) e
[`docs/DICIONARIO_DADOS_ABERTOS.md`](docs/DICIONARIO_DADOS_ABERTOS.md).

## Escopo deste snapshot

Entram no controle de versão os scripts, a documentação e os metadados leves
necessários para compreender o modelo. Não entram:

- dados brutos de `csv_exportado`;
- CSVs e ZIPs gerados em `saida/`;
- o arquivo Power BI e validações locais;
- backups históricos e arquivos temporários;
- credenciais, caches ou caminhos de rede como conteúdo versionado.

Esses itens estão protegidos pelo [`.gitignore`](.gitignore). Se uma execução
precisar ser reproduzida, forneça as fontes localmente e confira os caminhos em
[`config.py`](config.py).

## Estado registrado

O primeiro commit deste repositório representa o estado local disponível em
outubro de 2026. Alterações futuras devem preservar a rastreabilidade entre
fonte, fórmula, documentação, validação e pacote publicado.
