# Relatório de qualidade dos dados

As verificações da base de internações estão em `notebooks/qualidade.ipynb`. As da base analítica são geradas automaticamente pelo `montar_dataset.py` toda vez que ele roda, e ficam em `docs/etapa2/evidencias_qualidade.md` e `.json`. Aqui estão os resultados reunidos por dimensão.

## Base de internações (`internacoes_icsap_pr.csv.gz`)

| Dimensão | Verificação | Resultado |
|---|---|---|
| Completude | Valores ausentes por coluna | 0% nas 10 colunas |
| Completude | Meses presentes na série | 55 de 55. Antes da complementação pelo FTP eram 48 de 55 |
| Unicidade | `N_AIH` repetidos | 0 depois do tratamento. Antes, 639 AIHs apareciam em 2.382 linhas |
| Validade | Datas de internação inválidas | 0, todas entre 01/01/2022 e 31/07/2026 |
| Validade | `DIAS_PERM` negativo | 0 |
| Validade | `DIAG_PRINC` fora do formato CID-10 | 0 |
| Validade | Valores suspeitos sinalizados | 20.528 com 0 dias (3,1%), 662 acima de 58 dias (0,1%), 2 com valor zero |
| Consistência | `MUNIC_RES` fora da tabela do IBGE | 0, e os 399 municípios do PR aparecem |
| Atualidade | Internações por mês | Média de 12.125 por mês em 2022–2025. Jun/2026 tem 10.662 e jul/2026 tem 7.017, abaixo do patamar, provavelmente porque o DATASUS ainda recebe AIHs desses meses |
| Acurácia | Comparação com o TABNET | Não realizada nesta etapa |

Observações do gráfico mensal: jan e fev/2026 voltaram ao patamar normal depois da complementação pelo FTP, o que confirma que o buraco era do espelho do PySUS. Jan e fev/2022 ficam abaixo do padrão, possivelmente ainda efeito da pandemia, e há um pico entre maio e julho todos os anos (sazonalidade), relevante para a Etapa 3.

## Base analítica (`dataset_municipio_ano.csv`)

| Dimensão | Verificação | Resultado |
|---|---|---|
| Completude | Linhas esperadas (399 municípios × 5 anos) | 1.995 de 1.995 |
| Completude | Valores ausentes por coluna | 0% nas 16 colunas |
| Completude | Municípios do PR ausentes em cada tabela do IBGE | 0 nas cinco tabelas |
| Completude | Combinações município × ano sem internação, preenchidas com zero | 0 |
| Unicidade | Chave município + ano repetida | 0 |
| Validade | População zero ou negativa | 0 |
| Validade | `proporcao_idosos` fora de 0 a 1 | 0 |
| Validade | Percentuais de água e esgoto fora de 0 a 100 | 0 |
| Validade | Renda negativa | 0 |
| Consistência | Soma de `internacoes_icsap` contra a base tratada | 662.730 nos dois, confere |
| Consistência | Categoria-pai diferente da soma dos detalhamentos (tabelas 6803 e 6805) | 0 |
| Consistência | Total de domicílios da 6803 diferente da 6805 | 0 municípios |
| Consistência | % de esgoto adequado menor que % de rede, ou % com ligação de água menor que % rede principal | 0 |
| Consistência | Renda mediana maior que a média | 0 municípios |
| Plausibilidade | População 2024 entre 85% e 125% do Censo 2022 | Todos os 399 dentro da faixa |
| Atualidade | Defasagem das variáveis do Censo | Água, esgoto, renda e idosos são de 2022 e repetidos até 2026 |
| Atualidade | População de 2023 | Sem estimativa oficial, 399 linhas interpoladas |

A taxa ICSAP de 2022 a 2025 tem média de 166,8 por 10 mil habitantes e mediana de 143,7, variando de 19,2 a 1.248,9. Só uma combinação município × ano desse período tem menos de 10 internações, mas taxas de municípios muito pequenos continuam instáveis, porque poucas internações a mais mudam bastante o valor.

## Limitações que continuam

A acurácia não foi medida. O próximo passo seria comparar o total anual de alguns municípios com o TABNET do DATASUS. Os meses de jun e jul/2026 ainda vão mudar, e 2026 não entra nas comparações anuais. As variáveis do Censo 2022 assumem que saneamento, renda e estrutura etária não mudaram até 2026.
