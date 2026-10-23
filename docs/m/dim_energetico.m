let
    Fonte = Csv.Document(File.Contents(bis_outputs & "dim_energetico.csv"),[Delimiter=";", Columns=10, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"cd_energetico", Int64.Type}, {"teor_mo", type number}, {"materia_seca", type number}, {"cd_subclasse", Int64.Type}, {"cd_rota", Int64.Type}}),
    #"Personalização Adicionada" = Table.AddColumn(#"Tipo Alterado", "#", each 1),
    #"Consultas Mescladas" = Table.NestedJoin(#"Personalização Adicionada", {"cd_rota"}, dim_rota, {"cd_rota"}, "dim_rota", JoinKind.LeftOuter),
    #"dim_rota Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas", "dim_rota", {"rotas_possiveis"}, {"rotas_possiveis"})
in
    #"dim_rota Expandido"