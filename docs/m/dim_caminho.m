let
    Fonte = derivados_petroleo_mu,
    #"Outras Colunas Removidas" = Table.SelectColumns(Fonte,{"caminho"}),
    #"Duplicatas Removidas" = Table.Distinct(#"Outras Colunas Removidas")
in
    #"Duplicatas Removidas"