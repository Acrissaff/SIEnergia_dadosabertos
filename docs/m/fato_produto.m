let
    Fonte = Csv.Document(File.Contents(bis_outputs & "fatos_hist_mu_mod.csv"),[Delimiter=";", Columns=9, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Colunas Renomeadas1" = Table.RenameColumns(#"Cabeçalhos Promovidos",{{"valor", "valor_bruto"}}),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Colunas Renomeadas1",{{"cd_mu", Int64.Type}, {"cd_produto", Int64.Type}, {"ano", Int64.Type}, {"cd_origem", Int64.Type}, {"area_ha", type number}, {"producao_t", type number}, {"valor_bruto", type number}, {"rebanho", type number}, {"abate", type number}}),
    #"Colunas Renomeadas" = Table.RenameColumns(#"Tipo Alterado",{{"valor_bruto", "valor"}})
in
    #"Colunas Renomeadas"