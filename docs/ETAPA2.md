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

| Coluna | O que é |
|---|---|
| `N_AIH` | Número da internação |
| `MUNIC_RES` | Município onde o paciente mora |
| `DT_INTER` | Data da internação |
| `DIAG_PRINC` | Diagnóstico (CID-10) |
| `VAL_TOT` | Valor pago pelo SUS |
| `DIAS_PERM` | Dias internado |
| `grupo_icsap` | Qual dos 19 grupos ICSAP |
| `flag_dias_zero` | Internação com 0 dias (entrou e saiu no mesmo dia) |
| `flag_dias_alto` | Internação acima do limite de dias (percentil 99,9) |
| `flag_valor_zero` | Internação com valor pago igual a zero |

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