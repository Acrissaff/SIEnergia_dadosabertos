let
    Fonte = fato_energetico,
    #"Outras Colunas Removidas" = Table.SelectColumns(Fonte,{"rotas_possiveis"}),
    #"Duplicatas Removidas" = Table.Distinct(#"Outras Colunas Removidas"),
    #"Linhas Filtradas" = Table.SelectRows(#"Duplicatas Removidas", each ([rotas_possiveis] <> "N")),
    #"Índice Adicionado" = Table.AddIndexColumn(#"Linhas Filtradas", "cd_rotas_possiveis", 1, 1, Int64.Type)
in
    #"Índice Adicionado"