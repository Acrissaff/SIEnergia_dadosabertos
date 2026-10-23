let
    Fonte = Csv.Document(File.Contents("X:\Biocombustiveis - Diretorio\Técnico\Produtos\SIEnergia\bd\dim_pbi\dim_rota_cenario.csv"),[Delimiter=";", Columns=6, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Colunas Removidas" = Table.RemoveColumns(Fonte,{"Column1"}),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(#"Colunas Removidas", [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"cd_rota_cenario", Int64.Type}}),
    #"Linhas Filtradas" = Table.SelectRows(#"Tipo Alterado", each ([rota_cenario] <> null)),
    #"Tipo Alterado1" = Table.TransformColumnTypes(#"Linhas Filtradas",{{"Densificação", type number}, {"Biodigestão", type number}, {"cd_rota_cenario", Int64.Type}, {"rota_cenario", type text}, {"rota_cenario_sigla", type text}}),
    #"Personalização Adicionada" = Table.AddColumn(#"Tipo Alterado1", "#", each 1)
in
    #"Personalização Adicionada"