let
    Fonte = Csv.Document(File.Contents(bis_outputs & "fatores_produto_energetico.csv"),[Delimiter=";", Columns=7, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"fcoprod", type number}, {"fcoleta", type number}, {"cd_produto", Int64.Type}, {"cd_energetico", Int64.Type}}),
    #"Linhas Classificadas" = Table.Sort(#"Tipo Alterado",{{"cd_energetico", Order.Ascending}})
in
    #"Linhas Classificadas"