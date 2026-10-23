// =====================================================================================
// fato_energetico — VERSÃO CORRIGIDA (opção A)
//
// Este arquivo NÃO foi extraído do .pbix: é o M pronto para colar no Editor Avançado.
// O que está em produção continua em `fato_energetico.m`, ao lado, preservado para
// diferença. A única etapa alterada é `#"PAdicionada - coproduto"`.
//
// O QUE MUDA
//   antes:  if [rebanho] <> null then [rebanho]*[fcoprod] else [producao_t]*[fcoprod]
//   depois: if [abate]   <> null then [abate]*[fcoprod]
//           else if [rebanho] <> null then [rebanho]*[fcoprod]
//           else [producao_t]*[fcoprod]
//
// POR QUE
//   Os coprodutos 127/128/129 (Resíduos de indústria de abate — Bovinos/Suínos/Aves)
//   têm fcoprod em m³ de efluente por cabeça abatida. Sem este ramo, o modelo multiplica
//   o fator por `producao_t` — o peso de carcaça em toneladas — e entrega peso_kg/1000
//   do valor devido: 3,7x a menos em bovinos, 486x a menos em aves.
//
// POR QUE É SEGURO (verificado sobre as 6.364.878 linhas de fatos_hist_mu_mod.csv)
//   - `abate` só vem preenchida nos oito produtos de carcaça (1168–1175);
//   - nenhuma linha tem `abate` e `rebanho` preenchidas ao mesmo tempo;
//   - cinco dos oito (1169–1173, recortes bovinos) não têm linha em
//     fatores_produto_energetico e são eliminados pelo JoinKind.Inner da etapa anterior.
//     Sobram exatamente 1168, 1174 e 1175 — os três que têm fator por cabeça.
//
// A ORDEM IMPORTA
//   O teste de `abate` tem de vir antes do `else` final: os produtos de carcaça trazem
//   `producao_t` preenchida, então o `else` os capturaria primeiro — sem erro nenhum a
//   sinalizar o problema. Entre `abate` e `rebanho` a ordem é indiferente.
//
// NADA MAIS MUDA
//   `#"Colunas Removidas"` já descarta `abate`, e vem depois desta etapa.
//   `fato_produto` já tipa a coluna como `type number`. `fato_combustivel` não muda.
//
// EFEITO ESPERADO
//   fato_combustivel: 6.693.485 -> 7.115.920 linhas (+422.435)
//   biometano: +176 ktep no filtro de 2021, +4.423 ktep no acumulado 1997–2024
//   densificação: não se move nem um dígito
//   dim_rotas_possiveis: 4 -> 3 linhas (perde "Nenhuma"; os códigos 1–3 não se deslocam)
//
// Detalhes, passo a passo e verificação: docs/RESIDUOS_ABATE.md, seção 5.
// =====================================================================================
let
    Fonte = fato_produto,
    #"CMescladas - inner" = Table.NestedJoin(Fonte, {"cd_produto"}, fator_produto_energetico, {"cd_produto"}, "fator_produto_energetico", JoinKind.Inner),
    #"fator_produto_energetico Expandido" = Table.ExpandTableColumn(#"CMescladas - inner", "fator_produto_energetico", {"fcoprod", "fcoprod_unid", "fcoleta", "cd_energetico"}, {"fcoprod", "fcoprod_unid", "fcoleta", "cd_energetico"}),
    #"PAdicionada - coproduto" = Table.AddColumn(#"fator_produto_energetico Expandido", "q_coproduto", each if [abate] <> null then [abate]*[fcoprod] else if [rebanho] <> null then [rebanho]*[fcoprod] else
[producao_t]*[fcoprod]),
    #"PAdicionada - energetico" = Table.AddColumn(#"PAdicionada - coproduto", "q_energetico", each [q_coproduto]*[fcoleta]),
    #"Colunas Removidas" = Table.RemoveColumns(#"PAdicionada - energetico",{"area_ha", "producao_t", "valor", "rebanho", "cd_produto", "abate"}),
    #"Consultas Mescladas1" = Table.NestedJoin(#"Colunas Removidas", {"cd_energetico"}, dim_energetico, {"cd_energetico"}, "dim_energetico", JoinKind.LeftOuter),
    #"dim_energetico Expandido" = Table.ExpandTableColumn(#"Consultas Mescladas1", "dim_energetico", {"materia_seca", "rotas_possiveis"}, {"materia_seca", "rotas_possiveis"}),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"dim_energetico Expandido",{{"q_coproduto", type number}, {"q_energetico", type number}}),
    #"Colunas Renomeadas" = Table.RenameColumns(#"Tipo Alterado",{{"fcoprod", "fcoprod_u"}})
in
    #"Colunas Renomeadas"
