let
    Fonte = fator_energetico_combustivel,
    #"Consultas Mescladas" = Table.NestedJoin(Fonte, {"cd_energetico"}, dim_energetico, {"cd_energetico"}, "dim_energetico", JoinKind.LeftOuter),
    #"dim_energetico Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas", "dim_energetico", {"rotas_possiveis"}, {"rotas_possiveis"}),
    #"Outras Colunas Removidas" = Table.SelectColumns(#"dim_energetico Expandido",{"cd_combustivel", "rotas_possiveis"}),
    #"Duplicatas Removidas" = Table.Distinct(#"Outras Colunas Removidas"),
    #"Consultas Mescladas1" = Table.NestedJoin(#"Duplicatas Removidas", {"rotas_possiveis"}, dim_rotas_possiveis, {"rotas_possiveis"}, "dim_rotas_possiveis", JoinKind.LeftOuter),
    #"dim_rotas_possiveis Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas1", "dim_rotas_possiveis", {"cd_rotas_possiveis"}, {"cd_rotas_possiveis"}),
    #"Consultas Mescladas2" = Table.NestedJoin(#"dim_rotas_possiveis Expandido", {"cd_combustivel"}, dim_combustivel, {"cd_combustivel"}, "dim_combustivel", JoinKind.LeftOuter),
    #"dim_combustivel Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas2", "dim_combustivel", {"combustivel"}, {"combustivel"}),
    #"Personalização Adicionada" = Table.AddColumn(#"dim_combustivel Expandido", "#", each 1),
    #"Consultas Mescladas3" = Table.NestedJoin(#"Personalização Adicionada", {"#"}, dim_rota_cenario, {"#"}, "dim_rota_cenario", JoinKind.LeftOuter),
    #"dim_rota_cenario Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas3", "dim_rota_cenario", {"cd_rota_cenario", "rota_cenario"}, {"cd_rota_cenario", "rota_cenario"}),
    #"Linhas Classificadas" = Table.Sort(#"dim_rota_cenario Expandido",{{"rota_cenario", Order.Ascending}, {"rotas_possiveis", Order.Ascending}, {"combustivel", Order.Ascending}}),
    #"Colunas Reordenadas" = Table.ReorderColumns(#"Linhas Classificadas",{"cd_rota_cenario", "rota_cenario", "cd_combustivel", "rotas_possiveis", "cd_rotas_possiveis", "combustivel", "#"}),
    #"Personalização Adicionada2" = Table.AddColumn(#"Colunas Reordenadas", "fator_rota", each if [rota_cenario]= "Biodigestão" 
and [rotas_possiveis]= "Biod. e Densif." 
and [combustivel]= "Briquete" 
then 0 else

if [rotas_possiveis]= "Biodigestão" 
and [combustivel]= "Briquete" 
then 0 else

if [rotas_possiveis]= "Densificação" 
and [combustivel]= "Biometano" 
then 0 else

if [rota_cenario]= "Densificação" 
and [rotas_possiveis]= "Biod. e Densif." 
and [combustivel]= "Biometano" 
then 0 else

if [rota_cenario]= "Meio-a-meio" and [rotas_possiveis]= "Biod. e Densif." then 0.5 else


//if [rota_cenario]= "Biodigestão" 
//and [rotas_possiveis]= "Biod. e Densif." 
//and [combustivel]= "Briquete" 
//then 0 else

//if [rota_cenario]= "Biodigestão" 
//and [rotas_possiveis]= "Biodigestão" 
//and [combustivel]= "Briquete" 
//then 0 else

//if [rota_cenario]= "Biodigestão" 
//and [rotas_possiveis]= "Densificação" 
//and [combustivel]= "Biometano" 
//then 0 else

1),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Personalização Adicionada2",{{"fator_rota", type number}}),
    #"Colunas Removidas" = Table.RemoveColumns(#"Tipo Alterado",{"#"}),
    #"Valor Substituído" = Table.ReplaceValue(#"Colunas Removidas",0,null,Replacer.ReplaceValue,{"fator_rota"})
in
    #"Valor Substituído"