let
    Fonte = fato_produto,
    #"Linhas Filtradas" = Table.SelectRows(Fonte, each ([ano] = 2022)),
    #"Linhas Agrupadas" = Table.Group(#"Linhas Filtradas", {"ano", "cd_origem", "cd_produto"}, {{"producao_t", each List.Sum([producao_t]), type nullable number}})
in
    #"Linhas Agrupadas"