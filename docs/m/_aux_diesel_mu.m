let
    Fonte = Csv.Document(File.Contents("X:\SIEnergia\BASE DE DADOS\ANP\vendas-anuais-de-oleo-diesel-por-municipio.csv"),[Delimiter=";", Columns=7, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    #"Colunas Renomeadas" = Table.RenameColumns(#"Cabeçalhos Promovidos",{{"VENDAS", "venda_litro"}, {"CÓDIGO IBGE", "cd_mu"}, {"ANO", "ano"}}),
    #"Colunas Removidas" = Table.RemoveColumns(#"Colunas Renomeadas",{"MUNICÍPIO"}),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Colunas Removidas",{{"venda_litro", Int64.Type}, {"cd_mu", Int64.Type}, {"ano", Int64.Type}}),
    #"Personalização Adicionada1" = Table.AddColumn(#"Tipo Alterado", "combustivel", each "Óleo diesel"),
    #"Colunas Removidas1" = Table.RemoveColumns(#"Personalização Adicionada1",{"GRANDE REGIÃO", "UF", "PRODUTO"})
in
    #"Colunas Removidas1"