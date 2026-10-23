let
    Fonte = Csv.Document(File.Contents(bis_outputs & "dim_rota.csv"),[Delimiter=";", Columns=3, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"cd_rota", Int64.Type}})
in
    #"Tipo Alterado"