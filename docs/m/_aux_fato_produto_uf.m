let
    Fonte = Csv.Document(File.Contents(bis_outputs & "fatos_hist_uf.csv"),[Delimiter=";", Columns=9, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true])
in
    #"Cabeçalhos Promovidos"