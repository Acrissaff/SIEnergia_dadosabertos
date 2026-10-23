let
    Fonte = Csv.Document(File.Contents(bis_outputs & "fatores_energetico_combustivel.csv"),[Delimiter=";", Columns=7, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Tipo Alterado1" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"fdens", type number}, {"fmetanizacao", type number}, {"cd_energetico", Int64.Type}, {"cd_combustivel", Int64.Type}}),
    #"PAdicionada - rota_modelo" = Table.AddColumn(#"Tipo Alterado1", "rota_modelo", each if [fmetanizacao] = null then "Densificação" else if [fdens] = null then "Biodigestão" else null)
in
    #"PAdicionada - rota_modelo"