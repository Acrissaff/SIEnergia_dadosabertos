let
    Fonte = Csv.Document(File.Contents(bis_outputs & "dim_mu.csv"),[Delimiter=";", Columns=19, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"cd_mu", Int64.Type}, {"cd_micro", Int64.Type}, {"cd_meso", Int64.Type}, {"cd_uf", Int64.Type}}),
    #"Colunas Renomeadas" = Table.RenameColumns(#"Tipo Alterado",{{"uf_sigla", "UF"}, {"municipio", "Municipio"}, {"uf", "uf_nome"}})
in
    #"Colunas Renomeadas"