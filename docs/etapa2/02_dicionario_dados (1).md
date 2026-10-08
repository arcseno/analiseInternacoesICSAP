# Dicionário de dados

O projeto tem duas bases tratadas: a de internações (uma linha por internação) e a analítica (uma linha por município e ano), que junta as internações com os dados do IBGE. As duas estão descritas abaixo.

## 1. `internacoes_icsap_pr.csv.gz`

662.730 linhas, uma por internação evitável de morador do PR, de jan/2022 a jul/2026. Separador `;`.

| Campo | Significado | Tipo | Domínio | Qualidade |
|---|---|---|---|---|
| `N_AIH` | Número da Autorização de Internação Hospitalar | Texto (13 dígitos) | Identificador único por internação | Completo, 0 repetidos |
| `MUNIC_RES` | Município de residência do paciente | Texto (6 dígitos) | Códigos dos 399 municípios do PR | Completo, 100% válidos |
| `DT_INTER` | Data da internação | Data (AAAAMMDD) | 01/01/2022 a 31/07/2026 | Completo, 0 inválidas. Jun e jul/2026 ainda incompletos |
| `DIAG_PRINC` | Diagnóstico principal | Texto (CID-10) | Códigos da Lista ICSAP (Portaria SAS/MS 221/2008) | Completo, 100% no formato CID |
| `grupo_icsap` | Grupo de causa ICSAP (coluna derivada) | Texto | 19 grupos da Portaria 221/2008 | Completo |
| `VAL_TOT` | Valor pago pelo SUS, somando as partes da AIH | Decimal (R$) | 0 ou mais | Completo, 2 com valor zero (sinalizados) |
| `DIAS_PERM` | Dias de permanência, somando as partes da AIH | Inteiro | 0 ou mais | Completo, 0 negativos, 20.528 com 0 dias (3,1%) e 662 acima de 58 dias (0,1%) |
| `flag_dias_zero` | Internação registrada com 0 dias | Booleano | True / False | Completo |
| `flag_dias_alto` | Internação acima do percentil 99,9 de dias (58 dias) | Booleano | True / False | Completo |
| `flag_valor_zero` | Internação com valor pago zero | Booleano | True / False | Completo |

## 2. `dataset_municipio_ano.csv`

1.995 linhas (399 municípios × 5 anos, de 2022 a 2026). Separador `;`. Gerado por `src/transformacao/montar_dataset.py`. As variáveis do IBGE que vêm do Censo 2022 são repetidas nos cinco anos de cada município.

| Campo | Significado | Tipo | Domínio | Qualidade |
|---|---|---|---|---|
| `cod_municipio_datasus` | Código do município no DATASUS | Texto (6 dígitos) | 399 municípios do PR | Completo |
| `cod_municipio_ibge` | Código do município no IBGE (6 dígitos + verificador) | Texto (7 dígitos) | 399 municípios do PR | Completo, os 6 primeiros dígitos sempre batem com o DATASUS |
| `nome_municipio` | Nome do município | Texto | Nomes da DTB/IBGE | Completo |
| `ano` | Ano da internação | Inteiro | 2022 a 2026 | Completo, chave município + ano sem repetição |
| `ano_parcial` | Indica ano incompleto | Booleano | True só para 2026 (jan a jul) | Completo |
| `internacoes_icsap` | Número de internações ICSAP de residentes do município no ano | Inteiro | 5 a 18.564 | Completo, soma igual às 662.730 linhas da base tratada |
| `populacao` | População residente | Decimal | 1.316 a 1.832.183 | Completo. 2023 é interpolado (ver `populacao_origem`) |
| `populacao_origem` | De onde veio a população daquele ano | Texto | `censo_2022`, `interpolada_geometrica_2022_2024`, `estimativa_ibge` | Completo |
| `taxa_icsap` | Internações ICSAP por 10 mil habitantes | Decimal | 7,3 a 1.248,9 | Completo. Em 2026 a taxa é parcial e não deve ser comparada com os outros anos |
| `proporcao_idosos` | Proporção da população com 60 anos ou mais (Censo 2022) | Decimal | 0 a 1 (observado: 0,087 a 0,269) | Completo, 0 fora do intervalo |
| `pct_agua_rede` | % de domicílios que usam a rede geral como fonte principal de água (Censo 2022) | Decimal (%) | 0 a 100 (observado: 31,0 a 98,5) | Completo, 0 fora do intervalo |
| `pct_agua_ligacao_rede` | % de domicílios com ligação à rede geral, mesmo usando outra fonte (Censo 2022) | Decimal (%) | 0 a 100 (observado: 34,1 a 100) | Completo, sempre maior ou igual a `pct_agua_rede` |
| `pct_esgoto_rede` | % de domicílios ligados à rede geral, pluvial ou fossa ligada à rede (Censo 2022) | Decimal (%) | 0 a 100 (observado: 0,1 a 97,8) | Completo, 0 fora do intervalo |
| `pct_esgoto_adequado` | % com rede ou fossa séptica não ligada à rede (Censo 2022) | Decimal (%) | 0 a 100 (observado: 0,4 a 99,1) | Completo, sempre maior ou igual a `pct_esgoto_rede` |
| `renda_domiciliar_media` | Rendimento domiciliar per capita médio (Censo 2022) | Decimal (R$) | Maior que 0 (observado: 893 a 3.138) | Completo, 0 negativos |
| `renda_domiciliar_mediana` | Rendimento domiciliar per capita mediano (Censo 2022) | Decimal (R$) | Maior que 0 (observado: 630 a 1.850) | Completo, mediana nunca acima da média |

Uma observação para a Etapa 3: `pct_agua_rede` e `pct_agua_ligacao_rede` têm correlação de 0,94 entre os municípios, então medem quase a mesma coisa. Para o BI dá para manter as duas, mas no modelo vale escolher uma delas para não ter variáveis redundantes.
