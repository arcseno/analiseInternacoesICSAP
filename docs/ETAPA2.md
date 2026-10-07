### Documentando por aqui algumas coisas importantes para a entrega da etapa 2.

#### internacoes_icsap_pr.csv.gz é o nosso dataset já tratado.

Fizemos transformações documentáveis nesse dataset, por meio de um script em dataSus.py que gera o arquivo (qualquer pessoa pode rodar e chegar no mesmo resultado), e o registro das transformações.

Explicando melhor o que dataSus.py faz no dado original:

1. Junta os 48 meses do espelho com os 7 meses do FTP do DATASUS (completude).
2. Ficamos só com 6 das ~100 colunas (minimização).
3. Mantivemos só moradores do PR, de 2022 a 2026
4. Classificamos cada internação num grupo ICSAP, criando a coluna grupo_icsap e descartamos o que não era ICSAP.
5. Transformamos dias e valores em números.
6. Juntamos as partes de AIHs cobradas mês a mês, somando dias e valores, e removemos repetições exatas (unicidade).
7. Padronizamos os formatos das datas.
8. Sinalizamos alguns valores suspeitos (dias zerados, dias muito altos, valor zero) com colunas de flag, sem apagar nenhum registro.

O arquivo traz 662.730 linhas, cada uma com uma internação evitável de um morador do PR, entre jan/2022 e jul/2026. São 10 colunas:

#### Dicionário de dados

| Campo | Significado | Tipo | Domínio | Qualidade |
|---|---|---|---|---|
| `N_AIH` | Número da Autorização de Internação Hospitalar | Texto (13 dígitos) | Identificador único por internação | Completo, 0 repetidos |
| `MUNIC_RES` | Município de residência do paciente | Texto (6 dígitos) | Códigos IBGE dos 399 municípios do PR | Completo, 100% válidos |
| `DT_INTER` | Data da internação | Data (AAAAMMDD) | 01/01/2022 a 31/07/2026 | Completo, 0 inválidas, mas com jun e jul/2026 provisórios |
| `DIAG_PRINC` | Diagnóstico principal | Texto (CID-10) | Códigos da Lista ICSAP (Portaria 221/2008) | Completo, 100% no formato CID |
| `grupo_icsap` | Grupo de causa ICSAP | Texto | 19 grupos da Portaria 221/2008 | Completo |
| `VAL_TOT` | Valor pago pelo SUS (soma das partes da AIH) | Decimal (R$) | 0 ou mais | Completo, 2 com valor zero (sinalizados) |
| `DIAS_PERM` | Dias internado (soma das partes da AIH) | Inteiro | 0 ou mais | Completo, 0 negativos mas temos 20.528 com 0 dias (3,1%) e 662 acima de 58 dias (0,1%) |
| `flag_dias_zero` | Internação com 0 dias | Booleano | True / False | Completo |
| `flag_dias_alto` | Internação acima do percentil 99,9 de dias | Booleano | True / False | Completo |
| `flag_valor_zero` | Internação com valor pago zero | Booleano | True / False | Completo |

#### Números de cada etapa

| Etapa | Registros |
|---|---|
| Linhas baixadas (55 meses) | 4.615.785 |
| Depois do filtro de PR e período | 4.496.129 |
| Internações ICSAP | 664.473 |
| Depois da deduplicação | 662.730 |

Rodamos o pipeline duas vezes e chegamos exatamente nos mesmos números.

#### Decisões e justificativas

- **Fonte:** o PySUS (versão 2.11.6) lê, por padrão, um espelho próprio, e não o FTP do DATASUS como previsto na Etapa 1. O espelho tinha 48 dos 55 meses esperados. Conferimos com o `checarFTP.py`, em 06/10/2026, que os 7 meses ausentes existem no FTP oficial, e completamos a partir dele.
- **Lista ICSAP:** conferimos código por código com a Portaria SAS/MS nº 221/2008 e incluímos o A16.1, que estava faltando no grupo 01.
- **Período:** o recorte 2022–2026 também evita os anos de 2020 e 2021, afetados pela pandemia. 2026 está incompleto (até julho) e não entra nas comparações anuais.
- **Valores suspeitos:** sinalizamos em vez de apagar, porque apagar não é reversível. Com a marcação, cada análise decide o que fazer. O limite de dias muito altos é o percentil 99,9 de `DIAS_PERM`, recalculado automaticamente a cada execução (hoje, 58 dias), só 0,1% das internações ficam acima disso.
- **Deduplicação:** 639 AIHs apareciam em mais de uma linha (2.382 linhas no total). Investigando com o `checarDuplicatas.py`, vimos que todas tinham a mesma data de internação e que, em 637 delas, cada linha tinha um valor diferente. São internações longas, cobradas mês a mês, com uma linha por competência. A regra original (manter só a linha com mais dias) reduzia, por exemplo, uma internação de 90 dias a 31 e descartava R$ 3,2 milhões dos R$ 4,7 milhões pagos nessas internações. Passamos a remover só as repetições exatas (mesma AIH, competência `ANO_CMPT`/`MES_CMPT`, dias e valor), que foram apenas 6 linhas, e a somar dias e valores das partes de cada AIH. Sem considerar a competência, 112 linhas pareciam idênticas, mas 106 delas eram partes diferentes da mesma internação (por exemplo, dois meses de 31 dias com a mesma diária). Uma unica limitação é que duas partes diferentes com a mesma competência, os mesmos dias e o mesmo valor ainda seriam tratadas como repetição.

