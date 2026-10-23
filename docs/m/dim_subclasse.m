let
    Fonte = Csv.Document(File.Contents(bis_outputs & "dim_subclasse.csv"),[Delimiter=";", Columns=16, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"cd_subclasse", Int64.Type}})
in
    #"Tipo Alterado"