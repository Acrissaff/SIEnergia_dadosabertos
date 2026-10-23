let
    Fonte = Csv.Document(File.Contents("X:\Biocombustiveis - Diretorio\Técnico\Produtos\SIEnergia\BASE DE DADOS\ANP\vendas-anuais-de-oleo-diesel-por-municipio.csv"),[Delimiter=";", Columns=7, Encoding=65001, QuoteStyle=QuoteStyle.None])
in
    Fonte