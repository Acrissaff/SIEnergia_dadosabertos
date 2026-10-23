let
    Fonte = fato_produto,
    #"Outras Colunas Removidas" = Table.SelectColumns(Fonte,{"cd_produto"}),
    #"Duplicatas Removidas" = Table.Distinct(#"Outras Colunas Removidas")
in
    #"Duplicatas Removidas"