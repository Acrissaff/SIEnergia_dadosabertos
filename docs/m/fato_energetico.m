let
    Fonte = fato_produto,
    #"CMescladas - inner" = Table.NestedJoin(Fonte, {"cd_produto"}, fator_produto_energetico, {"cd_produto"}, "fator_produto_energetico", JoinKind.Inner),
    #"fator_produto_energetico Expandido" = Table.ExpandTableColumn(#"CMescladas - inner", "fator_produto_energetico", {"fcoprod", "fcoprod_unid", "fcoleta", "cd_energetico"}, {"fcoprod", "fcoprod_unid", "fcoleta", "cd_energetico"}),
    #"PAdicionada - coproduto" = Table.AddColumn(#"fator_produto_energetico Expandido", "q_coproduto", each if [rebanho] <> null then [rebanho]*[fcoprod] else 
[producao_t]*[fcoprod]),
    #"PAdicionada - energetico" = Table.AddColumn(#"PAdicionada - coproduto", "q_energetico", each [q_coproduto]*[fcoleta]),
    #"Colunas Removidas" = Table.RemoveColumns(#"PAdicionada - energetico",{"area_ha", "producao_t", "valor", "rebanho", "cd_produto", "abate"}),
    #"Consultas Mescladas1" = Table.NestedJoin(#"Colunas Removidas", {"cd_energetico"}, dim_energetico, {"cd_energetico"}, "dim_energetico", JoinKind.LeftOuter),
    #"dim_energetico Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas1", "dim_energetico", {"materia_seca", "rotas_possiveis"}, {"materia_seca", "rotas_possiveis"}),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"dim_energetico Expandido",{{"q_coproduto", type number}, {"q_energetico", type number}}),
    #"Colunas Renomeadas" = Table.RenameColumns(#"Tipo Alterado",{{"fcoprod", "fcoprod_u"}})
in
    #"Colunas Renomeadas"