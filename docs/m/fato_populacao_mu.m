let
    Fonte = Csv.Document(File.Contents(bis_outputs & "fatos_populacao_mu.csv"),[Delimiter=";", Columns=4, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"cd_mu", Int64.Type}, {"ano", Int64.Type}, {"populacao", type number}})
in
    #"Tipo Alterado"