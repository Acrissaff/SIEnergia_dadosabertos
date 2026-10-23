let
    Fonte = Csv.Document(File.Contents("X:\Biocombustiveis - Diretorio\Técnico\Produtos\SIEnergia\bd\dim_pbi\dim_rota_modelo.csv"),[Delimiter=";", Columns=3, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Colunas Removidas" = Table.RemoveColumns(Fonte,{"Column1"}),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(#"Colunas Removidas", [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"cd_rota_modelo", Int64.Type}})
in
    #"Tipo Alterado"