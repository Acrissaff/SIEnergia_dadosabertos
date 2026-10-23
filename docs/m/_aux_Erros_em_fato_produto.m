let
Fonte = fato_produto,
  #"Incompatibilidades de Tipo Detectadas" = let
    tableWithOnlyPrimitiveTypes = Table.SelectColumns(Fonte, Table.ColumnsOfType(Fonte, {type nullable number, type nullable text, type nullable logical, type nullable date, type nullable datetime, type nullable datetimezone, type nullable time, type nullable duration})),
    recordTypeFields = Type.RecordFields(Type.TableRow(Value.Type(tableWithOnlyPrimitiveTypes))),
    fieldNames = Record.FieldNames(recordTypeFields),
    fieldTypes = List.Transform(Record.ToList(recordTypeFields), each [Type]),
    pairs = List.Transform(List.Positions(fieldNames), (i) => {fieldNames{i}, (v) => if v = null or Value.Is(v, fieldTypes{i}) then v else error [Message = "O tipo do valor não corresponde ao tipo da coluna.", Detail = v], fieldTypes{i}})
in
    Table.TransformColumns(Fonte, pairs),
  #"Índice Adicionado" = Table.AddIndexColumn(#"Incompatibilidades de Tipo Detectadas", "Número da Linha" ,1),
  #"Erros Mantidos" = Table.SelectRowsWithErrors(#"Índice Adicionado", {"cd_mu", "cd_produto", "cd_origem", "ano", "area_ha", "producao_t", "valor", "rebanho", "produto_ibge", "abate"}),
  #"Colunas Reordenadas" = Table.ReorderColumns(#"Erros Mantidos", {"Número da Linha", "cd_mu", "cd_produto", "cd_origem", "ano", "area_ha", "producao_t", "valor", "rebanho", "produto_ibge", "abate"})
in
  #"Colunas Reordenadas"