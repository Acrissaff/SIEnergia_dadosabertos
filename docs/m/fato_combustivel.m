let
    Fonte = fato_energetico,
    #"Consultas Mescladas" = Table.NestedJoin(Fonte, {"cd_energetico"}, fator_energetico_combustivel, {"cd_energetico"}, "fator_energetico_combustivel", JoinKind.LeftOuter),
    #"fator_energetico_combustivel Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas", "fator_energetico_combustivel", {"cd_combustivel", "fdens", "fdens_unid", "fmetanizacao", "rota_modelo"}, {"cd_combustivel", "fdens", "fdens_unid", "fmetanizacao", "rota_modelo"}),
    #"LFilt - cd_combustivel= null" = Table.SelectRows(#"fator_energetico_combustivel Expandido", each ([cd_combustivel] <> null)),
    #"Colunas Removidas2" = Table.RemoveColumns(#"LFilt - cd_combustivel= null",{"fcoprod_u", "fcoprod_unid", "fcoleta", "q_coproduto"}),
    #"Consultas Mescladas1" = Table.NestedJoin(#"Colunas Removidas2", {"rota_modelo"}, dim_rota_modelo, {"rota_modelo"}, "dim_rota", JoinKind.LeftOuter),
    #"dim_rota Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas1", "dim_rota", {"cd_rota_modelo"}, {"cd_rota_modelo"}),
    #"PAdicionada - qct" = Table.AddColumn(#"dim_rota Expandido", "qct", each [q_energetico]*[fdens]*[materia_seca]),
    #"PAdicionada - vct" = Table.AddColumn(#"PAdicionada - qct", "vct", each [q_energetico]*[fmetanizacao]/1000),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"PAdicionada - vct",{{"qct", type number}, {"vct", type number}}),
    #"Colunas Removidas1" = Table.RemoveColumns(#"Tipo Alterado",{"q_energetico", "materia_seca"})
in
    #"Colunas Removidas1"