let
    Fonte = Csv.Document(File.Contents(bis_outputs & "dim_produto.csv"),[Delimiter=";", Columns=9, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"cd_subclasse", Int64.Type}, {"cd_produto", Int64.Type}})
in
    #"Tipo Alterado"