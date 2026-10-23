let
    Fonte = Excel.Workbook(File.Contents("X:\Biocombustiveis - Diretorio\Técnico\Produtos\SIEnergia\BASE DE DADOS\CAMINHOS DA SAFRA\caminhos_safra.xlsx"), null, true),
    trechos_Sheet = Fonte{[Item="trechos",Kind="Sheet"]}[Data],
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(trechos_Sheet, [PromoteAllScalars=true]),
    #"Outras Colunas Removidas" = Table.SelectColumns(#"Cabeçalhos Promovidos",{"CD_MUN"}),
    #"Duplicatas Removidas" = Table.Distinct(#"Outras Colunas Removidas")
in
    #"Duplicatas Removidas"