#### Registro das transformações

| Dado original | Problema identificado | Transformação | Justificativa |
|---|---|---|---|
| Espelho PySUS (48 arquivos) | 7 meses ausentes (48 de 55) | Complementação pelo FTP do DATASUS | Para completude dos dados, já que os meses existem na fonte oficial |
| Arquivos SIH (~100 colunas) | Colunas desnecessárias, algumas sensíveis | Seleção de 6 colunas | Minimização de dados |
| Todas as internações do PR | Moradores de outros estados e fora do período | Filtro: MUNIC_RES do PR, 2022 a 2026 | Escopo do projeto |
| `DIAG_PRINC` | Não indica se a internação é evitável | Classificação pela Lista ICSAP (Portaria 221/2008), com A16.1 incluído | Critério oficial, reproduzível e comparável |
| `DIAS_PERM`, `VAL_TOT` | Vêm como texto, com vírgula decimal | Conversão para número | Permitir cálculos |
| AIHs repetidas (639) | Internação longa cobrada mês a mês | Soma de dias e valores por AIH, com remoção de 6 repetições exatas | Regra anterior descartava R$ 3,2 mi |
| `DIAS_PERM`, `VAL_TOT` | Zeros e valores extremos | Flags, sem apagar | Apagar seria irreversível, cada análise decide como usar |

#### Qualidade dos dados

Os testes estão em `notebooks/qualidade.ipynb`.

| Dimensão | Verificação | Resultado |
|---|---|---|
| Completude | Valores ausentes por coluna | 0% em todas as 10 colunas |
| Completude | Meses na série | 55 de 55 (antes da complementação pelo FTP, 48 de 55) |
| Unicidade | `N_AIH` repetidos | 0 |
| Validade | Datas inválidas | 0, de 01/01/2022 a 31/07/2026 |
| Validade | `DIAS_PERM` negativo | 0 |
| Validade | CID fora do formato | 0 |
| Validade | Valores sinalizados | 20.528 com 0 dias (3,1%), 662 acima de 58 dias (0,1%), 2 com valor zero |
| Consistência | `MUNIC_RES` fora da tabela do IBGE | 0, com os 399 municípios do PR presentes |
| Atualidade | Internações por mês | Jun e jul/2026 bem abaixo do patamar, provavelmente dado ainda sendo processado pelo DATASUS |
| Acurácia | Comparação com o TABNET | Não realizada nesta etapa |

Observações do gráfico mensal:
- Jan e fev/2026 voltaram ao patamar normal depois da complementação pelo FTP. Isso confirma que o buraco era do espelho do PySUS.
- Jan e fev/2022 estão abaixo do padrão. Pode ser efeito ainda da pandemia, mas fica como ponto a investigar.
- Há um pico entre maio e julho todos os anos (sazonalidade), relevante para a Etapa 3.

#### Privacidade e ética

As análises estão em `notebooks/privacidade.ipynb`, que mostra só contagens, nunca linhas individuais.

- **Dados pessoais:** a base não tem nome, CPF nem endereço, mas o `N_AIH` é único em todas as linhas e identifica a internação.
- **Dados sensíveis:** o diagnóstico (CID) é dado de saúde, tratado pela LGPD como dado pessoal sensível.
- **Minimização:** das ~100 colunas do SIH, ficamos com 6. Idade, sexo e CEP ficaram de fora.
- **Reidentificação:** 74,2% das internações (491.608) são únicas na combinação município + data + CID. Quem sabe que alguém foi internado num certo dia, numa certa cidade, consegue achar o registro.
- **Células pequenas:** 12.247 das 29.669 combinações de município x ano x grupo (41%) têm menos de 5 casos.
- **Grupos sub-representados:** 4 municípios têm menos de 100 internações no período (o menor tem 62). Nesses, a taxa é instável.
- **Vieses:** só entram internações pagas pelo SUS, então município com muito plano privado parece ter menos ICSAP. Também só entram moradores do PR internados em hospital do PR, e o CID depende do preenchimento de cada hospital.
- **Limitações de uso:** a análise é por município e não serve pra avaliar paciente, médico ou hospital individualmente.

Decisões:
1. O CSV registro a registro não é publicado, e o repositório fica privado enquanto ele estiver no histórico.
2. O que for publicado (painel, tabelas, apresentação) é só agregado, com células com menos de 5 casos suprimidas.
3. Em municípios pequenos, as comparações agregam anos ou regiões, ou sinalizam que a taxa é instável.

Esses dados já são públicos no DATASUS. O risco não é vazar algo secreto, e sim facilitar o acesso e o cruzamento, por isso as decisões tratam do que publicamos.