# Registro das transformações

Todas as transformações estão em código e podem ser refeitas por qualquer pessoa: `src/extracao/dataSus.py` gera a base de internações e `src/transformacao/montar_dataset.py` gera a base analítica. Rodamos o pipeline duas vezes e chegamos exatamente nos mesmos números.

## Fluxo de registros (internações)

| Etapa | Registros |
|---|---|
| Linhas baixadas (55 meses) | 4.615.785 |
| Depois do filtro de residentes no PR e período | 4.496.129 |
| Internações ICSAP | 664.473 |
| Depois da deduplicação | 662.730 |
| Soma no dataset município × ano | 662.730 |

## Base de internações (`dataSus.py`)

| Dado original | Problema identificado | Transformação | Justificativa |
|---|---|---|---|
| Espelho do PySUS (48 arquivos) | 7 meses ausentes (48 de 55) | Complementação pelo FTP oficial do DATASUS | Completude, os meses existem na fonte oficial (conferido com `checarFTP.py` em 06/10/2026) |
| Arquivos SIH (~100 colunas) | Colunas desnecessárias, algumas sensíveis (idade, sexo, CEP) | Seleção de 6 colunas, mais competência para deduplicar | Minimização de dados |
| Todas as internações em hospitais do PR | Moradores de outros estados e datas fora do recorte | Filtro por `MUNIC_RES` do PR e internação de 2022 a 2026 | Escopo do projeto, evitando os anos de pandemia |
| `DIAG_PRINC` | Não indica se a internação é evitável | Classificação pela Lista ICSAP (Portaria 221/2008), com A16.1 incluído | Critério oficial, reproduzível e comparável |
| `DIAS_PERM`, `VAL_TOT` | Vêm como texto, com vírgula decimal | Conversão para número | Permitir cálculos |
| AIHs repetidas (639) | Internação longa cobrada mês a mês, uma linha por competência | Soma de dias e valores por AIH e remoção de 6 repetições exatas | Manter só a linha com mais dias descartava R$ 3,2 mi dos R$ 4,7 mi dessas internações |
| `DT_INTER` | Parte das datas vem como AAAA-MM-DD e parte como AAAAMMDD | Remoção do hífen, tudo em AAAAMMDD | Consistência |
| `DIAS_PERM`, `VAL_TOT` | Zeros e valores extremos | Flags, sem apagar | Apagar seria irreversível, cada análise decide como usar |

## Base analítica (`montar_dataset.py`)

| Dado original | Problema identificado | Transformação | Justificativa |
|---|---|---|---|
| Tabela de municípios do IBGE | DATASUS usa 6 dígitos e IBGE usa 7 | Código de 6 dígitos derivado tirando o dígito verificador, com teste de que bate em todos os 399 | Permitir o join sem perder municípios |
| CSVs do SIDRA | Cabeçalho em várias linhas, codificação variável (UTF-8 ou Latin-1) e algumas tabelas só com nome de município | Leitor próprio do layout do SIDRA, e ligação por nome normalizado (sem acento, sem "(PR)") quando não há código | O script para com erro se algum nome não encontrar par, então nenhum município fica de fora sem aviso |
| Símbolos do SIDRA | `-` é zero absoluto e `X`, `..`, `...` são valores omitidos | `-` vira 0, os demais viram ausente | Seguir a legenda do IBGE sem inventar valor |
| Tabela 9514 | Não tem coluna de total | População = soma das 21 faixas etárias, e `proporcao_idosos` = faixas de 60 anos ou mais sobre o total | O script confere se todas as faixas estão presentes |
| Tabela 6579 | Não existe estimativa oficial de 2023 | População de 2023 interpolada pela média geométrica de 2022 e 2024 | Crescimento populacional é multiplicativo. A origem fica marcada em `populacao_origem` |
| Tabela 6803 | Água vem em contagem de domicílios por categoria | Dois percentuais: rede como fonte principal e domicílios com ligação à rede | Separar quem tem acesso de quem de fato usa |
| Tabela 6805 | Esgoto vem em várias categorias, com subitens que se repetem | Percentual de rede e percentual adequado (rede + fossa séptica não ligada), sem somar os subitens duas vezes | Fossa séptica é considerada solução adequada, então o indicador de rede sozinho subestimaria o saneamento |
| Tabela 10295 | Rendimento aberto por sexo, cor e idade | Mantidos só os totais, média e mediana | Mediana reduz o efeito de rendas muito altas em municípios pequenos |
| Internações por município × ano | Combinação sem internação sumiria do join | Grade completa 399 × 5, com zero onde não houver internação | Não perder municípios (na prática, nenhum precisou) |
| Contagem absoluta | Municípios de tamanhos muito diferentes | `taxa_icsap` por 10 mil habitantes | Permitir comparação entre municípios |
| Ano de 2026 | Só vai até julho | Flag `ano_parcial` | Evitar comparar 2026 com anos completos |
