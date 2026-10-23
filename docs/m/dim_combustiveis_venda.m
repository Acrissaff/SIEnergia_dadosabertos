let
    Fonte = derivados_petroleo_mu,
    #"Outras Colunas Removidas" = Table.SelectColumns(Fonte,{"combustivel", "cd_combustivel", "combustivel_2"}),
    #"Duplicatas Removidas" = Table.Distinct(#"Outras Colunas Removidas", {"combustivel"})
in
    #"Duplicatas Removidas"