let
    Fonte = Csv.Document(File.Contents(bis_outputs & "dim_combustivel.csv"),[Delimiter=";", Columns=15, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"cd_combustivel", Int64.Type}, {"densidade", type number}, {"pcs", type number}, {"pci", type number}}),
    #"Erros Substituídos" = Table.ReplaceErrorValues(#"Tipo Alterado", {{"densidade", null}, {"pcs", null}, {"pci", null}}),
    #"Coluna dividida" = Table.TransformColumns(#"Erros Substituídos", {{"pci", each _ / 10000, type number}})
in
    #"Coluna dividida"