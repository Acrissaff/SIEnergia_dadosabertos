let
    Fonte = fato_produto,
    #"Linhas Filtradas" = Table.SelectRows(Fonte, each ([ano] = 2023)),
    #"Linhas Agrupadas" = Table.Group(#"Linhas Filtradas", {"cd_produto"}, {{"area_ha", each List.Sum([area_ha]), type nullable number}, {"producao_t", each List.Sum([producao_t]), type nullable number}}),
    #"Consultas Mescladas" = Table.NestedJoin(#"Linhas Agrupadas", {"cd_produto"}, dim_produto, {"cd_produto"}, "dim_produto", JoinKind.LeftOuter),
    #"dim_produto Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas", "dim_produto", {"produto", "cd_subclasse"}, {"produto", "cd_subclasse"}),
    #"Consultas Mescladas1" = Table.NestedJoin(#"dim_produto Expandido", {"cd_subclasse"}, dim_subclasse, {"cd_subclasse"}, "dim_subclasse", JoinKind.LeftOuter),
    #"dim_subclasse Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas1", "dim_subclasse", {"s3_grupo", "s4_divisao"}, {"s3_grupo", "s4_divisao"})
in
    #"dim_subclasse Expandido"