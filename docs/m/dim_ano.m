let
    Fonte = Csv.Document(File.Contents(bis_outputs & "dim_ano.csv"),[Delimiter=";", Columns=10, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"ano", Int64.Type}, {"ano_i", Int64.Type}, {"ano_f", Int64.Type}, {"ano_base", Int64.Type}})
in
    #"Tipo Alterado"