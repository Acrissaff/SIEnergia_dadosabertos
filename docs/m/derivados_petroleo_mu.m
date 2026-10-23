let
    Fonte = Table.Combine({diesel_mu, galosina_mu}),
    #"Consultas Mescladas" = Table.NestedJoin(Fonte, {"combustivel"}, dim_combustivel, {"combustivel"}, "dim_combustivel", JoinKind.LeftOuter),
    #"dim_combustivel Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas", "dim_combustivel", {"cd_combustivel", "combustivel_2", "densidade", "pci"}, {"cd_combustivel", "combustivel_2", "densidade", "pci"}),
    #"Personalização Adicionada" = Table.AddColumn(#"dim_combustivel Expandido", "venda_ktep", each [venda_litro]*[densidade]*[pci]/1000000/1000),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Personalização Adicionada",{{"combustivel", type text}, {"venda_ktep", type number}}),
    #"Consultas Mescladas1" = Table.NestedJoin(#"Tipo Alterado", {"cd_mu"}, trechos, {"CD_MUN"}, "trechos", JoinKind.LeftOuter),
    #"trechos Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas1", "trechos", {"CD_MUN"}, {"CD_MUN"}),
    #"Personalização Adicionada1" = Table.AddColumn(#"trechos Expandido", "caminho", each if [CD_MUN] <> null then "Caminho da Safra" else "Fora do Caminho")
in
    #"Personalização Adicionada1"