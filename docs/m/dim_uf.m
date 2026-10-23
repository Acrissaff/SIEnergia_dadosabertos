let
    Fonte = Csv.Document(File.Contents(bis_outputs & "dim_uf.csv"),[Delimiter=";", Columns=8, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"cd_uf", Int64.Type}})
in
    #"Tipo Alterado"